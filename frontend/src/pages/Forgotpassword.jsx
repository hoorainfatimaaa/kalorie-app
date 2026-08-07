import { useState } from "react";
import "./Forgotpassword.css";
import logo from "../assets/images/logo.svg";
import { Link } from "react-router-dom";

function ForgotPassword() {

    const [formData, setFormData] = useState({
        email: ""
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

    console.log("Forgot Password button clicked!");

    setLoading(true);
    setSuccessMessage("");
    setErrorMessage("");

        try {

            const response = await fetch("https://kalorie-app.onrender.com/forgot-password", {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    email: formData.email
                })

            });

            const data = await response.json();

            if (response.ok) {

                setSuccessMessage(data.message);

                setFormData({
                    email: ""
                });

            } else {

                setErrorMessage(data.message);

            }

        } catch (error) {

            console.error(error);
            setErrorMessage("Could not connect to the backend.");

        }

        setLoading(false);

    };

    return (

    <div className="forgot-container">

        <div className="forgot-header">
            <img src={logo} alt="AI Calorie App Logo" className="logo" />
            <h1>Kalorie App</h1>
        </div>

        <h2>Forgot Password?</h2>

        <p className="f_description">
            Enter your email address and we'll send you a password reset link.
        </p>

        <form onSubmit={handleSubmit}>

            <div className="f_form-group">

                <label>Email</label>

                <input
                    type="email"
                    name="email"
                    placeholder="Enter your email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                />

            </div>

            {successMessage &&
                <div className="success-message">
                    {successMessage}
                </div>
            }

            {errorMessage &&
                <div className="error-message">
                    {errorMessage}
                </div>
            }

            <button type="submit" disabled={loading}>

                {loading ? "Sending..." : "Send Reset Link"}

            </button>

            <p className="back-login">

                Back to

                <Link to="/login">
                    <span> Log In</span>
                </Link>

            </p>

        </form>

    </div>

);
}
export default ForgotPassword;