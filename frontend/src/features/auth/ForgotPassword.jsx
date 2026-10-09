// src/features/auth/ForgotPassword.jsx
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { authAPI } from '../../services/api';
import './auth.css';

const ForgotPassword = () => {
    const [email, setEmail] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [sent, setSent] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            // The backend answers 200 whether or not the address has an account,
            // so "sent" never reveals whether the email is registered.
            await authAPI.requestPasswordReset(email.trim());
            setSent(true);
        } catch (err) {
            if (err.response?.status === 429) {
                setError('Too many reset requests. Please wait a while before trying again.');
            } else {
                setError(err.response?.data?.email?.[0] || 'Could not send the reset email. Please try again.');
            }
        } finally {
            setIsLoading(false);
        }
    };

    if (sent) {
        return (
            <div className="auth-container">
                <div className="login-container">
                    <div className="auth-header">
                        <h2>Check Your Email</h2>
                        <p>If an account exists for {email}, we've sent password reset instructions.</p>
                    </div>

                    <div className="success-message">✓ Request received</div>

                    <p className="auth-hint">
                        Didn't receive it? Check your spam folder. The link expires after 1 hour.
                    </p>

                    <button type="button" className="auth-secondary-btn" onClick={() => setSent(false)}>
                        Try a different email
                    </button>

                    <p className="switch-auth">
                        <Link to="/login" className="link-btn">Back to Login</Link>
                    </p>
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

                {error && <div className="error-message">{error}</div>}

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
                            autoComplete="email"
                            autoFocus
                            required
                            disabled={isLoading}
                        />
                    </div>

                    <button type="submit" disabled={isLoading} className="submit-btn">
                        {isLoading && <span className="loading-spinner"></span>}
                        {isLoading ? 'Sending...' : 'Send Reset Link'}
                    </button>
                </form>

                <p className="switch-auth">
                    Remember your password?{' '}
                    <Link to="/login" className="link-btn">Back to Login</Link>
                </p>
            </div>
        </div>
    );
};

export default ForgotPassword;
