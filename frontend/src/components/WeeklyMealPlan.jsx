import { useEffect, useState } from "react";
import "./WeeklyMealPlan.css";

const DAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
];

function WeeklyMealPlan(){

    const [plan, setPlan] = useState({});
    const [selectedDay, setSelectedDay] = useState("Monday");


    useEffect(() => {

        const fetchPlan = async () => {

            try {

                const token = localStorage.getItem("token");


                const response = await fetch(
                    "https://kalorie-app.onrender.com/diet-plan",
                    {
                        headers:{
                            Authorization:`Bearer ${token}`
                        }
                    }
                );


                const data = await response.json();

                setPlan(data);

                const orderedDays = DAY_ORDER.filter(day => data[day]);

                if(orderedDays.length > 0){
                    setSelectedDay(orderedDays[0]);
                }


            }
            catch(error){

                console.error(
                    "Failed to fetch diet plan",
                    error
                );

            }

        };


        fetchPlan();


    }, []);
    const orderedDays = DAY_ORDER.filter(day => plan[day]);

    



    return (

        <div className="weekly-plan-card">


            <div className="weekly-plan-header">

                <h2>
                    Your Weekly Meal Plan
                </h2>

            </div>



            {
                 orderedDays.length === 0 ?

                (
                    <p>
                        No meal plan generated yet.
                        Ask your AI assistant to create one.
                    </p>
                )

                :

                (

                <>

                <div className="day-tabs">

                    {
                        orderedDays.map(day => (

                            <button

                            key={day}

                            className={
                                selectedDay === day
                                ?
                                "active-day"
                                :
                                ""
                            }

                            onClick={() =>
                                setSelectedDay(day)
                            }

                            >

                                {day}

                            </button>

                        ))

                    }

                </div>


                <div className="day-meals">


                {
                    plan[selectedDay]?.map(
                        (meal,index)=>(


                        <div 
                        className="meal-plan-item"
                        key={index}
                        >

                            <h3>
                                {meal.meal_type}
                            </h3>


                            <h4>
                                {meal.meal_name}
                            </h4>


                            <p>
                                {meal.description}
                            </p>


                            <div>

                            Calories:
                            {meal.calories} kcal

                            </div>


                            <div>

                            Protein:
                            {meal.protein}g

                            </div>


                        </div>


                    ))
                }


                </div>

                </>

                )

            }


        </div>

    );

}


export default WeeklyMealPlan;