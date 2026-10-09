import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../features/auth/AuthContext';

/* =========================
   Route guards
   ========================= */

export const ProtectedRoute = ({ children }) => {
    const { user, loading } = useAuth();
    if (loading) return <div className="loading-screen">Loading...</div>;
    return user ? children : <Navigate to="/login" />;
};

export const TriagerRoute = ({ children }) => {
    const { user, isTriager, loading } = useAuth();
    if (loading) return <div className="loading-screen">Loading...</div>;
    return user && isTriager() ? children : <Navigate to="/dashboard" />;
};

export const CompanyRoute = ({ children }) => {
    const { user, loading, isCompany, hasCompanyProfile } = useAuth();
    if (loading) return <div className="loading-screen">Loading...</div>;
    if (!user) return <Navigate to="/login" />;
    if (isCompany() && !hasCompanyProfile) return <Navigate to="/company-registration" />;
    return isCompany() ? children : <Navigate to="/dashboard" />;
};

export const ResearcherRoute = ({ children }) => {
    const { user, loading, isResearcher } = useAuth();
    if (loading) return <div className="loading-screen">Loading...</div>;
    if (!user) return <Navigate to="/login" />;
    return isResearcher() ? children : <Navigate to="/dashboard" />;
};
