import { useState, useEffect } from "react";
import "./Forgotpassword.css";
import logo from "../assets/images/logo.svg";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { API_URL } from "../config";
import { FiEye, FiEyeOff } from "react-icons/fi";

function ResetPassword() {

    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const token = searchParams.get("token") || "";

    const [formData, setFormData] = useState({
        password: "",
        confirmPassword: ""
    });

    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [successMessage, setSuccessMessage] = useState("");
    const [errorMessage, setErrorMessage] = useState(
        token ? "" : "This reset link is invalid or has expired."
    );
    const [loading, setLoading] = useState(false);
    const [tokenValid, setTokenValid] = useState(token ? null : false);

    useEffect(() => {

        if (!token) {
            return;
        }

        const check = async () => {

            try {

                const response = await fetch(`${API_URL}/reset-password/validate`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ token })
                });

                const data = await response.json();

                if (response.ok && data.valid) {
                    setTokenValid(true);
                } else {
                    setTokenValid(false);
                    setErrorMessage(data.message);
                }

            } catch (error) {
                console.error(error);
                setTokenValid(false);
                setErrorMessage("Could not connect to the backend.");
            }
        };

        check();

    }, [token]);

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

        if (formData.password.length < 8) {
            setErrorMessage("Password must be at least 8 characters long.");
            return;
        }

        if (formData.password !== formData.confirmPassword) {
            setErrorMessage("Passwords do not match.");
            return;
        }

        setLoading(true);
        setSuccessMessage("");
        setErrorMessage("");

        try {

            const response = await fetch(`${API_URL}/reset-password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    token: token,
                    password: formData.password
                })
            });

            const data = await response.json();

            if (response.ok) {
                setSuccessMessage(data.message);
                setFormData({ password: "", confirmPassword: "" });
                setTimeout(() => navigate("/login"), 2000);
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

            <h2>Reset Password</h2>

            <p className="f_description">
                Choose a new password for your account.
            </p>

            <form onSubmit={handleSubmit}>

                {tokenValid === false && (
                    <div className="error-message">
                        {errorMessage}
                    </div>
                )}

                {tokenValid && (
                    <>
                        <div className="f_form-group">

                            <label>New Password</label>

                            <div className="password-field">

                                <input
                                    type={showPassword ? "text" : "password"}
                                    name="password"
                                    placeholder="Enter a new password"
                                    minLength={8}
                                    value={formData.password}
                                    onChange={handleChange}
                                    required
                                />

                                <button
                                    type="button"
                                    className="password-toggle"
                                    onClick={() => setShowPassword(!showPassword)}
                                    title={showPassword ? "Hide password" : "Show password"}
                                    aria-label={
                                        showPassword
                                            ? "Hide password"
                                            : "Show password"
                                    }
                                >
                                    {showPassword ? <FiEyeOff /> : <FiEye />}
                                </button>

                            </div>

                        </div>

                        <div className="f_form-group">

                            <label>Confirm New Password</label>

                            <div className="password-field">

                                <input
                                    type={showConfirmPassword ? "text" : "password"}
                                    name="confirmPassword"
                                    placeholder="Re-enter the new password"
                                    minLength={8}
                                    value={formData.confirmPassword}
                                    onChange={handleChange}
                                    required
                                />

                                <button
                                    type="button"
                                    className="password-toggle"
                                    onClick={() =>
                                        setShowConfirmPassword(!showConfirmPassword)
                                    }
                                    title={
                                        showConfirmPassword
                                            ? "Hide password"
                                            : "Show password"
                                    }
                                    aria-label={
                                        showConfirmPassword
                                            ? "Hide password"
                                            : "Show password"
                                    }
                                >
                                    {showConfirmPassword ? <FiEyeOff /> : <FiEye />}
                                </button>

                            </div>

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
                            {loading ? "Saving..." : "Reset Password"}
                        </button>
                    </>
                )}

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

export default ResetPassword;
