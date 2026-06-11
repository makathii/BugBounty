// src/components/layout/Navbar.jsx
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './Navbar.css';

const Navbar = () => {
    const { user, logout, isTriager, isCompany, isResearcher } = useAuth();
    const location = useLocation();

    const handleLogout = () => {
        logout();
    };

    return (
        <nav className="navbar">
            <div className="nav-container">
                <Link to="/" className="nav-logo">
                    BugBounty
                </Link>

                <div className="nav-menu">
                    {user ? (
                        <>
                            <Link
                                to="/dashboard"
                                className={`nav-link ${location.pathname === '/dashboard' ? 'active' : ''}`}
                            >
                                Dashboard
                            </Link>

                            {/* COMPANY USER LINKS */}
                            {isCompany() && (
                                <>
                                    <Link
                                        to="/company/programs"
                                        className={`nav-link ${location.pathname === '/company/programs' ? 'active' : ''}`}
                                    >
                                        My Programs
                                    </Link>
                                    <Link
                                        to="/company/reports"
                                        className={`nav-link ${location.pathname === '/company/reports' ? 'active' : ''}`}
                                    >
                                        Company Reports
                                    </Link>
                                    <Link
                                        to="/company/programs/create"
                                        className={`nav-link ${location.pathname === '/company/programs/create' ? 'active' : ''}`}
                                    >
                                        Create Program
                                    </Link>
                                </>
                            )}

                            {/* RESEARCHER USER LINKS */}
                            {isResearcher() && (
                                <>
                                    <Link
                                        to="/submit"
                                        className={`nav-link ${location.pathname === '/submit' ? 'active' : ''}`}
                                    >
                                        Submit Report
                                    </Link>
                                    <Link
                                        to="/reports"
                                        className={`nav-link ${location.pathname === '/reports' ? 'active' : ''}`}
                                    >
                                        My Reports
                                    </Link>
                                    <Link
                                        to="/programs"
                                        className={`nav-link ${location.pathname === '/programs' ? 'active' : ''}`}
                                    >
                                        Find Programs
                                    </Link>
                                </>
                            )}

                            {/* TRIAGER/ADMIN LINKS */}
                            {isTriager() && (
                                <>
                                    <Link
                                        to="/triage"
                                        className={`nav-link ${location.pathname === '/triage' ? 'active' : ''}`}
                                    >
                                        Triage Reports
                                    </Link>
                                    <a
                                        href={`${(process.env.REACT_APP_API_URL || 'http://localhost:8000/api').replace(/\/api\/?$/, '')}/admin/`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="nav-link"
                                    >
                                        Admin
                                    </a>
                                </>
                            )}

                            <div className="nav-user">
                                <span>Welcome, {user.first_name || user.username}</span>
                                <button onClick={handleLogout} className="logout-btn">
                                    Logout
                                </button>
                            </div>
                        </>
                    ) : (
                        <>
                            <Link
                                to="/login"
                                className={`nav-link ${location.pathname === '/login' ? 'active' : ''}`}
                            >
                                Login
                            </Link>
                            <Link
                                to="/register/researcher"
                                className={`nav-link ${location.pathname === '/register/researcher' ? 'active' : ''}`}
                            >
                                For Researchers
                            </Link>
                            <Link
                                to="/register/company"
                                className={`nav-link ${location.pathname === '/register/company' ? 'active' : ''}`}
                            >
                                For Companies
                            </Link>
                        </>
                    )}
                </div>
            </div>
        </nav>
    );
};

export default Navbar;