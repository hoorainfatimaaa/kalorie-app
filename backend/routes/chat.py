from flask import Blueprint, request, jsonify, Response, stream_with_context, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.meal import Meal,UserMealContext
from database.db import db
import traceback
from models.chat_message import ChatMessage
import os
import uuid
from werkzeug.utils import secure_filename
from models.user import User
from models.diet_plan import DietPlan
from models.temp_diet_plan import TempDietPlan
from models.conversation_summary import ConversationSummary
from models.user_memory import UserMemory
from services.openai_service import (ask_openai, ask_openai_stream, STREAM_RESET, MEAL_INTENTS, transcribe, generate_audio,extract_display_text, summarize_conversation)
from services.embedding_service import embed_text, memory_embedding_text
from services.nutrition_service import calculate_calorie_goal, calculate_macro_goals
from sqlalchemy import func
from datetime import date, datetime, timedelta
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor

chat = Blueprint("chat", __name__)

logger = logging.getLogger(__name__)

CHAT_HISTORY_LIMIT = int(os.getenv("SHORT_TERM_HISTORY_LIMIT", "10"))

_PREFETCH = ThreadPoolExecutor(max_workers=4, thread_name_prefix="prefetch")

_SUMMARY_INFLIGHT = set()


def _schedule_summary_refresh(app, user_id):
    """Fold newly-aged messages into the rolling summary off the request path."""

    if user_id in _SUMMARY_INFLIGHT:
        return

    _SUMMARY_INFLIGHT.add(user_id)

    def work():
        try:
            with app.app_context():
                get_conversation_summary(user_id)
        except Exception:
            logger.exception("Background conversation-summary refresh failed")
        finally:
            _SUMMARY_INFLIGHT.discard(user_id)

    _PREFETCH.submit(work)


def normalize_intent(ai_reply):
    """
    The system prompt teaches the model two overlapping names for the
    same thing  "meal_history" (section 4, general "user asks about
    previous meals") and "show_meal_history" (the display-intent used
    for explicit "show my meal history" commands). Only the latter is
    wired to build_meal_history_data()/the frontend card, so a
    "meal_history"-classified reply (e.g. "when did I have pizza?",
    "what did I eat yesterday?") would otherwise fall through as a
    plain, uncarded AI paragraph. Collapse them to one name here so
    every meal-history question gets the same structured card.
    """
    if isinstance(ai_reply, dict) and ai_reply.get("intent") == "meal_history":
        ai_reply["intent"] = "show_meal_history"
    return ai_reply


def get_recent_chat_history(user_id, limit=CHAT_HISTORY_LIMIT):
    """
    Most recent `limit` messages for this user, in chronological order.
    Full unbounded history was being sent to the model on every request,
    which both wastes tokens and dilutes intent-classification accuracy
    as a user's chat grows.
    """
    recent = (
        ChatMessage.query
        .filter_by(user_id=user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(recent))


def get_conversation_summary(user_id, defer=False):
    """
    Rolling summary of everything OLDER than the short-term window
    (CHAT_HISTORY_LIMIT) get_recent_chat_history returns  so context
    from earlier in a long conversation isn't just dropped once it
    ages out of the recent-messages window sent to the model.

    Only calls the summarizer when there's genuinely new older content
    to fold in (tracked via ConversationSummary.summarized_message_count),
    so this stays a rare, bounded-cost call as the conversation grows,
    not a per-request one. Returns "" when the whole conversation still
    fits inside the short-term window  nothing to summarize yet.
    """
    total = ChatMessage.query.filter_by(user_id=user_id).count()

    if total <= CHAT_HISTORY_LIMIT:
        return ""

    record = ConversationSummary.query.filter_by(user_id=user_id).first()
    previous_summary = record.summary if record else ""
    already_summarized = record.summarized_message_count if record else 0

    to_summarize_count = total - CHAT_HISTORY_LIMIT

    if to_summarize_count <= already_summarized:
        return previous_summary

    if defer:
    
        _schedule_summary_refresh(current_app._get_current_object(), user_id)
        return previous_summary

    delta_messages = (
        ChatMessage.query
        .filter_by(user_id=user_id)
        .order_by(ChatMessage.created_at.asc())
        .offset(already_summarized)
        .limit(to_summarize_count - already_summarized)
        .all()
    )

    lightweight = [
        {"sender": m.sender, "text": extract_display_text(m)}
        for m in delta_messages
    ]

    updated_summary = summarize_conversation(previous_summary, lightweight)

    if record:
        record.summary = updated_summary
        record.summarized_message_count = to_summarize_count
    else:
        record = ConversationSummary(
            user_id=user_id,
            summary=updated_summary,
            summarized_message_count=to_summarize_count
        )
        db.session.add(record)

    db.session.commit()

    return updated_summary


LONG_TERM_MEMORY_LIMIT = int(os.getenv("LONG_TERM_MEMORY_LIMIT", "20"))


MEMORY_SIMILARITY_THRESHOLD = float(
    os.getenv("MEMORY_SIMILARITY_THRESHOLD", "0.25")
)


MEMORY_RELEVANCE_WEIGHT = 0.70
MEMORY_IMPORTANCE_WEIGHT = 0.25
MEMORY_RECENCY_WEIGHT = 0.05


MEMORY_RECENCY_WINDOW_DAYS = 180.0


def _memories_by_importance(user_id, limit, only_unembedded=False):
    query = UserMemory.query.filter_by(user_id=user_id)

    if only_unembedded:
        query = query.filter(UserMemory.embedding.is_(None))

    return (
        query
        .order_by(UserMemory.importance.desc(), UserMemory.updated_at.desc())
        .limit(limit)
        .all()
    )


def _memory_rank_score(relevance, memory, now):
    importance = max(1, min(5, memory.importance or 3))
    normalized_importance = (importance - 1) / 4.0

    updated_at = memory.updated_at or memory.created_at or now
    age_days = max(0.0, (now - updated_at).total_seconds() / 86400.0)
    recency = max(0.0, 1.0 - age_days / MEMORY_RECENCY_WINDOW_DAYS)

    return (
        relevance * MEMORY_RELEVANCE_WEIGHT
        + normalized_importance * MEMORY_IMPORTANCE_WEIGHT
        + recency * MEMORY_RECENCY_WEIGHT
    )


def _normalize_similarities(similarities):
    lowest, highest = min(similarities), max(similarities)
    span = highest - lowest

    if span < 1e-9:
        return [1.0 for _ in similarities]

    return [(value - lowest) / span for value in similarities]


def get_long_term_memories(user_id, query=None, limit=LONG_TERM_MEMORY_LIMIT,
                           query_embedding=None):
    if not query or not query.strip():
        return _memories_by_importance(user_id, limit)

    if query_embedding is None:
        query_embedding = embed_text(query)

    if query_embedding is None:
        logger.warning(
            "Long-term memory: query embedding unavailable, "
            "falling back to importance/recency retrieval."
        )
        return _memories_by_importance(user_id, limit)

    candidate_limit = max(limit * 3, 30)

    try:
        distance = UserMemory.embedding.cosine_distance(
            query_embedding
        ).label("distance")

        candidates = (
            db.session.query(UserMemory, distance)
          
            .filter(UserMemory.user_id == user_id)
            .filter(UserMemory.embedding.isnot(None))
            .order_by(distance)
            .limit(candidate_limit)
            .all()
        )
    except Exception as exc:
        db.session.rollback()
        logger.warning(
            "Long-term memory: vector search failed (%s: %s), "
            "falling back to importance/recency retrieval.",
            type(exc).__name__, exc
        )
        return _memories_by_importance(user_id, limit)

    if not candidates:
    
        return _memories_by_importance(user_id, limit)

    relevant = [
        (memory, 1.0 - float(distance_value))
        for memory, distance_value in candidates
        if (1.0 - float(distance_value)) >= MEMORY_SIMILARITY_THRESHOLD
    ]

    selected = []

    if relevant:
        now = datetime.utcnow()
        relevance_scores = _normalize_similarities([sim for _, sim in relevant])

        scored = [
            (_memory_rank_score(relevance, memory, now), memory)
            for (memory, _), relevance in zip(relevant, relevance_scores)
        ]

        scored.sort(key=lambda pair: pair[0], reverse=True)
        selected = [memory for _, memory in scored[:limit]]

    remaining = limit - len(selected)

    if remaining > 0:
        unembedded = _memories_by_importance(
            user_id, remaining, only_unembedded=True
        )
        if unembedded:
            logger.info(
                "Long-term memory: %d memor%s for user %s still lack "
                "embeddings; run scripts/setup_memory_embeddings.py.",
                len(unembedded), "y" if len(unembedded) == 1 else "ies", user_id
            )
        selected.extend(unembedded)

    return selected


VALID_MEMORY_ACTIONS = {"upsert", "delete"}


def apply_memory_update(ai_reply, user_id):
    """
    If the AI attached a "memory" operation to its reply (see
    LONG-TERM MEMORY in the system prompt), apply it to UserMemory.
    Silent/backend-only never touches ai_reply["reply"], so this
    never changes what the user sees, same "trust but verify" pattern
    as apply_profile_update: the AI proposes, the backend validates
    the shape before touching the database.

    Runs regardless of which intent the message classified as, since
    a lasting preference can be mentioned alongside any kind of
    message (a meal_log, a question, casual conversation).
    """
    if not isinstance(ai_reply, dict):
        return

    memory_op = ai_reply.get("memory")
    if not isinstance(memory_op, dict):
        return

    action = memory_op.get("action")
    memory_type = (memory_op.get("memory_type") or "").strip().lower()
    memory_key = (memory_op.get("memory_key") or "").strip().lower()

    if action not in VALID_MEMORY_ACTIONS or not memory_type or not memory_key:
        return

    existing = UserMemory.query.filter_by(
        user_id=user_id, memory_type=memory_type, memory_key=memory_key
    ).first()

    if action == "delete":
        if existing:
            db.session.delete(existing)
            db.session.commit()
        return

    memory_value = (memory_op.get("memory_value") or "").strip()
    if not memory_value:
        return

    try:
        importance = max(1, min(5, int(memory_op.get("importance"))))
    except (TypeError, ValueError):
        importance = 3

    if existing:
        previous_embedding_text = memory_embedding_text(
            existing.memory_type, existing.memory_key, existing.memory_value
        )
        existing.memory_value = memory_value
        existing.importance = importance
        record = existing
    else:
        previous_embedding_text = None
        record = UserMemory(
            user_id=user_id,
            memory_type=memory_type,
            memory_key=memory_key,
            memory_value=memory_value,
            importance=importance
        )
        db.session.add(record)

   
    db.session.commit()

    refresh_memory_embedding(record, previous_embedding_text)


def refresh_memory_embedding(record, previous_embedding_text=None):
    current_embedding_text = memory_embedding_text(
        record.memory_type, record.memory_key, record.memory_value
    )

    if previous_embedding_text == current_embedding_text:
        has_embedding = db.session.query(
            UserMemory.embedding.isnot(None)
        ).filter(UserMemory.id == record.id).scalar()

        if has_embedding:
            return

    vector = embed_text(current_embedding_text)

    if vector is None:
        logger.warning(
            "Long-term memory %s (%s/%s) saved without an embedding; "
            "run scripts/setup_memory_embeddings.py to backfill it.",
            record.id, record.memory_type, record.memory_key
        )
        return

    try:
      
        db.session.query(UserMemory).filter(
            UserMemory.id == record.id
        ).update({"embedding": vector}, synchronize_session=False)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.warning(
            "Long-term memory %s: could not store embedding (%s: %s).",
            record.id, type(exc).__name__, exc
        )


def clean_text(value):
    if isinstance(value, str):
        return value.replace("\x00", "")
    return value
today = date.today()


DISPLAY_INTENTS = {
    "show_profile",
    "show_progress",
    "calorie_status",
    "show_meal_history",
    "show_weekly_plan",
    "show_memories",
}

NUTRITION_INTENTS = {
    "nutrition_question",
    "general_chat",
}


def user_has_complete_profile(user):
    """calculate_bmr/calculate_tdee need these fields; bail out safely if any are missing."""
    return all([
        user is not None,
        user.age is not None,
        user.height is not None,
        user.weight is not None,
        user.gender is not None,
        user.fitness_goal is not None,
    ])


def get_today_totals(user_id):
    """Sum calories/protein/carbs/fat for this user's meals logged today."""
    result = db.session.query(
        func.coalesce(func.sum(Meal.calories), 0),
        func.coalesce(func.sum(Meal.protein), 0),
        func.coalesce(func.sum(Meal.carbs), 0),
        func.coalesce(func.sum(Meal.fat), 0),
    ).filter(
        Meal.user_id == user_id,
        func.date(Meal.created_at) == date.today()
    ).first()

    return {
        "calories": result[0] or 0,
        "protein": result[1] or 0,
        "carbs": result[2] or 0,
        "fat": result[3] or 0,
    }

def activity_suggestion_for_overage(calorie_over):
    if calorie_over <= 150:
        return "A short 10-15 minute walk can help offset this  nothing more is really needed."

    if calorie_over <= 350:
        return "A brisk 20-30 minute walk (or similarly light activity) can help balance this out."

    if calorie_over <= 600:
        return (
            "About 30 minutes of moderate cardio  a jog, cycling, or a fast-paced walk  "
            "would roughly offset this if you'd like to be active today."
        )

    return (
        "This is a bigger gap for one day. Roughly 30-45 minutes of moderate cardio would "
        "help offset it, but one day won't meaningfully affect your progress , there's no "
        "need to overcompensate. Staying consistent with your normal routine tomorrow "
        "matters more than making up for today."
    )


LOWER_FOOD_SUGGESTIONS = {
    "calories": "something lighter and lower-calorie  grilled chicken with vegetables, a salad, or a broth-based soup",
    "protein": "something with less protein and more carbs or vegetables  a vegetable stir-fry or a fruit bowl",
    "carbs": "something lower-carb  grilled protein with leafy greens or non-starchy vegetables",
    "fat": "something lower-fat  grilled or baked lean protein, steamed vegetables, or a light salad with minimal dressing",
}


def build_meal_guidance(user, user_id):
    """
    Deterministic, backend-computed guidance run after a meal is logged
    or updated. Never invents numbers  reuses the exact same
    calculate_calorie_goal()/calculate_macro_goals()/get_today_totals()
    used everywhere else, so it can never disagree with what the rest
    of the app shows.

    Fires whenever EITHER calories OR any individual macro is over its
    target  these are independent checks, not gated on each other, so
    a macro can be called out even on a day that's still under the
    calorie goal (e.g. fat already over target while calories are
    fine). Only ever warns when OVER  under/on-target is never called
    out. Returns None when nothing is exceeded, or the profile is
    incomplete.

    Returns {"text": ..., "exceeded": [ {label, unit, consumed, goal,
    over_by}, ... ]} "exceeded" lists every target that was crossed
    (calories first if applicable, then macros), for the frontend's
    immediate popup. Kept structured rather than parsed back out of
    the text.
    """
    if not user_has_complete_profile(user):
        return None

    calorie_goal = calculate_calorie_goal(user)
    macros = calculate_macro_goals(user)
    totals = get_today_totals(user_id)

    calorie_over = totals["calories"] - calorie_goal
    calorie_exceeded = calorie_over > 0

    macro_overages = {}
    for key, goal_key in [("protein", "protein_goal"), ("carbs", "carbs_goal"), ("fat", "fat_goal")]:
        goal = macros[goal_key]
        consumed = totals[key]
        if goal and consumed > goal:
            macro_overages[key] = {
                "consumed": round(consumed),
                "goal": round(goal),
                "over_by": round(consumed - goal),
            }

    if not calorie_exceeded and not macro_overages:
        return None

    exceeded = []

    if calorie_exceeded:
        exceeded.append({
            "label": "Calories",
            "unit": "kcal",
            "consumed": round(totals["calories"]),
            "goal": calorie_goal,
            "over_by": round(calorie_over),
        })
    for key in ("protein", "carbs", "fat"):
        if key not in macro_overages:
            continue

        m = macro_overages[key]
        exceeded.append({
            "label": key.capitalize(),
            "unit": "g",
            "consumed": m["consumed"],
            "goal": m["goal"],
            "over_by": m["over_by"],
        })


    over_summary = ", ".join(f"{item['label']} +{item['over_by']}{item['unit']}" for item in exceeded)
    lines = [f"⚠️ Over target today: {over_summary}."]

    if calorie_exceeded:
        lines.append(activity_suggestion_for_overage(calorie_over))
        lines.append(f"Try {LOWER_FOOD_SUGGESTIONS['calories']} for your remaining meals today.")
    else:
        first_macro = next(iter(macro_overages))
        lines.append(f"Try {LOWER_FOOD_SUGGESTIONS[first_macro]} for your remaining meals today.")

    today_name = date.today().strftime("%A")
    planned_today = DietPlan.query.filter_by(user_id=user_id, day=today_name).count()

    if planned_today:
        logged_today = Meal.query.filter(
            Meal.user_id == user_id,
            func.date(Meal.created_at) == date.today()
        ).count()
        remaining = max(planned_today - logged_today, 0)

        if remaining > 0:
            lines.append(f"{remaining} meal(s) left today  keep them light.")

    return {
        "text": "\n\n".join(lines),
        "exceeded": exceeded,
    }


VALID_CONFLICT_TYPES = {"allergy", "dietary_preference", "medical_condition"}


def attach_conflict_alert(ai_reply):
    """
    The AI itself flags food-vs-profile conflicts (allergy, dietary
    preference, medical condition) on meal_log/meal_update, since only
    it has the food knowledge to know e.g. a cheeseburger contains beef
    or pork. This just validates the shape before surfacing it to the
    frontend as a popup same "trust but verify" pattern used for
    profile field updates elsewhere in this file.
    """
    conflict = ai_reply.get("conflict") if isinstance(ai_reply, dict) else None

    if not isinstance(conflict, dict):
        return

    if conflict.get("type") not in VALID_CONFLICT_TYPES:
        return

    if not conflict.get("reason") or not conflict.get("guidance"):
        return

    ai_reply["conflict_alert"] = {
        "type": conflict["type"],
        "reason": conflict["reason"],
        "guidance": conflict["guidance"],
    }


MEAL_TYPE_PATTERN = re.compile(r"\b(breakfast|lunch|dinner|snack)\b", re.I)


def extract_meal_type_from_text(message):
    """Explicit-only meal-type detection never inferred from the clock (matches the same rule already enforced in the system prompt)."""
    if not message:
        return None
    m = MEAL_TYPE_PATTERN.search(message)
    return m.group(1).lower() if m else None


def build_meal_type_question(meal_name, calories):
    name = meal_name or "that meal"
    cal_part = f", about {round(calories)} kcal" if calories else ""
    return f"Got it — {name}{cal_part}. Was this breakfast, lunch, dinner, or snack?"


def find_pending_meal_log(chat_history):
    """
    If the most recent AI message was a meal_log left waiting on a
    meal_type answer, return its parsed JSON  it already carries the
    meal's name/nutrition/conflict_alert, so the answer to "which meal
    was this" can finalize it without re-running the AI. Only looks at
    the single most recent AI message, so an ignored question doesn't
    resurface later once the conversation has moved on.
    """
    if not chat_history:
        return None

    last = chat_history[-1]
    if last.sender != "ai":
        return None

    try:
        parsed = json.loads(last.message)
    except Exception:
        return None

    if isinstance(parsed, dict) and parsed.get("intent") == "meal_log" and parsed.get("pending_meal_type") is True:
        return parsed

    return None

PENDING_CONTEXT_HINTS = {
    "pending_diet_plan_cuisine": (
        "[Context: your previous message asked the user whether to "
        "base their weekly diet plan on their own country/region's "
        "cuisine or a different one. If the message below answers "
        "that question (names a cuisine, says no preference, "
        "declines, etc.), generate the full 7-day "
        "diet_plan_confirmation plan now using their answer do "
        "not ask again, and do not treat it as an unrelated "
        "nutrition question. If it's clearly about something else "
        "entirely, handle it normally instead.]"
    ),
    "pending_country_region_check": (
        "[Context: your previous message pointed out that the "
        "user's country and region don't seem to match, and asked "
        "which one they'd like to correct. If the message below "
        "answers that (confirms a country change, a region change, "
        "or both), apply it now as a normal update_profile, do "
        "not ask again. If it's clearly about something else "
        "entirely, handle it normally instead.]"
    ),
}


def find_pending_context_hint(chat_history):
    """
    If the most recent AI message set one of PENDING_CONTEXT_HINTS's
    flags, return its hint text. Only looks at the single most recent
    AI message, so an ignored question doesn't resurface once the
    conversation has moved on.
    """
    if not chat_history:
        return None

    last = chat_history[-1]
    if last.sender != "ai":
        return None

    try:
        parsed = json.loads(last.message)
    except Exception:
        return None

    if not isinstance(parsed, dict):
        return None

    for flag, hint in PENDING_CONTEXT_HINTS.items():
        if parsed.get(flag) is True:
            return hint

    return None


def with_pending_context(message, chat_history):
    """
    Prepends the relevant deterministic hint (see
    PENDING_CONTEXT_HINTS) when a clarifying question is pending, so
    the model reliably continues the right flow instead of
    reclassifying a short reply as an unrelated intent. Only affects
    what's sent to the AI, never what gets stored/shown as the user's
    actual message.
    """
    hint = find_pending_context_hint(chat_history)
    if not hint:
        return message

    return f"{hint}\n\nUser: {message}"


def finalize_pending_meal(pending, meal_type):
    """
    Builds a completed meal_log reply from a pending meal (recovered via find_pending_meal_log) plus the meal_type the user just gave.Reuses the pending entry's own nutrition numbers and conflict_alert
    rather than re-running the AI on a one-word answer like "lunch".
    """
    ai_reply = {
        "intent": "meal_log",
        "meal_name": pending.get("meal_name"),
        "meal_type": meal_type,
        "portion": pending.get("portion"),
        "is_estimated": pending.get("is_estimated", True),
        "calories": pending.get("calories"),
        "protein": pending.get("protein"),
        "carbs": pending.get("carbs"),
        "fat": pending.get("fat"),
        "reply": (
            "Meal Logged\n\n"
            f"Meal:\n{pending.get('meal_name')}\n\n"
            f"Meal Type:\n{meal_type.capitalize()}\n\n"
            "Nutrition:\n"
            f"- Calories: {pending.get('calories')}\n"
            f"- Protein: {pending.get('protein')}\n"
            f"- Carbs: {pending.get('carbs')}\n"
            f"- Fat: {pending.get('fat')}"
        ),
    }

    if pending.get("conflict_alert"):
        ai_reply["conflict_alert"] = pending["conflict_alert"]

    return ai_reply


PLAN_DEVIATION_THRESHOLD_KCAL = 100

WEEKDAY_ORDER = [
    "Monday", "Tuesday", "Wednesday", "Thursday","Friday", "Saturday", "Sunday",
]


def get_plan_for_weekday(user_id, weekday_name):
    """
    Saved DietPlan rows for one weekday, one entry per row (a day can have more than one row of the same meal_type, e.g. two snacks 
    those stay distinct so redistribution and display don't collapse them into a single blended slot).
    """
    rows = DietPlan.query.filter_by(user_id=user_id, day=weekday_name).all()

    return _plan_rows_to_entries(rows)


def _plan_rows_to_entries(rows):
    planned = []
    for row in rows:
        key = (row.meal_type or "").strip().lower()
        if not key:
            continue

        planned.append({
            "id": row.id,
            "meal_type": key,
            "meal_name": row.meal_name,
            "description": row.description,
            "calories": row.calories or 0,
            "protein": row.protein or 0,
            "carbs": row.carbs or 0,
            "fat": row.fat or 0,
        })

    return planned


def get_plan_for_all_weekdays(user_id):
    rows = DietPlan.query.filter(
        DietPlan.user_id == user_id,
        DietPlan.day.in_(WEEKDAY_ORDER)
    ).all()

    by_day = {}
    for row in rows:
        by_day.setdefault(row.day, []).append(row)

    return {
        day_name: entries
        for day_name, day_rows in by_day.items()
        for entries in [_plan_rows_to_entries(day_rows)]
        if entries
    }


def build_daily_reminder(user_id):
    """
    Timing-agnostic nudge shown once per app load when the user
    hasn't logged any meals yet today -- never asserts WHICH meal
    they're missing (breakfast/lunch/etc), since assuming someone's
    eating schedule from the clock is exactly what this app avoids
    everywhere else (see MEAL TYPE RULES in the system prompt: people
    eat on all kinds of schedules, a clock-based guess is often just
    wrong). Returns None once at least one meal is logged today.

    Also returns None for a user who has NEVER logged a meal at all
    (brand new signup) "you forgot today" only makes sense for
    someone who's actually used meal logging before and has a gap,
    not as the very first thing a new user sees.

    If a plan is saved, mentions today's planned meals for context
    only never phrased as "you're late" or tied to what time it is.
    """
    logged_today = Meal.query.filter(
        Meal.user_id == user_id,
        func.date(Meal.created_at) == date.today()
    ).count()

    if logged_today > 0:
        return None

    has_ever_logged = Meal.query.filter(Meal.user_id == user_id).first() is not None
    if not has_ever_logged:
        return None

    lines = ["You haven't logged any meals today yet."]

    today_name = date.today().strftime("%A")
    planned_rows = get_plan_for_weekday(user_id, today_name)

    if planned_rows:
        meal_list = ", ".join(
            f"{row['meal_type'].capitalize()} – {row['meal_name']}"
            for row in planned_rows
        )
        lines.append(f"Today's plan: {meal_list}.")

    lines.append("Want to log what you've had so far?")

    return "\n\n".join(lines)


def get_actual_by_meal_type_for_date(user_id, target_date):
    """
    Logged Meal rows for one calendar date, aggregated by meal_type.
    Meals with no meal_type (pre-migration rows) are excluded, not
    guessed. Keeps every individual meal_name logged for that slot
    (not just the totals) so a planned-vs-actual comparison can name
    what was actually eaten, not just show numbers.
    """
    rows = Meal.query.filter(
        Meal.user_id == user_id,
        func.date(Meal.created_at) == target_date
    ).all()

    return _aggregate_meals_by_type(rows)


def _aggregate_meals_by_type(rows):
    actual = {}
    for row in rows:
        key = (row.meal_type or "").strip().lower()
        if not key:
            continue

        slot = actual.setdefault(key, {"calories": 0, "protein": 0, "carbs": 0, "fat": 0, "meal_names": []})
        slot["calories"] += row.calories or 0
        slot["protein"] += row.protein or 0
        slot["carbs"] += row.carbs or 0
        slot["fat"] += row.fat or 0
        if row.meal_name:
            slot["meal_names"].append(row.meal_name)

    return actual


def get_actual_by_meal_type_for_range(user_id, start_date, end_date):
    rows = Meal.query.filter(
        Meal.user_id == user_id,
        func.date(Meal.created_at) >= start_date,
        func.date(Meal.created_at) <= end_date
    ).all()

    by_date = {}
    for row in rows:
        by_date.setdefault(row.created_at.date(), []).append(row)

    return {
        day: _aggregate_meals_by_type(day_rows)
        for day, day_rows in by_date.items()
    }


def get_today_actual_by_meal_type(user_id):
    return get_actual_by_meal_type_for_date(user_id, date.today())


def redistribute_variance(slots, variance, floor_ratio=0.6, floor_kcal=150):
    """
    Spreads a calorie variance (positive = over budget, needs reducing;
    negative = under budget, room to add) across `slots` proportionally to each slot's own planned calories, scaling protein/carbs/fat by
    the same ratio so macro balance is preserved. Reductions are floored (never below floor_ratio of the original or floor_kcal,
    whichever is higher) so no meal gets adjusted down to near-zero.

    Returns (adjusted_list, leftover) leftover is whatever a
    positive variance couldn't be absorbed by the floors (0 for a
    negative/under-budget variance, since increases are uncapped).
    """
    total_calories = sum(s["calories"] or 0 for s in slots)
    if total_calories <= 0:
        return [], variance

    adjusted = []
    total_change_applied = 0

    for s in slots:
        original_calories = s["calories"] or 0
        share = original_calories / total_calories
        target_change = variance * share
        candidate_calories = original_calories - target_change

        if variance > 0:
            min_allowed = max(original_calories * floor_ratio, floor_kcal)
            adjusted_calories = max(candidate_calories, min_allowed)
        else:
            adjusted_calories = candidate_calories

        ratio = (adjusted_calories / original_calories) if original_calories else 1
        total_change_applied += original_calories - adjusted_calories

        adjusted.append({
            **{k: v for k, v in s.items() if k not in ("calories", "protein", "carbs", "fat")},
            "original": {
                "calories": round(original_calories),
                "protein": round(s["protein"] or 0),
                "carbs": round(s["carbs"] or 0),
                "fat": round(s["fat"] or 0),
            },
            "adjusted": {
                "calories": round(adjusted_calories),
                "protein": round((s["protein"] or 0) * ratio),
                "carbs": round((s["carbs"] or 0) * ratio),
                "fat": round((s["fat"] or 0) * ratio),
            },
        })

    leftover = (variance - total_change_applied) if variance > 0 else 0
    return adjusted, leftover


def get_plan_anchor_day(user_id):
    """
    The weekday the current saved plan was confirmed DietPlan rows
    from the same save all land within the same request/commit, so
    the earliest created_at's weekday marks where its 7-day cycle
    starts. Returns None if there's no saved plan (or no timestamp,
    e.g. rows from before this column existed).
    """
    first_row = (
        DietPlan.query
        .filter_by(user_id=user_id)
        .order_by(DietPlan.created_at.asc())
        .first()
    )
    if not first_row or not first_row.created_at:
        return None
    return first_row.created_at.strftime("%A")


def remaining_days_this_cycle(today_name, anchor_name):
    """
    Days from tomorrow through the day before `anchor_name`, walking
    forward through the week and wrapping past Sunday back to Monday but never reaching `anchor_name` itself, since that's the start
    of the plan's next 7-day cycle (the same recurring template, not
    new data), not a day this overage should spill into. Falls back to
    "rest of the calendar week" if there's no known anchor.
    """
    if not anchor_name or anchor_name not in WEEKDAY_ORDER:
        today_index = WEEKDAY_ORDER.index(today_name)
        return WEEKDAY_ORDER[today_index + 1:]

    today_index = WEEKDAY_ORDER.index(today_name)
    anchor_index = WEEKDAY_ORDER.index(anchor_name)

    days = []
    i = (today_index + 1) % 7
    while i != anchor_index:
        days.append(WEEKDAY_ORDER[i])
        i = (i + 1) % 7
    return days


def compute_week_adjustment(user_id, leftover):
    """
    Redistributes `leftover` across the rest of the plan's current
    7-day cycle only  from tomorrow through the day before the plan
    was confirmed (see get_plan_anchor_day/remaining_days_this_cycle).
    E.g. a plan confirmed on Wednesday only ever rebalances through
    the following Tuesday, regardless of which day the overage happened on, never spilling into what's conceptually the next
    cycle of the same recurring template. Returns (days_list,
    remaining_leftover) days_list is None if there are no
    remaining days with a planned entry to adjust against.
    """
    today_name = date.today().strftime("%A")
    anchor_name = get_plan_anchor_day(user_id)
    remaining_days = remaining_days_this_cycle(today_name, anchor_name)

    day_slots = []
    for day_name in remaining_days:
        planned_rows = get_plan_for_weekday(user_id, day_name)
        for row in planned_rows:
            day_slots.append({**row, "day": day_name})

    if not day_slots:
        return None, leftover

    adjusted_slots, week_leftover = redistribute_variance(day_slots, leftover)

    days = {}
    for slot in adjusted_slots:
        day_name = slot["day"]
        days.setdefault(day_name, {"day": day_name, "meals": []})
        days[day_name]["meals"].append({
            "id": slot["id"],
            "meal_type": slot["meal_type"],
            "meal_name": slot["meal_name"],
            "original": slot["original"],
            "adjusted": slot["adjusted"],
        })

    ordered_days = [days[d] for d in remaining_days if d in days]
    return ordered_days, week_leftover


def evaluate_plan_adherence(user_id):
    """
    Deterministic plan-vs-actual comparison, run after a meal is saved
    with a resolved meal_type against a saved DietPlan. Never invents
    numbers -- everything here is either a stored DietPlan target or
    an actual logged Meal. Returns None when there's nothing planned
    for today (including when the user has no saved plan at all, or
    no plan entries for today's weekday) or today is still within
    PLAN_DEVIATION_THRESHOLD_KCAL of target.
    """
    today_name = date.today().strftime("%A")
    planned_rows = get_plan_for_weekday(user_id, today_name)
    if not planned_rows:
        return None

    actual = get_today_actual_by_meal_type(user_id)
    logged_types = set(actual.keys())
    planned_types = {row["meal_type"] for row in planned_rows}
    remaining_types = {mt for mt in planned_types if mt not in logged_types}

    planned_so_far = sum(
        row["calories"] for row in planned_rows if row["meal_type"] in logged_types
    )
    actual_total = get_today_totals(user_id)["calories"]
    so_far_variance = actual_total - planned_so_far

    if abs(so_far_variance) < PLAN_DEVIATION_THRESHOLD_KCAL:
        return None

    leftover = so_far_variance
    today_list = []

    if remaining_types:
        today_slots = [row for row in planned_rows if row["meal_type"] in remaining_types]
        today_list, leftover = redistribute_variance(today_slots, so_far_variance)

    week_list = None
    week_attempted = False
    if abs(leftover) >= PLAN_DEVIATION_THRESHOLD_KCAL:
        week_attempted = True
        week_list, _ = compute_week_adjustment(user_id, leftover)

    if not today_list and not week_list and not week_attempted:
        return None

    direction = "over" if so_far_variance > 0 else "under"
    amount = round(abs(so_far_variance))
    lines = [f"⚠️ You're about {amount} kcal {direction} plan so far today."]
    scope_parts = []

    if today_list:
        lines.append("I've adjusted your remaining meals today to help balance it out.")
        scope_parts.append("today")

    if week_list:
        lines.append(
            "There wasn't enough left today to fully balance it, so I've also "
            "adjusted the rest of this week's plan."
            if today_list else
            "I've adjusted the rest of this week's plan to help balance it out."
        )
        scope_parts.append("week")
    elif week_attempted:
        lines.append(
            "There are no more planned days left this week to rebalance against  "
            "try to get back on track with tomorrow's plan."
        )

    result = {
        "scope": "+".join(scope_parts) if scope_parts else "none",
        "message": " ".join(lines),
    }
    if today_list:
        result["today"] = today_list
    if week_list:
        result["week"] = week_list

    return result


def build_effective_plan(user_id):
    """
    The full saved weekly plan, but reflecting reality:

    - Any meal_type already logged on a given date (today, or an
      earlier date within this same week) always shows BOTH what was
      planned and what was actually eaten -- whether it matched,
      landed close, or went way over. Nothing about that comparison
      is hidden just because the numbers happened to line up.
    - Meal types not yet logged show the live rebalanced target when
      evaluate_plan_adherence()'s math applies (flagged "adjusted"),
      or the original plan otherwise.

    Returns the same [{day, meals:[...]}] shape the plain saved-plan
    view uses, with each meal additionally carrying "logged": bool,
    "adjusted": bool, and "actual" (the eaten totals, or None).
    Returns None if there's no saved plan at all.
    """
    today = date.today()
    today_name = today.strftime("%A")
    today_index = WEEKDAY_ORDER.index(today_name)

    all_rows = get_plan_for_all_weekdays(user_id)

    if not all_rows:
        return None

    plan_dates = [
        today + timedelta(days=WEEKDAY_ORDER.index(day_name) - today_index)
        for day_name in WEEKDAY_ORDER
        if all_rows.get(day_name)
    ]
    past_dates = [d for d in plan_dates if d <= today]

    actuals_by_date = (
        get_actual_by_meal_type_for_range(user_id, min(past_dates), max(past_dates))
        if past_dates
        else {}
    )

    adjusted_by_id = {}
    today_rows = all_rows.get(today_name)

    if today_rows:
        actual = actuals_by_date.get(today, {})
        logged_types = set(actual.keys())
        planned_types = {row["meal_type"] for row in today_rows}
        remaining_types = {mt for mt in planned_types if mt not in logged_types}

        planned_so_far = sum(
            row["calories"] for row in today_rows if row["meal_type"] in logged_types
        )
        actual_total = get_today_totals(user_id)["calories"]
        so_far_variance = actual_total - planned_so_far

        leftover = 0
        if abs(so_far_variance) >= PLAN_DEVIATION_THRESHOLD_KCAL:
            leftover = so_far_variance
            if remaining_types:
                remaining_rows = [row for row in today_rows if row["meal_type"] in remaining_types]
                adjusted_list, leftover = redistribute_variance(remaining_rows, so_far_variance)
                for slot in adjusted_list:
                    adjusted_by_id[slot["id"]] = slot["adjusted"]

        if abs(leftover) >= PLAN_DEVIATION_THRESHOLD_KCAL:
            week_days, _ = compute_week_adjustment(user_id, leftover)
            if week_days:
                for day in week_days:
                    for meal in day["meals"]:
                        adjusted_by_id[meal["id"]] = meal["adjusted"]

    result = []
    for day_name in WEEKDAY_ORDER:
        rows = all_rows.get(day_name)
        if not rows:
            continue

        day_date = today + timedelta(days=WEEKDAY_ORDER.index(day_name) - today_index)
        actual_for_day = (
            actuals_by_date.get(day_date, {})
            if day_date <= today
            else {}
        )

        meals = []
        for row in rows:
            planned_values = {
                "calories": round(row["calories"]),
                "protein": round(row["protein"]),
                "carbs": round(row["carbs"]),
                "fat": round(row["fat"]),
            }
            actual_values = actual_for_day.get(row["meal_type"])
            logged = actual_values is not None

            if logged:
                values = planned_values
                actual_out = {
                    "meal_name": ", ".join(actual_values["meal_names"]) or "Unnamed meal",
                    "calories": round(actual_values["calories"]),
                    "protein": round(actual_values["protein"]),
                    "carbs": round(actual_values["carbs"]),
                    "fat": round(actual_values["fat"]),
                }
            else:
                adjusted = adjusted_by_id.get(row["id"])
                values = adjusted or planned_values
                actual_out = None

            meals.append({
                "meal_type": row["meal_type"],
                "meal_name": row["meal_name"],
                "description": row["description"],
                "calories": values["calories"],
                "protein": values["protein"],
                "carbs": values["carbs"],
                "fat": values["fat"],
                "adjusted": (not logged) and row["id"] in adjusted_by_id,
                "logged": logged,
                "actual": actual_out,
            })

        result.append({"day": day_name, "meals": meals})

    return result


def build_profile_data(user):
    return {
        "full_name": user.full_name,
        "email": user.email,
        "age": user.age,
        "gender": user.gender,
        "height": user.height,
        "weight": user.weight,
        "activity_level": user.activity_level,
        "fitness_goal": user.fitness_goal,
        "dietary_preferences": user.dietary_preferences,
        "allergies": user.allergies,
        "medical_condition": user.medical_condition,
        "country": user.country,
        "region": user.region,
    }


def build_progress_data(user, user_id):
    calorie_goal = calculate_calorie_goal(user)
    macros = calculate_macro_goals(user)
    consumed = get_today_totals(user_id)

    return {
        "calorie_goal": calorie_goal,
        "calories_consumed": consumed["calories"],
        "calories_remaining": max(calorie_goal - consumed["calories"], 0),
        "protein_goal": macros["protein_goal"],
        "protein_consumed": consumed["protein"],
        "protein_remaining": max(macros["protein_goal"] - consumed["protein"], 0),
        "carbs_goal": macros["carbs_goal"],
        "carbs_consumed": consumed["carbs"],
        "carbs_remaining": max(macros["carbs_goal"] - consumed["carbs"], 0),
        "fat_goal": macros["fat_goal"],
        "fat_consumed": consumed["fat"],
        "fat_remaining": max(macros["fat_goal"] - consumed["fat"], 0),
    }


def build_calorie_status_data(user, user_id):
    calorie_goal = calculate_calorie_goal(user)
    consumed = get_today_totals(user_id)["calories"]

    if consumed > calorie_goal:
        exceeded = True
        exceeded_by = consumed - calorie_goal
        calories_remaining = 0
    else:
        exceeded = False
        exceeded_by = 0
        calories_remaining = calorie_goal - consumed

    return {
        "calorie_goal": calorie_goal,
        "calories_consumed": consumed,
        "calories_remaining": calories_remaining,
        "exceeded": exceeded,
        "exceeded_by": exceeded_by,
    }


def build_meal_history_data(user_id, limit=20):
    """Most recent logged meals for this user, from the database (not chat history)."""
    meals = (
        Meal.query
        .filter_by(user_id=user_id)
        .order_by(Meal.created_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "meals": [
            {
                "id": m.id,
                "meal_name": m.meal_name,
                "portion": m.portion,
                "calories": m.calories,
                "protein": m.protein,
                "carbs": m.carbs,
                "fat": m.fat,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in meals
        ]
    }


def build_memories_data(user_id):
    """
    Every long-term memory stored for this user (see UserMemory /
    get_long_term_memories), for the show_memories display intent
    lets the user actually see and audit what's been remembered about
    them, the read side of the create/update/delete flow the AI
    already does conversationally via apply_memory_update.
    """
    memories = (
        UserMemory.query
        .filter_by(user_id=user_id)
        .order_by(UserMemory.importance.desc(), UserMemory.updated_at.desc())
        .all()
    )

    return {
        "memories": [
            {
                "id": m.id,
                "memory_type": m.memory_type,
                "memory_key": m.memory_key,
                "memory_value": m.memory_value,
                "importance": m.importance,
                "updated_at": m.updated_at.isoformat() if m.updated_at else None,
            }
            for m in memories
        ]
    }


def build_nutrition_targets(user):
    """
    Backend-authoritative calorie/macro targets for the CURRENT user
    profile, computed via calculate_calorie_goal()/calculate_macro_goals()
    only  never invented anywhere else. Returns None if the profile is
    incomplete; callers must never substitute a guessed number in that
    case.
    """
    if not user_has_complete_profile(user):
        return None

    calorie_goal = calculate_calorie_goal(user)
    macros = calculate_macro_goals(user)

    return {
        "calorie_goal": calorie_goal,
        "protein_goal": macros["protein_goal"],
        "carbs_goal": macros["carbs_goal"],
        "fat_goal": macros["fat_goal"],
    }


def attach_nutrition_targets(ai_reply, user):
    """
    Attaches backend-calculated calorie/macro targets onto ai_reply for
    nutrition_question / general_chat  the free-form intents that
    apply_display_intent doesn't cover. Purely additive: never touches
    `reply` text. Ensures the caller/frontend always has the real
    numbers even if the AI's prose drifted (e.g. from stale
    conversation history).
    """
    if not isinstance(ai_reply, dict):
        return ai_reply

    if ai_reply.get("intent") not in NUTRITION_INTENTS:
        return ai_reply

    targets = build_nutrition_targets(user)
    if targets:
        ai_reply["calorie_goal"] = targets["calorie_goal"]
        ai_reply["protein_goal"] = targets["protein_goal"]
        ai_reply["carbs_goal"] = targets["carbs_goal"]
        ai_reply["fat_goal"] = targets["fat_goal"]

    return ai_reply


def build_display_payload(intent, user, user_id, saved_plan):
    """
    Computes the backend-sourced data (and an optional reply-text
    override for no-data edge cases) for a single display intent.
    Returns (data, reply_override)  reply_override is None unless
    the intent hit a "profile incomplete" / "no saved plan" case.
    Shared by apply_display_intent for both the primary intent and
    any additional_intents combined into the same request.
    """
    if intent == "show_profile":
        return build_profile_data(user), None

    if intent == "show_progress":
        if not user_has_complete_profile(user):
            return None, (
                "Please complete your profile (age, height, weight, gender, "
                "and fitness goal) so I can calculate your progress."
            )
        return build_progress_data(user, user_id), None

    if intent == "calorie_status":
        if not user_has_complete_profile(user):
            return None, (
                "Please complete your profile (age, height, weight, gender, "
                "and fitness goal) so I can calculate your calorie status."
            )
        return build_calorie_status_data(user, user_id), None

    if intent == "show_meal_history":
        return build_meal_history_data(user_id), None

    if intent == "show_weekly_plan":
        if not saved_plan:
            return {"plan": None}, "You don't have a saved weekly meal plan yet."
        return {"plan": build_effective_plan(user_id)}, None

    if intent == "show_memories":
        data = build_memories_data(user_id)
        if not data["memories"]:
            return data, "I don't have any long-term preferences or habits saved for you yet."
        return data, None

    return None, None


def apply_display_intent(ai_reply, user, user_id, saved_plan):
    """
    If ai_reply's intent is one of the read-only display intents,
    attach backend-sourced `data` to it (and override `reply` for the
    no-data edge cases). Mutates and returns ai_reply. No-op otherwise.

    show_weekly_plan is sourced from the saved DietPlan table (via
    build_effective_plan)  never an unconfirmed TempDietPlan. Asking
    to see "my weekly plan" must reflect what's actually saved, never
    a plan the user hasn't agreed to save yet. build_effective_plan
    layers in any live rebalancing from evaluate_plan_adherence, so
    the displayed plan always matches what the user's actually been
    guided toward, not the untouched original numbers.

    Also resolves ai_reply["additional_intents"] other display
    intents the model detected in a compound request (e.g. "show my
    progress and meal history"). Each is resolved the same way as the
    primary intent and attached as ai_reply["additional_data"], a
    list of {"intent", "data"} the frontend renders as extra cards
    alongside the primary one. Only values from DISPLAY_INTENTS are
    accepted (and never a duplicate of the primary intent), anything
    else is silently dropped, since combining side-effecting intents
    (meal_log, update_profile, etc.) is out of scope.
    """
    if not isinstance(ai_reply, dict):
        return ai_reply

    intent = ai_reply.get("intent")
    if intent not in DISPLAY_INTENTS:
        return ai_reply

    data, reply_override = build_display_payload(intent, user, user_id, saved_plan)
    ai_reply["data"] = data
    if reply_override:
        ai_reply["reply"] = reply_override

    raw_additional = ai_reply.get("additional_intents")
    if isinstance(raw_additional, list):
        seen = {intent}
        additional_data = []

        for extra_intent in raw_additional:
            if extra_intent not in DISPLAY_INTENTS or extra_intent in seen:
                continue
            seen.add(extra_intent)

            extra_data, _ = build_display_payload(extra_intent, user, user_id, saved_plan)
            additional_data.append({"intent": extra_intent, "data": extra_data})

        if additional_data:
            ai_reply["additional_data"] = additional_data

    return ai_reply


ALLOWED_PROFILE_FIELDS = {
    "full_name",
    "age",
    "gender",
    "height",
    "weight",
    "activity_level",
    "fitness_goal",
    "dietary_preferences",
    "allergies",
    "medical_condition",
    "country",
    "region",
}

CLEARABLE_PROFILE_FIELDS = {
    "dietary_preferences",
    "allergies",
    "medical_condition",
}


CLEARING_VALUES = {
    "", "none", "no", "nil", "n/a", "na", "nothing",
    "not applicable", "no allergies", "no allergy",
    "no medical condition", "no dietary preference",
    "no dietary preferences", "no restrictions", "no restriction",
}


GOAL_AFFECTING_FIELDS = {
    "age",
    "height",
    "weight",
    "gender",
    "activity_level",
    "fitness_goal",
    "medical_condition",
}

VALID_ACTIVITY_LEVELS = {
    "sedentary",
    "lightly_active",
    "moderately_active",
    "very_active",
    "extra_active",
}


VALID_FITNESS_GOALS = {
    "weight_loss",
    "weight_gain",
    "maintenance",
}


def validate_profile_updates(raw_updates):
    """
    Check the AI's proposed `updates` dict against the whitelist and
    per-field rules. Returns (valid_updates, rejected_fields) rejected_fields maps field -> reason, for fields the AI proposed
    but that failed validation (used to build a clarification reply).
    Any field not in ALLOWED_PROFILE_FIELDS is silently dropped: the
    AI has no business proposing it (e.g. email, password, id).
    """
    valid_updates = {}
    rejected_fields = {}

    if not isinstance(raw_updates, dict):
        return valid_updates, rejected_fields

    for field, value in raw_updates.items():

        if field not in ALLOWED_PROFILE_FIELDS:
            continue

        if field in ("age", "height", "weight"):
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                rejected_fields[field] = "not_a_number"
                continue

            if field == "age" and not (1 <= numeric_value <= 120):
                rejected_fields[field] = "out_of_range"
                continue
            if field == "height" and not (30 <= numeric_value <= 300):
                rejected_fields[field] = "out_of_range"
                continue
            if field == "weight" and not (2 <= numeric_value <= 500):
                rejected_fields[field] = "out_of_range"
                continue

            valid_updates[field] = int(numeric_value) if field == "age" else numeric_value

        elif field == "activity_level":
            normalized = str(value).strip().lower().replace(" ", "_")
            if normalized not in VALID_ACTIVITY_LEVELS:
                rejected_fields[field] = "invalid_choice"
                continue
            valid_updates[field] = normalized

        elif field == "fitness_goal":
            normalized = str(value).strip().lower().replace(" ", "_")
            if normalized not in VALID_FITNESS_GOALS:
                rejected_fields[field] = "invalid_choice"
                continue
            valid_updates[field] = normalized

        else:

            text_value = "" if value is None else str(value).strip()

            if (field in CLEARABLE_PROFILE_FIELDS
                    and text_value.lower() in CLEARING_VALUES):
                valid_updates[field] = None
                continue

            if not text_value:
                rejected_fields[field] = "empty_value"
                continue

            valid_updates[field] = text_value

    return valid_updates, rejected_fields


ACTIVITY_LEVEL_ALIASES = {
    "extremely active": "extra_active",
    "extra active": "extra_active",
    "very active": "very_active",
    "moderately active": "moderately_active",
    "moderate activity": "moderately_active",
    "lightly active": "lightly_active",
    "light activity": "lightly_active",
    "sedentary": "sedentary",
}

FITNESS_GOAL_ALIASES = {
    "lose weight": "weight_loss",
    "losing weight": "weight_loss",
    "weight loss": "weight_loss",
    "gain weight": "weight_gain",
    "gaining weight": "weight_gain",
    "weight gain": "weight_gain",
    "build muscle": "weight_gain",
    "muscle gain": "weight_gain",
    "maintain my weight": "maintenance",
    "maintain weight": "maintenance",
    "maintenance": "maintenance",
}


FALLBACK_EXCLUDED_INTENTS = {
    "meal_log",
    "meal_update",
    "meal_delete",
    "save_diet_plan",
    "diet_plan_confirmation",
    "delete_diet_plan",
    "discard_diet_plan",
    "delete_profile",
}

_QUESTION_START = re.compile(
    r"^(what|why|how|is|are|does|do|can|should|which|when|where)\b"
)


def extract_profile_updates_from_text(message, user):
    """
    Best-effort, conservative regex extraction of profile changes
    directly from the user's raw message. Returns a raw (unvalidated)
    updates dict still passed through validate_profile_updates()
    before anything is applied.
    """
    if not message:
        return {}

    text = message.strip().lower()

    if not text or text.endswith("?") or _QUESTION_START.match(text):
        return {}

    updates = {}

    m = (
        re.search(r"weight.{0,15}?to\s+(\d+(?:\.\d+)?)\s*kg", text)
        or re.search(r"\bi'?m\s+(\d+(?:\.\d+)?)\s*kg\b", text)
        or re.search(r"\bmy\s+weight\s+is\s+(\d+(?:\.\d+)?)\s*kg?\b", text)
    )
    if m:
        updates["weight"] = m.group(1)

    m = (
        re.search(r"height.{0,15}?to\s+(\d+(?:\.\d+)?)\s*cm", text)
        or re.search(r"\bi'?m\s+(\d+(?:\.\d+)?)\s*cm\b", text)
    )
    if m:
        updates["height"] = m.group(1)

    m = (
        re.search(r"age.{0,15}?to\s+(\d+)\b", text)
        or re.search(r"\bi'?m\s+(\d+)\s*(?:years?\s*old|yo)\b", text)
    )
    if m:
        updates["age"] = m.group(1)

   
    if "activ" in text:
        for phrase, normalized in ACTIVITY_LEVEL_ALIASES.items():
            if phrase in text:
                updates["activity_level"] = normalized
                break

    for phrase, normalized in FITNESS_GOAL_ALIASES.items():
        if phrase in text:
            updates["fitness_goal"] = normalized
            break


    m = re.search(r"dietary preference.{0,15}?to\s+([a-z\- ]+)", text)
    if m:
        updates["dietary_preferences"] = m.group(1).strip()
    elif "vegetarian" in text and ("i'm" in text or "i am" in text or "im " in text):
        updates["dietary_preferences"] = "vegetarian"
    elif "vegan" in text and ("i'm" in text or "i am" in text or "im " in text):
        updates["dietary_preferences"] = "vegan"


    m = re.search(r"(?:change|update|set)\s+my\s+name\s+to\s+([a-z ]+)", text)
    if m:
        updates["full_name"] = m.group(1).strip().title()

    if "allerg" in text and not re.search(r"no longer allerg|remove", text):
        m = re.search(r"(?:i'?m|i am)\s+allerg(?:y|ic)\s+to\s+([a-z, ]+)", text)
        if not m:
            m = re.search(r"add\s+([a-z, ]+?)\s+allerg", text)
        if m:
            new_allergen = m.group(1).strip()
            existing = [a.strip() for a in (user.allergies or "").split(",") if a.strip()]
            if new_allergen and new_allergen.lower() not in [e.lower() for e in existing]:
                existing.append(new_allergen)
            updates["allergies"] = ", ".join(existing)

    if "allerg" in text and re.search(r"no longer allerg|remove", text):
        m = re.search(r"(?:no longer allerg(?:y|ic) to|remove)\s+(?:my\s+)?([a-z, ]+?)(?:\s+allerg(?:y|ies))?\b", text)
        if m:
            removed = m.group(1).strip()
            existing = [a.strip() for a in (user.allergies or "").split(",") if a.strip()]
            remaining = [a for a in existing if a.lower() != removed.lower()]
            updates["allergies"] = ", ".join(remaining)

    return updates
CONFIRMATION_WORDS = {
    "yes", "yeah", "yep", "yup", "sure", "ok", "okay", "confirm",
    "correct", "affirmative", "do it", "go ahead", "please do",
}


def is_bare_confirmation(message):
    text = (message or "").strip().lower().strip(".!")
    return text in CONFIRMATION_WORDS


_PENDING_NUMERIC_PATTERNS = [
    ("weight", re.compile(r"weight\s+to\s+(\d+(?:\.\d+)?)\s*kg", re.I)),
    ("height", re.compile(r"height\s+to\s+(\d+(?:\.\d+)?)\s*cm", re.I)),
    ("age", re.compile(r"age\s+to\s+(\d+)\b", re.I)),
]

_PENDING_ACTIVITY_PATTERN = re.compile(
    r"activity level to\s+([a-z ]+?)(?:\s*[\(\?]|$)", re.I
)
_PENDING_GOAL_PATTERN = re.compile(
    r"(?:fitness )?goal to\s+([a-z ]+?)(?:\s*[\(\?]|$)", re.I
)


def extract_pending_update_from_history(chat_history):
    """
    A bare 'yes'/'confirm' message carries no field or value itself.
    Scan the chat history backwards for the most recent AI message
    that proposed a specific profile change (e.g. "change your weight
    to 100 kg?") and pull the field/value it was proposing out of
    THAT message instead.
    """
    if not chat_history:
        return {}

    for chat_msg in reversed(chat_history):
        if chat_msg.sender != "ai":
            continue

        try:
            parsed = json.loads(chat_msg.message)
            text = parsed.get("reply", "") if isinstance(parsed, dict) else chat_msg.message
        except Exception:
            text = chat_msg.message

        if not text:
            continue

        lower = text.lower()

        for field, pattern in _PENDING_NUMERIC_PATTERNS:
            m = pattern.search(lower)
            if m:
                return {field: m.group(1)}

        m = _PENDING_ACTIVITY_PATTERN.search(lower)
        if m:
            return {"activity_level": m.group(1).strip()}

        m = _PENDING_GOAL_PATTERN.search(lower)
        if m:
            return {"fitness_goal": m.group(1).strip()}

    
        break

    return {}

def apply_profile_update(ai_reply, user, message="", chat_history=None):
    """
    Applies profile changes to the authenticated user's row.

    Primary path: ai_reply["intent"] == "update_profile" with a valid
    "updates" dict, validated and applied as before.

    Fallback path: if the AI didn't produce a usable update (asked for
    confirmation, returned empty updates, or misclassified the intent
    as general_chat), a conservative regex pass over the raw user
    `message` is used instead, so a clear command like "change my
    weight to 65kg" still updates the database in this same turn
    regardless of what the AI decided to say back.

    After a successful commit, recalculates the user's calorie and
    macro targets using the existing nutrition_service functions
    (calculate_calorie_goal / calculate_macro_goals), these are the
    single authoritative source, never invented here or by the AI
    and attaches them to ai_reply along with an updated confirmation
    reply. If the profile is still incomplete after the update, no
    targets are returned and the reply explains what's missing
    instead.

    Mutates and returns ai_reply. No-op if neither path applies
    (e.g. this was a meal_log/nutrition_question/etc. message).
    """
    if not isinstance(ai_reply, dict):
        return ai_reply

    intent = ai_reply.get("intent")
    is_declared_update = intent == "update_profile"

    raw_updates = ai_reply.get("updates") if is_declared_update else None
    valid_updates, rejected_fields = validate_profile_updates(raw_updates or {})

    used_fallback = False
    if not valid_updates and intent not in FALLBACK_EXCLUDED_INTENTS:

        if is_bare_confirmation(message):
           
            fallback_raw = extract_pending_update_from_history(chat_history)
        else:
            fallback_raw = extract_profile_updates_from_text(message, user)

        if fallback_raw:
            fallback_valid, _ = validate_profile_updates(fallback_raw)
            if fallback_valid:
                valid_updates = fallback_valid
                used_fallback = True

    if not is_declared_update and not used_fallback:
        
        return ai_reply

    if valid_updates:
    
        for field, value in valid_updates.items():
            setattr(user, field, value)
        db.session.commit()
        ai_reply["profile"] = build_profile_data(user)
        changed = ", ".join(f.replace("_", " ") for f in valid_updates)
        ai_reply["intent"] = "update_profile"
        ai_reply["updates"] = valid_updates

        goals_changed = bool(GOAL_AFFECTING_FIELDS & valid_updates.keys())

        if user_has_complete_profile(user) and goals_changed:

            calorie_goal = calculate_calorie_goal(user)
            macros = calculate_macro_goals(user)

            ai_reply["calorie_goal"] = calorie_goal
            ai_reply["protein_goal"] = macros["protein_goal"]
            ai_reply["carbs_goal"] = macros["carbs_goal"]
            ai_reply["fat_goal"] = macros["fat_goal"]

            ai_reply["reply"] = (
                f"Your {changed} has been updated.\n\n"
                "Your daily nutrition targets have also been recalculated:\n\n"
                f"- Calories: {calorie_goal} kcal\n"
                f"- Protein: {macros['protein_goal']} g\n"
                f"- Carbs: {macros['carbs_goal']} g\n"
                f"- Fat: {macros['fat_goal']} g"
            )
        elif user_has_complete_profile(user):

            ai_reply["reply"] = f"Your {changed} has been updated."
        else:
         
            missing = [
                name for name, val in [
                    ("age", user.age),
                    ("height", user.height),
                    ("weight", user.weight),
                    ("gender", user.gender),
                    ("fitness goal", user.fitness_goal),
                ]
                if val is None
            ]
            ai_reply["calorie_goal"] = None
            ai_reply["protein_goal"] = None
            ai_reply["carbs_goal"] = None
            ai_reply["fat_goal"] = None
            ai_reply["reply"] = (
                f"Your {changed} has been updated. I still need your "
                + ", ".join(missing)
                + " to calculate your daily calorie and macro targets."
            )
        return ai_reply

    if is_declared_update:
        if rejected_fields:
           
            bad_field = next(iter(rejected_fields)).replace("_", " ")
            ai_reply["reply"] = (
                f"That doesn't look like a valid value for {bad_field}. "
                "Please try again."
            )
   
        ai_reply["updates"] = {}

    return ai_reply


def _chat_pipeline(streaming=False):
    """
    The complete chat pipeline. Identical to the previous endpoint body apart
    from how the model is called. As a generator it yields decoded reply-text
    pieces when streaming=True (and nothing at all when False), then returns
    the finished ai_reply dict.
    """

    try:

        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        meals = Meal.query.filter(Meal.user_id == user_id,func.date(Meal.created_at) == today).order_by(Meal.created_at.desc()).all()
        
        chat_history = get_recent_chat_history(user_id)
        message = request.form.get("message", "").strip()

        embedding_ahead = _PREFETCH.submit(embed_text, message) if message else None
        image = request.files.get("image")
        image_path = None

        if image:

            filename = secure_filename(image.filename)

            extension = os.path.splitext(filename)[1]#split filename and file type and takes file type

            unique_filename = f"{uuid.uuid4()}{extension}"

            upload_folder = os.path.join(os.getcwd(), "uploads")#gets current folder and creates folder 

            os.makedirs(upload_folder, exist_ok=True)#if nothin exists or else upload

            full_path = os.path.join(upload_folder, unique_filename)

            image.save(full_path)

            image_path = unique_filename

        if message or image:

            user_message = ChatMessage(
                user_id=user_id,
                sender="user",
                message=message if message else "",
                image_path=image_path,
                message_type="image" if image else "text"
                )

            db.session.add(user_message)
            db.session.commit()
        saved_plan_rows = DietPlan.query.filter_by(user_id=user_id).order_by(DietPlan.id.asc()).all()
        saved_plan = None

        if saved_plan_rows:

            days = {}

            for meal in saved_plan_rows:

               if meal.day not in days:
                   days[meal.day] = {"day": meal.day,"meals": []}


               days[meal.day]["meals"].append({

            "meal_type": meal.meal_type,
            "meal_name": meal.meal_name,
            "description": meal.description,
            "calories": meal.calories,
            "protein": meal.protein,
            "carbs": meal.carbs,
            "fat": meal.fat

        })

            saved_plan = list(days.values())

        temp_plan = TempDietPlan.query.filter_by(user_id=user_id).order_by(TempDietPlan.created_at.desc()).first()

        plan_is_pending = temp_plan is not None
        current_plan = temp_plan.plan_data if temp_plan else build_effective_plan(user_id)

        nutrition_targets = build_nutrition_targets(user)
        conversation_summary = get_conversation_summary(user_id, defer=True)
        long_term_memories = get_long_term_memories(
            user_id,
            message,
            query_embedding=embedding_ahead.result() if embedding_ahead else None,
        )

        ask_kwargs = dict(
        message=with_pending_context(message, chat_history),
        image=image,
        user=user,
        meals=meals,
        chat_history=chat_history,
        current_plan=current_plan,
        nutrition_targets=nutrition_targets,
        conversation_summary=conversation_summary,
        long_term_memories=long_term_memories,
        plan_is_pending=plan_is_pending
)

        if streaming and not find_pending_meal_log(chat_history):
         
            ai_reply = yield from ask_openai_stream(
                allow_intents=NUTRITION_INTENTS,
                meal_intents=MEAL_INTENTS,
                **ask_kwargs
            )
        else:
            ai_reply = ask_openai(**ask_kwargs)

        ai_reply = normalize_intent(ai_reply)
        apply_memory_update(ai_reply, user_id)

        pending_meal = find_pending_meal_log(chat_history)
        if pending_meal:
            resolved_type = extract_meal_type_from_text(message)
            if resolved_type:
                ai_reply = finalize_pending_meal(pending_meal, resolved_type)

        ai_reply = apply_profile_update(ai_reply, user, message,chat_history)
        user = User.query.get(user_id)

        ai_reply = apply_display_intent(ai_reply, user, user_id, saved_plan)
        ai_reply = attach_nutrition_targets(ai_reply, user)

        if isinstance(ai_reply, dict) and ai_reply.get("intent") == "meal_log":

            meal_type = (ai_reply.get("meal_type") or "").strip().lower()

            if not meal_type:
                ai_reply["pending_meal_type"] = True
                ai_reply["reply"] = build_meal_type_question(ai_reply.get("meal_name"), ai_reply.get("calories"))
                attach_conflict_alert(ai_reply)
            else:

                meal = Meal(
                    user_id=user_id,
                    meal_name=ai_reply.get("meal_name"),
                    meal_type=meal_type,
                    calories=ai_reply.get("calories"),
                    protein=ai_reply.get("protein"),
                    carbs=ai_reply.get("carbs"),
                    fat=ai_reply.get("fat"),
                    portion=ai_reply.get("portion"),
                    is_estimated=ai_reply.get("is_estimated", True))

                db.session.add(meal)
                db.session.commit()
                context = UserMealContext.query.filter_by(user_id=user_id).first()
                if context:

                    context.last_meal_id = meal.id
                else:

                    context = UserMealContext(
                    user_id=user_id,
                    last_meal_id=meal.id
                )

                    db.session.add(context)


                db.session.commit()

                guidance = build_meal_guidance(user, user_id)
                if guidance:
                    ai_reply["guidance"] = guidance["text"]
                    ai_reply["nutrition_alert"] = guidance["exceeded"]
                attach_conflict_alert(ai_reply)

                plan_adjustment = evaluate_plan_adherence(user_id)
                if plan_adjustment:
                    ai_reply["plan_adjustment"] = plan_adjustment

        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "meal_update":


            context = UserMealContext.query.filter_by(
                user_id=user_id
            ).first()


            if context:

                meal = Meal.query.get(
                context.last_meal_id
                )


                if meal:

                    if ai_reply.get("meal_name"):
                        meal.meal_name = ai_reply.get("meal_name")

                    if ai_reply.get("meal_type"):
                        meal.meal_type = ai_reply.get("meal_type").strip().lower()

                    if ai_reply.get("calories") is not None:
                        meal.calories = ai_reply.get("calories")

                    if ai_reply.get("protein") is not None:
                        meal.protein = ai_reply.get("protein")

                    if ai_reply.get("carbs") is not None:
                        meal.carbs = ai_reply.get("carbs")

                    if ai_reply.get("fat") is not None:
                        meal.fat = ai_reply.get("fat")

                    if ai_reply.get("portion"):
                        meal.portion = ai_reply.get("portion")

                    if ai_reply.get("is_estimated") is not None:
                        meal.is_estimated = ai_reply.get("is_estimated")


                    db.session.commit()

                    guidance = build_meal_guidance(user, user_id)
                    if guidance:
                        ai_reply["guidance"] = guidance["text"]
                        ai_reply["nutrition_alert"] = guidance["exceeded"]
                    attach_conflict_alert(ai_reply)

                    if meal.meal_type:
                        plan_adjustment = evaluate_plan_adherence(user_id)
                        if plan_adjustment:
                            ai_reply["plan_adjustment"] = plan_adjustment
        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "meal_delete":

            scope = ai_reply.get("scope", "last")

            if scope == "all_today":

                deleted_count = Meal.query.filter(
                    Meal.user_id == user_id,
                    func.date(Meal.created_at) == date.today()
                ).delete(synchronize_session=False)

                UserMealContext.query.filter_by(user_id=user_id).delete()
                db.session.commit()

                ai_reply["deleted_scope"] = "all_today"
                ai_reply["reply"] = (
                    "All of today's logged meals have been deleted."
                    if deleted_count > 0
                    else "You don't have any meals logged today to delete."
                )

            else:

                context = UserMealContext.query.filter_by(
                    user_id=user_id
                ).first()

                deleted_name = None

                if context and context.last_meal_id:

                    meal = Meal.query.get(
                        context.last_meal_id
                    )

                    if meal:
                        deleted_name = meal.meal_name
                        db.session.delete(meal)

                    db.session.delete(context)
                    db.session.commit()

                ai_reply["deleted_scope"] = "last"
                ai_reply["reply"] = (
                    f"{deleted_name} has been deleted."
                    if deleted_name
                    else "I don't see a recent meal to delete."
                )
        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "save_diet_plan":


            temp_plan = TempDietPlan.query.filter_by(
                user_id=user_id
            ).order_by(
                TempDietPlan.created_at.desc()
            ).first()
            
            if temp_plan:

                DietPlan.query.filter_by(
                    user_id=user_id
                ).delete()


                for day in temp_plan.plan_data:

                    for meal in day.get("meals", []):


                        diet_meal = DietPlan(

                            user_id=user_id,

                            day=day.get("day"),

                            meal_type=clean_text(meal.get("meal_type")),

                            meal_name=clean_text(meal.get("meal_name")),

                            description=clean_text(meal.get("description")),

                            calories=meal.get("calories"),

                            protein=meal.get("protein"),

                            carbs=meal.get("carbs"),

                            fat=meal.get("fat"))

                        db.session.add(diet_meal)


                db.session.delete(temp_plan)


                db.session.commit()         
        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "diet_plan_confirmation":

            plan = ai_reply.get("plan")


            if plan:


                TempDietPlan.query.filter_by(
                    user_id=user_id
                ).delete()

                temp = TempDietPlan(
                    user_id=user_id,
                    plan_data=plan
                )

                db.session.add(temp)
                db.session.commit()

        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "delete_diet_plan":

            DietPlan.query.filter_by(
                user_id=user_id
            ).delete()

            TempDietPlan.query.filter_by(
                user_id=user_id
            ).delete()

            db.session.commit()

        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "discard_diet_plan":

      
            TempDietPlan.query.filter_by(
                user_id=user_id
            ).delete()

            db.session.commit()

        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "delete_profile":

            user.age = None
            user.gender = None
            user.height = None
            user.weight = None
            user.activity_level = None
            user.fitness_goal = None
            user.dietary_preferences = None
            user.allergies = None
            user.medical_condition = None

            db.session.commit()

            ai_reply["profile"] = build_profile_data(user)
            ai_reply["calorie_goal"] = None
            ai_reply["protein_goal"] = None
            ai_reply["carbs_goal"] = None
            ai_reply["fat_goal"] = None
            ai_reply["reply"] = (
                "Your profile has been reset. I've kept your name and email, "
                "but I'll need your age, height, weight, gender, activity "
                "level, and fitness goal again to calculate your nutrition "
                "targets."
            )

        ai_message = ChatMessage(
            user_id=user_id,
            sender="ai",
            message=json.dumps(ai_reply)
        )

        db.session.add(ai_message)
        db.session.commit()

        return ai_reply

    except Exception as e:
        traceback.print_exc()
        raise


def _drain(pipeline):
    """Run a pipeline that yields nothing and hand back its return value."""
    try:
        while True:
            next(pipeline)
    except StopIteration as stop:
        return stop.value


@chat.route("/chat", methods=["POST"])
@jwt_required()
def chat_with_ai():

    try:
        ai_reply = _drain(_chat_pipeline(streaming=False))

        return jsonify({
                "success": True,
                "user_id": get_jwt_identity(),
                "reply": ai_reply
            }), 200

    except Exception as e:
        traceback.print_exc()

        return jsonify({
        "success": False,
        "message": str(e)
    }), 500


def _sse(event, payload):
    return "event: " + event + "\ndata: " + json.dumps(payload) + "\n\n"


@chat.route("/chat/stream", methods=["POST"])
@jwt_required()
def chat_with_ai_stream():

    user_id = get_jwt_identity()

    def events():
        try:
            pipeline = _chat_pipeline(streaming=True)

            while True:
                try:
                    piece = next(pipeline)
                except StopIteration as stop:
                    ai_reply = stop.value
                    break

                if piece is STREAM_RESET:
                    yield _sse("reset", {})
                elif isinstance(piece, tuple):
                    name, payload = piece
                    yield _sse(name, payload)
                else:
                    yield _sse("delta", {"text": piece})
            yield _sse("done", {
                "success": True,
                "user_id": user_id,
                "reply": ai_reply
            })

        except Exception as e:
            traceback.print_exc()
            yield _sse("error", {"success": False, "message": str(e)})

    return Response(
        stream_with_context(events()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
@chat.route("/chat/audio", methods=["POST"])
@jwt_required()
def chat_audio():

    try:

        user_id = get_jwt_identity()

        user = User.query.get(user_id)


        meals = Meal.query.filter_by(
            user_id=user_id
        ).order_by(
            Meal.created_at.desc()
        ).all()


        chat_history = get_recent_chat_history(user_id)

        audio = request.files.get("audio")
        if not audio:

            return jsonify({
                "success": False,
                "message": "No audio received."
            }), 400



        filename = secure_filename(audio.filename)

        extension = os.path.splitext(filename)[1]

        unique_filename = f"{uuid.uuid4()}{extension}"
        upload_folder = os.path.join(
            os.getcwd(),
            "uploads"
        )

        os.makedirs(
            upload_folder,
            exist_ok=True
        )
        full_path = os.path.join(
            upload_folder,
            unique_filename
        )


        audio.save(full_path)

        transcript = transcribe(full_path)



        user_message = ChatMessage(
            user_id=user_id,
            sender="user",
            message=transcript,
            message_type="audio",
            audio_path=unique_filename
        )


        db.session.add(user_message)

        db.session.commit()

        saved_plan_rows = DietPlan.query.filter_by(
            user_id=user_id
        ).order_by(
            DietPlan.id.asc()
        ).all()

        saved_plan = None

        if saved_plan_rows:

            days = {}
            for meal in saved_plan_rows:

                if meal.day not in days:

                    days[meal.day] = {
                        "day": meal.day,
                        "meals": []
                    }
                days[meal.day]["meals"].append({

                    "meal_type": meal.meal_type,

                    "meal_name": meal.meal_name,

                    "description": meal.description,

                    "calories": meal.calories,

                    "protein": meal.protein,

                    "carbs": meal.carbs,

                    "fat": meal.fat

                })

            saved_plan = list(days.values())

        temp_plan = TempDietPlan.query.filter_by(
            user_id=user_id
        ).order_by(
            TempDietPlan.created_at.desc()
        ).first()

        plan_is_pending = temp_plan is not None
        current_plan = temp_plan.plan_data if temp_plan else build_effective_plan(user_id)

        nutrition_targets = build_nutrition_targets(user)
        conversation_summary = get_conversation_summary(user_id)
        long_term_memories = get_long_term_memories(user_id, transcript)

        ai_reply = ask_openai(
            message=with_pending_context(transcript, chat_history),
            image=None,
            user=user,
            meals=meals,
            chat_history=chat_history,
            current_plan=current_plan,
            nutrition_targets=nutrition_targets,
            conversation_summary=conversation_summary,
            long_term_memories=long_term_memories,
            plan_is_pending=plan_is_pending
        )


        ai_reply = normalize_intent(ai_reply)
        apply_memory_update(ai_reply, user_id)

        pending_meal = find_pending_meal_log(chat_history)
        if pending_meal:
            resolved_type = extract_meal_type_from_text(transcript)
            if resolved_type:
                ai_reply = finalize_pending_meal(pending_meal, resolved_type)

        ai_reply = apply_profile_update(ai_reply, user, transcript,chat_history)

        user = User.query.get(user_id)

        ai_reply = apply_display_intent(ai_reply, user, user_id, saved_plan)
        ai_reply = attach_nutrition_targets(ai_reply, user)

        if isinstance(ai_reply, dict) and ai_reply.get("intent") == "meal_log":

            meal_type = (ai_reply.get("meal_type") or "").strip().lower()

            if not meal_type:
                ai_reply["pending_meal_type"] = True
                ai_reply["reply"] = build_meal_type_question(ai_reply.get("meal_name"), ai_reply.get("calories"))
                attach_conflict_alert(ai_reply)
            else:

                meal = Meal(

                    user_id=user_id,

                    meal_name=ai_reply.get("meal_name"),

                    meal_type=meal_type,

                    calories=ai_reply.get("calories"),

                    protein=ai_reply.get("protein"),

                    carbs=ai_reply.get("carbs"),

                    fat=ai_reply.get("fat"),

                    portion=ai_reply.get("portion"),

                    is_estimated=ai_reply.get("is_estimated", True)

                )


                db.session.add(meal)

                db.session.commit()



                context = UserMealContext.query.filter_by(
                    user_id=user_id
                ).first()



                if context:

                    context.last_meal_id = meal.id


                else:

                    context = UserMealContext(
                        user_id=user_id,
                        last_meal_id=meal.id
                    )

                    db.session.add(context)
                db.session.commit()

                guidance = build_meal_guidance(user, user_id)
                if guidance:
                    ai_reply["guidance"] = guidance["text"]
                    ai_reply["nutrition_alert"] = guidance["exceeded"]
                attach_conflict_alert(ai_reply)

                plan_adjustment = evaluate_plan_adherence(user_id)
                if plan_adjustment:
                    ai_reply["plan_adjustment"] = plan_adjustment

        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "meal_update":


            context = UserMealContext.query.filter_by(
                user_id=user_id
            ).first()

            if context:


                meal = Meal.query.get(
                    context.last_meal_id
                )


                if meal:


                    if ai_reply.get("meal_name"):

                        meal.meal_name = ai_reply.get("meal_name")


                    if ai_reply.get("meal_type"):

                        meal.meal_type = ai_reply.get("meal_type").strip().lower()


                    if ai_reply.get("calories") is not None:

                        meal.calories = ai_reply.get("calories")


                    if ai_reply.get("protein") is not None:

                        meal.protein = ai_reply.get("protein")


                    if ai_reply.get("carbs") is not None:

                        meal.carbs = ai_reply.get("carbs")


                    if ai_reply.get("fat") is not None:

                        meal.fat = ai_reply.get("fat")


                    if ai_reply.get("portion"):

                        meal.portion = ai_reply.get("portion")


                    if ai_reply.get("is_estimated") is not None:

                        meal.is_estimated = ai_reply.get("is_estimated")
                    db.session.commit()

                    guidance = build_meal_guidance(user, user_id)
                    if guidance:
                        ai_reply["guidance"] = guidance["text"]
                        ai_reply["nutrition_alert"] = guidance["exceeded"]
                    attach_conflict_alert(ai_reply)

                    if meal.meal_type:
                        plan_adjustment = evaluate_plan_adherence(user_id)
                        if plan_adjustment:
                            ai_reply["plan_adjustment"] = plan_adjustment

        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "meal_delete":

            scope = ai_reply.get("scope", "last")

            if scope == "all_today":

                deleted_count = Meal.query.filter(
                    Meal.user_id == user_id,
                    func.date(Meal.created_at) == date.today()
                ).delete(synchronize_session=False)

                UserMealContext.query.filter_by(user_id=user_id).delete()
                db.session.commit()

                ai_reply["deleted_scope"] = "all_today"
                ai_reply["reply"] = (
                    "All of today's logged meals have been deleted."
                    if deleted_count > 0
                    else "You don't have any meals logged today to delete."
                )

            else:

                context = UserMealContext.query.filter_by(
                    user_id=user_id
                ).first()

                deleted_name = None

                if context and context.last_meal_id:
                    meal = Meal.query.get(
                        context.last_meal_id
                    )

                    if meal:
                        deleted_name = meal.meal_name
                        db.session.delete(meal)

                    db.session.delete(context)
                    db.session.commit()

                ai_reply["deleted_scope"] = "last"
                ai_reply["reply"] = (
                    f"{deleted_name} has been deleted."
                    if deleted_name
                    else "I don't see a recent meal to delete."
                )

        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "save_diet_plan":


            temp_plan = TempDietPlan.query.filter_by(user_id=user_id).order_by(TempDietPlan.created_at.desc()).first()

            if temp_plan:


                DietPlan.query.filter_by(
                    user_id=user_id
                ).delete()

                for day in temp_plan.plan_data:
                    for meal in day.get("meals", []):
                        diet_meal = DietPlan(

                            user_id=user_id,

                            day=day.get("day"),

                            meal_type=meal.get("meal_type"),

                            meal_name=meal.get("meal_name"),

                            description=meal.get("description"),

                            calories=meal.get("calories"),

                            protein=meal.get("protein"),

                            carbs=meal.get("carbs"),

                            fat=meal.get("fat")

                        )


                        db.session.add(diet_meal)
                db.session.delete(temp_plan)

                db.session.commit()

        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "diet_plan_confirmation":


            plan = ai_reply.get("plan")

            if plan:
                TempDietPlan.query.filter_by(
                    user_id=user_id
                ).delete()

                temp = TempDietPlan(

                    user_id=user_id,

                    plan_data=plan

                )

                db.session.add(temp)

                db.session.commit()

        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "delete_diet_plan":

            DietPlan.query.filter_by(
                user_id=user_id
            ).delete()

            TempDietPlan.query.filter_by(
                user_id=user_id
            ).delete()

            db.session.commit()

        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "discard_diet_plan":

            TempDietPlan.query.filter_by(
                user_id=user_id
            ).delete()

            db.session.commit()

        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "delete_profile":
            user.age = None
            user.gender = None
            user.height = None
            user.weight = None
            user.activity_level = None
            user.fitness_goal = None
            user.dietary_preferences = None
            user.allergies = None
            user.medical_condition = None

            db.session.commit()

            ai_reply["profile"] = build_profile_data(user)
            ai_reply["calorie_goal"] = None
            ai_reply["protein_goal"] = None
            ai_reply["carbs_goal"] = None
            ai_reply["fat_goal"] = None
            ai_reply["reply"] = (
                "Your profile has been reset. I've kept your name and email, "
                "but I'll need your age, height, weight, gender, activity "
                "level, and fitness goal again to calculate your nutrition "
                "targets."
            )

        ai_message = ChatMessage(
            user_id=user_id,
            sender="ai",
            message=json.dumps(ai_reply),
            message_type="text"
        )

        db.session.add(ai_message)
        db.session.commit()

        return jsonify({

            "success": True,

            "transcript": transcript,

            "reply": ai_reply,

            "audio_file": unique_filename

        }), 200

    except Exception as e:

        traceback.print_exc()


        return jsonify({

            "success": False,

            "message": str(e)

        }), 500
@chat.route("/chat/history", methods=["GET"])
@jwt_required()
def get_chat_history():

    user_id = get_jwt_identity()

    messages = (
        ChatMessage.query
        .filter_by(user_id=user_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    history = []

    for msg in messages:

        text = msg.message
        intent = None
        plan = None
        portion = None
        is_estimated = None
        data = None
        updates = None
        profile = None
        calorie_goal = None
        protein_goal = None
        carbs_goal = None
        fat_goal = None
        guidance = None
        deleted_scope = None
        plan_adjustment = None
        pending_meal_type = None
        additional_data = None

        if msg.sender == "ai":

            try:

                parsed = json.loads(msg.message)

                if isinstance(parsed, dict):

                    text = parsed.get("reply", msg.message)
                    intent = parsed.get("intent")
                    plan = parsed.get("plan")
                    portion = parsed.get("portion")
                    is_estimated = parsed.get("is_estimated")
                    data = parsed.get("data")
                    updates = parsed.get("updates")
                    profile = parsed.get("profile")
                    calorie_goal = parsed.get("calorie_goal")
                    protein_goal = parsed.get("protein_goal")
                    carbs_goal = parsed.get("carbs_goal")
                    fat_goal = parsed.get("fat_goal")
                    guidance = parsed.get("guidance")
                    deleted_scope = parsed.get("deleted_scope")
                    plan_adjustment = parsed.get("plan_adjustment")
                    pending_meal_type = parsed.get("pending_meal_type")
                    additional_data = parsed.get("additional_data")

            except Exception:
                pass

        history.append({

            "sender": msg.sender,
            "text": text,
            "intent": intent,
            "plan": plan,
            "portion": portion,
            "is_estimated": is_estimated,
            "data": data,
            "updates": updates,
            "profile": profile,
            "calorie_goal": calorie_goal,
            "protein_goal": protein_goal,
            "carbs_goal": carbs_goal,
            "fat_goal": fat_goal,
            "guidance": guidance,
            "deleted_scope": deleted_scope,
            "plan_adjustment": plan_adjustment,
            "pending_meal_type": pending_meal_type,
            "additional_data": additional_data,

            "image":
                f"https://kalorie-app.onrender.com/uploads/{msg.image_path}"
                if msg.image_path else None,

            "audio":
                f"https://kalorie-app.onrender.com/uploads/{msg.audio_path}"
                if msg.audio_path else None,

            "message_type": msg.message_type

        })

    reminder = build_daily_reminder(user_id)

    return jsonify({
        "history": history,
        "reminder": reminder
    }), 200

@chat.route("/chat/speak", methods=["POST"])
@jwt_required()
def speak():

    try:

        data = request.get_json()

        text = data.get("text")

        audio_base64 = generate_audio(text)

        return jsonify({
            "success": True,
            "audio_base64": audio_base64
        }),200

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "success":False,
            "message":str(e)
        }),500


@chat.route("/meals/<int:meal_id>", methods=["DELETE"])
@jwt_required()
def delete_meal(meal_id):

    try:
        user_id = get_jwt_identity()

        meal = Meal.query.filter_by(
            id=meal_id,
            user_id=user_id
        ).first()

        if not meal:
            return jsonify({"message": "Meal not found"}), 404

        db.session.delete(meal)
        db.session.commit()

        return jsonify({"message": "Meal deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": str(e)}), 500
