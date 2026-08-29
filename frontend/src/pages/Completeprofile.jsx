import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Completeprofile.css";
import { API_URL } from "../config";

const COUNTRIES = [
    "Afghanistan", "Albania", "Algeria", "Argentina", "Armenia", "Australia",
    "Austria", "Azerbaijan", "Bahrain", "Bangladesh", "Belarus", "Belgium",
    "Bolivia", "Bosnia and Herzegovina", "Brazil", "Bulgaria", "Cambodia",
    "Cameroon", "Canada", "Chile", "China", "Colombia", "Costa Rica",
    "Croatia", "Cuba", "Cyprus", "Czech Republic", "Denmark", "Dominican Republic",
    "Ecuador", "Egypt", "El Salvador", "Estonia", "Ethiopia", "Finland",
    "France", "Georgia", "Germany", "Ghana", "Greece", "Guatemala",
    "Honduras", "Hong Kong", "Hungary", "Iceland", "India", "Indonesia",
    "Iran", "Iraq", "Ireland", "Israel", "Italy", "Ivory Coast", "Jamaica",
    "Japan", "Jordan", "Kazakhstan", "Kenya", "Kuwait", "Kyrgyzstan", "Laos",
    "Latvia", "Lebanon", "Libya", "Lithuania", "Luxembourg", "Malaysia",
    "Maldives", "Mali", "Malta", "Mexico", "Moldova", "Mongolia", "Morocco",
    "Myanmar", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Nigeria",
    "North Korea", "North Macedonia", "Norway", "Oman", "Pakistan", "Panama",
    "Paraguay", "Peru", "Philippines", "Poland", "Portugal", "Qatar",
    "Romania", "Russia", "Rwanda", "Saudi Arabia", "Senegal", "Serbia",
    "Singapore", "Slovakia", "Slovenia", "Somalia", "South Africa",
    "South Korea", "Spain", "Sri Lanka", "Sudan", "Sweden", "Switzerland",
    "Syria", "Taiwan", "Tajikistan", "Tanzania", "Thailand", "Tunisia",
    "Turkey", "Turkmenistan", "Uganda", "Ukraine",
    "United Arab Emirates", "United Kingdom", "United States", "Uruguay",
    "Uzbekistan", "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe"
];

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
    allergies: "",
    medical_condition: "",
    country: "",
    region: ""
});

    const [successMessage, setSuccessMessage] = useState("");
    const [errorMessage, setErrorMessage] = useState("");
    const [loading, setLoading] = useState(false);

    const handleChange = (e) => {

        const { name, value } = e.target;

        setFormData((previous) => ({
            ...previous,
            [name]: value,
            ...(name === "country" ? { region: "" } : {})
        }));

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

            const response = await fetch(`${API_URL}/complete-profile`, {

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
                allergies: formData.allergies,
                medical_condition: formData.medical_condition,
                country: formData.country,
                region: formData.region
                })
            });

            const data = await response.json();

            if (response.ok) {

                setSuccessMessage(data.message);

                setTimeout(() => {

                    navigate("/ai-assistant");

                }, 500);

            } else {

                setErrorMessage(data.error || data.message || data.msg || "Failed to update profile.");

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

                        <label>Country</label>

                        <select
                            name="country"
                            value={formData.country}
                            onChange={handleChange}
                            required
                        >
                            <option value="">Select Country</option>
                            {COUNTRIES.map((country) => (
                                <option key={country} value={country}>
                                    {country}
                                </option>
                            ))}
                        </select>

                    </div>

                    {formData.country && (

                        <div className="complete-profile-form-group">

                            <label>Region / State / Province</label>

                            <input
                                type="text"
                                name="region"
                                placeholder="e.g. Punjab, California, Lombardy"
                                value={formData.region}
                                onChange={handleChange}
                                required
                            />

                        </div>

                    )}

                    <div className="complete-profile-form-group">

                        <label>Dietary Preferences</label>

                        <textarea
                            name="dietary_preferences"
                            placeholder="e.g. Vegetarian, Vegan, Halal — or None"
                            value={formData.dietary_preferences}
                            onChange={handleChange}
                            required
                        />

                    </div>

                    <div className="complete-profile-form-group">

                        <label>Allergies</label>

                        <textarea
                            name="allergies"
                            placeholder="e.g. Peanuts, Dairy — or None"
                            value={formData.allergies}
                            onChange={handleChange}
                            required
                        />

                    </div>

                    <div className="complete-profile-form-group">

                        <label>Medical / Dietary Condition</label>

                        <textarea
                            name="medical_condition"
                            placeholder="e.g. Diabetes, Hypertension — or None"
                            value={formData.medical_condition}
                            onChange={handleChange}
                            required
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