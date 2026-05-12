// src/App.jsx
import React from 'react';
import {
    BrowserRouter as Router,
    Routes,
    Route,
    Navigate,
    useNavigate
} from 'react-router-dom';

import { AuthProvider, useAuth } from './contexts/AuthContext';

import Navbar from './components/layout/Navbar';
import RoleBasedDashboard from './components/common/RoleBasedDashboard';
import ProgramBrowser from "./components/researcher/ProgramBrowser";
import ProgramDetailResearcher from "./components/researcher/ProgramDetailResearcher";

// Pages
import Home from './pages/Home';
import Triage from './pages/Triage';

// Auth
import Login from './components/auth/Login';
import ResearcherRegister from './pages/researcher/ResearcherRegister';
import CompanyRegister from './pages/company/CompanyRegister';
import ForgotPassword from './components/auth/ForgotPassword';
import ResetPassword from './components/auth/ResetPassword';
import TwoFactorSetup from './components/auth/TwoFactorSetup';
import TwoFactorVerify from './components/auth/TwoFactorVerify';
import TwoFactorSettings from './components/auth/TwoFactorSettings';

// Reports
import SubmitReport from './pages/reports/SubmitReport';
import Reports from './pages/reports/Reports';

// Company
import CompanyRegistration from './components/company/CompanyRegistration';
import CompanyDashboard from './pages/company/CompanyDashboard';

import './App.css';
import ReportDetail from "./pages/reports/ReportDetail";

/* =========================
   Protected Route Components
   ========================= */

const ProtectedRoute = ({ children }) => {
    const { user, loading } = useAuth();
    if (loading) return <div>Loading...</div>;
    return user ? children : <Navigate to="/login" />;
};

const TriagerRoute = ({ children }) => {
    const { user, isTriager, loading } = useAuth();
    if (loading) return <div>Loading...</div>;
    return user && isTriager() ? children : <Navigate to="/dashboard" />;
};

const CompanyRoute = ({ children }) => {
    const { user, loading, isCompany, hasCompanyProfile } = useAuth();

    if (loading) return <div>Loading...</div>;
    if (!user) return <Navigate to="/login" />;

    if (isCompany() && !hasCompanyProfile) {
        return <Navigate to="/company-registration" />;
    }

    return isCompany() ? children : <Navigate to="/dashboard" />;
};

/* =========================
   Login Wrapper
   ========================= */

const LoginWrapper = () => {
    const navigate = useNavigate();

    const handleLogin = () => {
        navigate('/dashboard');
    };

    const switchToRegister = () => {
        navigate('/register');
    };

    return (
        <Login
            onLogin={handleLogin}
            switchToRegister={switchToRegister}
        />
    );
};

/* =========================
   App Content
   ========================= */

function AppContent() {
    const { loading } = useAuth();

    if (loading) {
        return <div className="loading-screen">Loading...</div>;
    }

    return (
        <div className="App">
            <Navbar />
            <main>
                <Routes>
                    {/* Public routes */}
                    <Route path="/" element={<Home />} />
                    <Route path="/login" element={<LoginWrapper />} />
                    <Route path="/register" element={<Navigate to="/register/researcher" />} />
                    <Route path="/register/researcher" element={<ResearcherRegister />} />
                    <Route path="/register/company" element={<CompanyRegister />} />

                    {/* Password Reset */}
                    <Route path="/forgot-password" element={<ForgotPassword />} />
                    <Route path="/reset-password/:token" element={<ResetPassword />} />

                    {/* 2FA Routes */}
                    <Route path="/2fa/verify" element={<TwoFactorVerify />} />
                    <Route
                        path="/2fa/setup"
                        element={
                            <ProtectedRoute>
                                <TwoFactorSetup />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/2fa/settings"
                        element={
                            <ProtectedRoute>
                                <TwoFactorSettings />
                            </ProtectedRoute>
                        }
                    />

                    {/* Company registration */}
                    <Route
                        path="/company-registration"
                        element={
                            <ProtectedRoute>
                                <CompanyRegistration />
                            </ProtectedRoute>
                        }
                    />

                    {/* Dashboard */}
                    <Route
                        path="/dashboard"
                        element={
                            <ProtectedRoute>
                                <RoleBasedDashboard />
                            </ProtectedRoute>
                        }
                    />

                    {/* Researcher routes */}
                    <Route
                        path="/submit"
                        element={
                            <ProtectedRoute>
                                <SubmitReport />
                            </ProtectedRoute>
                        }
                    />

                    <Route
                        path="/reports"
                        element={
                            <ProtectedRoute>
                                <Reports />
                            </ProtectedRoute>
                        }
                    />

                    <Route
                        path="/reports/:id"
                        element={
                            <ProtectedRoute>
                                <ReportDetail />
                            </ProtectedRoute>
                        }
                    />

                    <Route
                        path="/programs"
                        element={
                            <ProtectedRoute>
                                <ProgramBrowser />
                            </ProtectedRoute>
                        }
                    />

                    <Route
                        path="/programs/:id"
                        element={
                            <ProtectedRoute>
                                <ProgramDetailResearcher />
                            </ProtectedRoute>
                        }
                    />

                    {/* Company dashboard */}
                    <Route
                        path="/company-dashboard"
                        element={
                            <CompanyRoute>
                                <CompanyDashboard />
                            </CompanyRoute>
                        }
                    />

                    {/* Triager/Admin */}
                    <Route
                        path="/triage"
                        element={
                            <TriagerRoute>
                                <Triage />
                            </TriagerRoute>
                        }
                    />

                    {/* Fallback */}
                    <Route path="*" element={<Navigate to="/" />} />
                </Routes>
            </main>
        </div>
    );
}

/* =========================
   App Root
   ========================= */

function App() {
    return (
        <AuthProvider>
            <Router>
                <AppContent />
            </Router>
        </AuthProvider>
    );
}

export default App;
