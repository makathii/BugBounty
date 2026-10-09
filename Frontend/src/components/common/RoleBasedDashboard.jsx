// src/components/RoleBasedDashboard.jsx
import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import CompanyDashboard from '../../pages/company/CompanyDashboard';
import ResearcherDashboard from '../../pages/researcher/ResearcherDashboard';
import AdminDashboard from '../../pages/admin/AdminDashboard';

const RoleBasedDashboard = () => {
    const { user, isCompany, isResearcher, isTriager, isAdmin, loading } = useAuth();

    if (loading) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <div>Loading dashboard...</div>
            </div>
        );
    }

    if (!user) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <div>Please log in to access the dashboard.</div>
            </div>
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
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <h1>Welcome, {user.username}!</h1>
                <p>Your account doesn't have a specific role assigned yet.</p>
                <p>Please contact support to assign your user role.</p>
                <div style={{ marginTop: '1rem', color: '#666' }}>
                    <p>Available roles: Researcher, Company, Triager, Admin</p>
                </div>
            </div>
        );
    }
};

export default RoleBasedDashboard;