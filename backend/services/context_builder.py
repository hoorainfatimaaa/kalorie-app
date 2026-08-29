import json


def build_profile_block(user):
    return f"""
User Profile:

Age: {user.age or "Not provided"}
Gender: {user.gender or "Not provided"}
Height: {user.height or "Not provided"} cm
Weight: {user.weight or "Not provided"} kg
Activity Level: {user.activity_level or "Not provided"}
Fitness Goal: {user.fitness_goal or "Not provided"}
Dietary Preferences: {user.dietary_preferences or "None"}
Allergies: {user.allergies or "None"}
Medical/Dietary Condition: {user.medical_condition or "None"}
Country: {user.country or "Not provided"}
Region: {user.region or "Not provided"}

Use this information to personalize every response.

Never recommend foods that conflict with the user's allergies or dietary preferences.

When generating meal plans or nutrition advice, always consider the user's profile, including their medical/dietary condition — in general, non-medical terms only. Never give specific medical advice; suggest the user consult their doctor or a dietitian for anything beyond general food/lifestyle guidance.
"""


def build_targets_block(nutrition_targets):
    if nutrition_targets:
        return f"""
Backend-Calculated Nutrition Targets (Authoritative — Current Profile)

Calorie Goal: {nutrition_targets['calorie_goal']} kcal
Protein Goal: {nutrition_targets['protein_goal']} g
Carbs Goal: {nutrition_targets['carbs_goal']} g
Fat Goal: {nutrition_targets['fat_goal']} g

IMPORTANT:

These were calculated by the backend from the user's CURRENT saved
profile and are the ONLY correct calorie/macro target numbers.

- Never calculate, estimate, or invent your own calorie or macro
  goal number.
- If a different calorie/macro goal number appears earlier in the
  conversation history, IGNORE it , these values always reflect the
  latest profile and override anything stated previously. The
  "nutrition estimate is locked" rule elsewhere in this prompt
  applies to specific FOOD/MEAL estimates only, never to this
  overall calorie/macro goal.
- When the user asks about their calorie goal, daily intake, or
  macro targets, answer using EXACTLY these numbers. You may explain
  them, suggest surplus/deficit ranges around them, or add context 
  but the base numbers must match exactly.
"""

    return """
Backend-Calculated Nutrition Targets: Not available.

The user's profile is missing required information (age, height,
weight, gender, or fitness goal). If asked about their calorie or
macro goal, do NOT estimate a number  tell them what profile
information is still needed instead.
"""


def build_memory_block(long_term_memories):
    if not long_term_memories:
        return None

    memory_lines = "\n".join(
        f"- {m.memory_type} / {m.memory_key}: {m.memory_value}"
        for m in long_term_memories
    )

    return f"""Relevant Long-Term Memories (persistent preferences remembered about this user, retrieved by relevance to the current message):

{memory_lines}

These are the user's own stated, lasting preferences -- apply them
whenever they bear on your answer, without making the user repeat
them. This list is relevance-filtered, so it is not the complete set
of everything remembered about this user.

See LONG-TERM MEMORY above for how to use and update these.
"""


def build_summary_block(conversation_summary):
    if not conversation_summary:
        return None

    return f"""Conversation Summary (earlier context, already condensed):

{conversation_summary}

This summarizes parts of the conversation older than the Recent
Conversation below. Use it to understand ongoing context (an active
plan/meal/topic, prior decisions, constraints) that isn't repeated in
the recent messages, the Recent Conversation always has the exact
wording for anything recent.
"""


def build_conversation_block(chat_history, extract_display_text):
    if not chat_history:
        return None

    lines = "".join(
        f"{chat.sender.capitalize()}: {extract_display_text(chat)}\n"
        f"Time: {chat.created_at.strftime('%d %B %Y %I:%M %p')}\n\n"
        for chat in chat_history
    )

    return "Recent Conversation:\n\n" + lines


def build_meal_block(meals):
    if not meals:
        return ("Current Meal Context (Authoritative Database)\n\n"
                "No meals have been logged yet.")

    lines = "".join(
        f"- {meal.meal_name} | {meal.calories} kcal | "
        f"P {meal.protein} g, C {meal.carbs} g, F {meal.fat} g | "
        f"logged {meal.created_at.strftime('%A, %d %B %Y %I:%M %p')}\n"
        for meal in meals
    )

    return "Current Meal Context (Authoritative Database)\n\n" + lines


def build_plan_block(current_plan, plan_is_pending):
    if current_plan and plan_is_pending:
        return f"""Current Weekly Meal Plan (awaiting the user's confirmation):

{json.dumps(current_plan, indent=2)}

IMPORTANT:

This is the user's current meal plan.

If the user requests modifications:

- Modify this plan.
- Keep all unchanged days the same.
- Return the COMPLETE updated 7-day plan.
- Do not return only the changed day.
- Put the complete updated plan in the "plan" field.
"""

    if current_plan:
        return """The user HAS a saved weekly meal plan.

It is not printed here to keep this prompt small. Call
get_saved_diet_plan() whenever you need to see, discuss or modify it.

If the user requests modifications:

- Call get_saved_diet_plan() first.
- Modify the plan it returns.
- Keep all unchanged days the same.
- Return the COMPLETE updated 7-day plan.
- Do not return only the changed day.
- Put the complete updated plan in the "plan" field.
"""

    return "No current diet plan exists."


def build_context(
    system_prompt,
    intent_reminder,
    user,
    meals,
    chat_history,
    current_plan,
    nutrition_targets,
    conversation_summary,
    long_term_memories,
    plan_is_pending,
    extract_display_text,
):
    blocks = [
        system_prompt,
        build_profile_block(user),
        build_targets_block(nutrition_targets),
        build_memory_block(long_term_memories),
        build_summary_block(conversation_summary),
        build_conversation_block(chat_history, extract_display_text),
        build_meal_block(meals),
        build_plan_block(current_plan, plan_is_pending),
        intent_reminder,
    ]

    return [
        {"role": "system", "content": block}
        for block in blocks
        if block
    ]
