import { useState, useEffect } from "react";
import { FiLogOut } from "react-icons/fi";
import logo from "../assets/images/logo.svg";
import "./Navbar.css";

function Navbar() {

    const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

    useEffect(() => {

        if (!showLogoutConfirm) {
            return;
        }

        const onKeyDown = (e) => {
            if (e.key === "Escape") {
                setShowLogoutConfirm(false);
            }
        };

        window.addEventListener("keydown", onKeyDown);

        return () => window.removeEventListener("keydown", onKeyDown);

    }, [showLogoutConfirm]);

    const handleLogout = () => {
        localStorage.removeItem("token");
        window.location.href = "/login";
    };

    return (

        <>

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

                <div className="navbar-right">

    <button
        className="nav-logout-btn"
        title="Logout"
        onClick={() => setShowLogoutConfirm(true)}
    >
        <FiLogOut />
    </button>

</div>

            </div>

        </nav>

        {showLogoutConfirm && (

            <div
                className="logout-overlay"
                onClick={() => setShowLogoutConfirm(false)}
            >

                <div
                    className="logout-box"
                    role="dialog"
                    aria-modal="true"
                    aria-label="Confirm logout"
                    onClick={(e) => e.stopPropagation()}
                >

                    <p>Do you want to log out?</p>

                    <div className="logout-buttons">

                        <button
                            className="logout-cancel-btn"
                            onClick={() => setShowLogoutConfirm(false)}
                        >
                            Cancel
                        </button>

                        <button
                            className="logout-confirm-btn"
                            onClick={handleLogout}
                            autoFocus
                        >
                            Log Out
                        </button>

                    </div>

                </div>

            </div>

        )}

        </>

    );

}

export default Navbar;
