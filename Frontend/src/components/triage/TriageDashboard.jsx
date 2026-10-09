import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { reportAPI } from '../../services/api';

const statusColors = {
    open: '#3498db',
    triaged: '#9b59b6',
    accepted: '#2ecc71',
    rejected: '#e74c3c',
    duplicate: '#95a5a6',
    resolved: '#27ae60',
    closed: '#7f8c8d',
};

const severityColors = {
    low: '#3498db',
    medium: '#f39c12',
    high: '#e67e22',
    critical: '#e74c3c',
};

const badge = (text, color) => (
    <span style={{
        padding: '0.2rem 0.7rem',
        borderRadius: '12px',
        fontSize: '0.75rem',
        fontWeight: 'bold',
        color: 'white',
        background: color,
        textTransform: 'uppercase'
    }}>
        {text}
    </span>
);

const cardStyle = {
    background: 'white',
    borderRadius: '8px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
};

const TriageDashboard = () => {
    const [dashboardData, setDashboardData] = useState(null);
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({
        status: '',
        assigned_to: '',
        search: ''
    });

    const loadDashboardData = useCallback(async () => {
        try {
            const response = await reportAPI.getTriageDashboard();
            setDashboardData(response.data);
        } catch (error) {
            console.error('Failed to load dashboard:', error);
        }
    }, []);

    const loadReports = useCallback(async () => {
        try {
            const params = {};
            if (filters.status) params.status = filters.status;
            if (filters.assigned_to) params.assigned_to = filters.assigned_to;
            if (filters.search) params.search = filters.search;
            const response = await reportAPI.getReports(params);
            setReports(response.data.results || response.data || []);
        } catch (error) {
            console.error('Failed to load reports:', error);
        } finally {
            setLoading(false);
        }
    }, [filters]);

    useEffect(() => {
        loadDashboardData();
        loadReports();
    }, [loadDashboardData, loadReports]);

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
        setFilters(prev => ({ ...prev, [key]: value }));
    };

    if (loading) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <div>Loading triage dashboard...</div>
            </div>
        );
    }

    const stats = [
        { label: 'Total Reports', value: dashboardData?.counts?.total ?? 0, color: '#3498db' },
        { label: 'Awaiting Review', value: dashboardData?.counts?.triaged ?? 0, color: '#f39c12' },
        { label: 'Assigned to Me', value: dashboardData?.counts?.assigned_to_me ?? 0, color: '#2ecc71' },
        { label: 'Unassigned', value: dashboardData?.counts?.unassigned ?? 0, color: '#e74c3c' },
    ];

    return (
        <div>
            <div style={{ marginBottom: '2rem' }}>
                <h1>Triage Dashboard</h1>
                <p style={{ color: '#666' }}>Review, assign and process incoming vulnerability reports</p>
            </div>

            {/* Stats */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '1rem',
                marginBottom: '2rem'
            }}>
                {stats.map(({ label, value, color }) => (
                    <div key={label} style={{ ...cardStyle, padding: '1.5rem', textAlign: 'center' }}>
                        <div style={{ fontSize: '2rem', fontWeight: 'bold', color }}>{value}</div>
                        <div style={{ color: '#666' }}>{label}</div>
                    </div>
                ))}
            </div>

            {/* Filters */}
            <div style={{
                ...cardStyle,
                padding: '1.5rem',
                marginBottom: '2rem',
                display: 'flex',
                gap: '1rem',
                flexWrap: 'wrap'
            }}>
                <input
                    type="text"
                    placeholder="Search reports..."
                    value={filters.search}
                    onChange={(e) => handleFilterChange('search', e.target.value)}
                    style={{
                        flex: 1,
                        minWidth: '200px',
                        padding: '0.6rem 0.9rem',
                        border: '1px solid #ddd',
                        borderRadius: '4px'
                    }}
                />
                <select
                    value={filters.status}
                    onChange={(e) => handleFilterChange('status', e.target.value)}
                    style={{ padding: '0.6rem 0.9rem', border: '1px solid #ddd', borderRadius: '4px' }}
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
                    style={{ padding: '0.6rem 0.9rem', border: '1px solid #ddd', borderRadius: '4px' }}
                >
                    <option value="">All Assignments</option>
                    <option value="unassigned">Unassigned</option>
                    <option value="me">Assigned to Me</option>
                </select>
            </div>

            {/* Reports List */}
            <div style={{ display: 'grid', gap: '1rem' }}>
                {reports.length === 0 ? (
                    <div style={{ ...cardStyle, padding: '3rem', textAlign: 'center', color: '#666' }}>
                        No reports match the current filters.
                    </div>
                ) : (
                    reports.map(report => (
                        <div key={report.id} style={{ ...cardStyle, padding: '1.5rem' }}>
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'flex-start',
                                gap: '1rem',
                                flexWrap: 'wrap',
                                marginBottom: '0.5rem'
                            }}>
                                <h3 style={{ margin: 0, color: '#2c3e50' }}>{report.title}</h3>
                                <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
                                    {badge(report.severity, severityColors[report.severity] || '#95a5a6')}
                                    {badge(report.status, statusColors[report.status] || '#95a5a6')}
                                </div>
                            </div>
                            <div style={{ color: '#888', fontSize: '0.9rem', marginBottom: '0.75rem' }}>
                                By <strong>{report.reporter_username || report.reporter}</strong>
                                {report.program_name ? <> • {report.program_name}</> : null}
                                {' • '}
                                {report.assigned_to
                                    ? <>Assigned to <strong>{report.assigned_to_username || report.assigned_to}</strong></>
                                    : 'Unassigned'}
                                {' • '}
                                {new Date(report.created_at).toLocaleDateString()}
                            </div>
                            <p style={{ color: '#555', margin: '0 0 1rem 0' }}>
                                {report.description?.substring(0, 200)}{report.description?.length > 200 ? '…' : ''}
                            </p>
                            <div style={{ display: 'flex', gap: '0.75rem' }}>
                                {!report.assigned_to && (
                                    <button
                                        onClick={() => handleAssignToMe(report.id)}
                                        style={{
                                            background: '#3498db',
                                            color: 'white',
                                            padding: '0.5rem 1rem',
                                            border: 'none',
                                            borderRadius: '4px',
                                            cursor: 'pointer',
                                            fontSize: '0.9rem'
                                        }}
                                    >
                                        Assign to Me
                                    </button>
                                )}
                                <Link
                                    to={`/reports/${report.id}`}
                                    style={{
                                        background: '#2ecc71',
                                        color: 'white',
                                        padding: '0.5rem 1rem',
                                        borderRadius: '4px',
                                        textDecoration: 'none',
                                        fontSize: '0.9rem'
                                    }}
                                >
                                    View Details
                                </Link>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default TriageDashboard;
