import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { reportAPI } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';

const ReportDetail = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const { user, isTriager, isAdmin, isCompany } = useAuth();

    const [report, setReport] = useState(null);
    const [comments, setComments] = useState([]);
    const [activityLogs, setActivityLogs] = useState([]);
    const [loading, setLoading] = useState(true);

    const [newComment, setNewComment] = useState('');
    const [submittingComment, setSubmittingComment] = useState(false);

    // For triager/admin actions
    const [showAcceptModal, setShowAcceptModal] = useState(false);
    const [showRejectModal, setShowRejectModal] = useState(false);
    const [verificationNotes, setVerificationNotes] = useState('');
    const [bountyAmount, setBountyAmount] = useState('');

    useEffect(() => {
        loadReport();
        loadComments();
        loadActivityLogs();
    }, [id]);

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

    const loadComments = async () => {
        try {
            // Assuming comments come with the report or we fetch separately
            if (report?.comments) {
                setComments(report.comments);
            }
        } catch (error) {
            console.error('Failed to load comments:', error);
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

    const handleAddComment = async () => {
        if (!newComment.trim()) return;

        setSubmittingComment(true);
        try {
            await reportAPI.addComment(id, { text: newComment });
            setNewComment('');
            loadComments(); // Refresh comments
        } catch (error) {
            console.error('Failed to add comment:', error);
        } finally {
            setSubmittingComment(false);
        }
    };

    const handleAcceptReport = async () => {
        try {
            await reportAPI.acceptReport(id, {
                verification_notes: verificationNotes,
                bounty_amount: bountyAmount
            });
            setShowAcceptModal(false);
            setVerificationNotes('');
            setBountyAmount('');
            loadReport(); // Refresh report
        } catch (error) {
            console.error('Failed to accept report:', error);
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

    const getStatusColor = (status) => {
        switch(status) {
            case 'open': return '#3498db';
            case 'triaged': return '#9b59b6';
            case 'accepted': return '#2ecc71';
            case 'rejected': return '#e74c3c';
            case 'resolved': return '#27ae60';
            case 'closed': return '#95a5a6';
            default: return '#7f8c8d';
        }
    };

    const getSeverityColor = (severity) => {
        switch(severity) {
            case 'critical': return '#e74c3c';
            case 'high': return '#e67e22';
            case 'medium': return '#f1c40f';
            case 'low': return '#2ecc71';
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
                <p>Loading report...</p>
            </div>
        );
    }

    if (!report) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <h2>Report not found</h2>
                <p>The report you're looking for doesn't exist or you don't have access.</p>
                <button onClick={() => navigate('/reports')} style={{
                    padding: '0.75rem 1.5rem',
                    background: '#3498db',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                }}>
                    Back to Reports
                </button>
            </div>
        );
    }

    return (
        <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
            {/* Header */}
            <div style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                        <h1 style={{ margin: '0 0 0.5rem 0' }}>{report.title}</h1>
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                            <span style={{
                                padding: '0.5rem 1rem',
                                background: getStatusColor(report.status) + '20',
                                color: getStatusColor(report.status),
                                borderRadius: '20px',
                                fontSize: '0.9rem',
                                fontWeight: '500'
                            }}>
                                {report.status.toUpperCase()}
                            </span>
                            <span style={{
                                padding: '0.5rem 1rem',
                                background: getSeverityColor(report.severity) + '20',
                                color: getSeverityColor(report.severity),
                                borderRadius: '20px',
                                fontSize: '0.9rem',
                                fontWeight: '500'
                            }}>
                                {report.severity.toUpperCase()} SEVERITY
                            </span>
                            {report.bounty_amount && (
                                <span style={{
                                    padding: '0.5rem 1rem',
                                    background: '#27ae60' + '20',
                                    color: '#27ae60',
                                    borderRadius: '20px',
                                    fontSize: '0.9rem',
                                    fontWeight: '500'
                                }}>
                                    BOUNTY: ${report.bounty_amount}
                                </span>
                            )}
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                            onClick={() => navigate('/reports')}
                            style={{
                                padding: '0.75rem 1.5rem',
                                background: '#95a5a6',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer'
                            }}
                        >
                            Back
                        </button>

                        {(isTriager() || isAdmin()) && report.status === 'triaged' && (
                            <>
                                <button
                                    onClick={() => setShowAcceptModal(true)}
                                    style={{
                                        padding: '0.75rem 1.5rem',
                                        background: '#2ecc71',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '4px',
                                        cursor: 'pointer'
                                    }}
                                >
                                    Accept
                                </button>
                                <button
                                    onClick={() => setShowRejectModal(true)}
                                    style={{
                                        padding: '0.75rem 1.5rem',
                                        background: '#e74c3c',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '4px',
                                        cursor: 'pointer'
                                    }}
                                >
                                    Reject
                                </button>
                            </>
                        )}

                        {(isTriager() || isAdmin()) && !report.assigned_to && (
                            <button
                                onClick={handleAssignToMe}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    background: '#3498db',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer'
                                }}
                            >
                                Assign to Me
                            </button>
                        )}
                    </div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem' }}>
                {/* Main Content */}
                <div>
                    {/* Report Details */}
                    <div style={{
                        background: 'white',
                        padding: '2rem',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                        marginBottom: '2rem'
                    }}>
                        <h3 style={{ margin: '0 0 1rem 0' }}>Report Details</h3>
                        <div style={{ marginBottom: '2rem' }}>
                            <p style={{ lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>{report.description}</p>
                        </div>

                        {/* Report Metadata */}
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(2, 1fr)',
                            gap: '1rem',
                            background: '#18181f',
                            padding: '1.5rem',
                            borderRadius: '8px'
                        }}>
                            <div>
                                <div style={{ fontSize: '0.9rem', color: '#8888aa', marginBottom: '0.25rem' }}>Reporter</div>
                                <div style={{ fontWeight: '500', color: '#2c3e50' }}>{report.reporter_username || report.reporter}</div>
                            </div>
                            <div>
                                <div style={{ fontSize: '0.9rem', color: '#8888aa', marginBottom: '0.25rem' }}>Created</div>
                                <div style={{ color: '#2c3e50' }}>{new Date(report.created_at).toLocaleString()}</div>
                            </div>
                            <div>
                                <div style={{ fontSize: '0.9rem', color: '#8888aa', marginBottom: '0.25rem' }}>Last Updated</div>
                                <div style={{ color: '#2c3e50' }}>{new Date(report.updated_at).toLocaleString()}</div>
                            </div>
                            <div>
                                <div style={{ fontSize: '0.9rem', color: '#8888aa', marginBottom: '0.25rem' }}>Assigned To</div>
                                <div style={{ color: '#2c3e50' }}>{report.assigned_to_username || (report.assigned_to ? `User ${report.assigned_to}` : 'Unassigned')}</div>
                            </div>
                        </div>
                    </div>

                    {/* Comments Section */}
                    <div style={{
                        background: 'white',
                        padding: '2rem',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
                    }}>
                        <h3 style={{ margin: '0 0 1.5rem 0' }}>Comments</h3>

                        {/* Add Comment */}
                        <div style={{ marginBottom: '2rem' }}>
                            <textarea
                                value={newComment}
                                onChange={(e) => setNewComment(e.target.value)}
                                placeholder="Add a comment..."
                                rows="4"
                                style={{
                                    width: '100%',
                                    padding: '1rem',
                                    border: '1px solid #ddd',
                                    borderRadius: '4px',
                                    fontSize: '1rem',
                                    marginBottom: '1rem'
                                }}
                            />
                            <button
                                onClick={handleAddComment}
                                disabled={submittingComment || !newComment.trim()}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    background: '#3498db',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    opacity: submittingComment || !newComment.trim() ? 0.7 : 1
                                }}
                            >
                                {submittingComment ? 'Adding...' : 'Add Comment'}
                            </button>
                        </div>

                        {/* Comments List */}
                        {comments.length > 0 ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                                {comments.map((comment) => (
                                    <div key={comment.id} style={{
                                        border: '1px solid #e9ecef',
                                        borderRadius: '8px',
                                        padding: '1.5rem'
                                    }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                            <strong>{comment.author}</strong>
                                            <span style={{ color: '#666', fontSize: '0.9rem' }}>
                                                {new Date(comment.created_at).toLocaleString()}
                                            </span>
                                        </div>
                                        <p style={{ margin: 0, lineHeight: '1.5' }}>{comment.text}</p>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p style={{ color: '#666', textAlign: 'center', padding: '2rem' }}>
                                No comments yet. Be the first to comment!
                            </p>
                        )}
                    </div>
                </div>

                {/* Sidebar */}
                <div>
                    {/* Activity Log */}
                    <div style={{
                        background: 'white',
                        padding: '2rem',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                        marginBottom: '2rem'
                    }}>
                        <h3 style={{ margin: '0 0 1.5rem 0' }}>Activity Log</h3>

                        {activityLogs.length > 0 ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                {activityLogs.map((log) => (
                                    <div key={log.id} style={{
                                        padding: '1rem',
                                        borderLeft: '3px solid #3498db',
                                        background: '#f8f9fa',
                                        borderRadius: '4px'
                                    }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                                            <strong>{log.user_name}</strong>
                                            <span style={{ color: '#666', fontSize: '0.85rem' }}>
                                                {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                            </span>
                                        </div>
                                        <div style={{ color: '#666', fontSize: '0.9rem', marginBottom: '0.25rem' }}>
                                            {log.action_display}
                                        </div>
                                        {log.details && Object.keys(log.details).length > 0 && (
                                            <div style={{ fontSize: '0.85rem', color: '#888' }}>
                                                {Object.entries(log.details).map(([key, value]) => (
                                                    <div key={key}>{key}: {value}</div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p style={{ color: '#666', textAlign: 'center' }}>
                                No activity recorded yet.
                            </p>
                        )}
                    </div>

                    {/* Quick Actions */}
                    {(isTriager() || isAdmin() || isCompany()) && (
                        <div style={{
                            background: 'white',
                            padding: '2rem',
                            borderRadius: '8px',
                            boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
                        }}>
                            <h3 style={{ margin: '0 0 1.5rem 0' }}>Quick Actions</h3>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                {isTriager() || isAdmin() ? (
                                    <>
                                        {report.status === 'triaged' && (
                                            <>
                                                <button
                                                    onClick={() => setShowAcceptModal(true)}
                                                    style={{
                                                        padding: '0.75rem',
                                                        background: '#2ecc71',
                                                        color: 'white',
                                                        border: 'none',
                                                        borderRadius: '4px',
                                                        cursor: 'pointer',
                                                        width: '100%'
                                                    }}
                                                >
                                                    Accept Report
                                                </button>
                                                <button
                                                    onClick={() => setShowRejectModal(true)}
                                                    style={{
                                                        padding: '0.75rem',
                                                        background: '#e74c3c',
                                                        color: 'white',
                                                        border: 'none',
                                                        borderRadius: '4px',
                                                        cursor: 'pointer',
                                                        width: '100%'
                                                    }}
                                                >
                                                    Reject Report
                                                </button>
                                            </>
                                        )}
                                        {!report.assigned_to && (
                                            <button
                                                onClick={handleAssignToMe}
                                                style={{
                                                    padding: '0.75rem',
                                                    background: '#3498db',
                                                    color: 'white',
                                                    border: 'none',
                                                    borderRadius: '4px',
                                                    cursor: 'pointer',
                                                    width: '100%'
                                                }}
                                            >
                                                Assign to Me
                                            </button>
                                        )}
                                    </>
                                ) : isCompany() && (
                                    <button
                                        onClick={() => alert('Company-specific action here')}
                                        style={{
                                            padding: '0.75rem',
                                            background: '#9b59b6',
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: '4px',
                                            cursor: 'pointer',
                                            width: '100%'
                                        }}
                                    >
                                        View Program Details
                                    </button>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Modals */}
            {showAcceptModal && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(0,0,0,0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000
                }}>
                    <div style={{
                        background: 'white',
                        padding: '2rem',
                        borderRadius: '8px',
                        maxWidth: '500px',
                        width: '100%'
                    }}>
                        <h3 style={{ margin: '0 0 1rem 0' }}>Accept Report</h3>
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem' }}>Bounty Amount ($)</label>
                            <input
                                type="number"
                                value={bountyAmount}
                                onChange={(e) => setBountyAmount(e.target.value)}
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    border: '1px solid #ddd',
                                    borderRadius: '4px',
                                    fontSize: '1rem'
                                }}
                                placeholder="Enter bounty amount"
                            />
                        </div>
                        <div style={{ marginBottom: '1.5rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem' }}>Verification Notes</label>
                            <textarea
                                value={verificationNotes}
                                onChange={(e) => setVerificationNotes(e.target.value)}
                                rows="4"
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    border: '1px solid #ddd',
                                    borderRadius: '4px',
                                    fontSize: '1rem'
                                }}
                                placeholder="Add verification notes..."
                            />
                        </div>
                        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                            <button
                                onClick={() => {
                                    setShowAcceptModal(false);
                                    setVerificationNotes('');
                                    setBountyAmount('');
                                }}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    background: '#95a5a6',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer'
                                }}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleAcceptReport}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    background: '#2ecc71',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer'
                                }}
                            >
                                Accept
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {showRejectModal && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(0,0,0,0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000
                }}>
                    <div style={{
                        background: 'white',
                        padding: '2rem',
                        borderRadius: '8px',
                        maxWidth: '500px',
                        width: '100%'
                    }}>
                        <h3 style={{ margin: '0 0 1rem 0' }}>Reject Report</h3>
                        <div style={{ marginBottom: '1.5rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem' }}>Rejection Reason</label>
                            <textarea
                                value={verificationNotes}
                                onChange={(e) => setVerificationNotes(e.target.value)}
                                rows="4"
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    border: '1px solid #ddd',
                                    borderRadius: '4px',
                                    fontSize: '1rem'
                                }}
                                placeholder="Explain why this report is being rejected..."
                            />
                        </div>
                        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                            <button
                                onClick={() => {
                                    setShowRejectModal(false);
                                    setVerificationNotes('');
                                }}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    background: '#95a5a6',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer'
                                }}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleRejectReport}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    background: '#e74c3c',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer'
                                }}
                            >
                                Reject
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ReportDetail;