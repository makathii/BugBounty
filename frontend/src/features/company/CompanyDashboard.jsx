import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { companyAPI } from '../../services/api';
import { statusTone, severityTone } from '../../utils/tones';

const CompanyDashboard = () => {
    const { user, hasCompanyProfile, loading: authLoading } = useAuth();
    const navigate = useNavigate();
    const [company, setCompany] = useState(null);
    const [dashboard, setDashboard] = useState(null);
    const [loading, setLoading] = useState(true);

    const loadCompanyData = useCallback(async () => {
        try {
            const [dashRes, profileRes] = await Promise.all([
                companyAPI.getDashboard(),
                companyAPI.getProfile().catch(() => null),
            ]);
            setDashboard(dashRes.data);
            if (profileRes) setCompany(profileRes.data);
        } catch (error) {
            console.error('Error loading company dashboard:', error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!authLoading && user) {
            if (!hasCompanyProfile) {
                navigate('/company-registration');
                return;
            }
            loadCompanyData();
        }
    }, [authLoading, user, hasCompanyProfile, navigate, loadCompanyData]);

    if (authLoading || loading) {
        return (
            <div className="ui-loading">
                <div className="ui-spinner" />
                <p>Loading company dashboard...</p>
            </div>
        );
    }

    const programs = dashboard?.programs || [];
    const recentActivity = dashboard?.recent_activity || [];
    const statCards = [
        { label: 'Active Programs', value: dashboard?.active_programs ?? 0, tone: 'blue' },
        { label: 'Total Reports', value: dashboard?.total_reports ?? 0, tone: 'green' },
        { label: 'Total Payouts', value: `$${Number(dashboard?.total_bounties ?? 0).toLocaleString()}`, tone: 'accent' },
        { label: 'Total Programs', value: dashboard?.total_programs ?? 0, tone: 'orange' },
    ];
    const activeCount = dashboard?.active_programs ?? 0;

    return (
        <div className="ui-page">
            <header className="ui-page-header">
                <h1 className="ui-title">Company Dashboard</h1>
                <p className="ui-subtitle">Welcome back, {user?.first_name || user?.username}!</p>
            </header>

            {company && (
                <div className="ui-card ui-mb-lg">
                    <div className="ui-row ui-row--between ui-row--start">
                        <div>
                            <h2 className="ui-title" style={{ fontSize: '1.4rem' }}>{company.company_name}</h2>
                            <p className="ui-muted" style={{ margin: '0 0 0.4rem' }}>
                                <strong className="ui-strong">Website:</strong> {company.website}
                            </p>
                            <p className="ui-muted" style={{ margin: 0 }}>
                                <strong className="ui-strong">Industry:</strong> {company.industry || '—'}
                                {company.country ? ` • ${company.country}` : ''}
                            </p>
                        </div>
                        <span className={`ui-badge ui-badge--plain ${company.is_verified ? 'tone-green' : 'tone-yellow'}`}>
                            {company.is_verified ? '✓ Verified Company' : '⏳ Pending Verification'}
                        </span>
                    </div>

                    {company.description && (
                        <>
                            <hr className="ui-divider" />
                            <p className="ui-muted" style={{ margin: 0 }}>{company.description}</p>
                        </>
                    )}
                </div>
            )}

            <div className="ui-grid ui-grid--stats">
                {statCards.map(({ label, value, tone }) => (
                    <div key={label} className={`ui-stat tone-${tone}`}>
                        <div className="ui-stat-value">{value}</div>
                        <div className="ui-stat-label">{label}</div>
                    </div>
                ))}
            </div>

            <div className="ui-card ui-mb-lg">
                <h3 className="ui-section-title">Quick Actions</h3>
                <div className="ui-row">
                    <button className="ui-btn" onClick={() => navigate('/company/programs/create')}>+ Create New Program</button>
                    <button className="ui-btn ui-btn--ghost" onClick={() => navigate('/company/programs')}>🎯 Manage Programs</button>
                    <button className="ui-btn ui-btn--green" onClick={() => navigate('/reports')}>📋 View Reports</button>
                </div>
            </div>

            <div className="ui-card ui-mb-lg">
                <div className="ui-card-head">
                    <h3 className="ui-section-title">Your Programs</h3>
                    <div className="ui-row">
                        <span className="ui-muted ui-small">
                            {activeCount} active program{activeCount === 1 ? '' : 's'}
                        </span>
                        <button className="ui-btn ui-btn--sm" onClick={() => navigate('/company/programs/create')}>
                            + New Program
                        </button>
                    </div>
                </div>

                {programs.length === 0 ? (
                    <div className="ui-empty">
                        <div className="ui-empty-icon">📋</div>
                        <h3>No Programs Yet</h3>
                        <p>Create your first bug bounty program to start receiving vulnerability reports from security researchers.</p>
                        <button className="ui-btn" onClick={() => navigate('/company/programs/create')}>
                            Create Your First Program
                        </button>
                    </div>
                ) : (
                    <div className="ui-list">
                        {programs.map((program) => (
                            <div key={program.id} className="ui-list-item">
                                <div style={{ minWidth: 0 }}>
                                    <div className="ui-strong">{program.name}</div>
                                    <div className="ui-muted ui-small">
                                        {program.short_description || program.description?.slice(0, 120)}
                                    </div>
                                    {(program.min_bounty || program.max_bounty) && (
                                        <div className="ui-tone-text tone-green ui-strong ui-small" style={{ marginTop: '0.25rem' }}>
                                            ${Number(program.min_bounty || 0).toLocaleString()} – ${Number(program.max_bounty || 0).toLocaleString()}
                                        </div>
                                    )}
                                </div>
                                <div className="ui-row" style={{ flexShrink: 0 }}>
                                    <span className={`ui-badge ${statusTone(program.status)}`}>{program.status}</span>
                                    <Link to="/company/programs" className="ui-link ui-small">Manage →</Link>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <div className="ui-card">
                <h3 className="ui-section-title">Recent Activity</h3>
                {recentActivity.length === 0 ? (
                    <div className="ui-empty"><p>No recent activity</p></div>
                ) : (
                    <div className="ui-list">
                        {recentActivity.slice(0, 8).map((item) => (
                            <Link key={item.id} to={`/reports/${item.id}`} className="ui-list-item">
                                <div style={{ minWidth: 0 }}>
                                    <div className="ui-strong" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                        {item.title}
                                    </div>
                                    <div className="ui-muted ui-small">
                                        {item.program__name} • {new Date(item.created_at).toLocaleDateString()}
                                    </div>
                                </div>
                                <div className="ui-row" style={{ flexShrink: 0, gap: '0.4rem' }}>
                                    <span className={`ui-badge ${severityTone(item.severity)}`}>{item.severity}</span>
                                    <span className={`ui-badge ${statusTone(item.status)}`}>{item.status}</span>
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default CompanyDashboard;
