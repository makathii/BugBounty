// src/components/RoleBasedDashboard.jsx
import React from 'react';
import { useAuth } from '../auth/AuthContext';
import CompanyDashboard from '../company/CompanyDashboard';
import ResearcherDashboard from '../researcher/ResearcherDashboard';
import AdminDashboard from '../admin/AdminDashboard';

const RoleBasedDashboard = () => {
    const { user, isCompany, isResearcher, isTriager, isAdmin, loading } = useAuth();

    if (loading) {
        return (
            <div className="ui-loading">
                <div className="ui-spinner" />
                <p>Loading dashboard...</p>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="ui-loading">Please log in to access the dashboard.</div>
        );
    }

    // Route based on role
    if (isCompany()) {
        return <CompanyDashboard />;
    } else if (isAdmin() || isTriager()) {
        return <AdminDashboard />;
    } else if (isResearcher()) {
        return <ResearcherDashboard />;
    } else {
        // Fallback for users without specific role
        return (
            <div className="ui-page ui-page--narrow">
                <div className="ui-card ui-empty">
                    <h1 className="ui-title">Welcome, {user.username}!</h1>
                    <p>Your account doesn't have a specific role assigned yet.</p>
                    <p>Please contact support to assign your user role.</p>
                    <p className="ui-small">Available roles: Researcher, Company, Triager, Admin</p>
                </div>
            </div>
        );
    }
};

export default RoleBasedDashboard;