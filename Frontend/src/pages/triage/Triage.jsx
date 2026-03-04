import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { reportAPI } from '../services/api';

const Triage = () => {
    const { user, isAdmin, isTriager } = useAuth();
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({
        status: '',
        assigned_to: '',
        severity: '',
        search: ''
    });
    const [stats, setStats] = useState(null);
    const [actionMessage, setActionMessage] = useState(null);

    useEffect(() => {
        fetchTriageDashboard();
        fetchReports();
    }, [filters]);

    const fetchTriageDashboard = async () => {
        try {
            const response = await reportAPI.getTriageDashboard();
            setStats(response.data.counts);
        } catch (err) {
            console.error('Error fetching triage dashboard:', err);
        }
    };

    const fetchReports = async () => {
        try {
            setLoading(true);
            const response = await reportAPI.getReports(filters);
            // Handle both array and paginated response formats
            const reportsData = response.data.results || response.data || [];
            setReports(Array.isArray(reportsData) ? reportsData : []);
        } catch (err) {
            console.error('Error fetching reports:', err);
            setReports([]);
        } finally {
            setLoading(false);
        }
    };

    const handleAssignToMe = async (reportId) => {
        try {
            setActionMessage(null);
            const response = await reportAPI.assignToMe(reportId);
            setActionMessage({ type: 'success', text: response.data.message });
            fetchTriageDashboard();
            fetchReports();
        } catch (err) {
            setActionMessage({
                type: 'error',
                text: err.response?.data?.error || 'Failed to assign report'
            });
            console.error('Error assigning report:', err);
        }
    };

    const handleAcceptReport = async (reportId) => {
        const verificationNotes = prompt('Enter verification notes:');
        if (!verificationNotes) return;

        const bountyAmount = prompt('Enter bounty amount (optional):');
        const data = {
            verification_notes: verificationNotes,
            ...(bountyAmount && { bounty_amount: parseFloat(bountyAmount) })
        };

        try {
            setActionMessage(null);
            const response = await reportAPI.acceptReport(reportId, data);
            setActionMessage({ type: 'success', text: response.data.message });
            fetchTriageDashboard();
            fetchReports();
        } catch (err) {
            setActionMessage({
                type: 'error',
                text: err.response?.data?.error || 'Failed to accept report'
            });
            console.error('Error accepting report:', err);
        }
    };

    const handleRejectReport = async (reportId) => {
        const rejectionReason = prompt('Enter rejection reason:');
        if (!rejectionReason) return;

        try {
            setActionMessage(null);
            const response = await reportAPI.rejectReport(reportId, { rejection_reason: rejectionReason });
            setActionMessage({ type: 'success', text: response.data.message });
            fetchTriageDashboard();
            fetchReports();
        } catch (err) {
            setActionMessage({
                type: 'error',
                text: err.response?.data?.error || 'Failed to reject report'
            });
            console.error('Error rejecting report:', err);
        }
    };

    const handleStatusChange = async (reportId, newStatus) => {
        try {
            await reportAPI.changeStatus(reportId, { status: newStatus });
            fetchReports();
        } catch (err) {
            console.error('Error changing status:', err);
        }
    };

    const clearFilters = () => {
        setFilters({
            status: '',
            assigned_to: '',
            severity: '',
            search: ''
        });
    };

    return (
        <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h1>Triage Dashboard</h1>
                <div style={{ color: '#666', fontSize: '1rem' }}>
                    Welcome, {user?.username} ({isAdmin() ? 'Admin' : 'Triager'})
                </div>
            </div>

            {/* Action Message */}
            {actionMessage && (
                <div style={{
                    padding: '1rem',
                    marginBottom: '1rem',
                    borderRadius: '4px',
                    background: actionMessage.type === 'success' ? '#d4edda' : '#f8d7da',
                    color: actionMessage.type === 'success' ? '#155724' : '#721c24',
                    border: `1px solid ${actionMessage.type === 'success' ? '#c3e6cb' : '#f5c6cb'}`,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}>
                    <span>{actionMessage.text}</span>
                    <button
                        onClick={() => setActionMessage(null)}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.2rem' }}
                    >
                        ×
                    </button>
                </div>
            )}

            {/* Stats Cards */}
            {stats && (
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
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
                        <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>Total Reports</div>
                        <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#3498db' }}>{stats.total}</div>
                    </div>
                    <div style={{
                        background: 'white',
                        padding: '1.5rem',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                        textAlign: 'center'
                    }}>
                        <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>Open</div>
                        <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#e74c3c' }}>{stats.open}</div>
                    </div>
                    <div style={{
                        background: 'white',
                        padding: '1.5rem',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                        textAlign: 'center'
                    }}>
                        <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>Triaged</div>
                        <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#f39c12' }}>{stats.triaged}</div>
                    </div>
                    <div style={{
                        background: 'white',
                        padding: '1.5rem',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                        textAlign: 'center'
                    }}>
                        <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>Assigned to Me</div>
                        <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#27ae60' }}>{stats.assigned_to_me}</div>
                    </div>
                    <div style={{
                        background: 'white',
                        padding: '1.5rem',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                        textAlign: 'center'
                    }}>
                        <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>Unassigned</div>
                        <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#95a5a6' }}>{stats.unassigned}</div>
                    </div>
                </div>
            )}

            {/* Filters */}
            <div style={{
                background: 'white',
                padding: '1.5rem',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                marginBottom: '2rem'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h3 style={{ margin: 0 }}>Filters</h3>
                    <button
                        onClick={clearFilters}
                        style={{
                            background: '#95a5a6',
                            color: 'white',
                            padding: '0.5rem 1rem',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '0.875rem'
                        }}
                    >
                        Clear Filters
                    </button>
                </div>
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                    gap: '1rem'
                }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Status</label>
                        <select
                            value={filters.status}
                            onChange={(e) => setFilters({...filters, status: e.target.value})}
                            style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ddd' }}
                        >
                            <option value="">All Status</option>
                            <option value="open">Open</option>
                            <option value="triaged">Triaged</option>
                            <option value="accepted">Accepted</option>
                            <option value="rejected">Rejected</option>
                        </select>
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Assigned To</label>
                        <select
                            value={filters.assigned_to}
                            onChange={(e) => setFilters({...filters, assigned_to: e.target.value})}
                            style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ddd' }}
                        >
                            <option value="">All</option>
                            <option value="me">Assigned to Me</option>
                            <option value="unassigned">Unassigned</option>
                        </select>
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Severity</label>
                        <select
                            value={filters.severity}
                            onChange={(e) => setFilters({...filters, severity: e.target.value})}
                            style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ddd' }}
                        >
                            <option value="">All Severity</option>
                            <option value="critical">Critical</option>
                            <option value="high">High</option>
                            <option value="medium">Medium</option>
                            <option value="low">Low</option>
                            <option value="info">Info</option>
                        </select>
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Search</label>
                        <input
                            type="text"
                            placeholder="Search reports..."
                            value={filters.search}
                            onChange={(e) => setFilters({...filters, search: e.target.value})}
                            style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ddd' }}
                        />
                    </div>
                </div>
            </div>

            {/* Reports Table */}
            <div style={{
                background: 'white',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                overflow: 'hidden',
                minHeight: '400px'
            }}>
                {loading ? (
                    <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
                        Loading reports...
                    </div>
                ) : reports.length === 0 ? (
                    <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
                        No reports found matching your filters
                    </div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '800px' }}>
                            <thead>
                            <tr style={{ background: '#f8f9fa' }}>
                                <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid #dee2e6', fontSize: '0.875rem' }}>ID</th>
                                <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid #dee2e6', fontSize: '0.875rem' }}>Title</th>
                                <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid #dee2e6', fontSize: '0.875rem' }}>Reporter</th>
                                <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid #dee2e6', fontSize: '0.875rem' }}>Severity</th>
                                <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid #dee2e6', fontSize: '0.875rem' }}>Status</th>
                                <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid #dee2e6', fontSize: '0.875rem' }}>Assigned To</th>
                                <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid #dee2e6', fontSize: '0.875rem' }}>Created</th>
                                <th style={{ padding: '1rem', textAlign: 'left', borderBottom: '1px solid #dee2e6', fontSize: '0.875rem' }}>Actions</th>
                            </tr>
                            </thead>
                            <tbody>
                            {reports.map(report => (
                                <tr key={report.id} style={{ borderBottom: '1px solid #dee2e6', background: report.assigned_to?.id === user?.id ? '#f0f9ff' : 'white' }}>
                                    <td style={{ padding: '1rem', fontSize: '0.875rem', color: '#666' }}>#{report.id}</td>
                                    <td style={{ padding: '1rem', fontSize: '0.875rem' }}>
                                        <div style={{ fontWeight: '500' }}>{report.title}</div>
                                        {report.description && (
                                            <div style={{ fontSize: '0.75rem', color: '#666', marginTop: '0.25rem' }}>
                                                {report.description.substring(0, 80)}...
                                            </div>
                                        )}
                                    </td>
                                    <td style={{ padding: '1rem', fontSize: '0.875rem' }}>{report.reporter?.username}</td>
                                    <td style={{ padding: '1rem' }}>
                                            <span style={{
                                                padding: '0.25rem 0.5rem',
                                                borderRadius: '4px',
                                                fontSize: '0.75rem',
                                                fontWeight: 'bold',
                                                background: report.severity === 'critical' ? '#e74c3c' :
                                                    report.severity === 'high' ? '#e67e22' :
                                                        report.severity === 'medium' ? '#f39c12' :
                                                            report.severity === 'low' ? '#3498db' : '#95a5a6',
                                                color: 'white'
                                            }}>
                                                {report.severity?.toUpperCase()}
                                            </span>
                                    </td>
                                    <td style={{ padding: '1rem' }}>
                                        <select
                                            value={report.status}
                                            onChange={(e) => handleStatusChange(report.id, e.target.value)}
                                            style={{
                                                padding: '0.25rem 0.5rem',
                                                borderRadius: '4px',
                                                border: '1px solid #ddd',
                                                fontSize: '0.875rem',
                                                background: report.status === 'open' ? '#ffeaa7' :
                                                    report.status === 'triaged' ? '#fab1a0' :
                                                        report.status === 'accepted' ? '#55efc4' :
                                                            report.status === 'rejected' ? '#fd79a8' : '#dfe6e9'
                                            }}
                                        >
                                            <option value="open">Open</option>
                                            <option value="triaged">Triaged</option>
                                            <option value="accepted">Accepted</option>
                                            <option value="rejected">Rejected</option>
                                        </select>
                                    </td>
                                    <td style={{ padding: '1rem', fontSize: '0.875rem' }}>
                                        {report.assigned_to?.username || (
                                            <span style={{ color: '#95a5a6', fontStyle: 'italic' }}>Unassigned</span>
                                        )}
                                    </td>
                                    <td style={{ padding: '1rem', fontSize: '0.875rem', color: '#666' }}>
                                        {new Date(report.created_at).toLocaleDateString()}
                                    </td>
                                    <td style={{ padding: '1rem' }}>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                            {!report.assigned_to && (
                                                <button
                                                    onClick={() => handleAssignToMe(report.id)}
                                                    style={{
                                                        background: '#3498db',
                                                        color: 'white',
                                                        padding: '0.25rem 0.5rem',
                                                        border: 'none',
                                                        borderRadius: '4px',
                                                        cursor: 'pointer',
                                                        fontSize: '0.75rem',
                                                        width: '100%'
                                                    }}
                                                >
                                                    Assign to Me
                                                </button>
                                            )}
                                            <button
                                                onClick={() => window.location.href = `/reports/${report.id}`}
                                                style={{
                                                    background: '#2ecc71',
                                                    color: 'white',
                                                    padding: '0.25rem 0.5rem',
                                                    border: 'none',
                                                    borderRadius: '4px',
                                                    cursor: 'pointer',
                                                    fontSize: '0.75rem',
                                                    width: '100%'
                                                }}
                                            >
                                                View Details
                                            </button>
                                            <div style={{ display: 'flex', gap: '0.25rem' }}>
                                                <button
                                                    onClick={() => handleAcceptReport(report.id)}
                                                    style={{
                                                        background: '#27ae60',
                                                        color: 'white',
                                                        padding: '0.25rem 0.5rem',
                                                        border: 'none',
                                                        borderRadius: '4px',
                                                        cursor: 'pointer',
                                                        fontSize: '0.75rem',
                                                        flex: 1
                                                    }}
                                                >
                                                    Accept
                                                </button>
                                                <button
                                                    onClick={() => handleRejectReport(report.id)}
                                                    style={{
                                                        background: '#e74c3c',
                                                        color: 'white',
                                                        padding: '0.25rem 0.5rem',
                                                        border: 'none',
                                                        borderRadius: '4px',
                                                        cursor: 'pointer',
                                                        fontSize: '0.75rem',
                                                        flex: 1
                                                    }}
                                                >
                                                    Reject
                                                </button>
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Triage;