import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './ResearcherRegister.css';

const ResearcherRegister = () => {
    const navigate = useNavigate();
    const { register } = useAuth();
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState({});
    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: '',
        confirmPassword: '',
        firstName: '',
        lastName: ''
    });
    const captchaRef = useRef(null);
    const widgetIdRef = useRef(null);

    // Use production key if environment variable is not set
    const siteKey = process.env.REACT_APP_RECAPTCHA_SITE_KEY || "6Ld5sg8sAAAAAM4xrWvRtC6kcgogyg7MPxnoq7Tt";

    useEffect(() => {
        if (!siteKey) {
            console.error('reCAPTCHA site key is missing');
            return;
        }

        const loadRecaptcha = () => {
            if (!window.grecaptcha) {
                const script = document.createElement('script');
                script.src = 'https://www.google.com/recaptcha/api.js';
                script.async = true;
                script.defer = true;
                document.head.appendChild(script);

                script.onload = () => {
                    console.log('reCAPTCHA script loaded for ResearcherRegister');
                    renderCaptcha();
                };
            } else if (window.grecaptcha && captchaRef.current && widgetIdRef.current === null) {
                renderCaptcha();
            }
        };

        const renderCaptcha = () => {
            try {
                if (window.grecaptcha && captchaRef.current && widgetIdRef.current === null) {
                    console.log('Rendering reCAPTCHA with sitekey:', siteKey);
                    widgetIdRef.current = window.grecaptcha.render(captchaRef.current, {
                        sitekey: siteKey,
                    });
                }
            } catch (error) {
                console.error('Error rendering reCAPTCHA:', error);
            }
        };

        loadRecaptcha();

        return () => {
            if (window.grecaptcha && widgetIdRef.current !== null) {
                try {
                    window.grecaptcha.reset(widgetIdRef.current);
                } catch (error) {
                    console.error('Error resetting captcha:', error);
                }
            }
        };
    }, [siteKey]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
        if (errors[name]) {
            setErrors(prev => ({
                ...prev,
                [name]: ''
            }));
        }
        if (errors.general) {
            setErrors(prev => ({ ...prev, general: '' }));
        }
    };

    const validateForm = () => {
        const newErrors = {};

        if (!formData.username.trim()) {
            newErrors.username = 'Username is required';
        } else if (formData.username.length < 3) {
            newErrors.username = 'Username must be at least 3 characters';
        }

        if (!formData.email.trim()) {
            newErrors.email = 'Email is required';
        } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
            newErrors.email = 'Email is invalid';
        }

        if (!formData.password) {
            newErrors.password = 'Password is required';
        } else if (formData.password.length < 8) {
            newErrors.password = 'Password must be at least 8 characters';
        }

        if (formData.password !== formData.confirmPassword) {
            newErrors.confirmPassword = 'Passwords do not match';
        }

        if (!formData.firstName.trim()) {
            newErrors.firstName = 'First name is required';
        }

        if (!formData.lastName.trim()) {
            newErrors.lastName = 'Last name is required';
        }

        return newErrors;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setErrors({});

        const validationErrors = validateForm();
        if (Object.keys(validationErrors).length > 0) {
            setErrors(validationErrors);
            return;
        }

        const tokenInput = document.querySelector('textarea[name="g-recaptcha-response"]');
        const token = tokenInput ? tokenInput.value : '';

        if (!token) {
            setErrors({ captcha: 'Please complete the security verification' });
            return;
        }

        setLoading(true);

        try {
            const userData = {
                username: formData.username,
                email: formData.email,
                password: formData.password,
                password2: formData.confirmPassword,
                first_name: formData.firstName,
                last_name: formData.lastName,
                role: 'researcher',
                captcha: token
            };

            console.log('Sending registration data with captcha token');
            const result = await register(userData);

            if (result.success) {
                // Reset captcha (same as Register.jsx)
                if (window.grecaptcha && window.grecaptcha.reset) {
                    window.grecaptcha.reset();
                }

                navigate('/dashboard');
            } else {
                if (result.error) {
                    if (typeof result.error === 'object') {
                        const backendErrors = {};
                        Object.keys(result.error).forEach(key => {
                            backendErrors[key] = Array.isArray(result.error[key])
                                ? result.error[key].join(' ')
                                : result.error[key];
                        });
                        setErrors(backendErrors);
                    } else {
                        setErrors({ general: result.error });
                    }
                } else {
                    setErrors({ general: 'Registration failed' });
                }

                // Reset captcha on error
                if (window.grecaptcha && window.grecaptcha.reset) {
                    window.grecaptcha.reset();
                }
            }
        } catch (error) {
            console.error('Registration error:', error);
            setErrors({ general: 'An unexpected error occurred' });

            if (window.grecaptcha && window.grecaptcha.reset) {
                window.grecaptcha.reset();
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="researcher-register-page">
            <div className="register-container">
                <div className="register-header">
                    <h1>Join as Security Researcher</h1>
                    <p className="subtitle">
                        Start finding vulnerabilities and earning bounties
                    </p>
                </div>

                {errors.general && (
                    <div className="alert alert-danger">{errors.general}</div>
                )}

                <form onSubmit={handleSubmit} className="researcher-register-form">
                    <div className="form-section">
                        <h3>Account Information</h3>

                        <div className="form-group">
                            <label htmlFor="username">Username *</label>
                            <input
                                type="text"
                                id="username"
                                name="username"
                                value={formData.username}
                                onChange={handleChange}
                                className={errors.username ? 'error' : ''}
                                disabled={loading}
                                placeholder="Choose a username"
                            />
                            {errors.username && <div className="error-text">{errors.username}</div>}
                        </div>

                        <div className="form-group">
                            <label htmlFor="email">Email *</label>
                            <input
                                type="email"
                                id="email"
                                name="email"
                                value={formData.email}
                                onChange={handleChange}
                                className={errors.email ? 'error' : ''}
                                disabled={loading}
                                placeholder="your.email@example.com"
                            />
                            {errors.email && <div className="error-text">{errors.email}</div>}
                        </div>

                        <div className="form-row">
                            <div className="form-group">
                                <label htmlFor="password">Password *</label>
                                <input
                                    type="password"
                                    id="password"
                                    name="password"
                                    value={formData.password}
                                    onChange={handleChange}
                                    className={errors.password ? 'error' : ''}
                                    disabled={loading}
                                    placeholder="Minimum 8 characters"
                                />
                                {errors.password && <div className="error-text">{errors.password}</div>}
                            </div>

                            <div className="form-group">
                                <label htmlFor="confirmPassword">Confirm Password *</label>
                                <input
                                    type="password"
                                    id="confirmPassword"
                                    name="confirmPassword"
                                    value={formData.confirmPassword}
                                    onChange={handleChange}
                                    className={errors.confirmPassword ? 'error' : ''}
                                    disabled={loading}
                                    placeholder="Re-enter password"
                                />
                                {errors.confirmPassword && <div className="error-text">{errors.confirmPassword}</div>}
                            </div>
                        </div>
                    </div>

                    <div className="form-section">
                        <h3>Personal Information</h3>

                        <div className="form-row">
                            <div className="form-group">
                                <label htmlFor="firstName">First Name *</label>
                                <input
                                    type="text"
                                    id="firstName"
                                    name="firstName"
                                    value={formData.firstName}
                                    onChange={handleChange}
                                    className={errors.firstName ? 'error' : ''}
                                    disabled={loading}
                                    placeholder="Your first name"
                                />
                                {errors.firstName && <div className="error-text">{errors.firstName}</div>}
                            </div>

                            <div className="form-group">
                                <label htmlFor="lastName">Last Name *</label>
                                <input
                                    type="text"
                                    id="lastName"
                                    name="lastName"
                                    value={formData.lastName}
                                    onChange={handleChange}
                                    className={errors.lastName ? 'error' : ''}
                                    disabled={loading}
                                    placeholder="Your last name"
                                />
                                {errors.lastName && <div className="error-text">{errors.lastName}</div>}
                            </div>
                        </div>
                    </div>

                    <div className="form-section">
                        <h3>Security Verification</h3>
                        <div className="form-group">
                            <div
                                className="g-recaptcha"
                                ref={captchaRef}
                            />
                            {errors.captcha && <div className="error-text">{errors.captcha}</div>}
                        </div>
                    </div>

                    <div className="terms-section">
                        <label className="checkbox-label">
                            <input type="checkbox" required disabled={loading} />
                            <span>
                                I agree to the{' '}
                                <a href="/terms" target="_blank" rel="noopener noreferrer">
                                    Terms of Service
                                </a>{' '}
                                and{' '}
                                <a href="/privacy" target="_blank" rel="noopener noreferrer">
                                    Privacy Policy
                                </a>
                            </span>
                        </label>
                    </div>

                    <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                        {loading ? 'Creating Account...' : 'Register as Researcher'}
                    </button>

                    <div className="auth-links">
                        <p>
                            Already have an account? <Link to="/login">Sign In</Link>
                        </p>
                        <p>
                            Want to run a bug bounty program? <Link to="/register/company">Register as Company</Link>
                        </p>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default ResearcherRegister;