// src/pages/ResearcherDashboard.jsx
import React from 'react';
import { useAuth } from '../../contexts/AuthContext';

const ResearcherDashboard = () => {
    const { user } = useAuth();

    return (
        <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
            <div style={{ marginBottom: '2rem' }}>
                <h1>Researcher Dashboard</h1>
                <p style={{ color: '#666' }}>Welcome back, {user?.first_name}!</p>
            </div>

            {/* Stats Overview */}
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
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#3498db' }}>0</div>
                    <div style={{ color: '#666' }}>Active Submissions</div>
                </div>

                <div style={{
                    background: 'white',
                    padding: '1.5rem',
                    borderRadius: '8px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                    textAlign: 'center'
                }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#2ecc71' }}>0</div>
                    <div style={{ color: '#666' }}>Accepted Reports</div>
                </div>

                <div style={{
                    background: 'white',
                    padding: '1.5rem',
                    borderRadius: '8px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                    textAlign: 'center'
                }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#e74c3c' }}>$0</div>
                    <div style={{ color: '#666' }}>Total Earnings</div>
                </div>

                <div style={{
                    background: 'white',
                    padding: '1.5rem',
                    borderRadius: '8px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                    textAlign: 'center'
                }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#9b59b6' }}>0</div>
                    <div style={{ color: '#666' }}>Programs Participated</div>
                </div>
            </div>

            {/* Quick Actions */}
            <div style={{
                background: 'white',
                padding: '2rem',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                marginBottom: '2rem'
            }}>
                <h3 style={{ margin: '0 0 1.5rem 0' }}>Quick Actions</h3>
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                    <button style={{
                        background: '#3498db',
                        color: 'white',
                        padding: '1rem 1.5rem',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '1rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem'
                    }}>
                        <span>🔍</span>
                        Find Programs
                    </button>

                    <button style={{
                        background: '#2ecc71',
                        color: 'white',
                        padding: '1rem 1.5rem',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '1rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem'
                    }}>
                        <span>📝</span>
                        Submit Report
                    </button>

                    <button style={{
                        background: '#9b59b6',
                        color: 'white',
                        padding: '1rem 1.5rem',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '1rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem'
                    }}>
                        <span>👤</span>
                        Edit Profile
                    </button>
                </div>
            </div>

            {/* Active Programs */}
            <div style={{
                background: 'white',
                padding: '2rem',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h3 style={{ margin: 0 }}>Available Programs</h3>
                    <button style={{
                        background: '#3498db',
                        color: 'white',
                        padding: '0.5rem 1rem',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.9rem'
                    }}>
                        View All Programs
                    </button>
                </div>

                <div style={{
                    border: '2px dashed #ddd',
                    borderRadius: '8px',
                    padding: '3rem',
                    textAlign: 'center',
                    color: '#666'
                }}>
                    <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.5 }}>🎯</div>
                    <h4 style={{ margin: '0 0 1rem 0', color: '#333' }}>No Programs Available</h4>
                    <p style={{ margin: '0 0 1.5rem 0', maxWidth: '500px', marginInline: 'auto' }}>
                        There are currently no active bug bounty programs. Check back soon!
                    </p>
                </div>
            </div>

            {/* Recent Activity */}
            <div style={{
                background: 'white',
                padding: '2rem',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                marginTop: '2rem'
            }}>
                <h3 style={{ margin: '0 0 1.5rem 0' }}>Recent Submissions</h3>
                <div style={{
                    border: '1px dashed #ddd',
                    borderRadius: '8px',
                    padding: '2rem',
                    textAlign: 'center',
                    color: '#999'
                }}>
                    <p style={{ margin: 0 }}>No recent submissions</p>
                </div>
            </div>
        </div>
    );
};

export default ResearcherDashboard;