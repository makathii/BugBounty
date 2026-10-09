// src/pages/ResearcherDashboard.jsx
import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import api, { reportAPI } from '../../services/api';

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

const ResearcherDashboard = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [stats, setStats] = useState(null);
    const [submissions, setSubmissions] = useState([]);
    const [programs, setPrograms] = useState([]);
    const [leaderboard, setLeaderboard] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const load = async () => {
            try {
                const [statsRes, subsRes, programsRes, lbRes] = await Promise.all([
                    reportAPI.getStats().catch(() => null),
                    reportAPI.getMySubmissions().catch(() => null),
                    api.get('/programs/researcher/').catch(() => null),
                    api.get('/leaderboard/', { params: { limit: 5 } }).catch(() => null),
                ]);
                if (statsRes) setStats(statsRes.data);
                if (subsRes) setSubmissions(subsRes.data.results || subsRes.data || []);
                if (programsRes) setPrograms(programsRes.data.results || programsRes.data || []);
                if (lbRes) setLeaderboard(lbRes.data.results || []);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, []);

    if (loading) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <div>Loading dashboard...</div>
            </div>
        );
    }

    const acceptedCount = (stats?.by_status?.accepted || 0) + (stats?.by_status?.resolved || 0);
    const activeCount = (stats?.by_status?.open || 0) + (stats?.by_status?.triaged || 0);
    const totalEarnings = submissions.reduce(
        (sum, s) => sum + (s.bounty_amount ? Number(s.bounty_amount) : 0), 0
    );
    const programsParticipated = new Set(
        submissions.map(s => s.program?.id || s.program).filter(Boolean)
    ).size;
    const myRank = leaderboard.find(e => e.username === user?.username)?.rank;

    return (
        <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
            <div style={{ marginBottom: '2rem' }}>
                <h1>Researcher Dashboard</h1>
                <p style={{ color: '#666' }}>
                    Welcome back, {user?.first_name || user?.username}!
                    {myRank ? ` You're ranked #${myRank} on the leaderboard.` : ''}
                </p>
            </div>

            {/* Stats Overview */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '1rem',
                marginBottom: '2rem'
            }}>
                <div style={{ ...cardStyle, padding: '1.5rem', textAlign: 'center' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#3498db' }}>{activeCount}</div>
                    <div style={{ color: '#666' }}>Active Submissions</div>
                </div>

                <div style={{ ...cardStyle, padding: '1.5rem', textAlign: 'center' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#2ecc71' }}>{acceptedCount}</div>
                    <div style={{ color: '#666' }}>Accepted Reports</div>
                </div>

                <div style={{ ...cardStyle, padding: '1.5rem', textAlign: 'center' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#e74c3c' }}>
                        ${totalEarnings.toLocaleString()}
                    </div>
                    <div style={{ color: '#666' }}>Total Earnings</div>
                </div>

                <div style={{ ...cardStyle, padding: '1.5rem', textAlign: 'center' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#9b59b6' }}>{programsParticipated}</div>
                    <div style={{ color: '#666' }}>Programs Participated</div>
                </div>
            </div>

            {/* Quick Actions */}
            <div style={{ ...cardStyle, marginBottom: '2rem' }}>
                <h3 style={{ margin: '0 0 1.5rem 0' }}>Quick Actions</h3>
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                    <button
                        onClick={() => navigate('/programs')}
                        style={{
                            background: '#3498db', color: 'white', padding: '1rem 1.5rem',
                            border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '1rem',
                            display: 'flex', alignItems: 'center', gap: '0.5rem'
                        }}
                    >
                        <span>🔍</span>
                        Find Programs
                    </button>

                    <button
                        onClick={() => navigate('/submit')}
                        style={{
                            background: '#2ecc71', color: 'white', padding: '1rem 1.5rem',
                            border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '1rem',
                            display: 'flex', alignItems: 'center', gap: '0.5rem'
                        }}
                    >
                        <span>📝</span>
                        Submit Report
                    </button>

                    <button
                        onClick={() => navigate('/reports')}
                        style={{
                            background: '#9b59b6', color: 'white', padding: '1rem 1.5rem',
                            border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '1rem',
                            display: 'flex', alignItems: 'center', gap: '0.5rem'
                        }}
                    >
                        <span>📋</span>
                        My Reports
                    </button>
                </div>
            </div>

            <div style={{
                display: 'grid',
                gridTemplateColumns: 'minmax(0, 2fr) minmax(260px, 1fr)',
                gap: '2rem',
                alignItems: 'start'
            }}>
                <div style={{ display: 'grid', gap: '2rem' }}>
                    {/* Available Programs */}
                    <div style={cardStyle}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                            <h3 style={{ margin: 0 }}>Available Programs</h3>
                            <button
                                onClick={() => navigate('/programs')}
                                style={{
                                    background: '#3498db', color: 'white', padding: '0.5rem 1rem',
                                    border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.9rem'
                                }}
                            >
                                View All Programs
                            </button>
                        </div>

                        {programs.length === 0 ? (
                            <div style={{
                                border: '2px dashed #ddd', borderRadius: '8px', padding: '3rem',
                                textAlign: 'center', color: '#666'
                            }}>
                                <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.5 }}>🎯</div>
                                <h4 style={{ margin: '0 0 1rem 0', color: '#333' }}>No Programs Available</h4>
                                <p style={{ margin: 0 }}>
                                    There are currently no active bug bounty programs. Check back soon!
                                </p>
                            </div>
                        ) : (
                            <div style={{ display: 'grid', gap: '1rem' }}>
                                {programs.slice(0, 4).map((program) => (
                                    <Link
                                        key={program.id}
                                        to={`/programs/${program.id}`}
                                        style={{
                                            border: '1px solid #eee', borderRadius: '8px',
                                            padding: '1rem 1.25rem', textDecoration: 'none', color: 'inherit',
                                            display: 'flex', justifyContent: 'space-between',
                                            alignItems: 'center', gap: '1rem', flexWrap: 'wrap'
                                        }}
                                    >
                                        <div style={{ minWidth: 0 }}>
                                            <div style={{ fontWeight: 600 }}>{program.name}</div>
                                            <div style={{ color: '#888', fontSize: '0.85rem' }}>
                                                {program.company?.username || ''} {program.short_description ? `• ${program.short_description.slice(0, 70)}…` : ''}
                                            </div>
                                        </div>
                                        <div style={{ color: '#2ecc71', fontWeight: 'bold', fontSize: '0.9rem', flexShrink: 0 }}>
                                            {program.bounty_range || ''}
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Recent Submissions */}
                    <div style={cardStyle}>
                        <h3 style={{ margin: '0 0 1.5rem 0' }}>Recent Submissions</h3>
                        {submissions.length === 0 ? (
                            <div style={{
                                border: '1px dashed #ddd', borderRadius: '8px', padding: '2rem',
                                textAlign: 'center', color: '#999'
                            }}>
                                <p style={{ margin: 0 }}>No recent submissions</p>
                            </div>
                        ) : (
                            <div style={{ display: 'grid', gap: '0.5rem' }}>
                                {submissions.slice(0, 5).map((sub) => (
                                    <Link
                                        key={sub.id}
                                        to={`/reports/${sub.id}`}
                                        style={{
                                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                            gap: '1rem', padding: '0.75rem 1rem', border: '1px solid #f0f0f0',
                                            borderRadius: '6px', textDecoration: 'none', color: 'inherit', flexWrap: 'wrap'
                                        }}
                                    >
                                        <div style={{ minWidth: 0 }}>
                                            <div style={{ fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                                {sub.title}
                                            </div>
                                            <div style={{ color: '#888', fontSize: '0.85rem' }}>
                                                {new Date(sub.created_at).toLocaleDateString()}
                                                {sub.bounty_amount ? ` • $${Number(sub.bounty_amount).toLocaleString()}` : ''}
                                            </div>
                                        </div>
                                        <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
                                            <span style={{
                                                padding: '0.2rem 0.6rem', borderRadius: '10px', fontSize: '0.75rem',
                                                fontWeight: 'bold', color: 'white',
                                                background: severityColors[sub.severity] || '#95a5a6',
                                                textTransform: 'capitalize'
                                            }}>
                                                {sub.severity}
                                            </span>
                                            <span style={{
                                                padding: '0.2rem 0.6rem', borderRadius: '10px', fontSize: '0.75rem',
                                                fontWeight: 'bold', color: 'white',
                                                background: statusColors[sub.status] || '#95a5a6',
                                                textTransform: 'capitalize'
                                            }}>
                                                {sub.status}
                                            </span>
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Leaderboard */}
                <div style={cardStyle}>
                    <h3 style={{ margin: '0 0 1.5rem 0' }}>🏆 Leaderboard</h3>
                    {leaderboard.length === 0 ? (
                        <p style={{ color: '#999', margin: 0 }}>No rankings yet.</p>
                    ) : (
                        <div style={{ display: 'grid', gap: '0.5rem' }}>
                            {leaderboard.map((entry) => {
                                const isMe = entry.username === user?.username;
                                return (
                                    <div
                                        key={entry.researcher_id}
                                        style={{
                                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                            padding: '0.6rem 0.9rem', borderRadius: '6px',
                                            background: isMe ? 'rgba(99,102,241,0.15)' : 'transparent',
                                            border: isMe ? '1px solid #6366f1' : '1px solid #f0f0f0'
                                        }}
                                    >
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                            <span style={{
                                                fontWeight: 'bold',
                                                color: entry.rank === 1 ? '#f1c40f'
                                                    : entry.rank === 2 ? '#95a5a6'
                                                    : entry.rank === 3 ? '#cd7f32' : '#666',
                                                width: '1.6rem'
                                            }}>
                                                #{entry.rank}
                                            </span>
                                            <span style={{ fontWeight: isMe ? 700 : 500 }}>
                                                {entry.username}{isMe ? ' (you)' : ''}
                                            </span>
                                        </div>
                                        <span style={{ color: '#9b59b6', fontWeight: 'bold' }}>
                                            {entry.total_points} pts
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ResearcherDashboard;
