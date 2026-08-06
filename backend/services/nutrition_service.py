from math import floor

def calculate_bmr(user):
    

    if user.gender.lower() == "male":

        return (
            (10 * user.weight)
            + (6.25 * user.height)
            - (5 * user.age)
            + 5
        )

    return (
        (10 * user.weight)
        + (6.25 * user.height)
        - (5 * user.age)
        - 161
    )


def calculate_tdee(user):
    activity_multiplier = {

    "sedentary": 1.2,

    "lightly_active": 1.375,

    "moderately_active": 1.55,

    "very_active": 1.725,

    "extra_active": 1.9

}
    multiplier = activity_multiplier.get(
        user.activity_level,
        1.2
    )

    bmr = calculate_bmr(user)

    return bmr * multiplier


def calculate_calorie_goal(user):

    tdee = calculate_tdee(user)

    goal = user.fitness_goal


    if goal == "weight_loss":

        calorie_goal = tdee - 500

        if user.gender.lower() == "female":
            calorie_goal = max(calorie_goal, 1200)
        else:
            calorie_goal = max(calorie_goal, 1500)


    elif goal == "weight_gain":

        calorie_goal = tdee + 500


    else:

        calorie_goal = tdee


    return round(calorie_goal)

def calculate_macro_goals(user):

    calorie_goal = calculate_calorie_goal(user)

    goal = user.fitness_goal

    if goal == "weight_loss":

        protein_goal = user.weight * 1.8

    elif goal == "weight_gain":

        protein_goal = user.weight * 1.6

    else:

        protein_goal = user.weight * 1.2



    fat_goal = (calorie_goal * 0.25) / 9



    protein_calories = protein_goal * 4

    fat_calories = fat_goal * 9



    remaining_calories = (
        calorie_goal
        - protein_calories
        - fat_calories
    )

    carbs_goal = remaining_calories / 4


    return {

        "calorie_goal": round(calorie_goal),

        "protein_goal": round(protein_goal),

        "fat_goal": round(fat_goal),

        "carbs_goal": round(carbs_goal)

    }