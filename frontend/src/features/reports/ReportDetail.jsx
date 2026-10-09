import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { reportAPI } from '../../services/api';
import { useAuth } from '../auth/AuthContext';
import { statusTone, severityTone } from '../../utils/tones';
import { formatPoints } from '../../utils/points';
import CommentThread from './CommentThread';

const ReportDetail = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const { isTriager, isAdmin, isCompany } = useAuth();

    const [report, setReport] = useState(null);
    const [activityLogs, setActivityLogs] = useState([]);
    const [loading, setLoading] = useState(true);

    // For triager/admin actions
    const [showAcceptModal, setShowAcceptModal] = useState(false);
    const [showRejectModal, setShowRejectModal] = useState(false);
    const [verificationNotes, setVerificationNotes] = useState('');
    const [bonusPoints, setBonusPoints] = useState('');
    const [acceptError, setAcceptError] = useState('');

    useEffect(() => {
        loadReport();
        loadActivityLogs();
    }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

    const loadReport = async () => {
        try {
            const response = await reportAPI.getReport(id);
            setReport(response.data);
        } catch (error) {
            console.error('Failed to load report:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadActivityLogs = async () => {
        try {
            const response = await reportAPI.getActivityLogs(id);
            setActivityLogs(response.data);
        } catch (error) {
            console.error('Failed to load activity logs:', error);
        }
    };

    const handleAcceptReport = async () => {
        try {
            await reportAPI.acceptReport(id, {
                verification_notes: verificationNotes,
                bonus_points: bonusPoints || 0
            });
            setShowAcceptModal(false);
            setVerificationNotes('');
            setBonusPoints('');
            setAcceptError('');
            loadReport(); // Refresh report
            loadActivityLogs();
        } catch (error) {
            console.error('Failed to accept report:', error);
            setAcceptError(error.response?.data?.error || 'Could not accept the report.');
        }
    };

    const handleRejectReport = async () => {
        try {
            await reportAPI.rejectReport(id, {
                rejection_reason: verificationNotes
            });
            setShowRejectModal(false);
            setVerificationNotes('');
            loadReport(); // Refresh report
        } catch (error) {
            console.error('Failed to reject report:', error);
        }
    };

    const handleAssignToMe = async () => {
        try {
            await reportAPI.assignToMe(id);
            loadReport(); // Refresh report
        } catch (error) {
            console.error('Failed to assign report:', error);
        }
    };

    if (loading) {
        return (
            <div className="ui-loading">
                <div className="ui-spinner" />
                <p>Loading report...</p>
            </div>
        );
    }

    if (!report) {
        return (
            <div className="ui-page ui-page--narrow">
                <div className="ui-card ui-empty">
                    <h2 className="ui-title">Report not found</h2>
                    <p>The report you're looking for doesn't exist or you don't have access.</p>
                    <button className="ui-btn" onClick={() => navigate('/reports')}>Back to Reports</button>
                </div>
            </div>
        );
    }

    const canTriage = isTriager() || isAdmin();

    return (
        <div className="ui-page">
            <header className="ui-page-header ui-page-header--row">
                <div>
                    <h1 className="ui-title">{report.title}</h1>
                    <div className="ui-row">
                        <span className={`ui-badge ${statusTone(report.status)}`}>{report.status}</span>
                        <span className={`ui-badge ${severityTone(report.severity)}`}>{report.severity} severity</span>
                        {report.points_awarded > 0 && (
                            <span className="ui-badge tone-green">+{formatPoints(report.points_awarded)}</span>
                        )}
                    </div>
                </div>

                <div className="ui-row">
                    <button className="ui-btn ui-btn--ghost" onClick={() => navigate('/reports')}>Back</button>

                    {canTriage && report.status === 'triaged' && (
                        <>
                            <button className="ui-btn ui-btn--green" onClick={() => setShowAcceptModal(true)}>Accept</button>
                            <button className="ui-btn ui-btn--danger" onClick={() => setShowRejectModal(true)}>Reject</button>
                        </>
                    )}

                    {canTriage && !report.assigned_to && (
                        <button className="ui-btn" onClick={handleAssignToMe}>Assign to Me</button>
                    )}
                </div>
            </header>

            <div className="ui-grid ui-grid--sidebar">
                <div className="ui-stack" style={{ gap: '1.5rem' }}>
                    <div className="ui-card">
                        <h3 className="ui-section-title">Report Details</h3>
                        <p className="ui-pre" style={{ marginBottom: '1.5rem' }}>{report.description}</p>

                        <div className="ui-card--inset ui-kv" style={{ padding: '1.25rem' }}>
                            <div>
                                <div className="ui-kv-label">Reporter</div>
                                <div className="ui-kv-value">{report.reporter_username || report.reporter}</div>
                            </div>
                            <div>
                                <div className="ui-kv-label">Created</div>
                                <div className="ui-kv-value">{new Date(report.created_at).toLocaleString()}</div>
                            </div>
                            <div>
                                <div className="ui-kv-label">Last Updated</div>
                                <div className="ui-kv-value">{new Date(report.updated_at).toLocaleString()}</div>
                            </div>
                            <div>
                                <div className="ui-kv-label">Assigned To</div>
                                <div className="ui-kv-value">
                                    {report.assigned_to_username || (report.assigned_to ? `User ${report.assigned_to}` : 'Unassigned')}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="ui-card">
                        <h3 className="ui-section-title">Comments</h3>

                        <CommentThread reportId={id} canModerate={canTriage} onChange={loadActivityLogs} />
                    </div>
                </div>

                <div className="ui-stack" style={{ gap: '1.5rem' }}>
                    <div className="ui-card">
                        <h3 className="ui-section-title">Activity Log</h3>

                        {activityLogs.length > 0 ? (
                            <div className="ui-stack">
                                {activityLogs.map((log) => (
                                    <div key={log.id} className="ui-card--inset tone-accent"
                                         style={{ borderLeft: '3px solid rgb(var(--tone-rgb))' }}>
                                        <div className="ui-row ui-row--between" style={{ marginBottom: '0.2rem' }}>
                                            <strong className="ui-strong">{log.user_name}</strong>
                                            <span className="ui-muted ui-small">
                                                {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                            </span>
                                        </div>
                                        <div className="ui-muted ui-small">{log.action_display}</div>
                                        {log.details && Object.keys(log.details).length > 0 && (
                                            <div className="ui-muted ui-small" style={{ marginTop: '0.25rem' }}>
                                                {log.details.message ? (
                                                    <div>{log.details.message}</div>
                                                ) : (
                                                    Object.entries(log.details)
                                                        .filter(([, value]) => typeof value !== 'boolean' && value !== null)
                                                        .map(([key, value]) => (
                                                            <div key={key}>{key}: {String(value)}</div>
                                                        ))
                                                )}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="ui-muted" style={{ textAlign: 'center', margin: 0 }}>No activity recorded yet.</p>
                        )}
                    </div>

                    {(canTriage || isCompany()) && (
                        <div className="ui-card">
                            <h3 className="ui-section-title">Quick Actions</h3>
                            <div className="ui-stack">
                                {canTriage ? (
                                    <>
                                        {report.status === 'triaged' && (
                                            <>
                                                <button className="ui-btn ui-btn--green ui-btn--block" onClick={() => setShowAcceptModal(true)}>
                                                    Accept Report
                                                </button>
                                                <button className="ui-btn ui-btn--danger ui-btn--block" onClick={() => setShowRejectModal(true)}>
                                                    Reject Report
                                                </button>
                                            </>
                                        )}
                                        {!report.assigned_to && (
                                            <button className="ui-btn ui-btn--block" onClick={handleAssignToMe}>Assign to Me</button>
                                        )}
                                    </>
                                ) : isCompany() && (
                                    <button className="ui-btn ui-btn--ghost ui-btn--block" onClick={() => alert('Company-specific action here')}>
                                        View Program Details
                                    </button>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {showAcceptModal && (
                <div className="ui-overlay">
                    <div className="ui-modal">
                        <h3 className="ui-section-title">Accept Report</h3>
                        <div className="ui-field">
                            <label className="ui-label">Bonus Points (optional)</label>
                            <input
                                type="number"
                                min="0"
                                max="1000"
                                step="1"
                                className="ui-input ui-input--block"
                                value={bonusPoints}
                                onChange={(e) => setBonusPoints(e.target.value)}
                                placeholder="0"
                            />
                            <div className="ui-muted ui-small" style={{ marginTop: '0.35rem' }}>
                                Added on top of the points for the report's severity. Max 1,000.
                            </div>
                        </div>
                        <div className="ui-field">
                            <label className="ui-label">Verification Notes</label>
                            <textarea
                                className="ui-textarea"
                                value={verificationNotes}
                                onChange={(e) => setVerificationNotes(e.target.value)}
                                rows="4"
                                placeholder="Add verification notes..."
                            />
                        </div>
                        {acceptError && <div className="ui-muted ui-small" style={{ color: '#f87171', marginBottom: '0.75rem' }}>{acceptError}</div>}
                        <div className="ui-row" style={{ justifyContent: 'flex-end' }}>
                            <button
                                className="ui-btn ui-btn--ghost"
                                onClick={() => {
                                    setShowAcceptModal(false);
                                    setVerificationNotes('');
                                    setBonusPoints('');
                                    setAcceptError('');
                                }}
                            >
                                Cancel
                            </button>
                            <button className="ui-btn ui-btn--green" onClick={handleAcceptReport}>Accept</button>
                        </div>
                    </div>
                </div>
            )}

            {showRejectModal && (
                <div className="ui-overlay">
                    <div className="ui-modal">
                        <h3 className="ui-section-title">Reject Report</h3>
                        <div className="ui-field">
                            <label className="ui-label">Rejection Reason</label>
                            <textarea
                                className="ui-textarea"
                                value={verificationNotes}
                                onChange={(e) => setVerificationNotes(e.target.value)}
                                rows="4"
                                placeholder="Explain why this report is being rejected..."
                            />
                        </div>
                        <div className="ui-row" style={{ justifyContent: 'flex-end' }}>
                            <button
                                className="ui-btn ui-btn--ghost"
                                onClick={() => {
                                    setShowRejectModal(false);
                                    setVerificationNotes('');
                                }}
                            >
                                Cancel
                            </button>
                            <button className="ui-btn ui-btn--danger" onClick={handleRejectReport}>Reject</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ReportDetail;
