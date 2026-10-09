import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { reportAPI } from '../services/api';
import { statusTone, severityTone } from '../utils/tones';

const TriageDashboard = () => {
    const [dashboardData, setDashboardData] = useState(null);
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({
        status: '',
        assigned_to: '',
        search: ''
    });

    useEffect(() => {
        loadDashboardData();
        loadReports();
    }, [filters]); // eslint-disable-line react-hooks/exhaustive-deps

    const loadDashboardData = async () => {
        try {
            const response = await reportAPI.getTriageDashboard();
            setDashboardData(response.data);
        } catch (error) {
            console.error('Failed to load dashboard:', error);
        }
    };

    const loadReports = async () => {
        try {
            const response = await reportAPI.getReports(filters);
            setReports(response.data);
        } catch (error) {
            console.error('Failed to load reports:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleAssignToMe = async (reportId) => {
        try {
            await reportAPI.assignToMe(reportId);
            loadDashboardData();
            loadReports();
        } catch (error) {
            console.error('Failed to assign report:', error);
        }
    };

    const handleFilterChange = (key, value) => {
        setFilters(prev => ({
            ...prev,
            [key]: value
        }));
    };

    if (loading) {
        return (
            <div className="ui-loading">
                <div className="ui-spinner" />
                <p>Loading...</p>
            </div>
        );
    }

    const counts = dashboardData?.counts;
    const statCards = counts ? [
        { label: 'Total Reports', value: counts.total, tone: 'accent' },
        { label: 'Awaiting Review', value: counts.triaged, tone: 'yellow' },
        { label: 'Assigned to Me', value: counts.assigned_to_me, tone: 'blue' },
        { label: 'Unassigned', value: counts.unassigned, tone: 'orange' },
    ] : [];

    return (
        <div className="ui-page">
            <header className="ui-page-header">
                <h1 className="ui-title">Triage Dashboard</h1>
                <p className="ui-subtitle">Review, assign and prioritise incoming reports</p>
            </header>

            {counts && (
                <div className="ui-grid ui-grid--stats">
                    {statCards.map(({ label, value, tone }) => (
                        <div key={label} className={`ui-stat tone-${tone}`}>
                            <div className="ui-stat-value">{value}</div>
                            <div className="ui-stat-label">{label}</div>
                        </div>
                    ))}
                </div>
            )}

            <div className="ui-toolbar">
                <input
                    type="text"
                    className="ui-input ui-input--grow"
                    placeholder="Search reports..."
                    value={filters.search}
                    onChange={(e) => handleFilterChange('search', e.target.value)}
                />
                <select
                    className="ui-select"
                    value={filters.status}
                    onChange={(e) => handleFilterChange('status', e.target.value)}
                >
                    <option value="">All Status</option>
                    <option value="open">Open</option>
                    <option value="triaged">Triaged</option>
                    <option value="accepted">Accepted</option>
                    <option value="rejected">Rejected</option>
                </select>
                <select
                    className="ui-select"
                    value={filters.assigned_to}
                    onChange={(e) => handleFilterChange('assigned_to', e.target.value)}
                >
                    <option value="">All Assignments</option>
                    <option value="unassigned">Unassigned</option>
                    <option value="me">Assigned to Me</option>
                </select>
            </div>

            {reports.length === 0 ? (
                <div className="ui-card ui-empty">
                    <div className="ui-empty-icon">📭</div>
                    <h3>No reports found</h3>
                    <p>No reports match the current filters.</p>
                </div>
            ) : (
                <div className="ui-stack" style={{ gap: '1rem' }}>
                    {reports.map(report => (
                        <article key={report.id} className="ui-card ui-card--hover">
                            <div className="ui-row ui-row--between ui-row--nowrap" style={{ marginBottom: '0.6rem' }}>
                                <h3 className="ui-section-title" style={{ margin: 0 }}>{report.title}</h3>
                                <div className="ui-row" style={{ gap: '0.4rem' }}>
                                    <span className={`ui-badge ${severityTone(report.severity)}`}>{report.severity}</span>
                                    <span className={`ui-badge ${statusTone(report.status)}`}>{report.status}</span>
                                </div>
                            </div>
                            <div className="ui-row ui-muted ui-small" style={{ gap: '1.25rem', marginBottom: '0.75rem' }}>
                                <span>By: {report.reporter_username || report.reporter}</span>
                                <span>Assigned: {report.assigned_to_username || report.assigned_to || 'Unassigned'}</span>
                            </div>
                            <p className="ui-muted ui-small" style={{ margin: '0 0 1rem', lineHeight: 1.55 }}>
                                {report.description.substring(0, 200)}...
                            </p>
                            <div className="ui-row">
                                {!report.assigned_to && (
                                    <button className="ui-btn ui-btn--sm" onClick={() => handleAssignToMe(report.id)}>
                                        Assign to Me
                                    </button>
                                )}
                                <Link to={`/reports/${report.id}`} className="ui-btn ui-btn--ghost ui-btn--sm">
                                    View Details
                                </Link>
                            </div>
                        </article>
                    ))}
                </div>
            )}
        </div>
    );
};

export default TriageDashboard;
