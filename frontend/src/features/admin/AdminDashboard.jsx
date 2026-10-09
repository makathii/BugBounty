import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth/AuthContext';
import { reportAPI } from '../../services/api';
import { useNavigate } from 'react-router-dom';
import { statusTone, severityTone } from '../../utils/tones';

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

    // eslint-disable-next-line no-unused-vars
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

    const counts = dashboardData?.counts;
    const statCards = counts ? [
        { label: 'Total', value: counts.total, tone: 'accent' },
        { label: 'Open', value: counts.open, tone: 'blue' },
        { label: 'Triaged', value: counts.triaged, tone: 'yellow' },
        { label: 'Assigned to Me', value: counts.assigned_to_me, tone: 'green' },
        { label: 'Unassigned', value: counts.unassigned, tone: 'gray' },
    ] : [];

    const adminCards = [
        { show: isAdmin(), title: 'User Management', text: 'Manage user accounts and roles', label: 'Manage Users', onClick: handleManageUsers, cls: '' },
        { show: isAdmin() || isTriager(), title: 'Report Review', text: 'Review and triage vulnerability reports', label: 'Go to Triage Dashboard', onClick: handleReviewReports, cls: '' },
        { show: isAdmin() || isTriager(), title: 'All Reports', text: 'View and manage all vulnerability reports', label: 'View All Reports', onClick: handleViewReports, cls: 'ui-btn--ghost' },
        { show: isAdmin(), title: 'System Settings', text: 'Configure platform settings', label: 'System Settings', onClick: handleViewSettings, cls: 'ui-btn--ghost' },
        { show: isAdmin(), title: 'Analytics', text: 'View platform statistics and reports', label: 'View Analytics', onClick: handleViewAnalytics, cls: 'ui-btn--ghost' },
    ].filter(c => c.show);

    return (
        <div className="ui-page">
            <header className="ui-page-header">
                <h1 className="ui-title">Admin Dashboard</h1>
                <p className="ui-subtitle">
                    Welcome, {user?.username}! Role: {isAdmin() ? 'Administrator' : 'Triager'}
                </p>
            </header>

            {actionMessage && (
                <div className={`ui-alert ui-row ui-row--between ${actionMessage.type === 'success' ? 'tone-green' : 'tone-red'}`}>
                    <span>{actionMessage.text}</span>
                    <button className="ui-btn ui-btn--ghost ui-btn--sm" onClick={() => setActionMessage(null)} aria-label="Dismiss">×</button>
                </div>
            )}

            {loading ? (
                <div className="ui-loading"><div className="ui-spinner" /><p>Loading dashboard data...</p></div>
            ) : error ? (
                <div className="ui-alert tone-red">{error}</div>
            ) : counts && (
                <div className="ui-grid ui-grid--stats">
                    {statCards.map(({ label, value, tone }) => (
                        <div key={label} className={`ui-stat tone-${tone}`}>
                            <div className="ui-stat-value">{value}</div>
                            <div className="ui-stat-label">{label}</div>
                        </div>
                    ))}
                </div>
            )}

            <div className="ui-grid ui-grid--cards">
                {adminCards.map(({ title, text, label, onClick, cls }) => (
                    <div key={title} className="ui-card ui-card--hover ui-stack">
                        <h3 className="ui-section-title" style={{ margin: 0 }}>{title}</h3>
                        <p className="ui-muted ui-small" style={{ margin: 0 }}>{text}</p>
                        <button className={`ui-btn ui-btn--block ${cls}`} onClick={onClick}>{label}</button>
                    </div>
                ))}
            </div>

            {dashboardData?.recent_reports && dashboardData.recent_reports.length > 0 && (
                <section>
                    <h2 className="ui-section-title">Recent Reports</h2>
                    <div className="ui-card ui-card--flush">
                        <div className="ui-table-wrap">
                            <table className="ui-table">
                                <thead>
                                    <tr>
                                        <th>Title</th>
                                        <th>Status</th>
                                        <th>Severity</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {dashboardData.recent_reports.map(report => (
                                        <tr key={report.id}>
                                            <td className="ui-strong">{report.title}</td>
                                            <td><span className={`ui-badge ${statusTone(report.status)}`}>{report.status}</span></td>
                                            <td><span className={`ui-badge ${severityTone(report.severity)}`}>{report.severity}</span></td>
                                            <td>
                                                <div className="ui-row" style={{ gap: '0.4rem' }}>
                                                    <button className="ui-btn ui-btn--ghost ui-btn--sm" onClick={() => handleAssignToMe(report.id)}>
                                                        Assign to Me
                                                    </button>
                                                    <button className="ui-btn ui-btn--green ui-btn--sm" onClick={() => handleAcceptReport(report.id)}>
                                                        Accept
                                                    </button>
                                                    <button className="ui-btn ui-btn--danger ui-btn--sm" onClick={() => handleRejectReport(report.id)}>
                                                        Reject
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </section>
            )}
        </div>
    );
};

export default AdminDashboard;
