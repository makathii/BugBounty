// src/pages/ResearcherDashboard.jsx
import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import api, { reportAPI } from '../../services/api';
import { statusTone, severityTone } from '../../utils/tones';

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
            <div className="ui-loading">
                <div className="ui-spinner" />
                <p>Loading dashboard...</p>
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

    const statCards = [
        { label: 'Active Submissions', value: activeCount, tone: 'blue' },
        { label: 'Accepted Reports', value: acceptedCount, tone: 'green' },
        { label: 'Total Earnings', value: `$${totalEarnings.toLocaleString()}`, tone: 'accent' },
        { label: 'Programs Participated', value: programsParticipated, tone: 'orange' },
    ];
    const rankTone = (rank) => (rank === 1 ? 'tone-yellow' : rank === 2 ? 'tone-gray' : rank === 3 ? 'tone-orange' : 'tone-gray');

    return (
        <div className="ui-page">
            <header className="ui-page-header">
                <h1 className="ui-title">Researcher Dashboard</h1>
                <p className="ui-subtitle">
                    Welcome back, {user?.first_name || user?.username}!
                    {myRank ? ` You're ranked #${myRank} on the leaderboard.` : ''}
                </p>
            </header>

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
                    <button className="ui-btn" onClick={() => navigate('/programs')}>🔍 Find Programs</button>
                    <button className="ui-btn ui-btn--green" onClick={() => navigate('/submit')}>📝 Submit Report</button>
                    <button className="ui-btn ui-btn--ghost" onClick={() => navigate('/reports')}>📋 My Reports</button>
                </div>
            </div>

            <div className="ui-grid ui-grid--sidebar">
                <div className="ui-stack" style={{ gap: '1.25rem' }}>
                    <div className="ui-card">
                        <div className="ui-card-head">
                            <h3 className="ui-section-title">Available Programs</h3>
                            <button className="ui-btn ui-btn--ghost ui-btn--sm" onClick={() => navigate('/programs')}>
                                View All Programs
                            </button>
                        </div>

                        {programs.length === 0 ? (
                            <div className="ui-empty">
                                <div className="ui-empty-icon">🎯</div>
                                <h3>No Programs Available</h3>
                                <p>There are currently no active bug bounty programs. Check back soon!</p>
                            </div>
                        ) : (
                            <div className="ui-list">
                                {programs.slice(0, 4).map((program) => (
                                    <Link key={program.id} to={`/programs/${program.id}`} className="ui-list-item">
                                        <div style={{ minWidth: 0 }}>
                                            <div className="ui-strong">{program.name}</div>
                                            <div className="ui-muted ui-small">
                                                {program.company?.username || ''} {program.short_description ? `• ${program.short_description.slice(0, 70)}…` : ''}
                                            </div>
                                        </div>
                                        <div className="ui-tone-text tone-green ui-strong ui-small" style={{ flexShrink: 0 }}>
                                            {program.bounty_range || ''}
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="ui-card">
                        <h3 className="ui-section-title">Recent Submissions</h3>
                        {submissions.length === 0 ? (
                            <div className="ui-empty"><p>No recent submissions</p></div>
                        ) : (
                            <div className="ui-list">
                                {submissions.slice(0, 5).map((sub) => (
                                    <Link key={sub.id} to={`/reports/${sub.id}`} className="ui-list-item">
                                        <div style={{ minWidth: 0 }}>
                                            <div className="ui-strong" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                                {sub.title}
                                            </div>
                                            <div className="ui-muted ui-small">
                                                {new Date(sub.created_at).toLocaleDateString()}
                                                {sub.bounty_amount ? ` • $${Number(sub.bounty_amount).toLocaleString()}` : ''}
                                            </div>
                                        </div>
                                        <div className="ui-row" style={{ flexShrink: 0, gap: '0.4rem' }}>
                                            <span className={`ui-badge ${severityTone(sub.severity)}`}>{sub.severity}</span>
                                            <span className={`ui-badge ${statusTone(sub.status)}`}>{sub.status}</span>
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                <div className="ui-card">
                    <h3 className="ui-section-title">🏆 Leaderboard</h3>
                    {leaderboard.length === 0 ? (
                        <p className="ui-muted" style={{ margin: 0 }}>No rankings yet.</p>
                    ) : (
                        <div className="ui-list">
                            {leaderboard.map((entry) => {
                                const isMe = entry.username === user?.username;
                                return (
                                    <div
                                        key={entry.researcher_id}
                                        className={`ui-list-item${isMe ? ' ui-list-item--accent' : ''}`}
                                    >
                                        <div className="ui-row" style={{ gap: '0.6rem' }}>
                                            <span className={`ui-tone-text ${rankTone(entry.rank)} ui-strong`} style={{ width: '1.8rem' }}>
                                                #{entry.rank}
                                            </span>
                                            <span className={isMe ? 'ui-strong' : ''}>
                                                {entry.username}{isMe ? ' (you)' : ''}
                                            </span>
                                        </div>
                                        <span className="ui-tone-text tone-accent ui-strong ui-small">
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
