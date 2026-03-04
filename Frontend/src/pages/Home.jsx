// src/pages/Home.jsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { homeAPI } from '../services/api';
import './Home.css';

const Home = () => {
    const [stats, setStats] = useState(null);
    const [publicReports, setPublicReports] = useState([]);
    const [loading, setLoading] = useState(true);
    const { user, isCompany, isResearcher } = useAuth();

    useEffect(() => {
        loadHomeData();
    }, []);

    const loadHomeData = async () => {
        try {
            const [statsResponse, reportsResponse] = await Promise.all([
                homeAPI.getStats(),
                homeAPI.getPublicReports()
            ]);
            setStats(statsResponse.data);
            setPublicReports(reportsResponse.data || []);
        } catch (error) {
            console.error('Failed to load home data:', error);
            // Set default stats if API fails
            setStats({
                total_reports: 127,
                researchers_count: 89,
                bounties_paid: 42,
                avg_response_time: "24h"
            });
            setPublicReports([]);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="loading-container">
                <div className="loading-spinner"></div>
                <p>Loading platform data...</p>
            </div>
        );
    }

    return (
        <div className="home-page">
            {/* Hero Section */}
            <section className="hero-section">
                <div className="hero-content">
                    <div className="hero-text">
                        <h1 className="hero-title">
                            Secure the Digital World, <span className="highlight">Together</span>
                        </h1>
                        <p className="hero-subtitle">
                            A platform where security researchers and companies collaborate
                            to make the internet safer for everyone.
                        </p>
                        <div className="hero-buttons">
                            <Link to="/register/researcher" className="btn btn-primary btn-large">
                                Join as Researcher
                            </Link>
                            <Link to="/register/company" className="btn btn-secondary btn-large">
                                Start Company Program
                            </Link>
                            <Link to="/login" className="btn btn-outline btn-large">
                                Sign In
                            </Link>
                        </div>
                    </div>
                    <div className="hero-image">
                        <div className="platform-illustration">
                            <div className="illustration-researchers">
                                <span className="icon">🔍</span>
                                <span className="label">Researchers</span>
                            </div>
                            <div className="illustration-connection">⇄</div>
                            <div className="illustration-platform">
                                <span className="icon">🛡️</span>
                                <span className="label">BugBounty</span>
                            </div>
                            <div className="illustration-connection">⇄</div>
                            <div className="illustration-companies">
                                <span className="icon">🏢</span>
                                <span className="label">Companies</span>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* How It Works Section */}
            <section className="how-it-works">
                <div className="container">
                    <h2 className="section-title">How It Works</h2>
                    <p className="section-subtitle">
                        Whether you're a security researcher or a company, we've got you covered
                    </p>

                    <div className="workflow">
                        {/* For Researchers */}
                        <div className="workflow-column">
                            <div className="workflow-header researcher-header">
                                <h3>For Security Researchers</h3>
                                <p className="role-badge">🔍 Find Vulnerabilities</p>
                            </div>
                            <div className="steps">
                                <div className="step">
                                    <div className="step-number">1</div>
                                    <div className="step-content">
                                        <h4>Browse Programs</h4>
                                        <p>Explore bug bounty programs from trusted companies</p>
                                    </div>
                                </div>
                                <div className="step">
                                    <div className="step-number">2</div>
                                    <div className="step-content">
                                        <h4>Find & Report</h4>
                                        <p>Identify vulnerabilities and submit detailed reports</p>
                                    </div>
                                </div>
                                <div className="step">
                                    <div className="step-number">3</div>
                                    <div className="step-content">
                                        <h4>Get Rewarded</h4>
                                        <p>Receive bounties for valid findings</p>
                                    </div>
                                </div>
                            </div>
                            {!user && (
                                <Link to="/register" className="btn btn-outline">
                                    Join as Researcher
                                </Link>
                            )}
                        </div>

                        {/* For Companies */}
                        <div className="workflow-column">
                            <div className="workflow-header company-header">
                                <h3>For Companies</h3>
                                <p className="role-badge">🏢 Secure Your Assets</p>
                            </div>
                            <div className="steps">
                                <div className="step">
                                    <div className="step-number">1</div>
                                    <div className="step-content">
                                        <h4>Create Program</h4>
                                        <p>Define scope, rules, and rewards for your assets</p>
                                    </div>
                                </div>
                                <div className="step">
                                    <div className="step-number">2</div>
                                    <div className="step-content">
                                        <h4>Receive Reports</h4>
                                        <p>Get detailed vulnerability reports from experts</p>
                                    </div>
                                </div>
                                <div className="step">
                                    <div className="step-number">3</div>
                                    <div className="step-content">
                                        <h4>Fix & Reward</h4>
                                        <p>Patch vulnerabilities and reward researchers</p>
                                    </div>
                                </div>
                            </div>
                            {!user && (
                                <Link to="/register" className="btn btn-outline">
                                    Join as Company
                                </Link>
                            )}
                        </div>
                    </div>
                </div>
            </section>

            {/* Recent Reports Section */}
            {publicReports.length > 0 && (
                <section className="reports-section">
                    <div className="container">
                        <h2 className="section-title">Recently Accepted Reports</h2>
                        <p className="section-subtitle">
                            See what vulnerabilities researchers are finding and fixing
                        </p>
                        <div className="reports-grid">
                            {publicReports.slice(0, 4).map((report) => (
                                <div key={report.id} className="report-card">
                                    <div className="report-header">
                                        <h4 className="report-title">{report.title}</h4>
                                        <span className={`severity-badge severity-${report.severity}`}>
                      {report.severity}
                    </span>
                                    </div>
                                    <p className="report-description">
                                        {report.description.substring(0, 120)}...
                                    </p>
                                    <div className="report-footer">
                                        <span className="report-meta">By {report.reporter}</span>
                                        <span className="report-meta">{new Date(report.created_at).toLocaleDateString()}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                        {publicReports.length > 4 && (
                            <div className="text-center">
                                <Link to="/reports" className="btn btn-secondary">
                                    View All Reports
                                </Link>
                            </div>
                        )}
                    </div>
                </section>
            )}

            {/* CTA Section */}
            <section className="cta-section">
                <div className="container">
                    <div className="cta-content">
                        <h2 className="cta-title">Ready to Make an Impact?</h2>
                        <p className="cta-subtitle">
                            Join our community of security professionals and companies working together
                            to build a safer internet.
                        </p>
                        <div className="cta-buttons">
                            {!user ? (
                                <Link to="/register" className="btn btn-primary btn-large">
                                    Start Free Today
                                </Link>
                            ) : (
                                <Link to={isCompany() ? "/company-dashboard" : "/dashboard"} className="btn btn-primary btn-large">
                                    Go to Dashboard
                                </Link>
                            )}
                            <Link to="/login" className="btn btn-outline btn-large">
                                Sign In
                            </Link>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
};

export default Home;