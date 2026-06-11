import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../../services/api';

const SCOPE_COLORS = {
    public: '#3498db',
    private: '#9b59b6',
    vdp: '#e67e22',
};

const ProgramDetailResearcher = () => {
    const { id } = useParams();
    const navigate = useNavigate();

    const [program, setProgram] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState('overview');
    const [joining, setJoining] = useState(false);
    const [joinMessage, setJoinMessage] = useState(null); // { type: 'success'|'error', text }

    // For application modal
    const [showApplicationForm, setShowApplicationForm] = useState(false);
    const [applicationData, setApplicationData] = useState({
        message: '', experience: '', qualifications: ''
    });
    const [submittingApplication, setSubmittingApplication] = useState(false);

    useEffect(() => {
        loadProgram();
    }, [id]);

    const loadProgram = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await api.get(`/programs/programs/${id}/`);
            setProgram(response.data);
        } catch (err) {
            if (err.response?.status === 404) {
                setError('not_found');
            } else if (err.response?.status === 403) {
                setError('forbidden');
            } else {
                setError('generic');
            }
        } finally {
            setLoading(false);
        }
    };

    const handleJoin = async () => {
        // For private programs that require an application, show the form
        if (program.requires_application && program.scope_type === 'private') {
            setShowApplicationForm(true);
            return;
        }

        setJoining(true);
        setJoinMessage(null);
        try {
            const response = await api.post(`/programs/programs/${id}/join/`);
            setJoinMessage({ type: 'success', text: response.data.message });
            loadProgram(); // refresh to update can_accept_submissions etc.
        } catch (err) {
            const msg = err.response?.data?.error || 'Failed to join program.';
            setJoinMessage({ type: 'error', text: msg });
        } finally {
            setJoining(false);
        }
    };

    const handleSubmitApplication = async () => {
        setSubmittingApplication(true);
        setJoinMessage(null);
        try {
            const response = await api.post(`/programs/programs/${id}/join/`, applicationData);
            setJoinMessage({ type: 'success', text: response.data.message });
            setShowApplicationForm(false);
            setApplicationData({ message: '', experience: '', qualifications: '' });
        } catch (err) {
            const msg = err.response?.data?.error || 'Failed to submit application.';
            setJoinMessage({ type: 'error', text: msg });
        } finally {
            setSubmittingApplication(false);
        }
    };

    const joinButtonProps = () => {
        if (!program) return null;
        const { scope_type, can_accept_submissions, invitation_only, requires_application } = program;

        if (!can_accept_submissions) return null;

        if (scope_type === 'public' || scope_type === 'vdp') {
            return {
                label: joining ? 'Joining...' : 'Join Program',
                color: scope_type === 'vdp' ? '#e67e22' : '#2ecc71',
                onClick: handleJoin,
                disabled: joining,
            };
        }

        if (scope_type === 'private') {
            if (invitation_only) {
                return {
                    label: 'Accept Invitation',
                    color: '#9b59b6',
                    onClick: handleJoin,
                    disabled: joining,
                };
            }
            if (requires_application) {
                return {
                    label: joining ? 'Submitting...' : 'Apply to Program',
                    color: '#9b59b6',
                    onClick: handleJoin,
                    disabled: joining,
                };
            }
            return {
                label: 'Request Access',
                color: '#95a5a6',
                onClick: handleJoin,
                disabled: joining,
            };
        }

        return null;
    };

    if (loading) {
        return (
            <div style={{ padding: '3rem', textAlign: 'center' }}>
                <div style={{
                    border: '4px solid #f3f3f3', borderTop: '4px solid #3498db',
                    borderRadius: '50%', width: '40px', height: '40px',
                    animation: 'spin 1s linear infinite', margin: '0 auto 1rem'
                }} />
                <p style={{ color: '#666' }}>Loading program details...</p>
                <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </div>
        );
    }

    if (error) {
        const messages = {
            not_found: { title: 'Program not found', body: "This program doesn't exist or you don't have access." },
            forbidden: { title: 'Access denied', body: "You don't have permission to view this program." },
            generic: { title: 'Something went wrong', body: 'Failed to load program. Please try again.' },
        };
        const { title, body } = messages[error] || messages.generic;
        return (
            <div style={{ padding: '3rem', textAlign: 'center' }}>
                <h2>{title}</h2>
                <p style={{ color: '#666', marginBottom: '1.5rem' }}>{body}</p>
                <Link
                    to="/programs"
                    style={{
                        padding: '0.75rem 1.5rem', background: '#3498db',
                        color: 'white', textDecoration: 'none', borderRadius: '4px'
                    }}
                >
                    Browse Programs
                </Link>
            </div>
        );
    }

    const scopeColor = SCOPE_COLORS[program.scope_type] || '#7f8c8d';
    const joinBtn = joinButtonProps();
    const tabs = ['overview', 'scope', 'policy', 'guidelines'];

    return (
        <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>

            {/* Join message banner */}
            {joinMessage && (
                <div style={{
                    padding: '1rem 1.5rem', borderRadius: '8px', marginBottom: '1.5rem',
                    background: joinMessage.type === 'success' ? '#d4edda' : '#f8d7da',
                    color: joinMessage.type === 'success' ? '#155724' : '#721c24',
                    border: `1px solid ${joinMessage.type === 'success' ? '#c3e6cb' : '#f5c6cb'}`,
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                }}>
                    <span>{joinMessage.text}</span>
                    <button
                        onClick={() => setJoinMessage(null)}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.1rem' }}
                    >
                        ×
                    </button>
                </div>
            )}

            {/* Application modal */}
            {showApplicationForm && (
                <div style={{
                    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    zIndex: 1000
                }}>
                    <div style={{
                        background: 'white', borderRadius: '8px', padding: '2rem',
                        maxWidth: '600px', width: '90%', maxHeight: '80vh', overflowY: 'auto'
                    }}>
                        <h3 style={{ margin: '0 0 1.5rem 0' }}>Apply to {program.name}</h3>

                        <div style={{ marginBottom: '1.25rem' }}>
                            <label style={{ display: 'block', fontWeight: '500', marginBottom: '0.5rem' }}>
                                Why do you want to join?
                            </label>
                            <textarea
                                value={applicationData.message}
                                onChange={e => setApplicationData(d => ({ ...d, message: e.target.value }))}
                                rows={3}
                                placeholder="Tell the company why you're interested..."
                                style={{
                                    width: '100%', padding: '0.75rem', border: '1px solid #ddd',
                                    borderRadius: '4px', fontSize: '1rem', fontFamily: 'inherit'
                                }}
                            />
                        </div>

                        <div style={{ marginBottom: '1.25rem' }}>
                            <label style={{ display: 'block', fontWeight: '500', marginBottom: '0.5rem' }}>
                                Relevant experience
                            </label>
                            <textarea
                                value={applicationData.experience}
                                onChange={e => setApplicationData(d => ({ ...d, experience: e.target.value }))}
                                rows={3}
                                placeholder="Describe your security research experience..."
                                style={{
                                    width: '100%', padding: '0.75rem', border: '1px solid #ddd',
                                    borderRadius: '4px', fontSize: '1rem', fontFamily: 'inherit'
                                }}
                            />
                        </div>

                        <div style={{ marginBottom: '1.5rem' }}>
                            <label style={{ display: 'block', fontWeight: '500', marginBottom: '0.5rem' }}>
                                Qualifications / certifications
                            </label>
                            <textarea
                                value={applicationData.qualifications}
                                onChange={e => setApplicationData(d => ({ ...d, qualifications: e.target.value }))}
                                rows={2}
                                placeholder="OSCP, CVEs, HackerOne profile, etc."
                                style={{
                                    width: '100%', padding: '0.75rem', border: '1px solid #ddd',
                                    borderRadius: '4px', fontSize: '1rem', fontFamily: 'inherit'
                                }}
                            />
                        </div>

                        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                            <button
                                onClick={() => setShowApplicationForm(false)}
                                style={{
                                    padding: '0.75rem 1.5rem', background: '#95a5a6',
                                    color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer'
                                }}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSubmitApplication}
                                disabled={submittingApplication}
                                style={{
                                    padding: '0.75rem 1.5rem', background: '#9b59b6',
                                    color: 'white', border: 'none', borderRadius: '4px',
                                    cursor: submittingApplication ? 'not-allowed' : 'pointer',
                                    opacity: submittingApplication ? 0.7 : 1
                                }}
                            >
                                {submittingApplication ? 'Submitting...' : 'Submit Application'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Header */}
            <div style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                    <div>
                        <h1 style={{ margin: '0 0 0.75rem 0' }}>{program.name}</h1>
                        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                            <span style={{
                                padding: '0.4rem 1rem', borderRadius: '20px', fontSize: '0.85rem',
                                fontWeight: '600', background: scopeColor + '20', color: scopeColor
                            }}>
                                {program.scope_type_display || program.scope_type.toUpperCase()}
                            </span>
                            <span style={{
                                padding: '0.4rem 1rem', borderRadius: '20px', fontSize: '0.85rem',
                                fontWeight: '600', background: '#2ecc7120', color: '#2ecc71'
                            }}>
                                {program.status_display || program.status.toUpperCase()}
                            </span>
                            {program.bounty_range && program.bounty_range !== 'Not specified' && (
                                <span style={{
                                    padding: '0.4rem 1rem', borderRadius: '20px', fontSize: '0.85rem',
                                    fontWeight: '600', background: '#27ae6020', color: '#27ae60'
                                }}>
                                    {program.bounty_range}
                                </span>
                            )}
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                        {joinBtn && (
                            <button
                                onClick={joinBtn.onClick}
                                disabled={joinBtn.disabled}
                                style={{
                                    padding: '0.75rem 1.5rem', background: joinBtn.color,
                                    color: 'white', border: 'none', borderRadius: '4px',
                                    cursor: joinBtn.disabled ? 'not-allowed' : 'pointer',
                                    fontSize: '1rem', fontWeight: '500',
                                    opacity: joinBtn.disabled ? 0.7 : 1
                                }}
                            >
                                {joinBtn.label}
                            </button>
                        )}
                        {program.can_accept_submissions && (
                            <button
                                onClick={() => navigate(`/submit?program=${id}`)}
                                style={{
                                    padding: '0.75rem 1.5rem', background: '#3498db',
                                    color: 'white', border: 'none', borderRadius: '4px',
                                    cursor: 'pointer', fontSize: '1rem', fontWeight: '500'
                                }}
                            >
                                Submit Report
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Stats bar */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                gap: '1rem', marginBottom: '2rem'
            }}>
                {[
                    { label: 'Total Reports', value: program.total_reports ?? 0, color: '#3498db' },
                    { label: 'Total Bounties', value: `$${parseFloat(program.total_bounties || 0).toLocaleString()}`, color: '#9b59b6' },
                    { label: 'Avg Severity', value: program.avg_severity_score?.toFixed(1) ?? '—', color: '#e67e22' },
                    { label: 'In-Scope Targets', value: program.in_scope_count ?? program.scopes?.filter(s => s.is_in_scope).length ?? 0, color: '#2ecc71' },
                ].map(({ label, value, color }) => (
                    <div key={label} style={{
                        background: 'white', padding: '1.5rem', borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)', textAlign: 'center'
                    }}>
                        <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color }}>{value}</div>
                        <div style={{ color: '#666', fontSize: '0.85rem' }}>{label}</div>
                    </div>
                ))}
            </div>

            {/* Tabs */}
            <div style={{ borderBottom: '2px solid #e9ecef', marginBottom: '2rem' }}>
                <div style={{ display: 'flex', gap: '0' }}>
                    {tabs.map(tab => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            style={{
                                padding: '0.75rem 1.5rem',
                                background: 'transparent',
                                color: activeTab === tab ? '#3498db' : '#666',
                                border: 'none',
                                borderBottom: `3px solid ${activeTab === tab ? '#3498db' : 'transparent'}`,
                                cursor: 'pointer',
                                fontSize: '0.95rem',
                                fontWeight: activeTab === tab ? '600' : '400',
                                textTransform: 'capitalize',
                                transition: 'all 0.15s',
                            }}
                        >
                            {tab === 'policy' ? 'Bounty Policy' : tab.charAt(0).toUpperCase() + tab.slice(1)}
                        </button>
                    ))}
                </div>
            </div>

            {/* Tab content */}
            <div style={{
                background: 'white', padding: '2rem', borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)', marginBottom: '2rem'
            }}>
                {activeTab === 'overview' && (
                    <div>
                        <h3 style={{ marginTop: 0 }}>About This Program</h3>
                        <div style={{ whiteSpace: 'pre-line', lineHeight: '1.7', marginBottom: '2rem', color: '#444' }}>
                            {program.description}
                        </div>
                        <div style={{
                            display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                            gap: '2rem', background: '#f8f9fa', padding: '1.5rem', borderRadius: '8px'
                        }}>
                            <div>
                                <h4 style={{ margin: '0 0 1rem 0', color: '#2c3e50' }}>Program Details</h4>
                                {[
                                    ['Company', program.company?.username],
                                    ['Type', program.scope_type_display || program.scope_type],
                                    ['Status', program.status_display || program.status],
                                    ['Published', program.published_at ? new Date(program.published_at).toLocaleDateString() : '—'],
                                    ['Ends', program.end_date || 'No end date'],
                                ].map(([k, v]) => (
                                    <div key={k} style={{
                                        display: 'flex', justifyContent: 'space-between',
                                        padding: '0.4rem 0', borderBottom: '1px solid #e9ecef'
                                    }}>
                                        <span style={{ color: '#666' }}>{k}</span>
                                        <span style={{ fontWeight: '500', color: '#2c3e50' }}>{v || '—'}</span>
                                    </div>
                                ))}
                            </div>
                            <div>
                                <h4 style={{ margin: '0 0 1rem 0', color: '#2c3e50' }}>Program Flags</h4>
                                {[
                                    ['Anonymous submissions', program.allow_anonymous],
                                    ['NDA required', program.require_ndas],
                                    ['Invitation only', program.invitation_only],
                                    ['Application required', program.requires_application],
                                ].map(([k, v]) => (
                                    <div key={k} style={{
                                        display: 'flex', justifyContent: 'space-between',
                                        padding: '0.4rem 0', borderBottom: '1px solid #e9ecef'
                                    }}>
                                        <span style={{ color: '#666' }}>{k}</span>
                                        <span style={{
                                            fontWeight: '600',
                                            color: v ? '#27ae60' : '#95a5a6'
                                        }}>
                                            {v ? 'Yes' : 'No'}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'scope' && (
                    <div>
                        <h3 style={{ marginTop: 0 }}>Program Scope</h3>

                        {[true, false].map(inScope => {
                            const items = program.scopes?.filter(s => s.is_in_scope === inScope) || [];
                            if (items.length === 0 && inScope) return (
                                <p key="empty" style={{ color: '#666' }}>No in-scope targets defined.</p>
                            );
                            if (items.length === 0) return null;
                            return (
                                <div key={String(inScope)} style={{ marginBottom: '2rem' }}>
                                    <h4 style={{ color: inScope ? '#27ae60' : '#e74c3c', marginBottom: '1rem' }}>
                                        {inScope ? 'In-Scope Targets' : 'Out-of-Scope Targets'}
                                    </h4>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                        {items.map(scope => (
                                            <div key={scope.id} style={{
                                                border: `1px solid ${inScope ? '#d4edda' : '#f8d7da'}`,
                                                background: inScope ? '#f8fff8' : '#fff8f8',
                                                borderRadius: '8px', padding: '1.25rem'
                                            }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: scope.description ? '0.5rem' : 0 }}>
                                                    <strong>{scope.target}</strong>
                                                    <span style={{
                                                        padding: '0.2rem 0.6rem', borderRadius: '4px',
                                                        fontSize: '0.8rem',
                                                        background: inScope ? '#e3f2fd' : '#f8d7da',
                                                        color: inScope ? '#1565c0' : '#721c24',
                                                    }}>
                                                        {scope.target_type_display || scope.target_type.replace(/_/g, ' ')}
                                                    </span>
                                                </div>
                                                {scope.description && (
                                                    <p style={{ margin: 0, color: '#666', fontSize: '0.9rem' }}>
                                                        {scope.description}
                                                    </p>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}

                {activeTab === 'policy' && (
                    <div>
                        <h3 style={{ marginTop: 0 }}>Bounty Policy</h3>
                        {program.bounty_policy ? (
                            <div style={{ whiteSpace: 'pre-line', lineHeight: '1.7', marginBottom: '2rem', color: '#444' }}>
                                {program.bounty_policy}
                            </div>
                        ) : (
                            <p style={{ color: '#666' }}>No bounty policy specified.</p>
                        )}
                        <div style={{
                            background: '#f8f9fa', padding: '1.5rem',
                            borderRadius: '8px', marginBottom: '1.5rem'
                        }}>
                            <h4 style={{ margin: '0 0 1rem 0' }}>Bounty Range</h4>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1.5rem' }}>
                                {[
                                    ['Minimum', program.min_bounty ? `$${program.min_bounty}` : 'Not specified'],
                                    ['Maximum', program.max_bounty ? `$${program.max_bounty}` : 'Not specified'],
                                ].map(([k, v]) => (
                                    <div key={k}>
                                        <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '0.25rem' }}>{k} Bounty</div>
                                        <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#27ae60' }}>{v}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'guidelines' && (
                    <div>
                        <h3 style={{ marginTop: 0 }}>Testing Guidelines</h3>
                        {program.testing_guidelines ? (
                            <div style={{ whiteSpace: 'pre-line', lineHeight: '1.7', marginBottom: '2rem', color: '#444' }}>
                                {program.testing_guidelines}
                            </div>
                        ) : (
                            <p style={{ color: '#666' }}>No testing guidelines provided.</p>
                        )}

                        {program.report_guidelines && (
                            <>
                                <h4>Report Guidelines</h4>
                                <div style={{ whiteSpace: 'pre-line', lineHeight: '1.7', marginBottom: '2rem', color: '#444' }}>
                                    {program.report_guidelines}
                                </div>
                            </>
                        )}

                        {program.disclosure_policy && (
                            <>
                                <h4>Disclosure Policy</h4>
                                <div style={{ whiteSpace: 'pre-line', lineHeight: '1.7', color: '#444' }}>
                                    {program.disclosure_policy}
                                </div>
                            </>
                        )}
                    </div>
                )}
            </div>

            {/* CTA */}
            {program.can_accept_submissions && (
                <div style={{
                    background: 'white', padding: '2rem', borderRadius: '8px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.1)', textAlign: 'center'
                }}>
                    <h3 style={{ margin: '0 0 0.5rem 0' }}>Ready to submit a report?</h3>
                    <p style={{ margin: '0 0 1.5rem 0', color: '#666' }}>
                        Found a security vulnerability? Submit your findings now.
                    </p>
                    <button
                        onClick={() => navigate(`/submit?program=${id}`)}
                        style={{
                            padding: '0.75rem 2rem', background: '#3498db',
                            color: 'white', border: 'none', borderRadius: '4px',
                            cursor: 'pointer', fontSize: '1rem', fontWeight: '500'
                        }}
                    >
                        Submit Report to {program.company?.username}
                    </button>
                </div>
            )}
        </div>
    );
};

export default ProgramDetailResearcher;