// src/components/auth/ResetPassword.jsx
import React, { useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
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
            // TODO: Replace with actual API call
            // await api.post(`/users/password-reset/confirm/`, {
            //     token: token,
            //     new_password: formData.password
            // });

            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 1500));
            setSuccess(true);
            
            // Redirect to login after 2 seconds
            setTimeout(() => navigate('/login'), 2000);
        } catch (err) {
            setErrors({ 
                general: err.response?.data?.error || 'Failed to reset password. Link may be expired.' 
            });
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

                    <p style={{ textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>
                        Redirecting to login...
                    </p>
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
                    <div className="error-message">{errors.general}</div>
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
                        {strength && (
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
