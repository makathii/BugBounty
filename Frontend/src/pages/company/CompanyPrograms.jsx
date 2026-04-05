import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { companyAPI } from '../../services/api';

const STATUS_COLORS = {
    active: '#27ae60',
    draft: '#f39c12',
    paused: '#e74c3c',
    closed: '#95a5a6',
};

const CompanyPrograms = () => {
    const navigate = useNavigate();
    const [programs, setPrograms] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [actioning, setActioning] = useState(null);

    useEffect(() => { loadPrograms(); }, []);

    const loadPrograms = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await companyAPI.getPrograms();
            setPrograms(res.data.results ?? res.data);
        } catch {
            setError('Failed to load programs.');
        } finally {
            setLoading(false);
        }
    };

    const handleAction = async (id, action) => {
        setActioning(id);
        try {
            if (action === 'activate') await companyAPI.activateProgram(id);
            if (action === 'pause') await companyAPI.pauseProgram(id);
            if (action === 'close') await companyAPI.closeProgram(id);
            await loadPrograms();
        } catch (err) {
            alert(err.response?.data?.error || `Failed to ${action} program.`);
        } finally {
            setActioning(null);
        }
    };

    if (loading) return (
        <div style={{ padding: '3rem', textAlign: 'center', color: '#666' }}>
            Loading programs...
        </div>
    );

    return (
        <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                    <h1 style={{ margin: '0 0 0.25rem 0' }}>Your Programs</h1>
                    <p style={{ margin: 0, color: '#666' }}>Manage your bug bounty programs</p>
                </div>
                <button
                    onClick={() => navigate('/company/programs/create')}
                    style={{
                        padding: '0.75rem 1.5rem', background: '#27ae60',
                        color: 'white', border: 'none', borderRadius: '6px',
                        cursor: 'pointer', fontSize: '1rem', fontWeight: '600'
                    }}
                >
                    + Create Program
                </button>
            </div>

            {error && (
                <div style={{
                    background: '#f8d7da', color: '#721c24', padding: '1rem',
                    borderRadius: '6px', marginBottom: '1.5rem'
                }}>
                    {error}
                </div>
            )}

            {programs.length === 0 ? (
                <div style={{
                    background: 'white', padding: '3rem', borderRadius: '10px',
                    textAlign: 'center', boxShadow: '0 2px 10px rgba(0,0,0,0.08)'
                }}>
                    <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🎯</div>
                    <h3 style={{ margin: '0 0 0.5rem 0' }}>No programs yet</h3>
                    <p style={{ color: '#666', marginBottom: '1.5rem' }}>
                        Create your first bug bounty program to start receiving security reports.
                    </p>
                    <button
                        onClick={() => navigate('/company/programs/create')}
                        style={{
                            padding: '0.75rem 1.5rem', background: '#3498db',
                            color: 'white', border: 'none', borderRadius: '6px',
                            cursor: 'pointer', fontSize: '1rem'
                        }}
                    >
                        Create Your First Program
                    </button>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {programs.map(program => {
                        const statusColor = STATUS_COLORS[program.status] || '#7f8c8d';
                        const isActioning = actioning === program.id;
                        return (
                            <div key={program.id} style={{
                                background: 'white', borderRadius: '10px', padding: '1.5rem',
                                boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
                                borderLeft: `4px solid ${statusColor}`
                            }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                                    <div style={{ flex: 1 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                                            <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{program.name}</h3>
                                            <span style={{
                                                padding: '0.2rem 0.6rem', borderRadius: '4px',
                                                fontSize: '0.75rem', fontWeight: '700',
                                                background: statusColor + '20', color: statusColor,
                                                textTransform: 'uppercase'
                                            }}>
                                                {program.status}
                                            </span>
                                            <span style={{
                                                padding: '0.2rem 0.6rem', borderRadius: '4px',
                                                fontSize: '0.75rem', background: '#e9ecef', color: '#495057',
                                                textTransform: 'capitalize'
                                            }}>
                                                {program.scope_type}
                                            </span>
                                        </div>
                                        <p style={{ margin: '0 0 0.75rem 0', color: '#666', fontSize: '0.9rem' }}>
                                            {program.short_description || program.description?.substring(0, 100) + '...'}
                                        </p>
                                        <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.85rem', color: '#666' }}>
                                            <span>📋 {program.total_reports} reports</span>
                                            <span>💰 ${parseFloat(program.total_bounties || 0).toLocaleString()} paid</span>
                                            {program.bounty_range && program.bounty_range !== 'Not specified' && (
                                                <span>🎯 {program.bounty_range}</span>
                                            )}
                                        </div>
                                    </div>

                                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                                        <Link
                                            to={`/programs/${program.id}`}
                                            style={{
                                                padding: '0.5rem 1rem', background: '#f8f9fa',
                                                color: '#495057', textDecoration: 'none',
                                                borderRadius: '4px', fontSize: '0.85rem',
                                                border: '1px solid #dee2e6'
                                            }}
                                        >
                                            View
                                        </Link>

                                        {program.status === 'draft' && (
                                            <button
                                                onClick={() => handleAction(program.id, 'activate')}
                                                disabled={isActioning}
                                                style={{
                                                    padding: '0.5rem 1rem', background: '#27ae60',
                                                    color: 'white', border: 'none', borderRadius: '4px',
                                                    cursor: isActioning ? 'not-allowed' : 'pointer',
                                                    fontSize: '0.85rem', opacity: isActioning ? 0.7 : 1
                                                }}
                                            >
                                                {isActioning ? '...' : 'Activate'}
                                            </button>
                                        )}
                                        {program.status === 'active' && (
                                            <button
                                                onClick={() => handleAction(program.id, 'pause')}
                                                disabled={isActioning}
                                                style={{
                                                    padding: '0.5rem 1rem', background: '#e67e22',
                                                    color: 'white', border: 'none', borderRadius: '4px',
                                                    cursor: isActioning ? 'not-allowed' : 'pointer',
                                                    fontSize: '0.85rem', opacity: isActioning ? 0.7 : 1
                                                }}
                                            >
                                                {isActioning ? '...' : 'Pause'}
                                            </button>
                                        )}
                                        {program.status === 'paused' && (
                                            <button
                                                onClick={() => handleAction(program.id, 'activate')}
                                                disabled={isActioning}
                                                style={{
                                                    padding: '0.5rem 1rem', background: '#27ae60',
                                                    color: 'white', border: 'none', borderRadius: '4px',
                                                    cursor: isActioning ? 'not-allowed' : 'pointer',
                                                    fontSize: '0.85rem', opacity: isActioning ? 0.7 : 1
                                                }}
                                            >
                                                {isActioning ? '...' : 'Resume'}
                                            </button>
                                        )}
                                        {program.status !== 'closed' && (
                                            <button
                                                onClick={() => {
                                                    if (window.confirm('Close this program? Researchers will no longer be able to submit reports.')) {
                                                        handleAction(program.id, 'close');
                                                    }
                                                }}
                                                disabled={isActioning}
                                                style={{
                                                    padding: '0.5rem 1rem', background: 'white',
                                                    color: '#e74c3c', border: '1px solid #e74c3c',
                                                    borderRadius: '4px',
                                                    cursor: isActioning ? 'not-allowed' : 'pointer',
                                                    fontSize: '0.85rem', opacity: isActioning ? 0.7 : 1
                                                }}
                                            >
                                                Close
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

export default CompanyPrograms;