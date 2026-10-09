// src/pages/Home.jsx — Landing Page (kein Bootstrap, reines Custom CSS)
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './Home.css';

const faqs = [
    {
        question: "What is a Bug Bounty Platform?",
        answer: "A bug bounty platform connects companies with ethical security researchers. Companies define programs with scope and rewards — researchers actively hunt for vulnerabilities and get paid for valid findings."
    },
    {
        question: "How do I sign up as a researcher?",
        answer: "Register as a researcher, set up your profile and immediately browse all available programs. There are no entry barriers — you can start right away."
    },
    {
        question: "How do I create a program as a company?",
        answer: "After registering as a company, you can use the program wizard to launch your first bug bounty program in minutes — including scope definition, severity rules and reward structure."
    },
    {
        question: "How are reports evaluated?",
        answer: "Our triage team reviews every incoming report for validity, severity (CVSS) and scope compliance. The company is notified and can communicate directly with the researcher."
    },
    {
        question: "Is the platform free to use?",
        answer: "Yes — the platform was developed as part of an FH student project and is free for all participants."
    }
];

const Home = () => {
    const [openFaq, setOpenFaq] = useState(null);
    const [contactForm, setContactForm] = useState({ name: '', email: '', message: '' });
    const [contactSent, setContactSent] = useState(false);
    const [contactError, setContactError] = useState(false);
    const [contactLoading, setContactLoading] = useState(false);

    const { user, isCompany } = useAuth();

    const handleContactSubmit = async (e) => {
        e.preventDefault();
        setContactLoading(true);
        setContactError(false);
        try {
            const res = await fetch('https://formspree.io/f/mjgpzevj', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
                body: JSON.stringify(contactForm),
            });
            if (res.ok) {
                setContactSent(true);
                setContactForm({ name: '', email: '', message: '' });
            } else {
                setContactError(true);
            }
        } catch {
            setContactError(true);
        } finally {
            setContactLoading(false);
        }
    };

    return (
        <div className="home-page">

            {/* HERO */}
            <section className="hero-section">
                <div className="hero-bg-grid" aria-hidden="true"></div>
                <div className="hero-content">
                    <div className="hero-eyebrow">Ethical Security Research Platform</div>
                    <h1 className="hero-title">
                        Hunt Bugs.<br />
                        <span className="hero-title-accent">Get Rewarded.</span><br />
                        Stay Secure.
                    </h1>
                    <p className="hero-subtitle">
                        Connecting elite security researchers with companies that take
                        cybersecurity seriously — transparent, fair and fully managed.
                    </p>
                    <div className="hero-buttons">
                        {!user ? (
                            <>
                                <Link to="/register/researcher" className="btn btn-primary btn-lg">Start Hunting</Link>
                                <Link to="/register/company" className="btn btn-outline btn-lg">Secure Your Product →</Link>
                            </>
                        ) : (
                            <Link to={isCompany() ? "/company-dashboard" : "/dashboard"} className="btn btn-primary btn-lg">Go to Dashboard →</Link>
                        )}
                    </div>
                    <div className="hero-stats">
                        <div className="hero-stat">
                            <div className="hero-stat-num">127+</div>
                            <div className="hero-stat-label">Reports submitted</div>
                        </div>
                        <div className="hero-stat-divider" aria-hidden="true"></div>
                        <div className="hero-stat">
                            <div className="hero-stat-num">89</div>
                            <div className="hero-stat-label">Active researchers</div>
                        </div>
                        <div className="hero-stat-divider" aria-hidden="true"></div>
                        <div className="hero-stat">
                            <div className="hero-stat-num">24h</div>
                            <div className="hero-stat-label">Avg. response time</div>
                        </div>
                    </div>
                </div>
                <div className="hero-visual" aria-hidden="true">
                    <div className="hero-card hero-card-1">
                        <span className="hero-card-icon hero-card-icon-bug"></span>
                        <span className="hero-card-text">Critical XSS found</span>
                        <span className="hero-card-badge critical">Critical</span>
                    </div>
                    <div className="hero-card hero-card-2">
                        <span className="hero-card-icon hero-card-icon-bounty"></span>
                        <span className="hero-card-text">Bounty awarded</span>
                        <span className="hero-card-badge success">+500 pts</span>
                    </div>
                    <div className="hero-card hero-card-3">
                        <span className="hero-card-icon hero-card-icon-shield"></span>
                        <span className="hero-card-text">Vulnerability patched</span>
                        <span className="hero-card-badge resolved">Resolved</span>
                    </div>
                    <div className="hero-orb hero-orb-1"></div>
                    <div className="hero-orb hero-orb-2"></div>
                </div>
            </section>

            {/* TRUST BADGES */}
            <section className="trust-section">
                <div className="container">
                    <p className="trust-label">Built at</p>
                    <div className="trust-badges">
                        <div className="trust-badge">
                            <span className="trust-badge-icon trust-icon-grad"></span>
                            <div>
                                <strong className="trust-badge-title">FH Student Project</strong>
                                <span className="trust-badge-sub">Innovation &amp; Security Course</span>
                            </div>
                        </div>
                        <div className="trust-divider" aria-hidden="true"></div>
                        <div className="trust-badge">
                            <span className="trust-badge-icon trust-icon-research"></span>
                            <div>
                                <strong className="trust-badge-title">Research-Driven</strong>
                                <span className="trust-badge-sub">Based on industry standards</span>
                            </div>
                        </div>
                        <div className="trust-divider" aria-hidden="true"></div>
                        <div className="trust-badge">
                            <span className="trust-badge-icon trust-icon-open"></span>
                            <div>
                                <strong className="trust-badge-title">Open Platform</strong>
                                <span className="trust-badge-sub">Free for all participants</span>
                            </div>
                        </div>
                        <div className="trust-divider" aria-hidden="true"></div>
                        <div className="trust-badge">
                            <span className="trust-badge-icon trust-icon-bolt"></span>
                            <div>
                                <strong className="trust-badge-title">Fully Functional</strong>
                                <span className="trust-badge-sub">End-to-end triage workflow</span>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* FEATURES */}
            <section className="features-section">
                <div className="container">
                    <p className="section-eyebrow text-center">Why choose us</p>
                    <h2 className="section-title text-center">Everything you need.<br />Nothing you don't.</h2>
                    <p className="section-subtitle">We built the platform we always wanted — clean, fast and actually useful.</p>
                    <div className="features-grid">
                        <div className="feature-card feature-card-large">
                            <div className="feature-icon-wrap feature-icon-target"></div>
                            <h3>Scoped Programs</h3>
                            <p>Companies define clear in-scope targets so researchers know exactly where to focus their efforts. No guesswork, no grey zones.</p>
                        </div>
                        <div className="feature-card">
                            <div className="feature-icon-wrap feature-icon-bolt"></div>
                            <h3>Fast Triage</h3>
                            <p>Dedicated triage team reviews every report with a target response time under 24 hours.</p>
                        </div>
                        <div className="feature-card">
                            <div className="feature-icon-wrap feature-icon-lock"></div>
                            <h3>Safe Harbor</h3>
                            <p>Legal protection for good-faith researchers who follow our responsible disclosure policy.</p>
                        </div>
                        <div className="feature-card">
                            <div className="feature-icon-wrap feature-icon-chat"></div>
                            <h3>Direct Communication</h3>
                            <p>Researchers and companies communicate directly through structured report threads.</p>
                        </div>
                        <div className="feature-card">
                            <div className="feature-icon-wrap feature-icon-chart"></div>
                            <h3>CVSS Scoring</h3>
                            <p>Reports are scored using industry-standard CVSS methodology for fair and consistent severity assessment.</p>
                        </div>
                        <div className="feature-card feature-card-accent">
                            <div className="feature-icon-wrap feature-icon-rocket"></div>
                            <h3>Instant Onboarding</h3>
                            <p>Register in under 2 minutes. No contracts, no sales calls. Start hunting or launch your program today.</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* HOW IT WORKS */}
            <section className="how-section">
                <div className="container">
                    <p className="section-eyebrow text-center">Simple by design</p>
                    <h2 className="section-title text-center">How it works</h2>
                    <p className="section-subtitle">Three steps. Two roles. One platform.</p>
                    <div className="how-grid">
                        <div className="how-column">
                            <div className="how-column-header">
                                <span className="how-role-badge researcher-badge">Researcher</span>
                            </div>
                            <div className="how-steps">
                                <div className="how-step">
                                    <div className="how-step-num">01</div>
                                    <div className="how-step-body">
                                        <h4>Browse Programs</h4>
                                        <p>Explore active bug bounty programs, read scope and rules, pick your target.</p>
                                    </div>
                                </div>
                                <div className="how-connector" aria-hidden="true"></div>
                                <div className="how-step">
                                    <div className="how-step-num">02</div>
                                    <div className="how-step-body">
                                        <h4>Find &amp; Report</h4>
                                        <p>Identify a vulnerability, write a clear PoC and submit your report.</p>
                                    </div>
                                </div>
                                <div className="how-connector" aria-hidden="true"></div>
                                <div className="how-step">
                                    <div className="how-step-num">03</div>
                                    <div className="how-step-body">
                                        <h4>Get Rewarded</h4>
                                        <p>Valid reports get triaged and rewarded. Build your reputation on the leaderboard.</p>
                                    </div>
                                </div>
                            </div>
                            {!user && (
                                <Link to="/register/researcher" className="btn btn-primary how-cta">Join as Researcher</Link>
                            )}
                        </div>
                        <div className="how-column">
                            <div className="how-column-header">
                                <span className="how-role-badge company-badge">Company</span>
                            </div>
                            <div className="how-steps">
                                <div className="how-step">
                                    <div className="how-step-num how-step-num-green">01</div>
                                    <div className="how-step-body">
                                        <h4>Create a Program</h4>
                                        <p>Use the program wizard to define scope, severity levels and reward ranges.</p>
                                    </div>
                                </div>
                                <div className="how-connector" aria-hidden="true"></div>
                                <div className="how-step">
                                    <div className="how-step-num how-step-num-green">02</div>
                                    <div className="how-step-body">
                                        <h4>Receive Reports</h4>
                                        <p>Get structured vulnerability reports from verified security researchers.</p>
                                    </div>
                                </div>
                                <div className="how-connector" aria-hidden="true"></div>
                                <div className="how-step">
                                    <div className="how-step-num how-step-num-green">03</div>
                                    <div className="how-step-body">
                                        <h4>Fix &amp; Reward</h4>
                                        <p>Patch the issue, mark it resolved, reward the researcher. Done.</p>
                                    </div>
                                </div>
                            </div>
                            {!user && (
                                <Link to="/register/company" className="btn btn-outline-green how-cta">Launch a Program</Link>
                            )}
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="cta-section">
                <div className="cta-glow" aria-hidden="true"></div>
                <div className="container cta-inner">
                    <p className="section-eyebrow cta-eyebrow">Ready to start?</p>
                    <h2 className="cta-title">Security is a team sport.</h2>
                    <p className="cta-subtitle">
                        Whether you hack or build — there's a place for you here.
                        Join the platform built by students who care about security.
                    </p>
                    <div className="cta-buttons">
                        {!user ? (
                            <>
                                <Link to="/register/researcher" className="btn btn-primary btn-lg">Start Hunting — It's Free</Link>
                                <Link to="/register/company" className="btn btn-outline btn-lg">I'm a Company →</Link>
                            </>
                        ) : (
                            <Link to={isCompany() ? "/company-dashboard" : "/dashboard"} className="btn btn-primary btn-lg">Go to Dashboard →</Link>
                        )}
                    </div>
                </div>
            </section>

            {/* FAQ */}
            <section className="faq-section">
                <div className="container">
                    <div className="faq-inner">
                        <p className="section-eyebrow text-center">Got questions?</p>
                        <h2 className="section-title text-center">Frequently Asked Questions</h2>
                        <div className="faq-list">
                            {faqs.map((faq, i) => (
                                <div key={i} className={"faq-item" + (openFaq === i ? " faq-item-open" : "")}>
                                    <button
                                        className="faq-question"
                                        onClick={() => setOpenFaq(openFaq === i ? null : i)}
                                        aria-expanded={openFaq === i}
                                    >
                                        <span>{faq.question}</span>
                                        <span className="faq-chevron" aria-hidden="true">{openFaq === i ? "−" : "+"}</span>
                                    </button>
                                    {openFaq === i && (
                                        <div className="faq-answer">{faq.answer}</div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </section>

            {/* CONTACT */}
            <section className="contact-section">
                <div className="container">
                    <div className="contact-grid">
                        <div className="contact-info">
                            <p className="section-eyebrow">Get in touch</p>
                            <h2 className="section-title">We'd love to hear from you.</h2>
                            <p className="contact-subtitle">
                                Questions about the platform, feedback or ideas for collaboration?
                                Drop us a message and we'll get back to you.
                            </p>
                            <div className="contact-meta">
                                <div className="contact-meta-item">
                                    <span className="contact-icon contact-icon-mail"></span>
                                    <span>if25b188@technikum-wien.at</span>
                                </div>
                                <div className="contact-meta-item">
                                    <span className="contact-icon contact-icon-school"></span>
                                    <span>FH Technikum Wien — Innovation Lab</span>
                                </div>
                            </div>
                        </div>
                        <div className="contact-form-wrap">
                            <form className="contact-form" onSubmit={handleContactSubmit}>
                                {contactSent ? (
                                    <div className="contact-success">
                                        <p>Thanks! We'll be in touch soon.</p>
                                    </div>
                                ) : (
                                    <>
                                        <div className="form-group">
                                            <label htmlFor="contact-name">Name</label>
                                            <input id="contact-name" type="text" placeholder="Max Muster" value={contactForm.name} onChange={e => setContactForm({ ...contactForm, name: e.target.value })} required />
                                        </div>
                                        <div className="form-group">
                                            <label htmlFor="contact-email">Email</label>
                                            <input id="contact-email" type="email" placeholder="max@example.com" value={contactForm.email} onChange={e => setContactForm({ ...contactForm, email: e.target.value })} required />
                                        </div>
                                        <div className="form-group">
                                            <label htmlFor="contact-msg">Message</label>
                                            <textarea id="contact-msg" rows="4" placeholder="Your message…" value={contactForm.message} onChange={e => setContactForm({ ...contactForm, message: e.target.value })} required />
                                        </div>
                                        <button type="submit" className="btn btn-primary btn-full" disabled={contactLoading}>
                                            {contactLoading ? <span className="btn-spinner"></span> : "Send Message"}
                                        </button>
                                        {contactError && (
                                            <div className="contact-error">Something went wrong — please try again.</div>
                                        )}
                                    </>
                                )}
                            </form>
                        </div>
                    </div>
                </div>
            </section>

            {/* FOOTER */}
            <footer className="site-footer">
                <div className="container">
                    <div className="footer-inner">
                        <div className="footer-brand">
                            <span className="footer-logo">BugBounty</span>
                            <p>A student-built platform for ethical security research.<br />Made with purpose at FH Wien.</p>
                        </div>
                        <div className="footer-col">
                            <h4>Platform</h4>
                            <Link to="/register/researcher">For Researchers</Link>
                            <Link to="/register/company">For Companies</Link>
                            <Link to="/login">Sign In</Link>
                        </div>
                        <div className="footer-col">
                            <h4>Resources</h4>
                            <a href="#how-it-works">How it works</a>
                            <a href="#faq">FAQ</a>
                            <a href="#contact">Contact</a>
                        </div>
                        <div className="footer-col">
                            <h4>Legal</h4>
                            <a href="#responsible-disclosure">Responsible Disclosure</a>
                            <a href="#safe-harbor">Safe Harbor Policy</a>
                            <a href="#privacy">Privacy Policy</a>
                        </div>
                    </div>
                    <div className="footer-bottom">
                        <span>© {new Date().getFullYear()} BugBounty Platform — FH Technikum Wien Inno2</span>
                    </div>
                </div>
            </footer>

        </div>
    );
};

export default Home;
