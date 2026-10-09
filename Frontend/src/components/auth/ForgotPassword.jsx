// src/components/auth/ForgotPassword.jsx
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import './auth.css';

const ForgotPassword = () => {
    const [email, setEmail] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            // TODO: Replace with actual API call
            // await api.post('/users/password-reset/', { email });
            
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 1500));
            setSuccess(true);
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to send reset email');
        } finally {
            setIsLoading(false);
        }
    };

    if (success) {
        return (
            <div className="auth-container">
                <div className="login-container">
                    <div className="auth-header">
                        <h2>Check Your Email</h2>
                        <p>We've sent password reset instructions to {email}</p>
                    </div>

                    <div className="success-message">
                        ✓ Reset link sent successfully
                    </div>

                    <p style={{ textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '0.85rem', margin: '1rem 0' }}>
                        Didn't receive the email? Check your spam folder or try again.
                    </p>

                    <Link to="/login" className="btn-ghost" style={{ 
                        width: '100%', 
                        textDecoration: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: '0.75rem',
                        borderRadius: 'var(--radius-sm)'
                    }}>
                        Back to Login
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="auth-container">
            <div className="login-container">
                <div className="auth-header">
                    <h2>Reset Password</h2>
                    <p>Enter your email to receive a password reset link</p>
                </div>

                {error && (
                    <div className="error-message">{error}</div>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="email">Email Address</label>
                        <input
                            type="email"
                            id="email"
                            name="email"
                            placeholder="Enter your email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            disabled={isLoading}
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={isLoading}
                        className="submit-btn"
                    >
                        {isLoading && <span className="loading-spinner"></span>}
                        {isLoading ? 'Sending...' : 'Send Reset Link'}
                    </button>
                </form>

                <p className="switch-auth">
                    Remember your password?{' '}
                    <Link to="/login" className="link-btn">
                        Back to Login
                    </Link>
                </p>
            </div>
        </div>
    );
};

export default ForgotPassword;
