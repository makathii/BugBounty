import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { reportAPI } from '../services/api';

const TriageDashboard = () => {
    const { user } = useAuth();
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({
        status: '',
        severity: '',
        assigned_to: '',
        search: ''
    });
    const [stats, setStats] = useState(null);

    useEffect(() => {
        fetchReports();
        fetchStats();
    }, [filters]);

    const fetchReports = async () => {
        try {
            setLoading(true);
            const response = await reportAPI.getReports(filters);
            setReports(response.data.results || response.data);
        } catch (err) {
            console.error('Error fetching reports:', err);
        } finally {
            setLoading(false);
        }
    };

    const fetchStats = async () => {
        try {
            const response = await reportAPI.getTriageDashboard();
            setStats(response.data.counts);
        } catch (err) {
            console.error('Error fetching stats:', err);
        }
    };

    const handleAssignToMe = async (reportId) => {
        try {
            await reportAPI.assignToMe(reportId);
            fetchReports(); // Refresh list
            fetchStats(); // Refresh stats
        } catch (err) {
            console.error('Error assigning report:', err);
        }
    };

    const handleStatusChange = async (reportId, newStatus) => {
        try {
            await reportAPI.changeStatus(reportId, { status: newStatus });
            fetchReports(); // Refresh list
        } catch (err) {
            console.error('Error changing status:', err);
        }
    };

    return (
        <div style={{ padding: '2rem' }}>
            <h1>Triage Dashboard</h1>

            {/* Filter Section */}
            <div style={{
                background: 'white',
                padding: '1.5rem',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                marginBottom: '2rem'
            }}>
                <h3>Filters</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                    <div>
                        <label>Status</label>
                        <select
                            value={filters.status}
                            onChange={(e) => setFilters({...filters, status: e.target.value})}
                            style={{ width: '100%', padding: '0.5rem' }}
                        >
                            <option value="">All Status</option>
                            <option value="open">Open</option>
                            <option value="triaged">Triaged</option>
                            <option value="accepted">Accepted</option>
                            <option value="rejected">Rejected</option>
                        </select>
                    </div>
                    <div>
                        <label>Assigned To</label>
                        <select
                            value={filters.assigned_to}
                            onChange={(e) => setFilters({...filters, assigned_to: e.target.value})}
                            style={{ width: '100%', padding: '0.5rem' }}
                        >
                            <option value="">All</option>
                            <option value="me">Assigned to Me</option>
                            <option value="unassigned">Unassigned</option>
                        </select>
                    </div>
                    <div>
                        <label>Search</label>
                        <input
                            type="text"
                            placeholder="Search reports..."
                            value={filters.search}
                            onChange={(e) => setFilters({...filters, search: e.target.value})}
                            style={{ width: '100%', padding: '0.5rem' }}
                        />
                    </div>
                </div>
            </div>

            {/* Reports List */}
            <div style={{
                background: 'white',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                overflow: 'hidden'
            }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                    <tr style={{ background: '#f8f9fa' }}>
                        <th style={{ padding: '1rem', textAlign: 'left' }}>Title</th>
                        <th style={{ padding: '1rem', textAlign: 'left' }}>Reporter</th>
                        <th style={{ padding: '1rem', textAlign: 'left' }}>Status</th>
                        <th style={{ padding: '1rem', textAlign: 'left' }}>Assigned To</th>
                        <th style={{ padding: '1rem', textAlign: 'left' }}>Actions</th>
                    </tr>
                    </thead>
                    <tbody>
                    {reports.map(report => (
                        <tr key={report.id} style={{ borderBottom: '1px solid #dee2e6' }}>
                            <td style={{ padding: '1rem' }}>{report.title}</td>
                            <td style={{ padding: '1rem' }}>{report.reporter?.username}</td>
                            <td style={{ padding: '1rem' }}>
                                <select
                                    value={report.status}
                                    onChange={(e) => handleStatusChange(report.id, e.target.value)}
                                    style={{ padding: '0.25rem 0.5rem' }}
                                >
                                    <option value="open">Open</option>
                                    <option value="triaged">Triaged</option>
                                    <option value="accepted">Accepted</option>
                                    <option value="rejected">Rejected</option>
                                </select>
                            </td>
                            <td style={{ padding: '1rem' }}>
                                {report.assigned_to?.username || 'Unassigned'}
                            </td>
                            <td style={{ padding: '1rem' }}>
                                <button
                                    onClick={() => handleAssignToMe(report.id)}
                                    style={{
                                        background: '#3498db',
                                        color: 'white',
                                        padding: '0.25rem 0.5rem',
                                        border: 'none',
                                        borderRadius: '4px',
                                        cursor: 'pointer',
                                        marginRight: '0.5rem'
                                    }}
                                >
                                    Assign to Me
                                </button>
                                <button
                                    onClick={() => window.location.href = `/reports/${report.id}`}
                                    style={{
                                        background: '#2ecc71',
                                        color: 'white',
                                        padding: '0.25rem 0.5rem',
                                        border: 'none',
                                        borderRadius: '4px',
                                        cursor: 'pointer'
                                    }}
                                >
                                    View
                                </button>
                            </td>
                        </tr>
                    ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default TriageDashboard;