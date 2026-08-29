import { useState } from "react";
import "./Login.css";
import logo from "../assets/images/logo.svg";
import { Link, useNavigate } from "react-router-dom";
import { API_URL } from "../config";
import { FiEye, FiEyeOff } from "react-icons/fi";

function Login() {

    const navigate = useNavigate();

    const [formData, setFormData] = useState({
        email: "",
        password: ""
    });

    const [successMessage, setSuccessMessage] = useState("");
    const [errorMessage, setErrorMessage] = useState("");
    const [loading, setLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);

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

            const response = await fetch(`${API_URL}/login`, {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    email: formData.email,
                    password: formData.password
                })

            });

            const data = await response.json();

            if (response.ok) {

    localStorage.setItem("token", data.access_token);

    setSuccessMessage(data.message);

    navigate("/ai-assistant");

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

         <div className="login-container">

        <div className="login-header">
            <img src={logo} alt="Logo" className="logo" />
            <h1>Kalorie App</h1>
        </div>

        <h2>Welcome Back</h2>

        <p className="description">
            Log in to continue tracking your nutrition with AI.
        </p>

            <form onSubmit={handleSubmit}>

                <div className="form-group">

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

                <div className="form-group">

                    <label>Password</label>

                    <div className="password-field">

                        <input
                            type={showPassword ? "text" : "password"}
                            name="password"
                            placeholder="Enter your password"
                            minLength={8}
                            value={formData.password}
                            onChange={handleChange}
                            required
                        />

                        <button
                            type="button"
                            className="password-toggle"
                            onClick={() => setShowPassword(!showPassword)}
                            aria-label={showPassword ? "Hide password" : "Show password"}
                            title={showPassword ? "Hide password" : "Show password"}
                        >
                            {showPassword ? <FiEyeOff /> : <FiEye />}
                        </button>

                    </div>

                </div>

                <div className="forgot-password">

                    <Link to="/forgot-password">
                        Forgot Password?
                    </Link>

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

                <button type="submit" disabled={loading}>

                    {loading ? "Logging In..." : "Log In"}

                </button>

                <p className="signup-text">

                    Don't have an account?

                    <Link to="/signup">
                        <span> Sign Up</span>
                    </Link>

                </p>

            </form>

        </div>

    );

}

export default Login;