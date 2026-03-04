import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const CompanyDashboard = () => {
    const { user, hasCompanyProfile, loading: authLoading } = useAuth();
    const navigate = useNavigate();
    const [company, setCompany] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!authLoading && user) {
            if (!hasCompanyProfile) {
                console.log('Company user needs to complete profile, redirecting...');
                navigate('/company/setup-profile');
                return;
            }

            loadCompanyData();
        }
    }, [authLoading, user, hasCompanyProfile, navigate]);

    const loadCompanyData = async () => {
        try {
            // TODO: Replace with actual API call to get company data
            // For now, simulate API call
            setTimeout(() => {
                setCompany({
                    company_name: user.company_name || "Your Company",
                    verification_status: "pending",
                    website: "https://example.com",
                    description: "Security-focused company running bug bounty programs",
                    industry: "Technology",
                    country: "United States"
                });
                setLoading(false);
            }, 1000);
        } catch (error) {
            console.error('Error loading company data:', error);
            setLoading(false);
        }
    };

    const handleCreateProgram = () => {
        // TODO: Implement program creation
        console.log('Create program clicked');
        // navigate('/company/programs/create');
    };

    const handleViewReports = () => {
        // TODO: Implement view reports
        console.log('View reports clicked');
        // navigate('/company/reports');
    };

    const handleEditProfile = () => {
        // Navigate to profile edit page
        navigate('/company/setup-profile');
    };

    if (authLoading || loading) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <div>Loading company dashboard...</div>
            </div>
        );
    }

    return (
        <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
            <div style={{ marginBottom: '2rem' }}>
                <h1>Company Dashboard</h1>
                <p style={{ color: '#666' }}>Welcome back, {user?.first_name}!</p>
            </div>

            {/* Company Header */}
            <div style={{
                background: 'white',
                padding: '2rem',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                marginBottom: '2rem'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <h2 style={{ margin: '0 0 0.5rem 0' }}>{company.company_name}</h2>
                        <p style={{ margin: '0 0 0.5rem 0', color: '#666' }}>
                            <strong>Website:</strong> {company.website}
                        </p>
                        <p style={{ margin: '0', color: '#666' }}>
                            <strong>Industry:</strong> {company.industry} • {company.country}
                        </p>
                    </div>
                    <div style={{
                        padding: '0.5rem 1rem',
                        background: company.verification_status === 'verified' ? '#2ecc71' : '#f39c12',
                        color: 'white',
                        borderRadius: '20px',
                        fontSize: '0.9rem',
                        fontWeight: 'bold'
                    }}>
                        {company.verification_status === 'verified' ? '✓ Verified Company' : '⏳ Pending Verification'}
                    </div>
                </div>

                {company.description && (
                    <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid #eee' }}>
                        <p style={{ margin: 0, color: '#555' }}>{company.description}</p>
                    </div>
                )}
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
                    <div style={{ color: '#666' }}>Active Programs</div>
                </div>

                <div style={{
                    background: 'white',
                    padding: '1.5rem',
                    borderRadius: '8px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                    textAlign: 'center'
                }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#2ecc71' }}>0</div>
                    <div style={{ color: '#666' }}>Total Reports</div>
                </div>

                <div style={{
                    background: 'white',
                    padding: '1.5rem',
                    borderRadius: '8px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                    textAlign: 'center'
                }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#e74c3c' }}>$0</div>
                    <div style={{ color: '#666' }}>Total Payouts</div>
                </div>

                <div style={{
                    background: 'white',
                    padding: '1.5rem',
                    borderRadius: '8px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                    textAlign: 'center'
                }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#9b59b6' }}>0</div>
                    <div style={{ color: '#666' }}>Active Researchers</div>
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
                    <button
                        onClick={handleCreateProgram}
                        style={{
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
                        }}
                    >
                        <span>+</span>
                        Create New Program
                    </button>

                    <button
                        onClick={handleViewReports}
                        style={{
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
                        }}
                    >
                        <span>📋</span>
                        View Reports
                    </button>

                    <button
                        onClick={handleEditProfile}
                        style={{
                            background: '#95a5a6',
                            color: 'white',
                            padding: '1rem 1.5rem',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '1rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem'
                        }}
                    >
                        <span>✏️</span>
                        Edit Company Profile
                    </button>
                </div>
            </div>

            {/* Programs Section */}
            <div style={{
                background: 'white',
                padding: '2rem',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h3 style={{ margin: 0 }}>Your Programs</h3>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <span style={{ color: '#666' }}>0 active programs</span>
                        <button
                            onClick={handleCreateProgram}
                            style={{
                                background: '#3498db',
                                color: 'white',
                                padding: '0.5rem 1rem',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                fontSize: '0.9rem'
                            }}
                        >
                            + New Program
                        </button>
                    </div>
                </div>

                {company.verification_status === 'pending' ? (
                    <div style={{
                        background: '#fff3cd',
                        border: '1px solid #ffeaa7',
                        borderRadius: '8px',
                        padding: '2rem',
                        textAlign: 'center',
                        color: '#856404'
                    }}>
                        <h4 style={{ margin: '0 0 1rem 0' }}>Account Verification Required</h4>
                        <p style={{ margin: '0 0 1rem 0' }}>
                            Your company account is pending verification. You'll be able to create bug bounty programs once your account is verified.
                        </p>
                        <p style={{ margin: 0, fontSize: '0.9rem' }}>
                            <em>This usually takes 1-2 business days.</em>
                        </p>
                    </div>
                ) : (
                    <div style={{
                        border: '2px dashed #ddd',
                        borderRadius: '8px',
                        padding: '3rem',
                        textAlign: 'center',
                        color: '#666'
                    }}>
                        <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.5 }}>📋</div>
                        <h4 style={{ margin: '0 0 1rem 0', color: '#333' }}>No Programs Yet</h4>
                        <p style={{ margin: '0 0 1.5rem 0', maxWidth: '500px', marginInline: 'auto' }}>
                            Create your first bug bounty program to start receiving vulnerability reports from security researchers.
                        </p>
                        <button
                            onClick={handleCreateProgram}
                            style={{
                                background: '#3498db',
                                color: 'white',
                                padding: '0.75rem 1.5rem',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                fontSize: '1rem'
                            }}
                        >
                            Create Your First Program
                        </button>
                    </div>
                )}
            </div>

            {/* Recent Activity */}
            <div style={{
                background: 'white',
                padding: '2rem',
                borderRadius: '8px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                marginTop: '2rem'
            }}>
                <h3 style={{ margin: '0 0 1.5rem 0' }}>Recent Activity</h3>
                <div style={{
                    border: '1px dashed #ddd',
                    borderRadius: '8px',
                    padding: '2rem',
                    textAlign: 'center',
                    color: '#999'
                }}>
                    <p style={{ margin: 0 }}>No recent activity</p>
                </div>
            </div>
        </div>
    );
};

export default CompanyDashboard;