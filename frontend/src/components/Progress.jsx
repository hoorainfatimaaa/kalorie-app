import { useState, useEffect } from "react";
import "./Progress.css";

function DonutChart({ percent, size, strokeWidth, color, centerValue, centerLabel, glow, valueFontSize }) {

    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (percent / 100) * circumference;

    return (

        <div className={`donut-wrapper ${glow ? "donut-glow" : ""}`} style={{ width: size, height: size }}>

            <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>

                <circle
                    className="donut-track"
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    strokeWidth={strokeWidth}
                    fill="none"
                />

                <circle
                    className="donut-fill"
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    strokeWidth={strokeWidth}
                    fill="none"
                    stroke={color}
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    strokeLinecap="round"
                    transform={`rotate(-90 ${size / 2} ${size / 2})`}
                />

            </svg>

            <div className="donut-center">
                <span
                    className="donut-value"
                    style={valueFontSize ? { fontSize: valueFontSize } : undefined}
                >
                    {centerValue}
                </span>
                {centerLabel && <span className="donut-label">{centerLabel}</span>}
            </div>

        </div>

    );

}

function Progress({ compact = false, refresh }) {

    const [progress, setProgress] = useState({

        calories: 0,
        calorieGoal: 0,

        protein: 0,
        proteinGoal: 0,

        carbs: 0,
        carbsGoal: 0,

        fat: 0,
        fatGoal: 0

    });

    useEffect(() => {

        const fetchProgress = async () => {

            try {

                const token = localStorage.getItem("token");

                const response = await fetch(
                    "https://kalorie-app.onrender.com/progress",
                    {
                        method: "GET",

                        headers: {
                            Authorization: `Bearer ${token}`
                        }
                    }
                );

                const data = await response.json();

                if (data.success) {

                    setProgress({
                        calories: data.calories,
                        calorieGoal: data.calorieGoal,

                        protein: data.protein,
                        proteinGoal: data.proteinGoal,

                        carbs: data.carbs,
                        carbsGoal: data.carbsGoal,

                        fat: data.fat,
                        fatGoal: data.fatGoal
                    });

                }

            }

            catch (error) {

                console.log(error);

            }

        };

        fetchProgress();

    }, [refresh]);

    const remainingCalories = Math.max(
        0,
        progress.calorieGoal - progress.calories
    );

    const hasMeals = progress.calories > 0;

    const caloriePercent = Math.min(
        (progress.calories / (progress.calorieGoal || 1)) * 100,
        100
    );

    const proteinPercent = Math.min(
        (progress.protein / (progress.proteinGoal || 1)) * 100,
        100
    );

    const carbsPercent = Math.min(
        (progress.carbs / (progress.carbsGoal || 1)) * 100,
        100
    );

    const fatPercent = Math.min(
        (progress.fat / (progress.fatGoal || 1)) * 100,
        100
    );

    const isOverLimit =
        progress.calorieGoal > 0 && progress.calories > progress.calorieGoal;

    const isProteinOver =
        progress.proteinGoal > 0 && progress.protein > progress.proteinGoal;

    const isCarbsOver =
        progress.carbsGoal > 0 && progress.carbs > progress.carbsGoal;

    const isFatOver =
        progress.fatGoal > 0 && progress.fat > progress.fatGoal;

    const mainSize = compact ? 70 : 100;
    const mainStroke = compact ? 6 : 8;
    const macroSize = compact ? 34 : 54;
    const macroStroke = compact ? 3 : 5;

    return (

        <section className={`progress-section ${compact ? "compact" : ""}`}>

            <h2>Today's Progress</h2>


            <div className="p-progress-charts">

                <div className="p-main-chart-card">

                    <DonutChart
                        percent={caloriePercent}
                        size={mainSize}
                        strokeWidth={mainStroke}
                        color={isOverLimit ? "#D9534F" : "#7BAE7F"}
                        centerValue={`${progress.calories}`}
                        centerLabel={`/ ${progress.calorieGoal} kcal`}
                        glow={isOverLimit}
                    />

                    <div className="p-remaining-calories">
                        {remainingCalories} kcal
                    </div>

                    <span className="p-remaining-text">
                        Remaining for Today
                    </span>

                </div>

                <div className="p-macro-charts">

                    <div className="p-macro-card">

                        <DonutChart
                            percent={proteinPercent}
                            size={macroSize}
                            strokeWidth={macroStroke}
                            color={isProteinOver ? "#D9534F" : "#4F8F8B"}
                            centerValue={`${progress.protein}g`}
                            glow={isProteinOver}
                            valueFontSize="13px"
                        />

                        <div className="p-macro-info">
                            <h3>Protein</h3>
                            <p>{progress.protein} / {progress.proteinGoal} g</p>
                        </div>

                    </div>

                    <div className="p-macro-card">

                        <DonutChart
                            percent={carbsPercent}
                            size={macroSize}
                            strokeWidth={macroStroke}
                            color={isCarbsOver ? "#D9534F" : "#E4B363"}
                            centerValue={`${progress.carbs}g`}
                            glow={isCarbsOver}
                            valueFontSize="13px"
                        />

                        <div className="p-macro-info">
                            <h3>Carbohydrates</h3>
                            <p>{progress.carbs} / {progress.carbsGoal} g</p>
                        </div>

                    </div>

                    <div className="p-macro-card">

                        <DonutChart
                            percent={fatPercent}
                            size={macroSize}
                            strokeWidth={macroStroke}
                            color={isFatOver ? "#D9534F" : "#D97D82"}
                            centerValue={`${progress.fat}g`}
                            glow={isFatOver}
                            valueFontSize="13px"
                        />

                        <div className="p-macro-info">
                            <h3>Fat</h3>
                            <p>{progress.fat} / {progress.fatGoal} g</p>
                        </div>

                    </div>

                </div>

            </div>

        </section>

    );

}

export default Progress;