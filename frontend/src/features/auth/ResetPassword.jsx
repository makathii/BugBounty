// src/features/auth/ResetPassword.jsx
import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { authAPI } from '../../services/api';
import './auth.css';

const ResetPassword = () => {
    const { token } = useParams(); // Token from URL: /reset-password/:token
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        password: '',
        confirmPassword: ''
    });
    const [isLoading, setIsLoading] = useState(false);
    const [errors, setErrors] = useState({});
    const [success, setSuccess] = useState(false);
    const redirectTimer = useRef(null);

    useEffect(() => () => clearTimeout(redirectTimer.current), []);

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
        if (errors[e.target.name]) {
            setErrors({ ...errors, [e.target.name]: '' });
        }
    };

    const validatePassword = () => {
        const newErrors = {};

        if (formData.password.length < 8) {
            newErrors.password = 'Password must be at least 8 characters';
        }

        if (formData.password !== formData.confirmPassword) {
            newErrors.confirmPassword = 'Passwords do not match';
        }

        return newErrors;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const validationErrors = validatePassword();

        if (Object.keys(validationErrors).length > 0) {
            setErrors(validationErrors);
            return;
        }

        setIsLoading(true);
        setErrors({});

        try {
            await authAPI.confirmPasswordReset(token, formData.password, formData.confirmPassword);
            setSuccess(true);
            redirectTimer.current = setTimeout(() => navigate('/login'), 2000);
        } catch (err) {
            const data = err.response?.data || {};
            const first = (v) => (Array.isArray(v) ? v[0] : v);
            if (err.response?.status === 429) {
                setErrors({ general: 'Too many attempts. Please wait a while and try again.' });
            } else if (data.token) {
                // Invalid, expired or already-used link: the user needs a fresh one.
                setErrors({ general: first(data.token), expiredLink: true });
            } else if (data.password || data.password2) {
                // Django password validators (too common, too similar, numeric only...)
                setErrors({ password: Array.isArray(data.password) ? data.password.join(' ') : first(data.password || data.password2) });
            } else {
                setErrors({ general: 'Failed to reset password. Please try again.' });
            }
        } finally {
            setIsLoading(false);
        }
    };

    const getPasswordStrength = (password) => {
        if (password.length === 0) return null;
        if (password.length < 8) return { text: 'Weak', class: 'strength-weak' };
        if (password.length < 12) return { text: 'Medium', class: 'strength-medium' };
        return { text: 'Strong', class: 'strength-strong' };
    };

    const strength = getPasswordStrength(formData.password);

    if (success) {
        return (
            <div className="auth-container">
                <div className="login-container">
                    <div className="auth-header">
                        <h2>Password Reset Successful</h2>
                        <p>Your password has been updated</p>
                    </div>

                    <div className="success-message">
                        ✓ You can now login with your new password
                    </div>

                    <p className="auth-hint">Redirecting to login...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="auth-container">
            <div className="login-container">
                <div className="auth-header">
                    <h2>Create New Password</h2>
                    <p>Enter a strong password for your account</p>
                </div>

                {errors.general && (
                    <div className="error-message">
                        {errors.general}
                        {errors.expiredLink && (
                            <> <Link to="/forgot-password" className="link-btn">Request a new link</Link></>
                        )}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="password">New Password</label>
                        <input
                            type="password"
                            id="password"
                            name="password"
                            placeholder="Enter new password"
                            value={formData.password}
                            onChange={handleChange}
                            required
                            className={errors.password ? 'error' : ''}
                            disabled={isLoading}
                        />
                        {errors.password && <span className="error-text">{errors.password}</span>}
                        {strength && !errors.password && (
                            <div className={`password-strength ${strength.class}`}>
                                Password strength: {strength.text}
                            </div>
                        )}
                    </div>

                    <div className="form-group">
                        <label htmlFor="confirmPassword">Confirm Password</label>
                        <input
                            type="password"
                            id="confirmPassword"
                            name="confirmPassword"
                            placeholder="Confirm new password"
                            value={formData.confirmPassword}
                            onChange={handleChange}
                            required
                            className={errors.confirmPassword ? 'error' : ''}
                            disabled={isLoading}
                        />
                        {errors.confirmPassword && (
                            <span className="error-text">{errors.confirmPassword}</span>
                        )}
                    </div>

                    <button
                        type="submit"
                        disabled={isLoading}
                        className="submit-btn"
                    >
                        {isLoading && <span className="loading-spinner"></span>}
                        {isLoading ? 'Resetting...' : 'Reset Password'}
                    </button>
                </form>

                <p className="switch-auth">
                    <Link to="/login" className="link-btn">
                        Back to Login
                    </Link>
                </p>
            </div>
        </div>
    );
};

export default ResetPassword;
