import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import WeeklyMealPlan from "../components/WeeklyMealPlan";
import "./Profile.css";
import { FiChevronLeft, FiChevronRight } from "react-icons/fi";

function Profile() {

    const navigate = useNavigate();

    const [formData, setFormData] = useState({
        full_name: "",
        email: "",
        age: "",
        gender: "",
        height: "",
        weight: "",
        activity_level: "",
        fitness_goal: "",
        dietary_preferences: "",
        allergies: ""
    });

    const [message, setMessage] = useState("");

    const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

    useEffect(() => {

        const loadProfile = async () => {

            try {

                const token = localStorage.getItem("token");

                const response = await fetch(
                    "http://127.0.0.1:5000/profile",
                    {
                        method: "GET",
                        headers: {
                            Authorization: `Bearer ${token}`
                        }
                    }
                );

                const data = await response.json();

                if (response.ok) {
                    setFormData(data);
                } else {
                    setMessage(data.message || "Failed to load profile.");
                }

            } catch (error) {

                console.error(error);
                setMessage("Unable to connect to the server.");

            }

        };

        loadProfile();

    }, []);

    const handleChange = (e) => {

        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });

    };

    const saveProfile = async () => {

        try {

            const token = localStorage.getItem("token");

            const response = await fetch(
                "http://127.0.0.1:5000/profile",
                {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`
                    },
                    body: JSON.stringify({
                    full_name: formData.full_name,
                    age: Number(formData.age),
                    gender: formData.gender,
                    height: Number(formData.height),
                    weight: Number(formData.weight),
                    activity_level: formData.activity_level,
                    fitness_goal: formData.fitness_goal,
                    dietary_preferences: formData.dietary_preferences,
                    allergies: formData.allergies
                  })
                }
            );

            const data = await response.json();

            if (response.ok) {
                setMessage("Profile updated successfully!");
            } else {
                setMessage(data.message || "Failed to update profile.");
            }

        } catch (error) {

            console.error(error);
            setMessage("Unable to connect to the server.");

        }

    };

    const initials = formData.full_name
        ? formData.full_name
              .trim()
              .split(/\s+/)
              .map((part) => part[0])
              .slice(0, 2)
              .join("")
              .toUpperCase()
        : "?";

    return (

    <>
        <Navbar />

        <div className="profile-container">


            {message && (
                <p className="profile-message">
                    {message}
                </p>
            )}

            <div className="profile-layout">

    <div className="profile-top-left">

        <div className="profile-card">

            <div className="profile-card-header">

                <span className="profile-card-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                    </svg>
                </span>

                <h2>Personal Information</h2>

            </div>


            <div className="profile-form-row">


                <div className="profile-form-group">

                    <label>Full Name</label>

                    <input
                        type="text"
                        name="full_name"
                        value={formData.full_name}
                        onChange={handleChange}
                    />

                </div>



                <div className="profile-form-group">

                    <label>Age</label>

                    <input
                        type="number"
                        name="age"
                        value={formData.age}
                        onChange={handleChange}
                    />

                </div>


            </div>



            <div className="profile-form-row">


                <div className="profile-form-group">

                    <label>Email</label>

                    <input
                        type="email"
                        name="email"
                        value={formData.email}
                        disabled
                    />

                </div>



                <div className="profile-form-group">

                    <label>Gender</label>

                    <select
                        name="gender"
                        value={formData.gender}
                        onChange={handleChange}
                    >

                        <option value="">Select Gender</option>
                        <option value="Male">Male</option>
                        <option value="Female">Female</option>

                    </select>

                </div>


            </div>


        </div>


        <div className="profile-card">


            <div className="profile-card-header">


                <span className="profile-card-icon">

                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8Z" />
                    </svg>

                </span>


                <h2>Health Information</h2>


            </div>



            <div className="profile-form-row">


                <div className="profile-form-group">

                    <label>Height (cm)</label>

                    <input
                        type="number"
                        name="height"
                        value={formData.height}
                        onChange={handleChange}
                    />

                </div>



                <div className="profile-form-group">

                    <label>Weight (kg)</label>

                    <input
                        type="number"
                        name="weight"
                        value={formData.weight}
                        onChange={handleChange}
                    />

                </div>


            </div>



            <div className="profile-form-group">

                <label>Activity Level</label>

                <select
                    name="activity_level"
                    value={formData.activity_level}
                    onChange={handleChange}
                >

                    <option value="">Select Activity Level</option>
                    <option value="sedentary">
                        Sedentary
                    </option>

                    <option value="lightly_active">
                        Lightly Active
                    </option>

                    <option value="moderately_active">
                        Moderately Active
                    </option>

                    <option value="very_active">
                        Very Active
                    </option>


                    <option value="extra_active">
                        Extra Active
                    </option>


                </select>


            </div>



            <div className="profile-form-group">


                <label>Fitness Goal</label>


                <select
                    name="fitness_goal"
                    value={formData.fitness_goal}
                    onChange={handleChange}
                >

                    <option value="">Select Goal</option>

                    <option value="weight_loss">
                        Lose Weight
                    </option>

                    <option value="maintain">
                        Maintain Weight
                    </option>

                    <option value="weight_gain">
                        Gain Weight
                    </option>

                </select>


            </div>



        </div>



    </div>

    <div
        className={`profile-sidebar-overlay ${mobileSidebarOpen ? "active" : ""}`}
        onClick={() => setMobileSidebarOpen(false)}
    ></div>

    <button
        className={`profile-sidebar-toggle ${mobileSidebarOpen ? "open" : ""}`}
        onClick={() => setMobileSidebarOpen(prev => !prev)}
        aria-label={mobileSidebarOpen ? "Close meal plan" : "Open meal plan"}
        title={mobileSidebarOpen ? "Close" : "Weekly Meal Plan"}
    >
        {mobileSidebarOpen ? <FiChevronLeft /> : <FiChevronRight />}
    </button>

    <div className={`profile-weekly ${mobileSidebarOpen ? "mobile-open" : ""}`}>

        <WeeklyMealPlan />

    </div>



</div>


<div className="profile-bottom">



    <div className="profile-card">


        <div className="profile-card-header">

            <span className="profile-card-icon">

                🌱

            </span>

            <h2>Preferences</h2>

        </div>



        <div className="profile-preferences-grid">


            <div className="profile-form-group">


                <label>
                    Dietary Preferences
                </label>


                <textarea

                    name="dietary_preferences"

                    value={formData.dietary_preferences}

                    onChange={handleChange}

                />


            </div>




            <div className="profile-form-group">


                <label>
                    Allergies
                </label>


                <textarea

                    name="allergies"

                    value={formData.allergies}

                    onChange={handleChange}

                />


            </div>


        </div>



        <div className="profile-actions-card">


            <button
                className="profile-save-btn"
                onClick={saveProfile}
            >

                Save

            </button>


        </div>



    </div>



</div>
        </div>

    </>

);
}

export default Profile;