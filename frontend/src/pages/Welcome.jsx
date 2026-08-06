import { Link } from "react-router-dom";
import "./Welcome.css";
import logo from "../assets/images/logo.svg";

function Welcome() {
  return (
    <div className="welcome-page">
      <div className="hero-content">
        <img
          src={logo}
          alt="AI Calorie App Logo"
          className="logo"
        />
        <h1>Welcome to Kalorie</h1>

        <div className="hero-text">
          <p className="welcome-description">
            Your AI-powered nutrition assistant. Track your meals using text
            or images and get instant calorie estimates. It even generates
            your personalized nutritional plan.
          </p>

          <div className="button-row">
            <Link to="/signup">
              <button className="primary">Sign Up</button>
            </Link>

            <Link to="/login">
              <button className="secondary">Log In</button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Welcome;