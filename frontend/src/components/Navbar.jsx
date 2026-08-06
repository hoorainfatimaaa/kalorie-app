import { NavLink } from "react-router-dom";
import logo from "../assets/images/logo.svg";
import "./Navbar.css";

function Navbar() {

    return (

        <nav className="navbar">

            <div className="navbar-logo">

                <img
                    src={logo}
                    alt="AI Calorie Logo"
                    className="logo-image"
                />

                <h2 className="logo-text">
                Kalorie
                </h2>

            </div>

            <div className="navbar-links">


                <NavLink
                    to="/ai-assistant"
                    className={({ isActive }) =>
                        isActive ? "nav-link active-link" : "nav-link"
                    }
                >
                    Home
                </NavLink>


                <div className="navbar-right">

    <div className="nav-profile-dropdown">

        <button className="nav_profile-btn" title="nav-Profile">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
            </svg>
        </button>

        <div className="nav-dropdown-content">

            <NavLink
                to="/profile"
                className="dropdown-item"
            >
                My Profile
            </NavLink>

            <button
                className="nav-dropdown-item logout-item"
                onClick={() => {

                    localStorage.removeItem("token");
                    window.location.href = "/login";

                }}
            >
                Logout
            </button>

        </div>

    </div>

</div>

            </div>

        </nav>

    );

}

export default Navbar;