import {useEffect,useState} from "react";
import "./MealHistory.css";


function MealHistory({mealUpdated,setProgressRefresh}){

    const [meals,setMeals]=useState([]);
    const [deleteId, setDeleteId] = useState(null);
    const deleteMeal = async (mealId) => {
    

    try {
        const token = localStorage.getItem("token");

        const response = await fetch(
            `https://kalorie-app.onrender.com/meals/${mealId}`,
            {
                method: "DELETE",
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            }
        );

        if (response.ok) {
            console.log("Meal deleted, refreshing progress");
            setMeals(meals.filter((meal) => meal.id !== mealId));
            setProgressRefresh(prev => prev + 1);
        } else {
            const data = await response.json();
            alert(data.message || "Failed to delete meal.");
        }
    } catch (error) {
        console.log(error);
    }
};


    useEffect(()=>{


        const fetchMeals=async()=>{


            try{

                const token=
                localStorage.getItem("token");


                const response =
                await fetch(
                "https://kalorie-app.onrender.com/meal-history",
                {
                    headers:{
                        Authorization:
                        `Bearer ${token}`
                    }
                });


                const data =
                await response.json();


                setMeals(data);


            }

            catch(error){

                console.log(error);

            }


        };


        fetchMeals();


    },[mealUpdated]);



    return(

        <div className="meal-history">


            <h2>
                Meal History
            </h2>


            <div className="meal-list">


            {
            meals.length===0 ? (

                <p>
                    No meals logged yet.
                </p>

            ) :


            meals.map(meal=>(


                <div
                className="meal-card"
                key={meal.id}
                >

                    <div className="meal-header">
    <h3>{meal.meal_name}</h3>

    <button
        className="delete-btn"
        onClick={() => setDeleteId(meal.id)}
        title="Delete meal"
    >
        🗑️
    </button>
</div>


                    <p>
                    {meal.calories} kcal
                    </p>


                    <span>
                    Protein: {meal.protein}g
                    </span>

                    <span>
                    Carbs: {meal.carbs}g
                    </span>

                    <span>
                    Fat: {meal.fat}g
                    </span>


                    <small>
                    {meal.date} {meal.time}
                    </small>
                    


                </div>


            ))

            }


            </div>
            {deleteId && (
    <div className="confirm-overlay">

        <div className="confirm-box">

            <p>Are you sure you want to delete this meal?</p>

            <div className="confirm-buttons">

                <button
                    onClick={() => setDeleteId(null)}
                    className="cancel-btn"
                >
                    Cancel
                </button>

                <button
                    onClick={() => {
                        deleteMeal(deleteId);
                        setDeleteId(null);
                    }}
                    className="confirm-delete-btn"
                >
                    Delete
                </button>

            </div>

        </div>

    </div>
)}


        </div>

    );

}


export default MealHistory;