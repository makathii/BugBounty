import React, { useState, useEffect } from 'react';
import { reportAPI } from '../../services/api';

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

    if (loading) return <div>Loading...</div>;

    return (
        <div className="triage-dashboard">
            <h1>Triage Dashboard</h1>

            {/* Dashboard Stats */}
            {dashboardData && (
                <div className="dashboard-stats">
                    <div className="stat-cards">
                        <div className="stat-card">
                            <h3>{dashboardData.counts.total}</h3>
                            <p>Total Reports</p>
                        </div>
                        <div className="stat-card">
                            <h3>{dashboardData.counts.triaged}</h3>
                            <p>Awaiting Review</p>
                        </div>
                        <div className="stat-card">
                            <h3>{dashboardData.counts.assigned_to_me}</h3>
                            <p>Assigned to Me</p>
                        </div>
                        <div className="stat-card">
                            <h3>{dashboardData.counts.unassigned}</h3>
                            <p>Unassigned</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Filters */}
            <div className="filters">
                <input
                    type="text"
                    placeholder="Search reports..."
                    value={filters.search}
                    onChange={(e) => handleFilterChange('search', e.target.value)}
                />
                <select
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
                    value={filters.assigned_to}
                    onChange={(e) => handleFilterChange('assigned_to', e.target.value)}
                >
                    <option value="">All Assignments</option>
                    <option value="unassigned">Unassigned</option>
                    <option value="me">Assigned to Me</option>
                </select>
            </div>

            {/* Reports List */}
            <div className="reports-list">
                {reports.map(report => (
                    <div key={report.id} className="report-item">
                        <div className="report-header">
                            <h3>{report.title}</h3>
                            <span className={`severity-badge severity-${report.severity}`}>
                {report.severity}
              </span>
                        </div>
                        <div className="report-meta">
                            <span>By: {report.reporter}</span>
                            <span>Status: {report.status}</span>
                            <span>Assigned: {report.assigned_to || 'Unassigned'}</span>
                        </div>
                        <p className="report-description">
                            {report.description.substring(0, 200)}...
                        </p>
                        <div className="report-actions">
                            {!report.assigned_to && (
                                <button
                                    onClick={() => handleAssignToMe(report.id)}
                                    className="btn btn-primary"
                                >
                                    Assign to Me
                                </button>
                            )}
                            <button className="btn btn-secondary">View Details</button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default TriageDashboard;