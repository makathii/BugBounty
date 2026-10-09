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
import ProgramBrowser from './components/researcher/ProgramBrowser';
import ProgramDetailResearcher from './components/researcher/ProgramDetailResearcher';

// Pages
import Home from './pages/Home';
import Triage from './pages/Triage';

// Auth
import Login from './components/auth/Login';
import ResearcherRegister from './pages/researcher/ResearcherRegister';
import CompanyRegister from './pages/company/CompanyRegister';
import VerifyEmail from './components/auth/VerifyEmail';

// Reports
import SubmitReport from './pages/reports/SubmitReport';
import Reports from './pages/reports/Reports';
import ReportDetail from './pages/reports/ReportDetail';

// Company
import CompanyRegistration from './components/company/CompanyRegistration';
import CompanyDashboard from './pages/company/CompanyDashboard';
import CompanyPrograms from './pages/company/CompanyPrograms';
import CompanyReports from './pages/company/CompanyReports';
import CreateProgram from './pages/company/CreateProgram';

import './App.css';
import OAuthSuccess from "./pages/OAuthSuccess";
import TwoFactorSetup from './components/auth/TwoFactorSetup';
import TwoFactorSettings from './components/auth/TwoFactorSettings';
import Leaderboard from "./pages/leaderboard/leaderboard";


/* =========================
   Route guards
   ========================= */

const ProtectedRoute = ({ children }) => {
    const { user, loading } = useAuth();
    if (loading) return <div className="loading-screen">Loading...</div>;
    return user ? children : <Navigate to="/login" />;
};

const TriagerRoute = ({ children }) => {
    const { user, isTriager, loading } = useAuth();
    if (loading) return <div className="loading-screen">Loading...</div>;
    return user && isTriager() ? children : <Navigate to="/dashboard" />;
};

const CompanyRoute = ({ children }) => {
    const { user, loading, isCompany, hasCompanyProfile } = useAuth();
    if (loading) return <div className="loading-screen">Loading...</div>;
    if (!user) return <Navigate to="/login" />;
    if (isCompany() && !hasCompanyProfile) return <Navigate to="/company-registration" />;
    return isCompany() ? children : <Navigate to="/dashboard" />;
};

const ResearcherRoute = ({ children }) => {
    const { user, loading, isResearcher } = useAuth();
    if (loading) return <div className="loading-screen">Loading...</div>;
    if (!user) return <Navigate to="/login" />;
    return isResearcher() ? children : <Navigate to="/dashboard" />;
};


/* =========================
   Login wrapper
   ========================= */

const LoginWrapper = () => {
    const navigate = useNavigate();
    return (
        <Login
            onLogin={() => navigate('/dashboard')}
            switchToRegister={() => navigate('/register')}
        />
    );
};


/* =========================
   App content
   ========================= */

function AppContent() {
    const { loading } = useAuth();

    if (loading) return <div className="loading-screen">Loading...</div>;

    return (
        <div className="App">
            <Navbar />
            <main>
                <Routes>
                    {/* Public */}
                    <Route path="/" element={<Home />} />
                    <Route path="/login" element={<LoginWrapper />} />
                    <Route path="/register" element={<Navigate to="/register/researcher" />} />
                    <Route path="/register/researcher" element={<ResearcherRegister />} />
                    <Route path="/register/company" element={<CompanyRegister />} />
                    <Route path="/verify-email/:token" element={<VerifyEmail />} />

                    {/*Leaderboard */}
                    <Route path="/leaderboard" element={<Leaderboard />} />

                    {/* OAuth */}
                    <Route path="/oauth/success" element={<OAuthSuccess />} />

                    {/* Dashboard */}
                    <Route path="/dashboard" element={
                        <ProtectedRoute><RoleBasedDashboard /></ProtectedRoute>
                    } />

                    {/* Two-factor authentication */}
                    <Route path="/2fa/setup" element={
                        <ProtectedRoute><TwoFactorSetup /></ProtectedRoute>
                    } />
                    <Route path="/2fa/settings" element={
                        <ProtectedRoute><TwoFactorSettings /></ProtectedRoute>
                    } />

                    {/* Company registration */}
                    <Route path="/company-registration" element={
                        <ProtectedRoute><CompanyRegistration /></ProtectedRoute>
                    } />

                    {/* Company */}
                    <Route path="/company-dashboard" element={
                        <CompanyRoute><CompanyDashboard /></CompanyRoute>
                    } />
                    <Route path="/company/programs" element={
                        <CompanyRoute><CompanyPrograms /></CompanyRoute>
                    } />
                    <Route path="/company/programs/create" element={
                        <CompanyRoute><CreateProgram /></CompanyRoute>
                    } />
                    <Route path="/company/reports" element={
                        <CompanyRoute><CompanyReports /></CompanyRoute>
                    } />

                    {/* Programs — researchers */}
                    <Route path="/programs" element={
                        <ResearcherRoute><ProgramBrowser /></ResearcherRoute>
                    } />
                    <Route path="/programs/:id" element={
                        <ProtectedRoute><ProgramDetailResearcher /></ProtectedRoute>
                    } />

                    {/* Reports */}
                    <Route path="/reports" element={
                        <ProtectedRoute><Reports /></ProtectedRoute>
                    } />
                    <Route path="/reports/:id" element={
                        <ProtectedRoute><ReportDetail /></ProtectedRoute>
                    } />
                    <Route path="/submit" element={
                        <ProtectedRoute><SubmitReport /></ProtectedRoute>
                    } />

                    {/* Triage */}
                    <Route path="/triage" element={
                        <TriagerRoute><Triage /></TriagerRoute>
                    } />

                    {/* Fallback */}
                    <Route path="*" element={<Navigate to="/" />} />
                </Routes>
            </main>
        </div>
    );
}


/* =========================
   App root
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