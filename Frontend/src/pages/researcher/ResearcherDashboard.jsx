// src/pages/researcher/ResearcherDashboard.jsx
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const s = {
    page:    { padding: '2rem', maxWidth: '1200px', margin: '0 auto' },
    heading: { margin: '0 0 0.4rem 0', color: '#f0f0f5', fontWeight: 800, fontSize: '1.6rem', letterSpacing: '-0.02em' },
    sub:     { color: '#8888aa', margin: 0, fontSize: '0.9rem' },
    grid:    { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', margin: '2rem 0' },
    card:    { background: '#111118', border: '1px solid rgba(255,255,255,0.07)', padding: '1.5rem', borderRadius: '14px', textAlign: 'center' },
    cardVal: { fontSize: '2rem', fontWeight: 800, marginBottom: '0.3rem' },
    cardLbl: { color: '#8888aa', fontSize: '0.85rem' },
    section: { background: '#111118', border: '1px solid rgba(255,255,255,0.07)', padding: '1.75rem', borderRadius: '14px', marginBottom: '1.25rem' },
    sectionTitle: { margin: '0 0 1.25rem 0', color: '#f0f0f5', fontWeight: 700, fontSize: '1rem' },
    row:     { display: 'flex', gap: '0.75rem', flexWrap: 'wrap' },
    btnPrimary: { background: '#7c6aff', color: '#fff', padding: '0.7rem 1.25rem', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.4rem' },
    btnGreen:   { background: 'rgba(34,197,94,0.12)', color: '#22c55e', border: '1px solid rgba(34,197,94,0.3)', padding: '0.7rem 1.25rem', borderRadius: '8px', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.4rem' },
    btnGhost:   { background: 'rgba(255,255,255,0.06)', color: '#f0f0f5', border: '1px solid rgba(255,255,255,0.07)', padding: '0.7rem 1.25rem', borderRadius: '8px', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.4rem' },
    empty:   { border: '1px dashed rgba(255,255,255,0.1)', borderRadius: '10px', padding: '2.5rem', textAlign: 'center', color: '#8888aa' },
    emptyIcon: { fontSize: '2.5rem', marginBottom: '0.75rem', opacity: 0.5 },
    emptyTitle: { margin: '0 0 0.5rem 0', color: '#f0f0f5', fontWeight: 600 },
    sbRow:   { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' },
};

const ResearcherDashboard = () => {
    const { user } = useAuth();
    const navigate = useNavigate();

    return (
        <div style={s.page}>
            <div style={{ marginBottom: '0.5rem' }}>
                <h1 style={s.heading}>Researcher Dashboard</h1>
                <p style={s.sub}>Welcome back, {user?.first_name || user?.username}!</p>
            </div>

            {/* Stats */}
            <div style={s.grid}>
                <div style={s.card}>
                    <div style={{ ...s.cardVal, color: '#7c6aff' }}>0</div>
                    <div style={s.cardLbl}>Active Submissions</div>
                </div>
                <div style={s.card}>
                    <div style={{ ...s.cardVal, color: '#22c55e' }}>0</div>
                    <div style={s.cardLbl}>Accepted Reports</div>
                </div>
                <div style={s.card}>
                    <div style={{ ...s.cardVal, color: '#22c55e' }}>$0</div>
                    <div style={s.cardLbl}>Total Earnings</div>
                </div>
                <div style={s.card}>
                    <div style={{ ...s.cardVal, color: '#a78bfa' }}>0</div>
                    <div style={s.cardLbl}>Programs Joined</div>
                </div>
            </div>

            {/* Quick Actions */}
            <div style={s.section}>
                <h3 style={s.sectionTitle}>Quick Actions</h3>
                <div style={s.row}>
                    <button style={s.btnPrimary} onClick={() => navigate('/programs')}>🔍 Find Programs</button>
                    <button style={s.btnGreen}   onClick={() => navigate('/submit')}>📝 Submit Report</button>
                    <button style={s.btnGhost}   onClick={() => navigate('/reports')}>📋 My Reports</button>
                </div>
            </div>

            {/* Available Programs */}
            <div style={s.section}>
                <div style={s.sbRow}>
                    <h3 style={{ ...s.sectionTitle, margin: 0 }}>Available Programs</h3>
                    <button style={s.btnPrimary} onClick={() => navigate('/programs')}>View All</button>
                </div>
                <div style={s.empty}>
                    <div style={s.emptyIcon}>🎯</div>
                    <h4 style={s.emptyTitle}>No Programs Yet</h4>
                    <p style={{ margin: 0, fontSize: '0.85rem' }}>Browse active bug bounty programs to get started.</p>
                </div>
            </div>

            {/* Recent Submissions */}
            <div style={s.section}>
                <h3 style={s.sectionTitle}>Recent Submissions</h3>
                <div style={s.empty}>
                    <p style={{ margin: 0, fontSize: '0.85rem' }}>No recent submissions</p>
                </div>
            </div>
        </div>
    );
};

export default ResearcherDashboard;
