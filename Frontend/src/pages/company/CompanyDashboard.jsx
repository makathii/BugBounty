import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { companyAPI } from '../../services/api';

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

const cardStyle = {
    background: 'white',
    padding: '2rem',
    borderRadius: '8px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
};

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
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <div>Loading company dashboard...</div>
            </div>
        );
    }

    const programs = dashboard?.programs || [];
    const recentActivity = dashboard?.recent_activity || [];

    return (
        <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
            <div style={{ marginBottom: '2rem' }}>
                <h1>Company Dashboard</h1>
                <p style={{ color: '#666' }}>Welcome back, {user?.first_name || user?.username}!</p>
            </div>

            {/* Company Header */}
            {company && (
                <div style={{ ...cardStyle, marginBottom: '2rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <h2 style={{ margin: '0 0 0.5rem 0' }}>{company.company_name}</h2>
                            <p style={{ margin: '0 0 0.5rem 0', color: '#666' }}>
                                <strong>Website:</strong> {company.website}
                            </p>
                            <p style={{ margin: '0', color: '#666' }}>
                                <strong>Industry:</strong> {company.industry || '—'}
                                {company.country ? ` • ${company.country}` : ''}
                            </p>
                        </div>
                        <div style={{
                            padding: '0.5rem 1rem',
                            background: company.is_verified ? '#2ecc71' : '#f39c12',
                            color: 'white',
                            borderRadius: '20px',
                            fontSize: '0.9rem',
                            fontWeight: 'bold'
                        }}>
                            {company.is_verified ? '✓ Verified Company' : '⏳ Pending Verification'}
                        </div>
                    </div>

                    {company.description && (
                        <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid #eee' }}>
                            <p style={{ margin: 0, color: '#555' }}>{company.description}</p>
                        </div>
                    )}
                </div>
            )}

            {/* Stats Overview */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '1rem',
                marginBottom: '2rem'
            }}>
                <div style={{ ...cardStyle, padding: '1.5rem', textAlign: 'center' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#3498db' }}>
                        {dashboard?.active_programs ?? 0}
                    </div>
                    <div style={{ color: '#666' }}>Active Programs</div>
                </div>

                <div style={{ ...cardStyle, padding: '1.5rem', textAlign: 'center' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#2ecc71' }}>
                        {dashboard?.total_reports ?? 0}
                    </div>
                    <div style={{ color: '#666' }}>Total Reports</div>
                </div>

                <div style={{ ...cardStyle, padding: '1.5rem', textAlign: 'center' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#e74c3c' }}>
                        ${Number(dashboard?.total_bounties ?? 0).toLocaleString()}
                    </div>
                    <div style={{ color: '#666' }}>Total Payouts</div>
                </div>

                <div style={{ ...cardStyle, padding: '1.5rem', textAlign: 'center' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#9b59b6' }}>
                        {dashboard?.total_programs ?? 0}
                    </div>
                    <div style={{ color: '#666' }}>Total Programs</div>
                </div>
            </div>

            {/* Quick Actions */}
            <div style={{ ...cardStyle, marginBottom: '2rem' }}>
                <h3 style={{ margin: '0 0 1.5rem 0' }}>Quick Actions</h3>
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                    <button
                        onClick={() => navigate('/company/programs/create')}
                        style={{
                            background: '#3498db',
                            color: 'white',
                            padding: '1rem 1.5rem',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '1rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem'
                        }}
                    >
                        <span>+</span>
                        Create New Program
                    </button>

                    <button
                        onClick={() => navigate('/company/programs')}
                        style={{
                            background: '#9b59b6',
                            color: 'white',
                            padding: '1rem 1.5rem',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '1rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem'
                        }}
                    >
                        <span>🎯</span>
                        Manage Programs
                    </button>

                    <button
                        onClick={() => navigate('/reports')}
                        style={{
                            background: '#2ecc71',
                            color: 'white',
                            padding: '1rem 1.5rem',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '1rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem'
                        }}
                    >
                        <span>📋</span>
                        View Reports
                    </button>
                </div>
            </div>

            {/* Programs Section */}
            <div style={{ ...cardStyle, marginBottom: '2rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h3 style={{ margin: 0 }}>Your Programs</h3>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <span style={{ color: '#666' }}>
                            {dashboard?.active_programs ?? 0} active program{(dashboard?.active_programs ?? 0) === 1 ? '' : 's'}
                        </span>
                        <button
                            onClick={() => navigate('/company/programs/create')}
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
                            + New Program
                        </button>
                    </div>
                </div>

                {programs.length === 0 ? (
                    <div style={{
                        border: '2px dashed #ddd',
                        borderRadius: '8px',
                        padding: '3rem',
                        textAlign: 'center',
                        color: '#666'
                    }}>
                        <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.5 }}>📋</div>
                        <h4 style={{ margin: '0 0 1rem 0', color: '#333' }}>No Programs Yet</h4>
                        <p style={{ margin: '0 0 1.5rem 0', maxWidth: '500px', marginInline: 'auto' }}>
                            Create your first bug bounty program to start receiving vulnerability reports from security researchers.
                        </p>
                        <button
                            onClick={() => navigate('/company/programs/create')}
                            style={{
                                background: '#3498db',
                                color: 'white',
                                padding: '0.75rem 1.5rem',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                fontSize: '1rem'
                            }}
                        >
                            Create Your First Program
                        </button>
                    </div>
                ) : (
                    <div style={{ display: 'grid', gap: '1rem' }}>
                        {programs.map((program) => (
                            <div
                                key={program.id}
                                style={{
                                    border: '1px solid #eee',
                                    borderRadius: '8px',
                                    padding: '1.25rem 1.5rem',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    gap: '1rem',
                                    flexWrap: 'wrap'
                                }}
                            >
                                <div>
                                    <h4 style={{ margin: '0 0 0.25rem 0' }}>{program.name}</h4>
                                    <p style={{ margin: 0, color: '#666', fontSize: '0.9rem' }}>
                                        {program.short_description || program.description?.slice(0, 120)}
                                    </p>
                                    {(program.min_bounty || program.max_bounty) && (
                                        <p style={{ margin: '0.25rem 0 0 0', color: '#2ecc71', fontSize: '0.9rem', fontWeight: 'bold' }}>
                                            ${Number(program.min_bounty || 0).toLocaleString()} – ${Number(program.max_bounty || 0).toLocaleString()}
                                        </p>
                                    )}
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                    <span style={{
                                        padding: '0.25rem 0.75rem',
                                        borderRadius: '12px',
                                        fontSize: '0.8rem',
                                        fontWeight: 'bold',
                                        color: 'white',
                                        background: program.status === 'active' ? '#2ecc71'
                                            : program.status === 'paused' ? '#f39c12'
                                            : program.status === 'draft' ? '#95a5a6' : '#7f8c8d',
                                        textTransform: 'capitalize'
                                    }}>
                                        {program.status}
                                    </span>
                                    <Link
                                        to="/company/programs"
                                        style={{ color: '#3498db', textDecoration: 'none', fontSize: '0.9rem' }}
                                    >
                                        Manage →
                                    </Link>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Recent Activity */}
            <div style={cardStyle}>
                <h3 style={{ margin: '0 0 1.5rem 0' }}>Recent Activity</h3>
                {recentActivity.length === 0 ? (
                    <div style={{
                        border: '1px dashed #ddd',
                        borderRadius: '8px',
                        padding: '2rem',
                        textAlign: 'center',
                        color: '#999'
                    }}>
                        <p style={{ margin: 0 }}>No recent activity</p>
                    </div>
                ) : (
                    <div style={{ display: 'grid', gap: '0.5rem' }}>
                        {recentActivity.slice(0, 8).map((item) => (
                            <Link
                                key={item.id}
                                to={`/reports/${item.id}`}
                                style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    gap: '1rem',
                                    padding: '0.75rem 1rem',
                                    border: '1px solid #f0f0f0',
                                    borderRadius: '6px',
                                    textDecoration: 'none',
                                    color: 'inherit',
                                    flexWrap: 'wrap'
                                }}
                            >
                                <div style={{ minWidth: 0 }}>
                                    <div style={{ fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                        {item.title}
                                    </div>
                                    <div style={{ color: '#888', fontSize: '0.85rem' }}>
                                        {item.program__name} • {new Date(item.created_at).toLocaleDateString()}
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
                                    <span style={{
                                        padding: '0.2rem 0.6rem',
                                        borderRadius: '10px',
                                        fontSize: '0.75rem',
                                        fontWeight: 'bold',
                                        color: 'white',
                                        background: severityColors[item.severity] || '#95a5a6',
                                        textTransform: 'capitalize'
                                    }}>
                                        {item.severity}
                                    </span>
                                    <span style={{
                                        padding: '0.2rem 0.6rem',
                                        borderRadius: '10px',
                                        fontSize: '0.75rem',
                                        fontWeight: 'bold',
                                        color: 'white',
                                        background: statusColors[item.status] || '#95a5a6',
                                        textTransform: 'capitalize'
                                    }}>
                                        {item.status}
                                    </span>
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
