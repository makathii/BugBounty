import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const s = {
    page:    { padding: '2rem', maxWidth: '1200px', margin: '0 auto' },
    heading: { margin: '0 0 0.4rem 0', color: '#f0f0f5', fontWeight: 800, fontSize: '1.6rem', letterSpacing: '-0.02em' },
    sub:     { color: '#8888aa', margin: 0, fontSize: '0.9rem' },
    grid:    { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', margin: '1.25rem 0' },
    card:    { background: '#111118', border: '1px solid rgba(255,255,255,0.07)', padding: '1.5rem', borderRadius: '14px', textAlign: 'center' },
    cardVal: { fontSize: '2rem', fontWeight: 800, marginBottom: '0.3rem' },
    cardLbl: { color: '#8888aa', fontSize: '0.85rem' },
    section: { background: '#111118', border: '1px solid rgba(255,255,255,0.07)', padding: '1.75rem', borderRadius: '14px', marginBottom: '1.25rem' },
    sectionTitle: { margin: '0 0 1.25rem 0', color: '#f0f0f5', fontWeight: 700, fontSize: '1rem' },
    row:     { display: 'flex', gap: '0.75rem', flexWrap: 'wrap' },
    sbRow:   { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' },
    btnPrimary: { background: '#7c6aff', color: '#fff', padding: '0.7rem 1.25rem', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.4rem' },
    btnGreen:   { background: 'rgba(34,197,94,0.12)', color: '#22c55e', border: '1px solid rgba(34,197,94,0.3)', padding: '0.7rem 1.25rem', borderRadius: '8px', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.4rem' },
    btnGhost:   { background: 'rgba(255,255,255,0.06)', color: '#f0f0f5', border: '1px solid rgba(255,255,255,0.07)', padding: '0.7rem 1.25rem', borderRadius: '8px', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.4rem' },
    empty:   { border: '1px dashed rgba(255,255,255,0.1)', borderRadius: '10px', padding: '2.5rem', textAlign: 'center', color: '#8888aa' },
    emptyIcon: { fontSize: '2.5rem', marginBottom: '0.75rem', opacity: 0.5 },
    emptyTitle: { margin: '0 0 0.5rem 0', color: '#f0f0f5', fontWeight: 600 },
    badge:   (verified) => ({
        padding: '0.35rem 0.9rem',
        background: verified ? 'rgba(34,197,94,0.12)' : 'rgba(251,191,36,0.12)',
        color: verified ? '#22c55e' : '#fbbf24',
        border: `1px solid ${verified ? 'rgba(34,197,94,0.3)' : 'rgba(251,191,36,0.3)'}`,
        borderRadius: '20px',
        fontSize: '0.8rem',
        fontWeight: 600,
    }),
    warning: { background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.2)', borderRadius: '10px', padding: '1.5rem', textAlign: 'center', color: '#fbbf24' },
    divider: { borderTop: '1px solid rgba(255,255,255,0.07)', marginTop: '1rem', paddingTop: '1rem' },
};

const CompanyDashboard = () => {
    const { user, hasCompanyProfile, loading: authLoading } = useAuth();
    const navigate = useNavigate();
    const [company, setCompany] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!authLoading && user) {
            if (!hasCompanyProfile) {
                console.log('Company user needs to complete profile, redirecting...');
                navigate('/company/setup-profile');
                return;
            }

            loadCompanyData();
        }
    }, [authLoading, user, hasCompanyProfile, navigate]); // eslint-disable-line react-hooks/exhaustive-deps

    const loadCompanyData = async () => {
        try {
            // TODO: Replace with actual API call to get company data
            // For now, simulate API call
            setTimeout(() => {
                setCompany({
                    company_name: user.company_name || "Your Company",
                    verification_status: "pending",
                    website: "https://example.com",
                    description: "Security-focused company running bug bounty programs",
                    industry: "Technology",
                    country: "United States"
                });
                setLoading(false);
            }, 1000);
        } catch (error) {
            console.error('Error loading company data:', error);
            setLoading(false);
        }
    };

    const handleCreateProgram = () => {
        // TODO: Implement program creation
        console.log('Create program clicked');
        // navigate('/company/programs/create');
    };

    const handleViewReports = () => {
        // TODO: Implement view reports
        console.log('View reports clicked');
        // navigate('/company/reports');
    };

    const handleEditProfile = () => {
        // Navigate to profile edit page
        navigate('/company/setup-profile');
    };

    if (authLoading || loading) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#8888aa' }}>
                Loading...
            </div>
        );
    }

    const verified = company?.verification_status === 'verified';

    return (
        <div style={s.page}>
            {/* Header */}
            <div style={{ marginBottom: '1.5rem' }}>
                <h1 style={s.heading}>Company Dashboard</h1>
                <p style={s.sub}>Welcome back, {user?.first_name || user?.username}!</p>
            </div>

            {/* Company Card */}
            <div style={s.section}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                    <div>
                        <h2 style={{ margin: '0 0 0.4rem 0', color: '#f0f0f5', fontWeight: 700 }}>{company?.company_name}</h2>
                        <p style={{ margin: '0 0 0.2rem 0', color: '#8888aa', fontSize: '0.85rem' }}>{company?.website}</p>
                        <p style={{ margin: 0, color: '#8888aa', fontSize: '0.85rem' }}>{company?.industry} · {company?.country}</p>
                    </div>
                    <span style={s.badge(verified)}>
                        {verified ? '✓ Verified' : '⏳ Pending Verification'}
                    </span>
                </div>
                {company?.description && (
                    <div style={s.divider}>
                        <p style={{ margin: 0, color: '#8888aa', fontSize: '0.9rem' }}>{company.description}</p>
                    </div>
                )}
            </div>

            {/* Stats */}
            <div style={s.grid}>
                <div style={s.card}><div style={{ ...s.cardVal, color: '#7c6aff' }}>0</div><div style={s.cardLbl}>Active Programs</div></div>
                <div style={s.card}><div style={{ ...s.cardVal, color: '#22c55e' }}>0</div><div style={s.cardLbl}>Total Reports</div></div>
                <div style={s.card}><div style={{ ...s.cardVal, color: '#22c55e' }}>$0</div><div style={s.cardLbl}>Total Payouts</div></div>
                <div style={s.card}><div style={{ ...s.cardVal, color: '#a78bfa' }}>0</div><div style={s.cardLbl}>Researchers</div></div>
            </div>

            {/* Quick Actions */}
            <div style={s.section}>
                <h3 style={s.sectionTitle}>Quick Actions</h3>
                <div style={s.row}>
                    <button style={s.btnPrimary} onClick={handleCreateProgram}>+ Create Program</button>
                    <button style={s.btnGreen}   onClick={handleViewReports}>📋 View Reports</button>
                    <button style={s.btnGhost}   onClick={handleEditProfile}>✏️ Edit Profile</button>
                </div>
            </div>

            {/* Programs */}
            <div style={s.section}>
                <div style={s.sbRow}>
                    <h3 style={{ ...s.sectionTitle, margin: 0 }}>Your Programs</h3>
                    <span style={{ color: '#8888aa', fontSize: '0.85rem' }}>0 active</span>
                </div>
                {!verified ? (
                    <div style={s.warning}>
                        <h4 style={{ margin: '0 0 0.5rem 0' }}>Verification Required</h4>
                        <p style={{ margin: 0, fontSize: '0.85rem', color: '#8888aa' }}>
                            Your account is pending verification. Programs can be created once verified (1–2 business days).
                        </p>
                    </div>
                ) : (
                    <div style={s.empty}>
                        <div style={s.emptyIcon}>📋</div>
                        <h4 style={s.emptyTitle}>No Programs Yet</h4>
                        <p style={{ margin: '0 0 1.25rem 0', fontSize: '0.85rem' }}>Create your first bug bounty program to start receiving reports.</p>
                        <button style={s.btnPrimary} onClick={handleCreateProgram}>Create First Program</button>
                    </div>
                )}
            </div>

            {/* Recent Activity */}
            <div style={s.section}>
                <h3 style={s.sectionTitle}>Recent Activity</h3>
                <div style={s.empty}>
                    <p style={{ margin: 0, fontSize: '0.85rem' }}>No recent activity</p>
                </div>
            </div>
        </div>
    );
};

export default CompanyDashboard;

