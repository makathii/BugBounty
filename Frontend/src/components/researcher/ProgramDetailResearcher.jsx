import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';

const ProgramDetailResearcher = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const [program, setProgram] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview');
    const [hasJoined, setHasJoined] = useState(false);
    const [joining, setJoining] = useState(false);

    useEffect(() => {
        loadProgram();
        checkIfJoined();
    }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

    const loadProgram = async () => {
        try {
            // Simulate API call - replace with actual:
            // const response = await api.get(`/programs/programs/${id}/`);

            setTimeout(() => {
                setProgram({
                    id: 1,
                    name: 'Acme Corp Public Bug Bounty',
                    description: 'Acme Corporation welcomes security researchers to participate in our public bug bounty program. We value the security research community and believe that working with skilled security researchers is crucial to identifying vulnerabilities in our systems.\n\nThis program covers our customer-facing web applications and APIs. We are particularly interested in findings related to authentication bypass, privilege escalation, sensitive data exposure, and remote code execution.',
                    company_name: 'Acme Corporation',
                    scope_type: 'public',
                    status: 'active',
                    bounty_policy: 'We offer bounties ranging from $100 to $10,000 based on severity and impact. Critical vulnerabilities can receive up to $10,000. Payments are made via PayPal or cryptocurrency within 30 days of verification.\n\nPayment tiers:\n- Critical: $5,000 - $10,000\n- High: $1,000 - $5,000\n- Medium: $100 - $1,000\n- Low: Swag or recognition',
                    min_bounty: 100,
                    max_bounty: 10000,
                    total_reports: 42,
                    total_payout: 12500,
                    avg_severity_score: 3.2,
                    created_at: '2024-01-15T10:30:00Z',
                    updated_at: '2024-03-15T14:20:00Z',
                    scopes: [
                        {
                            id: 1,
                            target: '*.acmecorp.com',
                            target_type: 'web_application',
                            is_in_scope: true,
                            description: 'All subdomains of acmecorp.com'
                        },
                        {
                            id: 2,
                            target: 'api.acmecorp.com',
                            target_type: 'api',
                            is_in_scope: true,
                            description: 'Public API endpoints'
                        },
                        {
                            id: 3,
                            target: 'admin.acmecorp.com',
                            target_type: 'web_application',
                            is_in_scope: false,
                            description: 'Administrative interface (out of scope)'
                        },
                        {
                            id: 4,
                            target: 'mobile.acmecorp.com',
                            target_type: 'mobile_app',
                            is_in_scope: true,
                            description: 'Mobile application backend'
                        }
                    ]
                });
                setLoading(false);
            }, 1000);
        } catch (error) {
            console.error('Failed to load program:', error);
            setLoading(false);
        }
    };

    const checkIfJoined = async () => {
        // Check if user has joined this program
        setHasJoined(false); // For now, simulate
    };

    const handleJoinProgram = async () => {
        setJoining(true);
        try {
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 1000));
            setHasJoined(true);
        } catch (error) {
            console.error('Failed to join program:', error);
        } finally {
            setJoining(false);
        }
    };

    const handleSubmitReport = () => {
        navigate(`/submit?program=${id}`);
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
                <p>Loading program details...</p>
            </div>
        );
    }

    if (!program) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <h2>Program not found</h2>
                <p>The program you're looking for doesn't exist or you don't have access.</p>
                <Link to="/programs" style={{
                    padding: '0.75rem 1.5rem',
                    background: '#3498db',
                    color: 'white',
                    textDecoration: 'none',
                    borderRadius: '4px',
                    display: 'inline-block'
                }}>
                    Browse Programs
                </Link>
            </div>
        );
    }

    return (
        <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
            {/* Header */}
            <div style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                        <h1 style={{ margin: '0 0 0.5rem 0' }}>{program.name}</h1>
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                            <span style={{
                                padding: '0.5rem 1rem',
                                background: '#3498db20',
                                color: '#3498db',
                                borderRadius: '20px',
                                fontSize: '0.9rem',
                                fontWeight: '500'
                            }}>
                                {program.scope_type.toUpperCase()}
                            </span>
                            <span style={{
                                padding: '0.5rem 1rem',
                                background: '#2ecc7120',
                                color: '#2ecc71',
                                borderRadius: '20px',
                                fontSize: '0.9rem',
                                fontWeight: '500'
                            }}>
                                ACTIVE
                            </span>
                            <span style={{
                                padding: '0.5rem 1rem',
                                background: '#9b59b620',
                                color: '#9b59b6',
                                borderRadius: '20px',
                                fontSize: '0.9rem',
                                fontWeight: '500'
                            }}>
                                ${program.min_bounty} - ${program.max_bounty} BOUNTY RANGE
                            </span>
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        {program.scope_type === 'public' && !hasJoined ? (
                            <button
                                onClick={handleJoinProgram}
                                disabled={joining}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    background: '#2ecc71',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '1rem',
                                    opacity: joining ? 0.7 : 1
                                }}
                            >
                                {joining ? 'Joining...' : 'Join Program'}
                            </button>
                        ) : program.scope_type === 'private' && !hasJoined ? (
                            <button
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    background: '#95a5a6',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '1rem'
                                }}
                            >
                                Request Access
                            </button>
                        ) : null}

                        <button
                            onClick={handleSubmitReport}
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
                            Submit Report
                        </button>
                    </div>
                </div>
            </div>

            {/* Stats Bar */}
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
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#3498db' }}>{program.total_reports}</div>
                    <div style={{ color: '#666' }}>Total Reports</div>
                </div>
                <div style={{
                    background: 'white',
                    padding: '1.5rem',
                    borderRadius: '8px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                    textAlign: 'center'
                }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#9b59b6' }}>${program.total_payout?.toLocaleString()}</div>
                    <div style={{ color: '#666' }}>Total Paid</div>
                </div>
                <div style={{
                    background: 'white',
                    padding: '1.5rem',
                    borderRadius: '8px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                    textAlign: 'center'
                }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#e67e22' }}>{program.avg_severity_score}</div>
                    <div style={{ color: '#666' }}>Avg Severity</div>
                </div>
                <div style={{
                    background: 'white',
                    padding: '1.5rem',
                    borderRadius: '8px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                    textAlign: 'center'
                }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#2ecc71' }}>{program.scopes?.filter(s => s.is_in_scope).length || 0}</div>
                    <div style={{ color: '#666' }}>In-Scope Targets</div>
                </div>
            </div>

            {/* Tabs */}
            <div style={{ borderBottom: '1px solid #ddd', marginBottom: '2rem' }}>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                        onClick={() => setActiveTab('overview')}
                        style={{
                            padding: '0.75rem 1.5rem',
                            background: activeTab === 'overview' ? '#3498db' : 'transparent',
                            color: activeTab === 'overview' ? 'white' : '#666',
                            border: 'none',
                            borderBottom: activeTab === 'overview' ? '3px solid #3498db' : '3px solid transparent',
                            cursor: 'pointer',
                            fontSize: '1rem'
                        }}
                    >
                        Overview
                    </button>
                    <button
                        onClick={() => setActiveTab('scope')}
                        style={{
                            padding: '0.75rem 1.5rem',
                            background: activeTab === 'scope' ? '#3498db' : 'transparent',
                            color: activeTab === 'scope' ? 'white' : '#666',
                            border: 'none',
                            borderBottom: activeTab === 'scope' ? '3px solid #3498db' : '3px solid transparent',
                            cursor: 'pointer',
                            fontSize: '1rem'
                        }}
                    >
                        Scope
                    </button>
                    <button
                        onClick={() => setActiveTab('policy')}
                        style={{
                            padding: '0.75rem 1.5rem',
                            background: activeTab === 'policy' ? '#3498db' : 'transparent',
                            color: activeTab === 'policy' ? 'white' : '#666',
                            border: 'none',
                            borderBottom: activeTab === 'policy' ? '3px solid #3498db' : '3px solid transparent',
                            cursor: 'pointer',
                            fontSize: '1rem'
                        }}
                    >
                        Bounty Policy
                    </button>
                    <button
                        onClick={() => setActiveTab('guidelines')}
                        style={{
                            padding: '0.75rem 1.5rem',
                            background: activeTab === 'guidelines' ? '#3498db' : 'transparent',
                            color: activeTab === 'guidelines' ? 'white' : '#666',
                            border: 'none',
                            borderBottom: activeTab === 'guidelines' ? '3px solid #3498db' : '3px solid transparent',
                            cursor: 'pointer',
                            fontSize: '1rem'
                        }}
                    >
                        Guidelines
                    </button>
                </div>
            </div>

            {/* Tab Content */}
            <div style={{
                background: 'white',
                padding: '2rem',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                marginBottom: '2rem'
            }}>
                {activeTab === 'overview' && (
                    <div>
                        <h3 style={{ marginBottom: '1rem' }}>About This Program</h3>
                        <div style={{ whiteSpace: 'pre-line', lineHeight: '1.6', marginBottom: '2rem' }}>
                            {program.description}
                        </div>

                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(2, 1fr)',
                            gap: '2rem',
                            background: '#f8f9fa',
                            padding: '1.5rem',
                            borderRadius: '8px'
                        }}>
                            <div>
                                <h4 style={{ margin: '0 0 1rem 0' }}>Program Details</h4>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span style={{ color: '#666' }}>Company:</span>
                                        <span style={{ fontWeight: '500' }}>{program.company_name}</span>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span style={{ color: '#666' }}>Program Type:</span>
                                        <span style={{ fontWeight: '500', textTransform: 'capitalize' }}>{program.scope_type}</span>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span style={{ color: '#666' }}>Status:</span>
                                        <span style={{ fontWeight: '500', textTransform: 'capitalize' }}>{program.status}</span>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span style={{ color: '#666' }}>Created:</span>
                                        <span>{new Date(program.created_at).toLocaleDateString()}</span>
                                    </div>
                                </div>
                            </div>

                            <div>
                                <h4 style={{ margin: '0 0 1rem 0' }}>Key Statistics</h4>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span style={{ color: '#666' }}>Total Reports:</span>
                                        <span style={{ fontWeight: '500' }}>{program.total_reports}</span>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span style={{ color: '#666' }}>Total Payout:</span>
                                        <span style={{ fontWeight: '500', color: '#9b59b6' }}>${program.total_payout?.toLocaleString()}</span>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span style={{ color: '#666' }}>Avg Severity Score:</span>
                                        <span style={{ fontWeight: '500' }}>{program.avg_severity_score}</span>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span style={{ color: '#666' }}>In-Scope Targets:</span>
                                        <span style={{ fontWeight: '500' }}>{program.scopes?.filter(s => s.is_in_scope).length || 0}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'scope' && (
                    <div>
                        <h3 style={{ marginBottom: '1.5rem' }}>Program Scope</h3>

                        <div style={{ marginBottom: '2rem' }}>
                            <h4 style={{ color: '#27ae60', marginBottom: '1rem' }}>In-Scope Targets</h4>
                            {program.scopes?.filter(s => s.is_in_scope).length > 0 ? (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                    {program.scopes.filter(s => s.is_in_scope).map((scope) => (
                                        <div key={scope.id} style={{
                                            border: '1px solid #d4edda',
                                            background: '#f8fff8',
                                            borderRadius: '8px',
                                            padding: '1.5rem'
                                        }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                                                <div>
                                                    <strong style={{ fontSize: '1.1rem' }}>{scope.target}</strong>
                                                    <div style={{ marginTop: '0.25rem' }}>
                                                        <span style={{
                                                            padding: '0.25rem 0.5rem',
                                                            background: '#e3f2fd',
                                                            color: '#1565c0',
                                                            borderRadius: '4px',
                                                            fontSize: '0.85rem',
                                                            textTransform: 'capitalize'
                                                        }}>
                                                            {scope.target_type.replace('_', ' ')}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                            {scope.description && (
                                                <p style={{ margin: '0.5rem 0 0 0', color: '#666' }}>{scope.description}</p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p style={{ color: '#666', textAlign: 'center', padding: '2rem' }}>
                                    No in-scope targets defined.
                                </p>
                            )}
                        </div>

                        {program.scopes?.filter(s => !s.is_in_scope).length > 0 && (
                            <div>
                                <h4 style={{ color: '#e74c3c', marginBottom: '1rem' }}>Out-of-Scope Targets</h4>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                    {program.scopes.filter(s => !s.is_in_scope).map((scope) => (
                                        <div key={scope.id} style={{
                                            border: '1px solid #f8d7da',
                                            background: '#fff8f8',
                                            borderRadius: '8px',
                                            padding: '1.5rem'
                                        }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                                                <div>
                                                    <strong style={{ fontSize: '1.1rem' }}>{scope.target}</strong>
                                                    <div style={{ marginTop: '0.25rem' }}>
                                                        <span style={{
                                                            padding: '0.25rem 0.5rem',
                                                            background: '#f8d7da',
                                                            color: '#721c24',
                                                            borderRadius: '4px',
                                                            fontSize: '0.85rem',
                                                            textTransform: 'capitalize'
                                                        }}>
                                                            {scope.target_type.replace('_', ' ')}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                            {scope.description && (
                                                <p style={{ margin: '0.5rem 0 0 0', color: '#666' }}>{scope.description}</p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'policy' && (
                    <div>
                        <h3 style={{ marginBottom: '1rem' }}>Bounty Policy</h3>
                        <div style={{ whiteSpace: 'pre-line', lineHeight: '1.6', marginBottom: '2rem' }}>
                            {program.bounty_policy}
                        </div>

                        <div style={{
                            background: '#f8f9fa',
                            padding: '1.5rem',
                            borderRadius: '8px',
                            marginBottom: '2rem'
                        }}>
                            <h4 style={{ margin: '0 0 1rem 0' }}>Bounty Range</h4>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1.5rem' }}>
                                <div>
                                    <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '0.25rem' }}>
                                        Minimum Bounty
                                    </div>
                                    <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#27ae60' }}>
                                        ${program.min_bounty || 'Not specified'}
                                    </div>
                                </div>
                                <div>
                                    <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '0.25rem' }}>
                                        Maximum Bounty
                                    </div>
                                    <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#27ae60' }}>
                                        ${program.max_bounty || 'Not specified'}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div>
                            <h4 style={{ margin: '0 0 1rem 0' }}>Payment Terms</h4>
                            <ul style={{ margin: '0 0 0 1.5rem', padding: 0 }}>
                                <li style={{ marginBottom: '0.5rem' }}>Payments are processed within 30 days of report acceptance</li>
                                <li style={{ marginBottom: '0.5rem' }}>Payments are made via PayPal, wire transfer, or cryptocurrency</li>
                                <li style={{ marginBottom: '0.5rem' }}>Tax documentation may be required for bounties over $600</li>
                                <li>Only one bounty will be awarded per unique vulnerability</li>
                            </ul>
                        </div>
                    </div>
                )}

                {activeTab === 'guidelines' && (
                    <div>
                        <h3 style={{ marginBottom: '1.5rem' }}>Testing Guidelines</h3>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                            <div>
                                <h4 style={{ margin: '0 0 1rem 0' }}>Testing Rules</h4>
                                <ul style={{ margin: '0 0 0 1.5rem', padding: 0 }}>
                                    <li style={{ marginBottom: '0.5rem' }}>Only test systems explicitly listed as in-scope</li>
                                    <li style={{ marginBottom: '0.5rem' }}>Do not perform Denial of Service (DoS/DDoS) attacks</li>
                                    <li style={{ marginBottom: '0.5rem' }}>Do not access or modify other users' data</li>
                                    <li style={{ marginBottom: '0.5rem' }}>Report vulnerabilities as soon as they are discovered</li>
                                    <li>Social engineering attacks are strictly prohibited</li>
                                </ul>
                            </div>

                            <div>
                                <h4 style={{ margin: '0 0 1rem 0' }}>Report Requirements</h4>
                                <ul style={{ margin: '0 0 0 1.5rem', padding: 0 }}>
                                    <li style={{ marginBottom: '0.5rem' }}>Include detailed steps to reproduce the vulnerability</li>
                                    <li style={{ marginBottom: '0.5rem' }}>Provide proof of concept (screenshots, videos, or code)</li>
                                    <li style={{ marginBottom: '0.5rem' }}>Explain the potential impact of the vulnerability</li>
                                    <li>Suggest remediation steps if possible</li>
                                </ul>
                            </div>

                            <div>
                                <h4 style={{ margin: '0 0 1rem 0' }}>Disclosure Policy</h4>
                                <ul style={{ margin: '0 0 0 1.5rem', padding: 0 }}>
                                    <li style={{ marginBottom: '0.5rem' }}>Do not disclose vulnerabilities publicly until they are fixed</li>
                                    <li style={{ marginBottom: '0.5rem' }}>Allow 90 days for the company to fix the issue</li>
                                    <li>Coordinate disclosure with the program owner</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Call to Action */}
            <div style={{
                background: 'white',
                padding: '2rem',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                textAlign: 'center'
            }}>
                <h3 style={{ margin: '0 0 1rem 0' }}>Ready to Submit a Report?</h3>
                <p style={{ margin: '0 0 1.5rem 0', color: '#666' }}>
                    Found a security vulnerability? Submit your report now!
                </p>
                <button
                    onClick={handleSubmitReport}
                    style={{
                        padding: '0.75rem 1.5rem',
                        background: '#3498db',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '1rem',
                        fontWeight: '500'
                    }}
                >
                    Submit Report to {program.company_name}
                </button>
            </div>
        </div>
    );
};

export default ProgramDetailResearcher;