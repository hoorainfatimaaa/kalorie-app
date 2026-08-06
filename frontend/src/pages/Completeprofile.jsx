import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Completeprofile.css";

function CompleteProfile() {

    const navigate = useNavigate();

    const [formData, setFormData] = useState({
    age: "",
    gender: "",
    height: "",
    weight: "",
    activity_level: "",
    fitness_goal: "",
    dietary_preferences: "",
    allergies: ""
});

    const [successMessage, setSuccessMessage] = useState("");
    const [errorMessage, setErrorMessage] = useState("");
    const [loading, setLoading] = useState(false);

    const handleChange = (e) => {

        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });

        setSuccessMessage("");
        setErrorMessage("");

    };

    const handleSubmit = async (e) => {

        e.preventDefault();
        setLoading(true);
        setSuccessMessage("");
        setErrorMessage("");

        try {

            const token = localStorage.getItem("token");

            const response = await fetch("http://127.0.0.1:5000/complete-profile", {

                method: "PUT",

                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },

                body: JSON.stringify({
                age: Number(formData.age),
                gender: formData.gender,
                height: Number(formData.height),
                weight: Number(formData.weight),
                activity_level: formData.activity_level,
                fitness_goal: formData.fitness_goal,
                dietary_preferences: formData.dietary_preferences,
                allergies: formData.allergies
                })
            });

            const data = await response.json();

            if (response.ok) {

                setSuccessMessage(data.message);

                setTimeout(() => {

                    navigate("/ai-assistant");

                }, 500);

            } else {

                setErrorMessage(data.message || data.msg || "Failed to update profile.");

            }

        } catch (error) {

            console.error(error);

            setErrorMessage("Could not connect to the backend.");

        }

        setLoading(false);

    };

    return (

        <div className="complete-profile-container">

            <div className="complete-profile-card">

                <h1>Build Your Nutrition Profile</h1>

                <p className="profile-description">
                    Please provide the following information to personalize your nutrition recommendations.
                </p>

                <form onSubmit={handleSubmit}>

                    <div className="complete-profile-form-group">

                        <label>Age</label>

                        <input
                            type="number"
                            name="age"
                            placeholder="Enter your age"
                            value={formData.age}
                            onChange={handleChange}
                            required
                            min = "15"
                            max = "120"
                        />

                    </div>

                    <div className="complete-profile-form-group">

                        <label>Gender</label>

                        <select
                            name="gender"
                            value={formData.gender}
                            onChange={handleChange}
                            required
                        >
                            <option value="">Select Gender</option>
                            <option value="Male">Male</option>
                            <option value="Female">Female</option>
                        </select>

                    </div>

                    <div className="complete-profile-form-group">

                        <label>Height (cm)</label>

                        <input
                            type="number"
                            name="height"
                            placeholder="Enter your height"
                            value={formData.height}
                            onChange={handleChange}
                            min = "50"
                            max = "300"
                            required
                        />

                    </div>

                    <div className="complete-profile-form-group">

                        <label>Weight (kg)</label>

                        <input
                            type="number"
                            name="weight"
                            placeholder="Enter your weight"
                            value={formData.weight}
                            onChange={handleChange}
                            min = "30"
                            max = "500"
                            required
                        />

                    </div>
                    <div className="complete-profile-form-group">

    <label>Activity Level</label>

    <select
        name="activity_level"
        value={formData.activity_level}
        onChange={handleChange}
        required
    >
        <option value="">Select Activity Level</option>

        <option value="sedentary">
    Sedentary (Little or no exercise)
</option>

<option value="lightly_active">
    Lightly Active (1-3 days/week)
</option>

<option value="moderately_active">
    Moderately Active (3-5 days/week)
</option>

<option value="very_active">
    Very Active (6-7 days/week)
</option>

<option value="extra_active">
    Extra Active (Very intense exercise)
</option>

    </select>

</div>

                    <div className="complete-profile-form-group">

                        <label>Fitness Goal</label>

                        <select
                            name="fitness_goal"
                            value={formData.fitness_goal}
                            onChange={handleChange}
                            required
                        >
                            <option value="">Select Goal</option>
                            <option value="weight_loss">Lose Weight</option>

                            <option value="maintain">Maintain Weight</option>

                            <option value="weight_gain">Gain Weight</option>
                        </select>

                    </div>

                    <div className="complete-profile-form-group">

                        <label>Dietary Preferences (Optional)</label>

                        <textarea
                            name="dietary_preferences"
                            placeholder="e.g. Vegetarian, Vegan, Halal"
                            value={formData.dietary_preferences}
                            onChange={handleChange}
                        />

                    </div>

                    <div className="complete-profile-form-group">

                        <label>Allergies (Optional)</label>

                        <textarea
                            name="allergies"
                            placeholder="e.g. Peanuts, Dairy"
                            value={formData.allergies}
                            onChange={handleChange}
                        />

                    </div>

                    {successMessage && (

                        <div className="success-message">
                            {successMessage}
                        </div>

                    )}

                    {errorMessage && (

                        <div className="error-message">
                            {errorMessage}
                        </div>

                    )}

                    <button
                        type="submit"
                        disabled={loading}
                    >
                        {loading ? "Saving..." : "Save"}
                    </button>

                </form>

            </div>

        </div>

    );

}

export default CompleteProfile;