import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { reportAPI } from '../../services/api';
import { useNavigate } from 'react-router-dom';

const AdminDashboard = () => {
    const { user, isAdmin, isTriager } = useAuth();
    const navigate = useNavigate();
    const [dashboardData, setDashboardData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [actionMessage, setActionMessage] = useState(null);

    useEffect(() => {
        if (isAdmin() || isTriager()) {
            fetchTriageDashboard();
        }
    }, [isAdmin, isTriager]);

    const fetchTriageDashboard = async () => {
        try {
            setLoading(true);
            const response = await reportAPI.getTriageDashboard();
            setDashboardData(response.data);
            setError(null);
        } catch (err) {
            setError('Failed to load dashboard data');
            console.error('Error fetching dashboard:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleAssignToMe = async (reportId) => {
        try {
            setActionMessage(null);
            const response = await reportAPI.assignToMe(reportId);
            setActionMessage({ type: 'success', text: response.data.message });
            fetchTriageDashboard(); // Refresh data
        } catch (err) {
            setActionMessage({ type: 'error', text: err.response?.data?.error || 'Failed to assign report' });
            console.error('Error assigning report:', err);
        }
    };

    const handleAcceptReport = async (reportId) => {
        const verificationNotes = prompt('Enter verification notes:');
        if (!verificationNotes) return;

        const bountyAmount = prompt('Enter bounty amount (optional):');
        const data = {
            verification_notes: verificationNotes,
            ...(bountyAmount && { bounty_amount: bountyAmount })
        };

        try {
            setActionMessage(null);
            const response = await reportAPI.acceptReport(reportId, data);
            setActionMessage({ type: 'success', text: response.data.message });
            fetchTriageDashboard(); // Refresh data
        } catch (err) {
            setActionMessage({ type: 'error', text: err.response?.data?.error || 'Failed to accept report' });
            console.error('Error accepting report:', err);
        }
    };

    const handleRejectReport = async (reportId) => {
        const rejectionReason = prompt('Enter rejection reason:');
        if (!rejectionReason) return;

        try {
            setActionMessage(null);
            const response = await reportAPI.rejectReport(reportId, { rejection_reason: rejectionReason });
            setActionMessage({ type: 'success', text: response.data.message });
            fetchTriageDashboard(); // Refresh data
        } catch (err) {
            setActionMessage({ type: 'error', text: err.response?.data?.error || 'Failed to reject report' });
            console.error('Error rejecting report:', err);
        }
    };

    const handleReopenReport = async (reportId) => {
        try {
            setActionMessage(null);
            const response = await reportAPI.reopenReport(reportId);
            setActionMessage({ type: 'success', text: response.data.message });
            fetchTriageDashboard(); // Refresh data
        } catch (err) {
            setActionMessage({ type: 'error', text: err.response?.data?.error || 'Failed to reopen report' });
            console.error('Error reopening report:', err);
        }
    };

    const handleViewReports = () => {
        navigate('/reports?view=all');
    };

    const handleReviewReports = () => {
        navigate('/triage');
    };

    const handleManageUsers = () => {
        navigate('/admin/users');
    };

    const handleViewSettings = () => {
        navigate('/admin/settings');
    };

    const handleViewAnalytics = () => {
        navigate('/admin/analytics');
    };

    return (
        <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
            <h1>Admin Dashboard</h1>

            {/* Action Message */}
            {actionMessage && (
                <div style={{
                    padding: '1rem',
                    marginBottom: '1rem',
                    borderRadius: '4px',
                    background: actionMessage.type === 'success' ? '#d4edda' : '#f8d7da',
                    color: actionMessage.type === 'success' ? '#155724' : '#721c24',
                    border: `1px solid ${actionMessage.type === 'success' ? '#c3e6cb' : '#f5c6cb'}`
                }}>
                    {actionMessage.text}
                    <button
                        onClick={() => setActionMessage(null)}
                        style={{ float: 'right', background: 'none', border: 'none', cursor: 'pointer' }}
                    >
                        ×
                    </button>
                </div>
            )}

            <div style={{
                background: 'white',
                padding: '2rem',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                marginBottom: '2rem'
            }}>
                <h2>Welcome, {user?.username}!</h2>
                <p style={{ color: '#666' }}>
                    Role: {isAdmin() ? 'Administrator' : 'Triager'}
                </p>
            </div>

            {/* Dashboard Stats */}
            {loading ? (
                <div style={{ textAlign: 'center', padding: '2rem' }}>Loading dashboard data...</div>
            ) : error ? (
                <div style={{ color: '#e74c3c', textAlign: 'center', padding: '2rem' }}>{error}</div>
            ) : dashboardData && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
                    <div style={{
                        background: 'white',
                        padding: '1.5rem',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                        textAlign: 'center'
                    }}>
                        <h3 style={{ margin: '0 0 0.5rem 0', color: '#3498db' }}>Total</h3>
                        <p style={{ fontSize: '2rem', fontWeight: 'bold', margin: '0' }}>{dashboardData.counts.total}</p>
                    </div>
                    <div style={{
                        background: 'white',
                        padding: '1.5rem',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                        textAlign: 'center'
                    }}>
                        <h3 style={{ margin: '0 0 0.5rem 0', color: '#e74c3c' }}>Open</h3>
                        <p style={{ fontSize: '2rem', fontWeight: 'bold', margin: '0' }}>{dashboardData.counts.open}</p>
                    </div>
                    <div style={{
                        background: 'white',
                        padding: '1.5rem',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                        textAlign: 'center'
                    }}>
                        <h3 style={{ margin: '0 0 0.5rem 0', color: '#f39c12' }}>Triaged</h3>
                        <p style={{ fontSize: '2rem', fontWeight: 'bold', margin: '0' }}>{dashboardData.counts.triaged}</p>
                    </div>
                    <div style={{
                        background: 'white',
                        padding: '1.5rem',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                        textAlign: 'center'
                    }}>
                        <h3 style={{ margin: '0 0 0.5rem 0', color: '#27ae60' }}>Assigned to Me</h3>
                        <p style={{ fontSize: '2rem', fontWeight: 'bold', margin: '0' }}>{dashboardData.counts.assigned_to_me}</p>
                    </div>
                    <div style={{
                        background: 'white',
                        padding: '1.5rem',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                        textAlign: 'center'
                    }}>
                        <h3 style={{ margin: '0 0 0.5rem 0', color: '#95a5a6' }}>Unassigned</h3>
                        <p style={{ fontSize: '2rem', fontWeight: 'bold', margin: '0' }}>{dashboardData.counts.unassigned}</p>
                    </div>
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                {/* User Management - Only for Admins */}
                {isAdmin() && (
                    <div style={{
                        background: 'white',
                        padding: '1.5rem',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
                    }}>
                        <h3>User Management</h3>
                        <p>Manage user accounts and roles</p>
                        <button
                            onClick={handleManageUsers}
                            style={{
                                background: '#3498db',
                                color: 'white',
                                padding: '0.75rem 1.5rem',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                marginTop: '1rem',
                                width: '100%'
                            }}
                        >
                            Manage Users
                        </button>
                    </div>
                )}

                {/* Report Review - For both Admins and Triagers */}
                {(isAdmin() || isTriager()) && (
                    <div style={{
                        background: 'white',
                        padding: '1.5rem',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
                    }}>
                        <h3>Report Review</h3>
                        <p>Review and triage vulnerability reports</p>
                        <button
                            onClick={handleReviewReports}
                            style={{
                                background: '#2ecc71',
                                color: 'white',
                                padding: '0.75rem 1.5rem',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                marginTop: '1rem',
                                width: '100%'
                            }}
                        >
                            Go to Triage Dashboard
                        </button>
                    </div>
                )}

                {/* All Reports - For both Admins and Triagers */}
                {(isAdmin() || isTriager()) && (
                    <div style={{
                        background: 'white',
                        padding: '1.5rem',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
                    }}>
                        <h3>All Reports</h3>
                        <p>View and manage all vulnerability reports</p>
                        <button
                            onClick={handleViewReports}
                            style={{
                                background: '#9b59b6',
                                color: 'white',
                                padding: '0.75rem 1.5rem',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                marginTop: '1rem',
                                width: '100%'
                            }}
                        >
                            View All Reports
                        </button>
                    </div>
                )}

                {isAdmin() && (
                    <>
                        <div style={{
                            background: 'white',
                            padding: '1.5rem',
                            borderRadius: '8px',
                            boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
                        }}>
                            <h3>System Settings</h3>
                            <p>Configure platform settings</p>
                            <button
                                onClick={handleViewSettings}
                                style={{
                                    background: '#e74c3c',
                                    color: 'white',
                                    padding: '0.75rem 1.5rem',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    marginTop: '1rem',
                                    width: '100%'
                                }}
                            >
                                System Settings
                            </button>
                        </div>

                        <div style={{
                            background: 'white',
                            padding: '1.5rem',
                            borderRadius: '8px',
                            boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
                        }}>
                            <h3>Analytics</h3>
                            <p>View platform statistics and reports</p>
                            <button
                                onClick={handleViewAnalytics}
                                style={{
                                    background: '#f39c12',
                                    color: 'white',
                                    padding: '0.75rem 1.5rem',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    marginTop: '1rem',
                                    width: '100%'
                                }}
                            >
                                View Analytics
                            </button>
                        </div>
                    </>
                )}
            </div>

            {/* Recent Reports Section */}
            {dashboardData?.recent_reports && dashboardData.recent_reports.length > 0 && (
                <div style={{ marginTop: '2rem' }}>
                    <h2>Recent Reports</h2>
                    <div style={{
                        background: 'white',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                        overflow: 'hidden'
                    }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                            <tr style={{ background: '#f8f9fa' }}>
                                <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid #dee2e6' }}>Title</th>
                                <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid #dee2e6' }}>Status</th>
                                <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid #dee2e6' }}>Severity</th>
                                <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid #dee2e6' }}>Actions</th>
                            </tr>
                            </thead>
                            <tbody>
                            {dashboardData.recent_reports.map(report => (
                                <tr key={report.id} style={{ borderBottom: '1px solid #dee2e6' }}>
                                    <td style={{ padding: '1rem' }}>{report.title}</td>
                                    <td style={{ padding: '1rem' }}>
                                            <span style={{
                                                padding: '0.25rem 0.5rem',
                                                borderRadius: '4px',
                                                background: report.status === 'open' ? '#e74c3c' :
                                                    report.status === 'triaged' ? '#f39c12' :
                                                        report.status === 'accepted' ? '#27ae60' : '#95a5a6',
                                                color: 'white',
                                                fontSize: '0.875rem'
                                            }}>
                                                {report.status}
                                            </span>
                                    </td>
                                    <td style={{ padding: '1rem' }}>{report.severity}</td>
                                    <td style={{ padding: '1rem' }}>
                                        <button
                                            onClick={() => handleAssignToMe(report.id)}
                                            style={{
                                                background: '#3498db',
                                                color: 'white',
                                                padding: '0.25rem 0.5rem',
                                                border: 'none',
                                                borderRadius: '4px',
                                                cursor: 'pointer',
                                                marginRight: '0.5rem',
                                                fontSize: '0.875rem'
                                            }}
                                        >
                                            Assign to Me
                                        </button>
                                        <button
                                            onClick={() => handleAcceptReport(report.id)}
                                            style={{
                                                background: '#27ae60',
                                                color: 'white',
                                                padding: '0.25rem 0.5rem',
                                                border: 'none',
                                                borderRadius: '4px',
                                                cursor: 'pointer',
                                                marginRight: '0.5rem',
                                                fontSize: '0.875rem'
                                            }}
                                        >
                                            Accept
                                        </button>
                                        <button
                                            onClick={() => handleRejectReport(report.id)}
                                            style={{
                                                background: '#e74c3c',
                                                color: 'white',
                                                padding: '0.25rem 0.5rem',
                                                border: 'none',
                                                borderRadius: '4px',
                                                cursor: 'pointer',
                                                fontSize: '0.875rem'
                                            }}
                                        >
                                            Reject
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AdminDashboard;