import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import api from '../../services/api';

const SCOPE_COLORS = {
    public: '#3498db',
    private: '#9b59b6',
    vdp: '#e67e22',
};

const STATUS_COLORS = {
    active: '#2ecc71',
    draft: '#f39c12',
    paused: '#e74c3c',
    closed: '#95a5a6',
};

const badge = (color, text) => ({
    display: 'inline-block',
    padding: '0.25rem 0.75rem',
    background: color + '20',
    color,
    borderRadius: '20px',
    fontSize: '0.8rem',
    fontWeight: '500',
    textTransform: 'uppercase',
    text,
});

const ProgramBrowser = () => {
    const [programs, setPrograms] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [joining, setJoining] = useState(null); // program id currently being joined
    const [filters, setFilters] = useState({
        scope_type: '',
        search: '',
    });

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

    const handleJoin = async (program) => {
        setJoining(program.id);
        try {
            const response = await api.post(`/programs/programs/${program.id}/join/`);
            alert(response.data.message);
            // Refresh so the button state updates
            loadPrograms();
        } catch (err) {
            const msg = err.response?.data?.error || 'Failed to join program.';
            alert(msg);
        } finally {
            setJoining(null);
        }
    };

    const handleRequestAccess = async (program) => {
        setJoining(program.id);
        try {
            const response = await api.post(`/programs/programs/${program.id}/join/`);
            alert(response.data.message);
            loadPrograms();
        } catch (err) {
            const msg = err.response?.data?.error || 'Failed to request access.';
            alert(msg);
        } finally {
            setJoining(null);
        }
    };

    const stats = {
        total: programs.length,
        public: programs.filter(p => p.scope_type === 'public').length,
        totalPaid: programs.reduce((sum, p) => sum + (parseFloat(p.total_bounties) || 0), 0),
        totalReports: programs.reduce((sum, p) => sum + (p.total_reports || 0), 0),
    };

    return (
        <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
            <div style={{ marginBottom: '2rem' }}>
                <h1 style={{ margin: '0 0 0.5rem 0' }}>Browse Bug Bounty Programs</h1>
                <p style={{ color: '#666', margin: 0 }}>
                    Discover security research programs from companies worldwide
                </p>
            </div>

            {/* Filters */}
            <div style={{
                background: 'white', padding: '1.5rem', borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)', marginBottom: '2rem'
            }}>
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                    <input
                        type="text"
                        placeholder="Search programs..."
                        value={filters.search}
                        onChange={(e) => setFilters(f => ({ ...f, search: e.target.value }))}
                        style={{
                            flex: 1, minWidth: '200px', padding: '0.75rem',
                            border: '1px solid #ddd', borderRadius: '4px', fontSize: '1rem'
                        }}
                    />
                    <select
                        value={filters.scope_type}
                        onChange={(e) => setFilters(f => ({ ...f, scope_type: e.target.value }))}
                        style={{
                            padding: '0.75rem', border: '1px solid #ddd',
                            borderRadius: '4px', fontSize: '1rem', minWidth: '140px'
                        }}
                    >
                        <option value="">All Types</option>
                        <option value="public">Public</option>
                        <option value="private">Private</option>
                        <option value="vdp">VDP</option>
                    </select>
                    {(filters.search || filters.scope_type) && (
                        <button
                            onClick={() => setFilters({ scope_type: '', search: '' })}
                            style={{
                                padding: '0.75rem 1rem', background: '#f8f9fa',
                                border: '1px solid #ddd', borderRadius: '4px',
                                cursor: 'pointer', fontSize: '0.9rem'
                            }}
                        >
                            Clear
                        </button>
                    )}
                </div>
            </div>

            {/* Summary stats */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                gap: '1rem', marginBottom: '2rem'
            }}>
                {[
                    { label: 'Total Programs', value: stats.total, color: '#3498db' },
                    { label: 'Public Programs', value: stats.public, color: '#2ecc71' },
                    { label: 'Total Paid Out', value: `$${stats.totalPaid.toLocaleString()}`, color: '#9b59b6' },
                    { label: 'Total Reports', value: stats.totalReports, color: '#e67e22' },
                ].map(({ label, value, color }) => (
                    <div key={label} style={{
                        background: 'white', padding: '1.5rem', borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)', textAlign: 'center'
                    }}>
                        <div style={{ fontSize: '2rem', fontWeight: 'bold', color }}>{value}</div>
                        <div style={{ color: '#666', fontSize: '0.9rem' }}>{label}</div>
                    </div>
                ))}
            </div>

            {/* Error */}
            {error && (
                <div style={{
                    background: '#f8d7da', color: '#721c24', padding: '1rem',
                    borderRadius: '8px', marginBottom: '2rem', border: '1px solid #f5c6cb'
                }}>
                    {error}
                    <button
                        onClick={loadPrograms}
                        style={{
                            marginLeft: '1rem', padding: '0.25rem 0.75rem',
                            background: '#721c24', color: 'white',
                            border: 'none', borderRadius: '4px', cursor: 'pointer'
                        }}
                    >
                        Retry
                    </button>
                </div>
            )}

            {/* Loading */}
            {loading && (
                <div style={{ textAlign: 'center', padding: '3rem' }}>
                    <div style={{
                        border: '4px solid #f3f3f3', borderTop: '4px solid #3498db',
                        borderRadius: '50%', width: '40px', height: '40px',
                        animation: 'spin 1s linear infinite', margin: '0 auto 1rem'
                    }} />
                    <p style={{ color: '#666' }}>Loading programs...</p>
                </div>
            )}

            {/* Programs grid */}
            {!loading && (
                <>
                    {programs.length === 0 ? (
                        <div style={{
                            background: 'white', padding: '3rem', borderRadius: '8px',
                            boxShadow: '0 2px 10px rgba(0,0,0,0.1)', textAlign: 'center'
                        }}>
                            <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.4 }}>🎯</div>
                            <h3 style={{ margin: '0 0 0.5rem 0' }}>No Programs Found</h3>
                            <p style={{ color: '#666', margin: '0 0 1.5rem 0' }}>
                                {filters.search
                                    ? `No programs match "${filters.search}".`
                                    : 'No active programs match your filters.'}
                            </p>
                            <button
                                onClick={() => setFilters({ scope_type: '', search: '' })}
                                style={{
                                    padding: '0.75rem 1.5rem', background: '#3498db',
                                    color: 'white', border: 'none',
                                    borderRadius: '4px', cursor: 'pointer'
                                }}
                            >
                                Clear Filters
                            </button>
                        </div>
                    ) : (
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))',
                            gap: '1.5rem', marginBottom: '2rem'
                        }}>
                            {programs.map((program) => {
                                const scopeColor = SCOPE_COLORS[program.scope_type] || '#7f8c8d';
                                const statusColor = STATUS_COLORS[program.status] || '#7f8c8d';
                                const isJoining = joining === program.id;
                                const canAccept = program.can_accept_submissions;

                                return (
                                    <div
                                        key={program.id}
                                        style={{
                                            background: 'white', borderRadius: '8px',
                                            boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                                            overflow: 'hidden', transition: 'transform 0.2s, box-shadow 0.2s'
                                        }}
                                        onMouseEnter={e => {
                                            e.currentTarget.style.transform = 'translateY(-4px)';
                                            e.currentTarget.style.boxShadow = '0 8px 25px rgba(0,0,0,0.15)';
                                        }}
                                        onMouseLeave={e => {
                                            e.currentTarget.style.transform = 'translateY(0)';
                                            e.currentTarget.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
                                        }}
                                    >
                                        <div style={{ padding: '1.5rem' }}>
                                            {/* Header */}
                                            <div style={{
                                                display: 'flex', justifyContent: 'space-between',
                                                alignItems: 'flex-start', marginBottom: '1rem'
                                            }}>
                                                <div style={{ flex: 1, marginRight: '1rem' }}>
                                                    <h3 style={{ margin: '0 0 0.25rem 0', fontSize: '1.1rem' }}>
                                                        <Link
                                                            to={`/programs/${program.id}`}
                                                            style={{ color: '#2c3e50', textDecoration: 'none' }}
                                                        >
                                                            {program.name}
                                                        </Link>
                                                    </h3>
                                                    <p style={{ color: '#666', fontSize: '0.85rem', margin: 0 }}>
                                                        {program.company?.username || '—'}
                                                    </p>
                                                </div>
                                                <span style={{
                                                    padding: '0.25rem 0.75rem',
                                                    background: scopeColor + '20',
                                                    color: scopeColor,
                                                    borderRadius: '20px',
                                                    fontSize: '0.75rem',
                                                    fontWeight: '600',
                                                    textTransform: 'uppercase',
                                                    whiteSpace: 'nowrap',
                                                }}>
                                                    {program.scope_type_display || program.scope_type}
                                                </span>
                                            </div>

                                            {/* Description */}
                                            <p style={{
                                                color: '#555', marginBottom: '1.25rem',
                                                lineHeight: '1.5', fontSize: '0.9rem',
                                                display: '-webkit-box',
                                                WebkitLineClamp: 3,
                                                WebkitBoxOrient: 'vertical',
                                                overflow: 'hidden',
                                            }}>
                                                {program.short_description || program.description}
                                            </p>

                                            {/* Stats grid */}
                                            <div style={{
                                                display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)',
                                                gap: '0.75rem', background: '#f8f9fa',
                                                padding: '1rem', borderRadius: '6px', marginBottom: '1.25rem'
                                            }}>
                                                <div>
                                                    <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.2rem' }}>
                                                        Bounty Range
                                                    </div>
                                                    <div style={{ fontWeight: '600', color: '#27ae60', fontSize: '0.9rem' }}>
                                                        {program.bounty_range || 'Not specified'}
                                                    </div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.2rem' }}>
                                                        Total Reports
                                                    </div>
                                                    <div style={{ fontWeight: '600', fontSize: '0.9rem' }}>
                                                        {program.total_reports ?? 0}
                                                    </div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.2rem' }}>
                                                        Total Bounties
                                                    </div>
                                                    <div style={{ fontWeight: '600', color: '#9b59b6', fontSize: '0.9rem' }}>
                                                        ${parseFloat(program.total_bounties || 0).toLocaleString()}
                                                    </div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.2rem' }}>
                                                        Status
                                                    </div>
                                                    <span style={{
                                                        padding: '0.2rem 0.5rem',
                                                        background: statusColor + '20',
                                                        color: statusColor,
                                                        borderRadius: '4px',
                                                        fontSize: '0.75rem', fontWeight: '600',
                                                    }}>
                                                        {program.status_display || program.status}
                                                    </span>
                                                </div>
                                            </div>

                                            {/* Actions */}
                                            <div style={{
                                                display: 'flex', justifyContent: 'space-between',
                                                alignItems: 'center'
                                            }}>
                                                <span style={{ fontSize: '0.8rem', color: '#999' }}>
                                                    {program.published_at
                                                        ? `Published ${new Date(program.published_at).toLocaleDateString()}`
                                                        : `Created ${new Date(program.created_at).toLocaleDateString()}`
                                                    }
                                                </span>
                                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                                    <Link
                                                        to={`/programs/${program.id}`}
                                                        style={{
                                                            padding: '0.5rem 1rem',
                                                            background: '#3498db', color: 'white',
                                                            textDecoration: 'none', borderRadius: '4px',
                                                            fontSize: '0.85rem', fontWeight: '500'
                                                        }}
                                                    >
                                                        View
                                                    </Link>
                                                    {canAccept && program.scope_type === 'public' && (
                                                        <button
                                                            onClick={() => handleJoin(program)}
                                                            disabled={isJoining}
                                                            style={{
                                                                padding: '0.5rem 1rem',
                                                                background: '#2ecc71', color: 'white',
                                                                border: 'none', borderRadius: '4px',
                                                                fontSize: '0.85rem', fontWeight: '500',
                                                                cursor: isJoining ? 'not-allowed' : 'pointer',
                                                                opacity: isJoining ? 0.7 : 1,
                                                            }}
                                                        >
                                                            {isJoining ? '...' : 'Join'}
                                                        </button>
                                                    )}
                                                    {canAccept && program.scope_type === 'private' && (
                                                        <button
                                                            onClick={() => handleRequestAccess(program)}
                                                            disabled={isJoining}
                                                            style={{
                                                                padding: '0.5rem 1rem',
                                                                background: '#9b59b6', color: 'white',
                                                                border: 'none', borderRadius: '4px',
                                                                fontSize: '0.85rem', fontWeight: '500',
                                                                cursor: isJoining ? 'not-allowed' : 'pointer',
                                                                opacity: isJoining ? 0.7 : 1,
                                                            }}
                                                        >
                                                            {isJoining ? '...' : 'Request Access'}
                                                        </button>
                                                    )}
                                                    {canAccept && program.scope_type === 'vdp' && (
                                                        <button
                                                            onClick={() => handleJoin(program)}
                                                            disabled={isJoining}
                                                            style={{
                                                                padding: '0.5rem 1rem',
                                                                background: '#e67e22', color: 'white',
                                                                border: 'none', borderRadius: '4px',
                                                                fontSize: '0.85rem', fontWeight: '500',
                                                                cursor: isJoining ? 'not-allowed' : 'pointer',
                                                                opacity: isJoining ? 0.7 : 1,
                                                            }}
                                                        >
                                                            {isJoining ? '...' : 'Participate'}
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </>
            )}

            {/* Legend */}
            <div style={{
                background: 'white', padding: '1.5rem', borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
            }}>
                <h4 style={{ margin: '0 0 1rem 0' }}>Program Types</h4>
                <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
                    {[
                        { color: SCOPE_COLORS.public, label: 'Public', desc: 'Open to all researchers' },
                        { color: SCOPE_COLORS.private, label: 'Private', desc: 'Invitation or application required' },
                        { color: SCOPE_COLORS.vdp, label: 'VDP', desc: 'Vulnerability Disclosure — no bounties' },
                    ].map(({ color, label, desc }) => (
                        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: color }} />
                            <span><strong>{label}:</strong> {desc}</span>
                        </div>
                    ))}
                </div>
            </div>

            <style>{`
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
};

export default ProgramBrowser;