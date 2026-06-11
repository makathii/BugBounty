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
        padding: '0.25rem 0.75rem',
        borderRadius: '12px',
        fontSize: '0.8rem',
        fontWeight: 'bold',
        color: 'white',
        background: color,
        textTransform: 'uppercase'
    }}>
        {text}
    </span>
);

const CompanyReports = () => {
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({ status: '', severity: '', search: '' });

    const loadReports = useCallback(async () => {
        try {
            const params = {};
            if (filters.status) params.status = filters.status;
            if (filters.severity) params.severity = filters.severity;
            if (filters.search) params.search = filters.search;
            const response = await reportAPI.getReports(params);
            setReports(response.data.results || response.data || []);
        } catch (error) {
            console.error('Failed to load company reports:', error);
        } finally {
            setLoading(false);
        }
    }, [filters]);

    useEffect(() => {
        loadReports();
    }, [loadReports]);

    const totalBounty = reports.reduce(
        (sum, r) => sum + (r.bounty_amount ? Number(r.bounty_amount) : 0), 0
    );
    const openCount = reports.filter(r => ['open', 'triaged'].includes(r.status)).length;
    const criticalCount = reports.filter(r => r.severity === 'critical').length;

    const cardStyle = {
        background: 'white',
        padding: '1.5rem',
        borderRadius: '8px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
        textAlign: 'center'
    };

    if (loading) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <div>Loading reports...</div>
            </div>
        );
    }

    return (
        <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
            <div style={{ marginBottom: '2rem' }}>
                <h1>Incoming Reports</h1>
                <p style={{ color: '#666' }}>Vulnerability reports submitted to your programs</p>
            </div>

            {/* Stats */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '1rem',
                marginBottom: '2rem'
            }}>
                <div style={cardStyle}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#3498db' }}>{reports.length}</div>
                    <div style={{ color: '#666' }}>Total Reports</div>
                </div>
                <div style={cardStyle}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#f39c12' }}>{openCount}</div>
                    <div style={{ color: '#666' }}>Awaiting Action</div>
                </div>
                <div style={cardStyle}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#e74c3c' }}>{criticalCount}</div>
                    <div style={{ color: '#666' }}>Critical</div>
                </div>
                <div style={cardStyle}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#9b59b6' }}>
                        ${totalBounty.toLocaleString()}
                    </div>
                    <div style={{ color: '#666' }}>Bounties Paid</div>
                </div>
            </div>

            {/* Filters */}
            <div style={{
                background: 'white',
                padding: '1.5rem',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                marginBottom: '2rem',
                display: 'flex',
                gap: '1rem',
                flexWrap: 'wrap'
            }}>
                <input
                    type="text"
                    placeholder="Search reports..."
                    value={filters.search}
                    onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
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
                    onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
                    style={{ padding: '0.6rem 0.9rem', border: '1px solid #ddd', borderRadius: '4px' }}
                >
                    <option value="">All Status</option>
                    <option value="open">Open</option>
                    <option value="triaged">Triaged</option>
                    <option value="accepted">Accepted</option>
                    <option value="rejected">Rejected</option>
                    <option value="duplicate">Duplicate</option>
                    <option value="resolved">Resolved</option>
                </select>
                <select
                    value={filters.severity}
                    onChange={(e) => setFilters(prev => ({ ...prev, severity: e.target.value }))}
                    style={{ padding: '0.6rem 0.9rem', border: '1px solid #ddd', borderRadius: '4px' }}
                >
                    <option value="">All Severity</option>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                </select>
            </div>

            {/* Reports list */}
            <div style={{
                background: 'white',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                overflow: 'hidden'
            }}>
                {reports.length === 0 ? (
                    <div style={{ padding: '3rem', textAlign: 'center', color: '#666' }}>
                        <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.5 }}>📋</div>
                        <h4 style={{ margin: '0 0 0.5rem 0', color: '#333' }}>No reports yet</h4>
                        <p style={{ margin: 0 }}>
                            Reports submitted to your programs will appear here.
                        </p>
                    </div>
                ) : (
                    reports.map((report, i) => (
                        <Link
                            key={report.id}
                            to={`/reports/${report.id}`}
                            style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                gap: '1rem',
                                padding: '1.1rem 1.5rem',
                                borderBottom: i < reports.length - 1 ? '1px solid #f0f0f0' : 'none',
                                textDecoration: 'none',
                                color: 'inherit',
                                flexWrap: 'wrap'
                            }}
                        >
                            <div style={{ minWidth: 0, flex: 1 }}>
                                <div style={{ fontWeight: 600, color: '#2c3e50', marginBottom: '0.2rem' }}>
                                    {report.title}
                                </div>
                                <div style={{ color: '#888', fontSize: '0.85rem' }}>
                                    {report.program_name ? `${report.program_name} • ` : ''}
                                    by {report.reporter_username || 'unknown'} • {new Date(report.created_at).toLocaleDateString()}
                                    {report.bounty_amount ? ` • $${Number(report.bounty_amount).toLocaleString()} paid` : ''}
                                </div>
                            </div>
                            <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
                                {badge(report.severity, severityColors[report.severity] || '#95a5a6')}
                                {badge(report.status, statusColors[report.status] || '#95a5a6')}
                            </div>
                        </Link>
                    ))
                )}
            </div>
        </div>
    );
};

export default CompanyReports;
