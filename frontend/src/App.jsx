import React from 'react';
import {
    BrowserRouter as Router,
    Routes,
    Route,
    Navigate,
    useNavigate
} from 'react-router-dom';

import { ProtectedRoute, TriagerRoute, CompanyRoute, ResearcherRoute } from './app/guards';
import Navbar from './components/layout/Navbar';

/*
 * NOTE: the order of these imports is also the order global stylesheets load in
 * (Home.css, auth.css, register.css, Wizard.css and App.css define overlapping
 * selectors such as .btn and .form-group), so keep App.css after the feature
 * imports and Home before auth. Scoping those files to their features would
 * remove this coupling.
 */
import { AuthProvider, useAuth } from './features/auth/AuthContext';
import RoleBasedDashboard from './features/dashboard/RoleBasedDashboard';
import ProgramBrowser from './features/programs/ProgramBrowser';
import ProgramDetail from './features/programs/ProgramDetail';
import Home from './features/home/Home';
import Triage from './features/triage/Triage';
import Login from './features/auth/Login';
import ResearcherRegister from './features/auth/register/ResearcherRegister';
import CompanyRegister from './features/auth/register/CompanyRegister';
import VerifyEmail from './features/auth/VerifyEmail';
import SubmitReport from './features/reports/SubmitReport';
import Reports from './features/reports/Reports';
import ReportDetail from './features/reports/ReportDetail';
import CompanyRegistration from './features/company/CompanyRegistration';
import CompanyDashboard from './features/company/CompanyDashboard';
import CompanyPrograms from './features/company/CompanyPrograms';
import CompanyReports from './features/company/CompanyReports';
import CreateProgram from './features/company/CreateProgram';
import './App.css';
import OAuthSuccess from './features/auth/OAuthSuccess';
import TwoFactorSetup from './features/auth/TwoFactorSetup';
import TwoFactorSettings from './features/auth/TwoFactorSettings';
import Leaderboard from './features/leaderboard/Leaderboard';


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
                    <Route path="/2fa/enroll" element={<TwoFactorSetup enrollment />} />
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
                        <ProtectedRoute><ProgramDetail /></ProtectedRoute>
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