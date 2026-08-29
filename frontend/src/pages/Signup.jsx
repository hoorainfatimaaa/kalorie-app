import {useState} from "react";
import "./Signup.css";
import logo from "../assets/images/logo.svg";
import {Link, useNavigate} from "react-router-dom";
import { API_URL } from "../config";
import { FiEye, FiEyeOff } from "react-icons/fi";

function Signup() {

  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });

  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setSuccessMessage("");
    setErrorMessage("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    setSuccessMessage("");
    setErrorMessage("");

    if (formData.password.length < 8) {
      setErrorMessage("Password must be at least 8 characters long.");
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setErrorMessage("Passwords do not match.");
      return;
    }
    const fullName = formData.full_name.trim();

const nameRegex = /^[A-Za-z\s'-]+$/;

if (!nameRegex.test(fullName)) {
    setErrorMessage(
        "Full name can only contain letters, spaces, apostrophes, and hyphens."
    );
    return;
}

if (fullName.split(/\s+/).length < 2) {
    setErrorMessage("Please enter your first and last name.");
    return;
}
if (fullName.length < 3) {
    setErrorMessage("Full name must be at least 3 characters long.");
    return;
}

if (fullName.length > 50) {
    setErrorMessage("Full name cannot exceed 50 characters.");
    return;
}

    try {
      const response = await fetch(`${API_URL}/signup`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          full_name: formData.full_name,
          email: formData.email,
          password: formData.password,
        }),
      });

      const data = await response.json();
      

      if (response.ok) {

    localStorage.setItem(
        "token",
        data.access_token
    );

    setSuccessMessage(
        "Account created successfully! Completing profile..."
    );

    setFormData({
        full_name: "",
        email: "",
        password: "",
        confirmPassword: "",
    });

    setTimeout(() => {
        navigate("/complete-profile");
    }, 500);

}

    } catch (error) {
      console.error(error);
      setErrorMessage("Could not connect to the backend.");
    }
  };

  return (
    <div className="signup-container">

      <div className="signup-header">

  <img 
    src={logo} 
    alt="AI Calorie App Logo" 
    className="logo" 
  />
    <h1>Kalorie App</h1>

</div>
  

      <h2>Create an Account</h2>

      <p className="description">
        Join Kalorie App and start tracking your meals and nutrition with AI.
      </p>

      <form onSubmit={handleSubmit}>

        <div className="form-group">
          <label>Full Name</label>
          <input
            type="text"
            name="full_name"
            placeholder="Enter your full name"
            value={formData.full_name}
            onChange={handleChange}
            required
          />
        </div>

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
              placeholder="Create a password"
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

        <div className="form-group">
          <label>Confirm Password</label>
          <div className="password-field">

            <input
              type={showConfirmPassword ? "text" : "password"}
              name="confirmPassword"
              placeholder="Confirm your password"
              minLength={8}
              value={formData.confirmPassword}
              onChange={handleChange}
              required
            />

            <button
              type="button"
              className="password-toggle"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              aria-label={
                showConfirmPassword ? "Hide password" : "Show password"
              }
              title={showConfirmPassword ? "Hide password" : "Show password"}
            >
              {showConfirmPassword ? <FiEyeOff /> : <FiEye />}
            </button>

          </div>
        </div>

        {successMessage && (<div 
        className="success-message">
            {successMessage} </div>
        )}

        {errorMessage && (
          <div className="error-message">
            {errorMessage}
          </div>
        )}

        <button type="submit">
          Sign Up
        </button>

        <p className="login-text">
          Already have an account?
          <Link to="/login">
            <span> Log In</span>
          </Link>
        </p>
      </form>
    </div>
  );
}

export default Signup;