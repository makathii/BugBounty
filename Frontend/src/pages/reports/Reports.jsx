import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { reportAPI } from '../../services/api';
import { statusTone, severityTone } from '../../utils/tones';

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

    const bounty = reports.reduce((sum, r) => sum + (r.bounty_amount ? Number(r.bounty_amount) : 0), 0);
    const statCards = [
        { label: 'Total Submissions', value: stats.total_submissions || 0, tone: 'accent' },
        { label: 'Accepted', value: (stats.by_status?.accepted || 0) + (stats.by_status?.resolved || 0), tone: 'green' },
        { label: 'High Severity', value: (stats.by_severity?.high || 0) + (stats.by_severity?.critical || 0), tone: 'orange' },
        { label: 'Total Bounty', value: `$${bounty.toLocaleString()}`, tone: 'blue' },
    ];

    if (loading) {
        return (
            <div className="ui-loading">
                <div className="ui-spinner" />
                <p>Loading reports...</p>
            </div>
        );
    }

    return (
        <div className="ui-page ui-page--wide">
            <header className="ui-page-header">
                <h1 className="ui-title">My Reports</h1>
                <p className="ui-subtitle">View and manage your submitted bug reports</p>
            </header>

            <div className="ui-grid ui-grid--stats">
                {statCards.map(({ label, value, tone }) => (
                    <div key={label} className={`ui-stat tone-${tone}`}>
                        <div className="ui-stat-value">{value}</div>
                        <div className="ui-stat-label">{label}</div>
                    </div>
                ))}
            </div>

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
                    <option value="resolved">Resolved</option>
                    <option value="closed">Closed</option>
                </select>
                <select
                    className="ui-select"
                    value={filters.severity}
                    onChange={(e) => handleFilterChange('severity', e.target.value)}
                >
                    <option value="">All Severity</option>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                </select>
            </div>

            <div className="ui-card ui-card--flush">
                {reports.length > 0 ? (
                    <div className="ui-table-wrap">
                        <table className="ui-table">
                            <thead>
                                <tr>
                                    <th>Title</th>
                                    <th>Status</th>
                                    <th>Severity</th>
                                    <th>Date</th>
                                    <th>Bounty</th>
                                    <th />
                                </tr>
                            </thead>
                            <tbody>
                                {reports.map((report) => (
                                    <tr key={report.id}>
                                        <td>
                                            <Link to={`/reports/${report.id}`} className="ui-link--title">{report.title}</Link>
                                            <div className="ui-muted ui-small" style={{ marginTop: '0.2rem' }}>
                                                {report.description.substring(0, 80)}...
                                            </div>
                                        </td>
                                        <td><span className={`ui-badge ${statusTone(report.status)}`}>{report.status}</span></td>
                                        <td><span className={`ui-badge ${severityTone(report.severity)}`}>{report.severity}</span></td>
                                        <td className="ui-muted">{new Date(report.created_at).toLocaleDateString()}</td>
                                        <td>
                                            {report.bounty_amount
                                                ? <span className="ui-tone-text tone-green ui-strong">${report.bounty_amount}</span>
                                                : <span className="ui-muted">—</span>}
                                        </td>
                                        <td>
                                            <Link to={`/reports/${report.id}`} className="ui-btn ui-btn--ghost ui-btn--sm">View</Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div className="ui-empty">
                        <div className="ui-empty-icon">📋</div>
                        <h3>No Reports Yet</h3>
                        <p>You haven't submitted any bug reports yet.</p>
                        <Link to="/submit" className="ui-btn">Submit Your First Report</Link>
                    </div>
                )}
            </div>

            <div className="ui-card ui-mt">
                <h4 className="ui-section-title">Severity Legend</h4>
                <div className="ui-row" style={{ gap: '1.5rem' }}>
                    {['critical', 'high', 'medium', 'low'].map((level) => (
                        <div key={level} className={`ui-row ${severityTone(level)}`} style={{ gap: '0.5rem' }}>
                            <span className="ui-dot" />
                            <span className="ui-muted" style={{ textTransform: 'capitalize' }}>{level}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default Reports;
