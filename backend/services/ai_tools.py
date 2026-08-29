import json
import logging

logger = logging.getLogger(__name__)


def _chat_module():
    from routes import chat as chat_module
    return chat_module


def _user(user_id):
    from models.user import User
    return User.query.get(user_id)


def get_user_profile(user_id):
    chat_module = _chat_module()
    user = _user(user_id)

    if user is None:
        return {"error": "user not found"}

    return {
        "profile": chat_module.build_profile_data(user),
        "nutrition_targets": chat_module.build_nutrition_targets(user),
    }


def get_today_progress(user_id):
    chat_module = _chat_module()
    user = _user(user_id)

    if user is None:
        return {"error": "user not found"}

    return chat_module.build_calorie_status_data(user, user_id)


def get_meal_history(user_id, limit=20):
    chat_module = _chat_module()

    try:
        limit = max(1, min(50, int(limit)))
    except (TypeError, ValueError):
        limit = 20

    return chat_module.build_meal_history_data(user_id, limit=limit)


def get_saved_diet_plan(user_id, weekday=None):
    chat_module = _chat_module()

    if weekday:
        rows = chat_module.get_plan_for_weekday(user_id, str(weekday).capitalize())
        return {"weekday": str(weekday).capitalize(), "meals": rows or []}

    plan = chat_module.build_effective_plan(user_id)

    if not plan:
        return {"plan": None, "note": "no saved diet plan exists for this user"}

    return {"plan": plan}


def get_weight_progress(user_id):
    chat_module = _chat_module()
    user = _user(user_id)

    if user is None:
        return {"error": "user not found"}

    return chat_module.build_progress_data(user, user_id)


TOOL_HANDLERS = {
    "get_user_profile": get_user_profile,
    "get_today_progress": get_today_progress,
    "get_meal_history": get_meal_history,
    "get_saved_diet_plan": get_saved_diet_plan,
    "get_weight_progress": get_weight_progress,
}


TOOL_SCHEMAS = [
    {
        "type": "function",
        "name": "get_user_profile",
        "description": (
            "The user's saved profile (age, gender, height, weight, activity "
            "level, fitness goal, dietary preferences, allergies, medical "
            "condition, country) together with their backend-calculated "
            "calorie and macro targets. Call this when the user asks about a "
            "profile field or a goal number that is not already given to you."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_today_progress",
        "description": (
            "Calories and macros the user has consumed so far today versus "
            "their daily goals, including how much is remaining and whether "
            "they have exceeded the target."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_meal_history",
        "description": (
            "Previously logged meals across all days, newest first. Call this "
            "for questions about earlier days ('what did I eat yesterday', "
            "'when did I last have pizza'). Meals logged TODAY are already "
            "provided to you in the Current Meal Context do not call this "
            "just to see today."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "How many recent meals to return (1-50, default 20).",
                }
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_saved_diet_plan",
        "description": (
            "The user's SAVED weekly diet plan, or a single weekday of it. "
            "Call this whenever you need to see, discuss, or modify the saved "
            "plan. When modifying, call it first so you can return the "
            "complete updated 7-day plan. If a plan is already shown to you in "
            "the prompt (one the user is still confirming), use that instead "
            "of calling this."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "weekday": {
                    "type": "string",
                    "description": (
                        "Optional single weekday, e.g. 'Monday'. Omit to get "
                        "the whole 7-day plan."
                    ),
                }
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_weight_progress",
        "description": (
            "The user's weight progress toward their fitness goal, as shown on "
            "the progress card."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
]


def execute_tool(name, arguments, user_id):
    handler = TOOL_HANDLERS.get(name)

    if handler is None:
        logger.warning("Model requested unknown tool %r", name)
        return json.dumps({"error": "unknown tool: %s" % name})

    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments) if arguments.strip() else {}
        except json.JSONDecodeError:
            logger.warning("Tool %s called with unparseable arguments", name)
            arguments = {}

    if not isinstance(arguments, dict):
        arguments = {}

    try:
        result = handler(user_id, **arguments)
    except TypeError as exc:
        logger.warning("Tool %s rejected arguments %s (%s); retrying with none",
                       name, sorted(arguments), exc)
        try:
            result = handler(user_id)
        except Exception as inner:
            logger.warning("Tool %s failed: %s: %s", name, type(inner).__name__, inner)
            return json.dumps({"error": "tool failed"})
    except Exception as exc:
        logger.warning("Tool %s failed: %s: %s", name, type(exc).__name__, exc)
        return json.dumps({"error": "tool failed"})

    return json.dumps(result, default=str)
