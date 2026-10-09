// src/components/auth/TwoFactorVerify.jsx
import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './auth.css';

const TwoFactorVerify = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const [code, setCode] = useState('');
    const [useBackupCode, setUseBackupCode] = useState(false);
    const [backupCode, setBackupCode] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    // Get user info from location state (passed from login)
    const userId = location.state?.userId;

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setError('');

        try {
            // TODO: Replace with actual API call
            // const response = await api.post('/users/2fa/authenticate/', {
            //     user_id: userId,
            //     code: useBackupCode ? backupCode : code
            // });
            // localStorage.setItem('token', response.data.token);

            // Simulate API response
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Redirect to dashboard after successful verification
            navigate('/dashboard');
        } catch (err) {
            setError(err.response?.data?.error || 'Invalid code. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleCodeChange = (e) => {
        const value = e.target.value.replace(/\D/g, '').slice(0, 6);
        setCode(value);
    };

    const handleBackupCodeChange = (e) => {
        const value = e.target.value.toUpperCase().replace(/[^A-Z0-9-]/g, '');
        setBackupCode(value);
    };

    const toggleBackup = () => {
        setUseBackupCode(!useBackupCode);
        setCode('');
        setBackupCode('');
        setError('');
    };

    return (
        <div className="auth-container">
            <div className="register-container tf-narrow">
                <div className="auth-header">
                    <h2>Two-Factor Authentication</h2>
                    <p>
                        {useBackupCode
                            ? 'Enter one of your backup codes'
                            : 'Enter the 6-digit code from your authenticator app'
                        }
                    </p>
                </div>

                {error && <div className="error-message">{error}</div>}

                <form onSubmit={handleSubmit}>
                    {!useBackupCode ? (
                        <div className="form-group">
                            <label htmlFor="code">Authentication Code</label>
                            <input
                                type="text"
                                id="code"
                                name="code"
                                className="tf-code-input tf-code-input--lg"
                                placeholder="000000"
                                value={code}
                                onChange={handleCodeChange}
                                maxLength="6"
                                pattern="[0-9]{6}"
                                required
                                disabled={isLoading}
                                autoFocus
                            />
                        </div>
                    ) : (
                        <div className="form-group">
                            <label htmlFor="backupCode">Backup Code</label>
                            <input
                                type="text"
                                id="backupCode"
                                name="backupCode"
                                className="tf-code-input tf-code-input--backup"
                                placeholder="XXXX-XXXX-XXXX"
                                value={backupCode}
                                onChange={handleBackupCodeChange}
                                maxLength="14"
                                required
                                disabled={isLoading}
                                autoFocus
                            />
                            <small className="tf-warning">⚠️ Each backup code can only be used once</small>
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={isLoading || (!useBackupCode && code.length !== 6) || (useBackupCode && backupCode.length < 12)}
                        className="submit-btn"
                    >
                        {isLoading && <span className="loading-spinner"></span>}
                        {isLoading ? 'Verifying...' : 'Verify'}
                    </button>
                </form>

                <div className="tf-link-row">
                    <button type="button" className="tf-link-btn" onClick={toggleBackup}>
                        {useBackupCode
                            ? '← Use authenticator app instead'
                            : "Can't access your app? Use a backup code"
                        }
                    </button>
                </div>

                <p className="switch-auth">
                    <button type="button" className="link-btn" onClick={() => navigate('/login')}>
                        ← Back to Login
                    </button>
                </p>

                <div className="tf-tip">
                    <strong className="tf-tip-label">💡 Tip:</strong> We recommend using apps like{' '}
                    <strong>Google Authenticator</strong>, <strong>Authy</strong>, or{' '}
                    <strong>Microsoft Authenticator</strong>
                </div>
            </div>
        </div>
    );
};

export default TwoFactorVerify;
