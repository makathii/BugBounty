import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { reportAPI } from '../../services/api';

const Reports = () => {
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState({
        total: 0,
        byStatus: {},
        bySeverity: {}
    });
    const [filters, setFilters] = useState({
        status: '',
        severity: '',
        search: ''
    });

    useEffect(() => {
        loadReports();
        loadStats();
    }, [filters]); // eslint-disable-line react-hooks/exhaustive-deps

    const loadReports = async () => {
        try {
            const response = await reportAPI.getMySubmissions(filters);
            setReports(response.data.results || response.data);
        } catch (error) {
            console.error('Failed to load reports:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadStats = async () => {
        try {
            const response = await reportAPI.getStats();
            setStats(response.data);
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    };

    const handleFilterChange = (key, value) => {
        setFilters(prev => ({
            ...prev,
            [key]: value
        }));
    };

    const getStatusColor = (status) => {
        switch(status) {
            case 'open': return '#3498db';
            case 'triaged': return '#9b59b6';
            case 'accepted': return '#2ecc71';
            case 'rejected': return '#e74c3c';
            case 'resolved': return '#27ae60';
            case 'closed': return '#95a5a6';
            default: return '#7f8c8d';
        }
    };

    const getSeverityColor = (severity) => {
        switch(severity) {
            case 'critical': return '#e74c3c';
            case 'high': return '#e67e22';
            case 'medium': return '#f1c40f';
            case 'low': return '#2ecc71';
            default: return '#7f8c8d';
        }
    };

    if (loading) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <div style={{
                    border: '4px solid #f3f3f3',
                    borderTop: '4px solid #3498db',
                    borderRadius: '50%',
                    width: '40px',
                    height: '40px',
                    animation: 'spin 1s linear infinite',
                    margin: '0 auto 1rem'
                }}></div>
                <p>Loading reports...</p>
            </div>
        );
    }

    return (
        <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
            <div style={{ marginBottom: '2rem' }}>
                <h1>My Reports</h1>
                <p style={{ color: '#666' }}>View and manage your submitted bug reports</p>
            </div>

            {/* Stats Overview */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '1rem',
                marginBottom: '2rem'
            }}>
                <div style={{
                    background: 'white',
                    padding: '1.5rem',
                    borderRadius: '8px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                    textAlign: 'center'
                }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#3498db' }}>
                        {stats.total_submissions || 0}
                    </div>
                    <div style={{ color: '#666' }}>Total Submissions</div>
                </div>

                <div style={{
                    background: 'white',
                    padding: '1.5rem',
                    borderRadius: '8px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                    textAlign: 'center'
                }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#2ecc71' }}>
                        {(stats.by_status?.accepted || 0) + (stats.by_status?.resolved || 0)}
                    </div>
                    <div style={{ color: '#666' }}>Accepted</div>
                </div>

                <div style={{
                    background: 'white',
                    padding: '1.5rem',
                    borderRadius: '8px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                    textAlign: 'center'
                }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#f1c40f' }}>
                        {(stats.by_severity?.high || 0) + (stats.by_severity?.critical || 0)}
                    </div>
                    <div style={{ color: '#666' }}>High Severity</div>
                </div>

                <div style={{
                    background: 'white',
                    padding: '1.5rem',
                    borderRadius: '8px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                    textAlign: 'center'
                }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#9b59b6' }}>
                        ${reports.reduce((sum, r) => sum + (r.bounty_amount ? Number(r.bounty_amount) : 0), 0).toLocaleString()}
                    </div>
                    <div style={{ color: '#666' }}>Total Bounty</div>
                </div>
            </div>

            {/* Filters */}
            <div style={{
                background: 'white',
                padding: '1.5rem',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                marginBottom: '2rem'
            }}>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                    <div style={{ flex: 1, minWidth: '200px' }}>
                        <input
                            type="text"
                            placeholder="Search reports..."
                            value={filters.search}
                            onChange={(e) => handleFilterChange('search', e.target.value)}
                            style={{
                                width: '100%',
                                padding: '0.75rem',
                                border: '1px solid #ddd',
                                borderRadius: '4px',
                                fontSize: '1rem'
                            }}
                        />
                    </div>

                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <select
                            value={filters.status}
                            onChange={(e) => handleFilterChange('status', e.target.value)}
                            style={{
                                padding: '0.75rem',
                                border: '1px solid #ddd',
                                borderRadius: '4px',
                                fontSize: '1rem',
                                minWidth: '120px'
                            }}
                        >
                            <option value="">All Status</option>
                            <option value="open">Open</option>
                            <option value="triaged">Triaged</option>
                            <option value="accepted">Accepted</option>
                            <option value="rejected">Rejected</option>
                            <option value="resolved">Resolved</option>
                            <option value="closed">Closed</option>
                        </select>

                        <select
                            value={filters.severity}
                            onChange={(e) => handleFilterChange('severity', e.target.value)}
                            style={{
                                padding: '0.75rem',
                                border: '1px solid #ddd',
                                borderRadius: '4px',
                                fontSize: '1rem',
                                minWidth: '120px'
                            }}
                        >
                            <option value="">All Severity</option>
                            <option value="critical">Critical</option>
                            <option value="high">High</option>
                            <option value="medium">Medium</option>
                            <option value="low">Low</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* Reports Table */}
            <div style={{
                background: 'white',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                overflow: 'hidden'
            }}>
                {reports.length > 0 ? (
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                        <tr style={{ background: '#f8f9fa', borderBottom: '2px solid #e9ecef' }}>
                            <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600' }}>Title</th>
                            <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600' }}>Status</th>
                            <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600' }}>Severity</th>
                            <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600' }}>Date</th>
                            <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600' }}>Bounty</th>
                            <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600' }}>Actions</th>
                        </tr>
                        </thead>
                        <tbody>
                        {reports.map((report) => (
                            <tr
                                key={report.id}
                                style={{
                                    borderBottom: '1px solid #e9ecef',
                                    cursor: 'pointer',
                                    transition: 'background 0.2s'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.background = '#f8fafc'}
                                onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
                            >
                                <td style={{ padding: '1rem' }}>
                                    <div style={{ fontWeight: '500' }}>{report.title}</div>
                                    <div style={{ fontSize: '0.9rem', color: '#666', marginTop: '0.25rem' }}>
                                        {report.description.substring(0, 80)}...
                                    </div>
                                </td>
                                <td style={{ padding: '1rem' }}>
                                        <span style={{
                                            padding: '0.4rem 0.8rem',
                                            background: getStatusColor(report.status) + '20',
                                            color: getStatusColor(report.status),
                                            borderRadius: '20px',
                                            fontSize: '0.85rem',
                                            fontWeight: '500',
                                            display: 'inline-block'
                                        }}>
                                            {report.status.toUpperCase()}
                                        </span>
                                </td>
                                <td style={{ padding: '1rem' }}>
                                        <span style={{
                                            padding: '0.4rem 0.8rem',
                                            background: getSeverityColor(report.severity) + '20',
                                            color: getSeverityColor(report.severity),
                                            borderRadius: '20px',
                                            fontSize: '0.85rem',
                                            fontWeight: '500',
                                            display: 'inline-block'
                                        }}>
                                            {report.severity.toUpperCase()}
                                        </span>
                                </td>
                                <td style={{ padding: '1rem', color: '#666' }}>
                                    {new Date(report.created_at).toLocaleDateString()}
                                </td>
                                <td style={{ padding: '1rem' }}>
                                    {report.bounty_amount ? (
                                        <span style={{ color: '#27ae60', fontWeight: '500' }}>
                                                ${report.bounty_amount}
                                            </span>
                                    ) : (
                                        <span style={{ color: '#95a5a6' }}>—</span>
                                    )}
                                </td>
                                <td style={{ padding: '1rem' }}>
                                    <Link
                                        to={`/reports/${report.id}`}
                                        style={{
                                            padding: '0.4rem 0.8rem',
                                            background: '#3498db',
                                            color: 'white',
                                            textDecoration: 'none',
                                            borderRadius: '4px',
                                            fontSize: '0.85rem'
                                        }}
                                    >
                                        View
                                    </Link>
                                </td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                ) : (
                    <div style={{ padding: '3rem', textAlign: 'center' }}>
                        <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.5 }}>📋</div>
                        <h3 style={{ margin: '0 0 1rem 0', color: '#333' }}>No Reports Yet</h3>
                        <p style={{ margin: '0 0 1.5rem 0', color: '#666' }}>
                            You haven't submitted any bug reports yet.
                        </p>
                        <Link
                            to="/submit"
                            style={{
                                padding: '0.75rem 1.5rem',
                                background: '#3498db',
                                color: 'white',
                                textDecoration: 'none',
                                borderRadius: '4px',
                                fontSize: '1rem',
                                display: 'inline-block'
                            }}
                        >
                            Submit Your First Report
                        </Link>
                    </div>
                )}
            </div>

            {/* Severity Legend */}
            <div style={{
                background: 'white',
                padding: '1.5rem',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                marginTop: '2rem'
            }}>
                <h4 style={{ margin: '0 0 1rem 0' }}>Severity Legend</h4>
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{
                            width: '12px',
                            height: '12px',
                            borderRadius: '50%',
                            background: '#e74c3c'
                        }}></div>
                        <span>Critical</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{
                            width: '12px',
                            height: '12px',
                            borderRadius: '50%',
                            background: '#e67e22'
                        }}></div>
                        <span>High</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{
                            width: '12px',
                            height: '12px',
                            borderRadius: '50%',
                            background: '#f1c40f'
                        }}></div>
                        <span>Medium</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{
                            width: '12px',
                            height: '12px',
                            borderRadius: '50%',
                            background: '#2ecc71'
                        }}></div>
                        <span>Low</span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Reports;