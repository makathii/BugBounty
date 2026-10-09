// src/features/auth/TwoFactorVerify.jsx
import React, { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';
import './auth.css';

// Second step of login for accounts with 2FA. It arrives here from <Login> with the
// short-lived challenge token in router state (never the password); the token plus a
// TOTP or backup code completes the login.
const TwoFactorVerify = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const { completeMfaLogin } = useAuth();
    const mfaToken = location.state?.mfaToken;

    const [useBackupCode, setUseBackupCode] = useState(false);
    const [code, setCode] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');
    const [expired, setExpired] = useState(false);

    // No token (page reload, direct visit): the challenge is gone, start from login.
    if (!mfaToken) {
        return <Navigate to="/login" replace />;
    }

    const normalize = (value) => (useBackupCode
        ? value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 10)
        : value.replace(/\D/g, '').slice(0, 6));

    const ready = useBackupCode ? code.length === 10 : code.length === 6;

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setError('');

        const result = await completeMfaLogin(mfaToken, code);
        if (result.success) {
            navigate('/dashboard', { replace: true });
            return;
        }
        if (result.mfaExpired) {
            setExpired(true);
        } else {
            setError(result.error || 'Invalid code. Please try again.');
            setCode('');
        }
        setIsLoading(false);
    };

    const toggleMode = () => {
        setUseBackupCode((v) => !v);
        setCode('');
        setError('');
    };

    if (expired) {
        return (
            <div className="auth-container">
                <div className="login-container">
                    <div className="auth-header">
                        <h2>Sign-in Expired</h2>
                        <p>That sign-in step timed out. Please sign in again.</p>
                    </div>
                    <button type="button" className="submit-btn" onClick={() => navigate('/login', { replace: true })}>
                        Back to Login
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="auth-container">
            <div className="login-container">
                <div className="auth-header">
                    <h2>Two-Factor Authentication</h2>
                    <p>
                        {useBackupCode
                            ? 'Enter one of your backup codes'
                            : 'Enter the 6-digit code from your authenticator app'}
                    </p>
                </div>

                {error && <div className="error-message">{error}</div>}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="code">{useBackupCode ? 'Backup Code' : 'Authentication Code'}</label>
                        <input
                            type="text"
                            id="code"
                            name="code"
                            className={`tf-code-input${useBackupCode ? ' tf-code-input--backup' : ' tf-code-input--lg'}`}
                            placeholder={useBackupCode ? 'XXXXXXXXXX' : '000000'}
                            value={code}
                            onChange={(e) => setCode(normalize(e.target.value))}
                            inputMode={useBackupCode ? 'text' : 'numeric'}
                            autoComplete="one-time-code"
                            autoFocus
                            required
                            disabled={isLoading}
                        />
                        {useBackupCode && (
                            <small className="tf-warning">⚠️ Each backup code can only be used once</small>
                        )}
                    </div>

                    <button type="submit" className="submit-btn" disabled={isLoading || !ready}>
                        {isLoading && <span className="loading-spinner"></span>}
                        {isLoading ? 'Verifying...' : 'Verify'}
                    </button>
                </form>

                <div className="tf-link-row">
                    <button type="button" className="tf-link-btn" onClick={toggleMode}>
                        {useBackupCode
                            ? '← Use authenticator app instead'
                            : "Can't access your app? Use a backup code"}
                    </button>
                </div>

                <p className="switch-auth">
                    <Link to="/login" className="link-btn">← Back to Login</Link>
                </p>
            </div>
        </div>
    );
};

export default TwoFactorVerify;
