import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { reportAPI } from '../../services/api';
import { statusTone, severityTone } from '../../utils/tones';
import { formatPoints } from '../../utils/points';

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

    const totalPoints = reports.reduce((sum, r) => sum + (r.points_awarded || 0), 0);
    const openCount = reports.filter(r => ['open', 'triaged'].includes(r.status)).length;
    const criticalCount = reports.filter(r => r.severity === 'critical').length;

    const statCards = [
        { label: 'Total Reports', value: reports.length, tone: 'accent' },
        { label: 'Awaiting Action', value: openCount, tone: 'yellow' },
        { label: 'Critical', value: criticalCount, tone: 'red' },
        { label: 'Points Awarded', value: formatPoints(totalPoints), tone: 'blue' },
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
        <div className="ui-page">
            <header className="ui-page-header">
                <h1 className="ui-title">Incoming Reports</h1>
                <p className="ui-subtitle">Vulnerability reports submitted to your programs</p>
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
                    onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                />
                <select
                    className="ui-select"
                    value={filters.status}
                    onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
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
                    className="ui-select"
                    value={filters.severity}
                    onChange={(e) => setFilters(prev => ({ ...prev, severity: e.target.value }))}
                >
                    <option value="">All Severity</option>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                </select>
            </div>

            <div className="ui-card ui-card--flush">
                {reports.length === 0 ? (
                    <div className="ui-empty">
                        <div className="ui-empty-icon">📋</div>
                        <h3>No reports yet</h3>
                        <p>Reports submitted to your programs will appear here.</p>
                    </div>
                ) : (
                    reports.map((report) => (
                        <Link key={report.id} to={`/reports/${report.id}`} className="ui-row-link">
                            <div style={{ minWidth: 0, flex: 1 }}>
                                <div className="ui-strong" style={{ marginBottom: '0.2rem' }}>{report.title}</div>
                                <div className="ui-muted ui-small">
                                    {report.program_name ? `${report.program_name} • ` : ''}
                                    by {report.reporter_username || 'unknown'} • {new Date(report.created_at).toLocaleDateString()}
                                    {report.points_awarded ? ` • ${formatPoints(report.points_awarded)} awarded` : ''}
                                </div>
                            </div>
                            <div className="ui-row" style={{ flexShrink: 0, gap: '0.4rem' }}>
                                <span className={`ui-badge ${severityTone(report.severity)}`}>{report.severity}</span>
                                <span className={`ui-badge ${statusTone(report.status)}`}>{report.status}</span>
                            </div>
                        </Link>
                    ))
                )}
            </div>
        </div>
    );
};

export default CompanyReports;
