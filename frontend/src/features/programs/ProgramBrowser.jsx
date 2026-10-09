import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import api from '../../services/api';
import { statusTone, scopeTone } from '../../utils/tones';
import { formatPoints } from '../../utils/points';

const LEGEND = [
    { scope: 'public', label: 'Public', desc: 'Open to all researchers' },
    { scope: 'private', label: 'Private', desc: 'Invitation or application required' },
    { scope: 'vdp', label: 'VDP', desc: 'Vulnerability Disclosure — no points' },
];

const JOIN_LABEL = { public: 'Join', private: 'Request Access', vdp: 'Participate' };

const ProgramBrowser = () => {
    const [programs, setPrograms] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [joining, setJoining] = useState(null); // program id currently being joined
    const [filters, setFilters] = useState({ scope_type: '', search: '' });

    const loadPrograms = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const params = {};
            if (filters.scope_type) params.scope_type = filters.scope_type;
            if (filters.search) params.search = filters.search;

            const response = await api.get('/programs/researcher/', { params });
            setPrograms(response.data.results ?? response.data);
        } catch (err) {
            setError('Failed to load programs. Please try again.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [filters]);

    useEffect(() => {
        const debounce = setTimeout(loadPrograms, 300);
        return () => clearTimeout(debounce);
    }, [loadPrograms]);

    // Public / VDP programs are joined directly; private ones create an access request.
    // Both go through the same endpoint, the backend decides what the call means.
    const handleJoin = async (program) => {
        setJoining(program.id);
        try {
            const response = await api.post(`/programs/programs/${program.id}/join/`);
            alert(response.data.message);
            loadPrograms(); // refresh so the button state updates
        } catch (err) {
            alert(err.response?.data?.error || 'Failed to join program.');
        } finally {
            setJoining(null);
        }
    };

    const clearFilters = () => setFilters({ scope_type: '', search: '' });

    const stats = [
        { label: 'Total Programs', value: programs.length, tone: 'accent' },
        { label: 'Public Programs', value: programs.filter(p => p.scope_type === 'public').length, tone: 'green' },
        {
            label: 'Points Awarded',
            value: formatPoints(programs.reduce((sum, p) => sum + (p.total_points || 0), 0)),
            tone: 'blue',
        },
        { label: 'Total Reports', value: programs.reduce((sum, p) => sum + (p.total_reports || 0), 0), tone: 'orange' },
    ];

    return (
        <div className="ui-page ui-page--wide">
            <header className="ui-page-header">
                <h1 className="ui-title">Browse Bug Bounty Programs</h1>
                <p className="ui-subtitle">Discover security research programs from companies worldwide</p>
            </header>

            <div className="ui-toolbar">
                <input
                    type="text"
                    className="ui-input ui-input--grow"
                    placeholder="Search programs..."
                    value={filters.search}
                    onChange={(e) => setFilters(f => ({ ...f, search: e.target.value }))}
                />
                <select
                    className="ui-select"
                    value={filters.scope_type}
                    onChange={(e) => setFilters(f => ({ ...f, scope_type: e.target.value }))}
                >
                    <option value="">All Types</option>
                    <option value="public">Public</option>
                    <option value="private">Private</option>
                    <option value="vdp">VDP</option>
                </select>
                {(filters.search || filters.scope_type) && (
                    <button className="ui-btn ui-btn--ghost" onClick={clearFilters}>Clear</button>
                )}
            </div>

            <div className="ui-grid ui-grid--stats">
                {stats.map(({ label, value, tone }) => (
                    <div key={label} className={`ui-stat tone-${tone}`}>
                        <div className="ui-stat-value">{value}</div>
                        <div className="ui-stat-label">{label}</div>
                    </div>
                ))}
            </div>

            {error && (
                <div className="ui-alert tone-red ui-row ui-row--between">
                    <span>{error}</span>
                    <button className="ui-btn ui-btn--danger ui-btn--sm" onClick={loadPrograms}>Retry</button>
                </div>
            )}

            {loading && (
                <div className="ui-loading">
                    <div className="ui-spinner" />
                    <p>Loading programs...</p>
                </div>
            )}

            {!loading && programs.length === 0 && (
                <div className="ui-card ui-empty">
                    <div className="ui-empty-icon">🎯</div>
                    <h3>No Programs Found</h3>
                    <p>
                        {filters.search
                            ? `No programs match "${filters.search}".`
                            : 'No active programs match your filters.'}
                    </p>
                    <button className="ui-btn" onClick={clearFilters}>Clear Filters</button>
                </div>
            )}

            {!loading && programs.length > 0 && (
                <div className="ui-grid ui-grid--cards">
                    {programs.map((program) => {
                        const isJoining = joining === program.id;
                        return (
                            <article key={program.id} className="ui-card ui-card--hover ui-stack">
                                <div className="ui-row ui-row--between ui-row--start ui-row--nowrap">
                                    <div className="ui-grow">
                                        <h3 className="ui-section-title" style={{ margin: 0 }}>
                                            <Link to={`/programs/${program.id}`} className="ui-link--title">
                                                {program.name}
                                            </Link>
                                        </h3>
                                        <p className="ui-muted ui-small" style={{ margin: '0.2rem 0 0' }}>
                                            {program.company?.username || '—'}
                                        </p>
                                    </div>
                                    <span className={`ui-badge ${scopeTone(program.scope_type)}`}>
                                        {program.scope_type_display || program.scope_type}
                                    </span>
                                </div>

                                <p className="ui-muted ui-small ui-clamp-3" style={{ margin: 0, lineHeight: 1.55 }}>
                                    {program.short_description || program.description}
                                </p>

                                <div className="ui-card--inset ui-kv">
                                    <div>
                                        <div className="ui-kv-label">Points Range</div>
                                        <div className="ui-kv-value tone-green ui-tone-text">
                                            {program.points_range || 'Not specified'}
                                        </div>
                                    </div>
                                    <div>
                                        <div className="ui-kv-label">Total Reports</div>
                                        <div className="ui-kv-value">{program.total_reports ?? 0}</div>
                                    </div>
                                    <div>
                                        <div className="ui-kv-label">Points Awarded</div>
                                        <div className="ui-kv-value">
                                            {formatPoints(program.total_points)}
                                        </div>
                                    </div>
                                    <div>
                                        <div className="ui-kv-label">Status</div>
                                        <span className={`ui-badge ${statusTone(program.status)}`}>
                                            {program.status_display || program.status}
                                        </span>
                                    </div>
                                </div>

                                <div className="ui-row ui-row--between">
                                    <span className="ui-muted ui-small">
                                        {program.published_at
                                            ? `Published ${new Date(program.published_at).toLocaleDateString()}`
                                            : `Created ${new Date(program.created_at).toLocaleDateString()}`}
                                    </span>
                                    <div className="ui-row">
                                        <Link to={`/programs/${program.id}`} className="ui-btn ui-btn--ghost ui-btn--sm">
                                            View
                                        </Link>
                                        {program.can_accept_submissions && JOIN_LABEL[program.scope_type] && (
                                            <button
                                                className="ui-btn ui-btn--sm"
                                                onClick={() => handleJoin(program)}
                                                disabled={isJoining}
                                            >
                                                {isJoining ? '...' : JOIN_LABEL[program.scope_type]}
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </article>
                        );
                    })}
                </div>
            )}

            <div className="ui-card">
                <h4 className="ui-section-title">Program Types</h4>
                <div className="ui-row" style={{ gap: '2rem' }}>
                    {LEGEND.map(({ scope, label, desc }) => (
                        <div key={scope} className={`ui-row ${scopeTone(scope)}`} style={{ gap: '0.5rem' }}>
                            <span className="ui-dot" />
                            <span className="ui-muted"><strong className="ui-strong">{label}:</strong> {desc}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default ProgramBrowser;
