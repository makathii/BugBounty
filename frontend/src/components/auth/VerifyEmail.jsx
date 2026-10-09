// src/components/auth/VerifyEmail.jsx
import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../services/api';
import './auth.css';

const VerifyEmail = () => {
    const { token } = useParams();
    const navigate = useNavigate();
    const [status, setStatus] = useState('verifying'); // verifying, success, error
    const [message, setMessage] = useState('');
    const hasAttempted = useRef(false);

    useEffect(() => {
        const verifyToken = async () => {
            // Prevent double verification attempt
            if (hasAttempted.current) return;
            hasAttempted.current = true;

            try {
                const response = await api.get(`/users/verify-email/${token}/`);
                setStatus('success');
                setMessage(response.data.detail || 'Email verified successfully!');
            } catch (error) {
                // Check if it's a "token already used" error vs actually invalid
                const errorDetail = error.response?.data?.detail || '';
                if (errorDetail.toLowerCase().includes('invalid')) {
                    setStatus('error');
                    setMessage(errorDetail);
                } else {
                    // If not specifically "invalid", assume already verified
                    setStatus('success');
                    setMessage('Email already verified. You can now log in.');
                }
            }
        };

        if (token) {
            verifyToken();
        }
    }, [token]);

    const handleGoToLogin = () => {
        navigate('/login');
    };

    const handleGoHome = () => {
        navigate('/');
    };

    return (
        <div className="verify-email-container">
            <div className="verify-email-card">
                {status === 'verifying' && (
                    <>
                        <h2>Verifying your email...</h2>
                        <div className="loading-spinner">Please wait while we verify your email address.</div>
                    </>
                )}

                {status === 'success' && (
                    <>
                        <div className="success-icon">✓</div>
                        <h2>Email Verified!</h2>
                        <p>{message}</p>
                        <p>You can now log in to your account.</p>
                        <button onClick={handleGoToLogin} className="submit-btn">
                            Go to Login
                        </button>
                    </>
                )}

                {status === 'error' && (
                    <>
                        <div className="error-icon">✗</div>
                        <h2>Verification Failed</h2>
                        <p>{message}</p>
                        <div className="button-group">
                            <button onClick={handleGoToLogin} className="submit-btn">
                                Go to Login
                            </button>
                            <button onClick={handleGoHome} className="link-btn">
                                Go Home
                            </button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default VerifyEmail;
