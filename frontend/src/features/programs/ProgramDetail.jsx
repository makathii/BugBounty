import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../../services/api';
import { statusTone, scopeTone } from '../../utils/tones';


const TextBlock = ({ children }) => <div className="ui-pre" style={{ marginBottom: '1.5rem' }}>{children}</div>;

const ProgramDetail = () => {
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
                cls: scope_type === 'vdp' ? 'ui-btn--warn' : 'ui-btn--green',
                onClick: handleJoin,
                disabled: joining,
            };
        }

        if (scope_type === 'private') {
            if (invitation_only) {
                return {
                    label: 'Accept Invitation',
                    cls: '',
                    onClick: handleJoin,
                    disabled: joining,
                };
            }
            if (requires_application) {
                return {
                    label: joining ? 'Submitting...' : 'Apply to Program',
                    cls: '',
                    onClick: handleJoin,
                    disabled: joining,
                };
            }
            return {
                label: 'Request Access',
                cls: 'ui-btn--ghost',
                onClick: handleJoin,
                disabled: joining,
            };
        }

        return null;
    };

    if (loading) {
        return (
            <div className="ui-loading">
                <div className="ui-spinner" />
                <p>Loading program details...</p>
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
            <div className="ui-page ui-page--narrow">
                <div className="ui-card ui-empty">
                    <h2 className="ui-title">{title}</h2>
                    <p>{body}</p>
                    <Link to="/programs" className="ui-btn">Browse Programs</Link>
                </div>
            </div>
        );
    }

    const joinBtn = joinButtonProps();
    const tabs = ['overview', 'scope', 'policy', 'guidelines'];
    const statCards = [
        { label: 'Total Reports', value: program.total_reports ?? 0, tone: 'accent' },
        { label: 'Total Bounties', value: `$${parseFloat(program.total_bounties || 0).toLocaleString()}`, tone: 'blue' },
        { label: 'Avg Severity', value: program.avg_severity_score?.toFixed(1) ?? '—', tone: 'orange' },
        { label: 'In-Scope Targets', value: program.in_scope_count ?? program.scopes?.filter(s => s.is_in_scope).length ?? 0, tone: 'green' },
    ];

    return (
        <div className="ui-page">
            {joinMessage && (
                <div className={`ui-alert ui-row ui-row--between ${joinMessage.type === 'success' ? 'tone-green' : 'tone-red'}`}>
                    <span>{joinMessage.text}</span>
                    <button className="ui-btn ui-btn--ghost ui-btn--sm" onClick={() => setJoinMessage(null)} aria-label="Dismiss">×</button>
                </div>
            )}

            {showApplicationForm && (
                <div className="ui-overlay">
                    <div className="ui-modal" style={{ maxWidth: '600px' }}>
                        <h3 className="ui-section-title">Apply to {program.name}</h3>

                        <div className="ui-field">
                            <label className="ui-label">Why do you want to join?</label>
                            <textarea
                                className="ui-textarea"
                                value={applicationData.message}
                                onChange={e => setApplicationData(d => ({ ...d, message: e.target.value }))}
                                rows={3}
                                placeholder="Tell the company why you're interested..."
                            />
                        </div>
                        <div className="ui-field">
                            <label className="ui-label">Relevant experience</label>
                            <textarea
                                className="ui-textarea"
                                value={applicationData.experience}
                                onChange={e => setApplicationData(d => ({ ...d, experience: e.target.value }))}
                                rows={3}
                                placeholder="Describe your security research experience..."
                            />
                        </div>
                        <div className="ui-field">
                            <label className="ui-label">Qualifications / certifications</label>
                            <textarea
                                className="ui-textarea"
                                value={applicationData.qualifications}
                                onChange={e => setApplicationData(d => ({ ...d, qualifications: e.target.value }))}
                                rows={2}
                                placeholder="OSCP, CVEs, HackerOne profile, etc."
                            />
                        </div>

                        <div className="ui-row" style={{ justifyContent: 'flex-end' }}>
                            <button className="ui-btn ui-btn--ghost" onClick={() => setShowApplicationForm(false)}>Cancel</button>
                            <button className="ui-btn" onClick={handleSubmitApplication} disabled={submittingApplication}>
                                {submittingApplication ? 'Submitting...' : 'Submit Application'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <header className="ui-page-header ui-page-header--row">
                <div>
                    <h1 className="ui-title">{program.name}</h1>
                    <div className="ui-row">
                        <span className={`ui-badge ${scopeTone(program.scope_type)}`}>
                            {program.scope_type_display || program.scope_type}
                        </span>
                        <span className={`ui-badge ${statusTone(program.status)}`}>
                            {program.status_display || program.status}
                        </span>
                        {program.bounty_range && program.bounty_range !== 'Not specified' && (
                            <span className="ui-badge ui-badge--plain tone-green">{program.bounty_range}</span>
                        )}
                    </div>
                </div>

                <div className="ui-row">
                    {joinBtn && (
                        <button className={`ui-btn ${joinBtn.cls}`} onClick={joinBtn.onClick} disabled={joinBtn.disabled}>
                            {joinBtn.label}
                        </button>
                    )}
                    {program.can_accept_submissions && (
                        <button className="ui-btn" onClick={() => navigate(`/submit?program=${id}`)}>Submit Report</button>
                    )}
                </div>
            </header>

            <div className="ui-grid ui-grid--stats">
                {statCards.map(({ label, value, tone }) => (
                    <div key={label} className={`ui-stat tone-${tone}`}>
                        <div className="ui-stat-value">{value}</div>
                        <div className="ui-stat-label">{label}</div>
                    </div>
                ))}
            </div>

            <div className="ui-tabs">
                {tabs.map(tab => (
                    <button
                        key={tab}
                        className={`ui-tab${activeTab === tab ? ' is-active' : ''}`}
                        onClick={() => setActiveTab(tab)}
                    >
                        {tab === 'policy' ? 'Bounty Policy' : tab.charAt(0).toUpperCase() + tab.slice(1)}
                    </button>
                ))}
            </div>

            <div className="ui-card ui-mb-lg">
                {activeTab === 'overview' && (
                    <div>
                        <h3 className="ui-section-title">About This Program</h3>
                        <TextBlock>{program.description}</TextBlock>
                        <div className="ui-card--inset ui-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '2rem', padding: '1.5rem' }}>
                            <div>
                                <h4 className="ui-eyebrow">Program Details</h4>
                                {[
                                    ['Company', program.company?.username],
                                    ['Type', program.scope_type_display || program.scope_type],
                                    ['Status', program.status_display || program.status],
                                    ['Published', program.published_at ? new Date(program.published_at).toLocaleDateString() : '—'],
                                    ['Ends', program.end_date || 'No end date'],
                                ].map(([k, v]) => (
                                    <div key={k} className="ui-row ui-row--between ui-detail-row">
                                        <span className="ui-muted">{k}</span>
                                        <span className="ui-strong">{v || '—'}</span>
                                    </div>
                                ))}
                            </div>
                            <div>
                                <h4 className="ui-eyebrow">Program Flags</h4>
                                {[
                                    ['Anonymous submissions', program.allow_anonymous],
                                    ['NDA required', program.require_ndas],
                                    ['Invitation only', program.invitation_only],
                                    ['Application required', program.requires_application],
                                ].map(([k, v]) => (
                                    <div key={k} className="ui-row ui-row--between ui-detail-row">
                                        <span className="ui-muted">{k}</span>
                                        <span className={`ui-strong ui-tone-text ${v ? 'tone-green' : 'tone-gray'}`}>{v ? 'Yes' : 'No'}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'scope' && (
                    <div>
                        <h3 className="ui-section-title">Program Scope</h3>

                        {[true, false].map(inScope => {
                            const items = program.scopes?.filter(s => s.is_in_scope === inScope) || [];
                            if (items.length === 0 && inScope) return (
                                <p key="empty" className="ui-muted">No in-scope targets defined.</p>
                            );
                            if (items.length === 0) return null;
                            return (
                                <div key={String(inScope)} className={inScope ? 'tone-green' : 'tone-red'} style={{ marginBottom: '2rem' }}>
                                    <h4 className="ui-tone-text" style={{ marginBottom: '1rem' }}>
                                        {inScope ? 'In-Scope Targets' : 'Out-of-Scope Targets'}
                                    </h4>
                                    <div className="ui-stack">
                                        {items.map(scope => (
                                            <div key={scope.id} className="ui-scope-item">
                                                <div className="ui-row" style={{ marginBottom: scope.description ? '0.5rem' : 0 }}>
                                                    <strong className="ui-strong">{scope.target}</strong>
                                                    <span className="ui-badge ui-badge--plain">
                                                        {scope.target_type_display || scope.target_type.replace(/_/g, ' ')}
                                                    </span>
                                                </div>
                                                {scope.description && (
                                                    <p className="ui-muted ui-small" style={{ margin: 0 }}>{scope.description}</p>
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
                        <h3 className="ui-section-title">Bounty Policy</h3>
                        {program.bounty_policy ? (
                            <TextBlock>{program.bounty_policy}</TextBlock>
                        ) : (
                            <p className="ui-muted">No bounty policy specified.</p>
                        )}
                        <div className="ui-card--inset" style={{ padding: '1.5rem' }}>
                            <h4 className="ui-eyebrow">Bounty Range</h4>
                            <div className="ui-grid ui-grid--2">
                                {[
                                    ['Minimum', program.min_bounty ? `$${program.min_bounty}` : 'Not specified'],
                                    ['Maximum', program.max_bounty ? `$${program.max_bounty}` : 'Not specified'],
                                ].map(([k, v]) => (
                                    <div key={k}>
                                        <div className="ui-kv-label">{k} Bounty</div>
                                        <div className="ui-stat-value tone-green" style={{ fontSize: '1.5rem' }}>{v}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'guidelines' && (
                    <div>
                        <h3 className="ui-section-title">Testing Guidelines</h3>
                        {program.testing_guidelines ? (
                            <TextBlock>{program.testing_guidelines}</TextBlock>
                        ) : (
                            <p className="ui-muted">No testing guidelines provided.</p>
                        )}

                        {program.report_guidelines && (
                            <>
                                <h4 className="ui-section-title">Report Guidelines</h4>
                                <TextBlock>{program.report_guidelines}</TextBlock>
                            </>
                        )}

                        {program.disclosure_policy && (
                            <>
                                <h4 className="ui-section-title">Disclosure Policy</h4>
                                <TextBlock>{program.disclosure_policy}</TextBlock>
                            </>
                        )}
                    </div>
                )}
            </div>

            {program.can_accept_submissions && (
                <div className="ui-card ui-card--center">
                    <h3 className="ui-section-title">Ready to submit a report?</h3>
                    <p className="ui-muted" style={{ margin: '0 0 1.5rem' }}>
                        Found a security vulnerability? Submit your findings now.
                    </p>
                    <button className="ui-btn ui-btn--lg" onClick={() => navigate(`/submit?program=${id}`)}>
                        Submit Report to {program.company?.username}
                    </button>
                </div>
            )}
        </div>
    );
};

export default ProgramDetail;
