// src/components/auth/TwoFactorSetup.jsx
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import { mfaAPI } from '../../services/api';
import { downloadBackupCodes } from './backupCodes';
import './auth.css';

const errorText = (err, fallback) => err.response?.data?.detail || fallback;

const TwoFactorSetup = () => {
    const navigate = useNavigate();
    const [step, setStep] = useState(1); // 1: scan + verify, 2: backup codes
    const [provisioningUri, setProvisioningUri] = useState('');
    const [secret, setSecret] = useState('');
    const [verificationCode, setVerificationCode] = useState('');
    const [backupCodes, setBackupCodes] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');
    // POST /mfa/setup/ rotates the secret, so it must run exactly once per visit
    // (React StrictMode would otherwise call it twice and the QR could go stale).
    const requested = useRef(false);

    useEffect(() => {
        if (requested.current) return;
        requested.current = true;

        const init = async () => {
            try {
                // An already-enabled account must not be handed its secret again.
                const { data: status } = await mfaAPI.getStatus();
                if (status.is_enabled) {
                    navigate('/2fa/settings', { replace: true });
                    return;
                }
                const { data } = await mfaAPI.setup();
                setSecret(data.secret);
                setProvisioningUri(data.provisioning_uri);
            } catch (err) {
                setError(errorText(err, 'Failed to load 2FA setup'));
            }
        };
        init();
    }, [navigate]);

    const handleVerify = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setError('');

        try {
            const { data } = await mfaAPI.confirm(verificationCode);
            setBackupCodes(data.backup_codes || []);
            setStep(2);
        } catch (err) {
            setError(errorText(err, 'Invalid verification code'));
        } finally {
            setIsLoading(false);
        }
    };

    if (step === 2) {
        return (
            <div className="auth-container">
                <div className="register-container tf-medium">
                    <div className="auth-header">
                        <h2>Save Your Backup Codes</h2>
                        <p>Store these codes in a safe place. Each can only be used once and they will not be shown again.</p>
                    </div>

                    <div className="success-message">✓ Two-Factor Authentication Enabled</div>

                    <div className="tf-panel">
                        <div className="tf-codes">
                            {backupCodes.map((code) => (
                                <div key={code}>{code}</div>
                            ))}
                        </div>
                    </div>

                    <button type="button" className="tf-btn tf-btn--block" onClick={() => downloadBackupCodes(backupCodes)}>
                        📥 Download Backup Codes
                    </button>

                    <button type="button" className="submit-btn" onClick={() => navigate('/dashboard')}>
                        Continue to Dashboard
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="auth-container">
            <div className="register-container tf-medium">
                <div className="auth-header">
                    <h2>Setup Two-Factor Authentication</h2>
                    <p>Scan the QR code with your authenticator app</p>
                </div>

                {error && <div className="error-message">{error}</div>}

                <div className="tf-panel tf-panel--center">
                    <h3 className="tf-panel-title tf-panel-title--sm">Step 1: Scan QR Code</h3>

                    <div className="tf-qr">
                        {provisioningUri ? (
                            <QRCodeSVG value={provisioningUri} size={200} level="M" title="2FA QR code" />
                        ) : (
                            <div className="tf-qr-placeholder">
                                <span className="loading-spinner"></span>
                            </div>
                        )}
                    </div>

                    <p className="tf-text" style={{ marginBottom: '0.5rem' }}>Or enter this key manually:</p>
                    <code className="tf-secret">{secret || '…'}</code>
                </div>

                <form onSubmit={handleVerify}>
                    <div className="tf-panel tf-panel--flush-form">
                        <h3 className="tf-panel-title tf-panel-title--sm">Step 2: Enter Verification Code</h3>

                        <div className="form-group">
                            <label htmlFor="code">6-Digit Code from App</label>
                            <input
                                type="text"
                                id="code"
                                name="code"
                                className="tf-code-input"
                                placeholder="000000"
                                value={verificationCode}
                                onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                maxLength="6"
                                pattern="[0-9]{6}"
                                inputMode="numeric"
                                autoComplete="one-time-code"
                                required
                                disabled={isLoading}
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={isLoading || verificationCode.length !== 6 || !secret}
                        className="submit-btn"
                    >
                        {isLoading && <span className="loading-spinner"></span>}
                        {isLoading ? 'Verifying...' : 'Verify & Enable 2FA'}
                    </button>
                </form>

                <p className="switch-auth">
                    <button type="button" className="link-btn" onClick={() => navigate('/dashboard')}>
                        Skip for now
                    </button>
                </p>
            </div>
        </div>
    );
};

export default TwoFactorSetup;
