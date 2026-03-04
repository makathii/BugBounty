import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../../services/api';

const ProgramBrowser = () => {
    const [programs, setPrograms] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({
        scope_type: 'all',
        status: 'active',
        min_bounty: '',
        max_bounty: '',
        search: ''
    });

    useEffect(() => {
        loadPrograms();
    }, [filters]);

    const loadPrograms = async () => {
        try {
            // For now, we'll simulate data. Replace with actual API call:
            // const response = await api.get('/programs/researcher/');

            // Simulated data for testing
            setTimeout(() => {
                setPrograms([
                    {
                        id: 1,
                        name: 'Acme Corp Public Bug Bounty',
                        description: 'Public bug bounty program for Acme Corp web applications. Looking for security vulnerabilities in our customer-facing platforms.',
                        company_name: 'Acme Corporation',
                        scope_type: 'public',
                        status: 'active',
                        min_bounty: 100,
                        max_bounty: 10000,
                        total_reports: 42,
                        total_payout: 12500,
                        created_at: '2024-01-15T10:30:00Z'
                    },
                    {
                        id: 2,
                        name: 'TechSecure API Security Program',
                        description: 'Private program focused on API security testing. Invitation-only for trusted researchers.',
                        company_name: 'TechSecure Inc.',
                        scope_type: 'private',
                        status: 'active',
                        min_bounty: 500,
                        max_bounty: 20000,
                        total_reports: 18,
                        total_payout: 8500,
                        created_at: '2024-02-20T14:45:00Z'
                    },
                    {
                        id: 3,
                        name: 'FinTrust VDP',
                        description: 'Vulnerability Disclosure Program for FinTrust banking applications.',
                        company_name: 'FinTrust Bank',
                        scope_type: 'vdp',
                        status: 'active',
                        min_bounty: 0,
                        max_bounty: 5000,
                        total_reports: 25,
                        total_payout: 3200,
                        created_at: '2024-03-10T09:15:00Z'
                    }
                ]);
                setLoading(false);
            }, 1000);
        } catch (error) {
            console.error('Failed to load programs:', error);
            setLoading(false);
        }
    };

    const handleFilterChange = (key, value) => {
        setFilters(prev => ({
            ...prev,
            [key]: value
        }));
    };

    const getStatusColor = (status) => {
        switch(status) {
            case 'active': return '#2ecc71';
            case 'draft': return '#f39c12';
            case 'paused': return '#e74c3c';
            case 'closed': return '#95a5a6';
            default: return '#7f8c8d';
        }
    };

    const getScopeTypeColor = (scope_type) => {
        switch(scope_type) {
            case 'public': return '#3498db';
            case 'private': return '#9b59b6';
            case 'vdp': return '#e67e22';
            default: return '#7f8c8d';
        }
    };

    if (loading) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <div style={{
                    border: '4px solid #f3f3f3',
                    borderTop: '4px solid #3498db',
                    borderRadius: '50%',
                    width: '40px',
                    height: '40px',
                    animation: 'spin 1s linear infinite',
                    margin: '0 auto 1rem'
                }}></div>
                <p>Loading programs...</p>
            </div>
        );
    }

    return (
        <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
            <div style={{ marginBottom: '2rem' }}>
                <h1>Browse Bug Bounty Programs</h1>
                <p style={{ color: '#666' }}>Discover security research programs from companies worldwide</p>
        </div>

    {/* Filters */}
    <div style={{
        background: 'white',
        padding: '1.5rem',
        borderRadius: '8px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
        marginBottom: '2rem'
    }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '200px' }}>
                <input
                    type="text"
                    placeholder="Search programs..."
                    value={filters.search}
                    onChange={(e) => handleFilterChange('search', e.target.value)}
                    style={{
                        width: '100%',
                        padding: '0.75rem',
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        fontSize: '1rem'
                    }}
                />
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <select
                    value={filters.scope_type}
                    onChange={(e) => handleFilterChange('scope_type', e.target.value)}
                    style={{
                        padding: '0.75rem',
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        fontSize: '1rem',
                        minWidth: '120px'
                    }}
                >
                    <option value="all">All Types</option>
                    <option value="public">Public</option>
                    <option value="private">Private</option>
                    <option value="vdp">VDP</option>
                </select>

                <select
                    value={filters.status}
                    onChange={(e) => handleFilterChange('status', e.target.value)}
                    style={{
                        padding: '0.75rem',
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        fontSize: '1rem',
                        minWidth: '120px'
                    }}
                >
                    <option value="active">Active</option>
                    <option value="all">All Status</option>
                    <option value="draft">Draft</option>
                    <option value="paused">Paused</option>
                </select>
            </div>
        </div>
    </div>

    {/* Program Stats */}
    <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '1rem',
        marginBottom: '2rem'
    }}>
        <div style={{
            background: 'white',
            padding: '1.5rem',
            borderRadius: '8px',
            boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
            textAlign: 'center'
        }}>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#3498db' }}>
                {programs.length}
            </div>
            <div style={{ color: '#666' }}>Total Programs</div>
        </div>

        <div style={{
            background: 'white',
            padding: '1.5rem',
            borderRadius: '8px',
            boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
            textAlign: 'center'
        }}>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#2ecc71' }}>
                {programs.filter(p => p.scope_type === 'public').length}
            </div>
            <div style={{ color: '#666' }}>Public Programs</div>
        </div>

        <div style={{
            background: 'white',
            padding: '1.5rem',
            borderRadius: '8px',
            boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
            textAlign: 'center'
        }}>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#9b59b6' }}>
                ${programs.reduce((sum, p) => sum + (p.total_payout || 0), 0).toLocaleString()}
            </div>
            <div style={{ color: '#666' }}>Total Paid Out</div>
        </div>

        <div style={{
            background: 'white',
            padding: '1.5rem',
            borderRadius: '8px',
            boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
            textAlign: 'center'
        }}>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#e67e22' }}>
                {programs.reduce((sum, p) => sum + (p.total_reports || 0), 0)}
            </div>
            <div style={{ color: '#666' }}>Total Reports</div>
        </div>
    </div>

    {/* Programs Grid */}
    <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))',
        gap: '1.5rem',
        marginBottom: '2rem'
    }}>
        {programs.map((program) => (
            <div
                key={program.id}
                style={{
                    background: 'white',
                    borderRadius: '8px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                    overflow: 'hidden',
                    transition: 'transform 0.2s, box-shadow 0.2s'
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-4px)';
                    e.currentTarget.style.boxShadow = '0 8px 25px rgba(0,0,0,0.15)';
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
                }}
            >
                <div style={{ padding: '1.5rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                        <div>
                            <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.25rem' }}>
                                <Link
                                    to={`/programs/${program.id}`}
                                    style={{ color: '#2c3e50', textDecoration: 'none' }}
                                >
                                    {program.name}
                                </Link>
                            </h3>
                            <p style={{ color: '#666', fontSize: '0.9rem', margin: 0 }}>
                                {program.company_name}
                            </p>
                        </div>
                        <span style={{
                            padding: '0.25rem 0.75rem',
                            background: getScopeTypeColor(program.scope_type) + '20',
                            color: getScopeTypeColor(program.scope_type),
                            borderRadius: '20px',
                            fontSize: '0.8rem',
                            fontWeight: '500',
                            textTransform: 'uppercase'
                        }}>
                                    {program.scope_type}
                                </span>
                    </div>

                    <p style={{
                        color: '#666',
                        marginBottom: '1.5rem',
                        lineHeight: '1.5',
                        fontSize: '0.95rem'
                    }}>
                        {program.description.length > 150
                            ? `${program.description.substring(0, 150)}...`
                            : program.description
                        }
                    </p>

                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(2, 1fr)',
                        gap: '1rem',
                        background: '#f8f9fa',
                        padding: '1rem',
                        borderRadius: '6px',
                        marginBottom: '1.5rem'
                    }}>
                        <div>
                            <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.25rem' }}>
                                Bounty Range
                            </div>
                            <div style={{ fontWeight: '500', color: '#27ae60' }}>
                                ${program.min_bounty || '0'} - ${program.max_bounty || 'Unlimited'}
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.25rem' }}>
                                Total Reports
                            </div>
                            <div style={{ fontWeight: '500' }}>
                                {program.total_reports || 0}
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.25rem' }}>
                                Total Payout
                            </div>
                            <div style={{ fontWeight: '500', color: '#9b59b6' }}>
                                ${program.total_payout?.toLocaleString() || '0'}
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.25rem' }}>
                                Status
                            </div>
                            <span style={{
                                padding: '0.25rem 0.5rem',
                                background: getStatusColor(program.status) + '20',
                                color: getStatusColor(program.status),
                                borderRadius: '4px',
                                fontSize: '0.8rem',
                                fontWeight: '500'
                            }}>
                                        {program.status}
                                    </span>
                        </div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span style={{ fontSize: '0.85rem', color: '#7f8c8d' }}>
                                    Created: {new Date(program.created_at).toLocaleDateString()}
                                </span>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <Link
                                to={`/programs/${program.id}`}
                                style={{
                                    padding: '0.5rem 1rem',
                                    background: '#3498db',
                                    color: 'white',
                                    textDecoration: 'none',
                                    borderRadius: '4px',
                                    fontSize: '0.9rem',
                                    fontWeight: '500'
                                }}
                            >
                                View Details
                            </Link>
                            {program.scope_type === 'public' ? (
                                <button
                                    style={{
                                        padding: '0.5rem 1rem',
                                        background: '#2ecc71',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '4px',
                                        fontSize: '0.9rem',
                                        fontWeight: '500',
                                        cursor: 'pointer'
                                    }}
                                >
                                    Join Program
                                </button>
                            ) : (
                                <button
                                    style={{
                                        padding: '0.5rem 1rem',
                                        background: '#95a5a6',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '4px',
                                        fontSize: '0.9rem',
                                        fontWeight: '500',
                                        cursor: 'pointer'
                                    }}
                                >
                                    Request Access
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        ))}
    </div>

    {programs.length === 0 && (
        <div style={{
            background: 'white',
            padding: '3rem',
            borderRadius: '8px',
            boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
            textAlign: 'center'
        }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.5 }}>🎯</div>
            <h3 style={{ margin: '0 0 1rem 0' }}>No Programs Found</h3>
            <p style={{ margin: '0 0 1.5rem 0', color: '#666' }}>
                {filters.search
                    ? `No programs match "${filters.search}". Try a different search.`
                    : 'There are currently no active bug bounty programs matching your filters.'
                }
            </p>
            <button
                onClick={() => setFilters({
                    scope_type: 'all',
                    status: 'active',
                    min_bounty: '',
                    max_bounty: '',
                    search: ''
                })}
                style={{
                    padding: '0.75rem 1.5rem',
                    background: '#3498db',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '1rem'
                }}
            >
                Clear Filters
            </button>
        </div>
    )}

    {/* Legend */}
    <div style={{
        background: 'white',
        padding: '1.5rem',
        borderRadius: '8px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
        marginTop: '2rem'
    }}>
        <h4 style={{ margin: '0 0 1rem 0' }}>Program Types</h4>
        <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    background: '#3498db'
                }}></div>
                <span><strong>Public:</strong> Open to all researchers</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    background: '#9b59b6'
                }}></div>
                <span><strong>Private:</strong> Invitation or application required</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    background: '#e67e22'
                }}></div>
                <span><strong>VDP:</strong> Vulnerability Disclosure Program (no bounties)</span>
            </div>
        </div>
    </div>
</div>
);
};

export default ProgramBrowser;