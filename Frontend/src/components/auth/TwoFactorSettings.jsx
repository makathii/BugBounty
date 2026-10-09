// src/components/auth/TwoFactorSettings.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { mfaAPI } from '../../services/api';
import { downloadBackupCodes } from './backupCodes';
import './auth.css';

const errorText = (err, fallback) => err.response?.data?.detail || fallback;

// Defined at module level: a component declared inside TwoFactorSettings would be
// re-created on every keystroke, remounting the input and dropping focus.
const CodeField = ({ label, code, setCode, disabled }) => (
    <div className="form-group" style={{ marginBottom: '1rem' }}>
        <label htmlFor="mfa-code">{label}</label>
        <input
            type="text"
            id="mfa-code"
            className="tf-code-input"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            placeholder="000000"
            maxLength="6"
            inputMode="numeric"
            autoComplete="one-time-code"
            autoFocus
            required
            disabled={disabled}
        />
    </div>
);

const TwoFactorSettings = () => {
    const navigate = useNavigate();
    const [status, setStatus] = useState(null); // { is_enabled, is_required, backup_codes_remaining }
    const [loadingStatus, setLoadingStatus] = useState(true);
    const [confirming, setConfirming] = useState(null); // 'regenerate' | 'disable' | null
    const [code, setCode] = useState('');
    const [newBackupCodes, setNewBackupCodes] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const loadStatus = async () => {
        try {
            const { data } = await mfaAPI.getStatus();
            setStatus(data);
        } catch (err) {
            setError(errorText(err, 'Failed to load 2FA status'));
        } finally {
            setLoadingStatus(false);
        }
    };

    useEffect(() => {
        loadStatus();
    }, []);

    const startConfirm = (kind) => {
        setConfirming(kind);
        setCode('');
        setError('');
        setSuccess('');
    };

    const cancelConfirm = () => {
        setConfirming(null);
        setCode('');
    };

    const handleDisable = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setError('');
        try {
            await mfaAPI.disable(code);
            setConfirming(null);
            setCode('');
            setNewBackupCodes([]);
            setSuccess('Two-Factor Authentication has been disabled');
            await loadStatus();
        } catch (err) {
            setError(errorText(err, 'Failed to disable 2FA'));
        } finally {
            setIsLoading(false);
        }
    };

    const handleRegenerate = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setError('');
        try {
            const { data } = await mfaAPI.regenerateBackupCodes(code);
            setNewBackupCodes(data.backup_codes || []);
            setConfirming(null);
            setCode('');
            setSuccess('New backup codes generated. Save them now — they will not be shown again.');
            await loadStatus();
        } catch (err) {
            setError(errorText(err, 'Failed to regenerate backup codes'));
        } finally {
            setIsLoading(false);
        }
    };

    if (loadingStatus) {
        return (
            <div className="auth-container">
                <div className="register-container tf-wide">
                    <div className="tf-panel tf-panel--center">
                        <span className="loading-spinner"></span>
                    </div>
                </div>
            </div>
        );
    }

    const enabled = !!status?.is_enabled;

    return (
        <div className="auth-container">
            <div className="register-container tf-wide">
                <div className="auth-header">
                    <h2>Two-Factor Authentication Settings</h2>
                    <p>Manage your 2FA security settings</p>
                </div>

                {error && <div className="error-message">{error}</div>}
                {success && <div className="success-message">{success}</div>}

                <div className="tf-panel">
                    <div className="tf-row">
                        <div>
                            <h3 className="tf-panel-title" style={{ marginBottom: '0.25rem' }}>Status</h3>
                            <p className="tf-text">
                                Two-Factor Authentication is currently{' '}
                                <strong className={enabled ? 'tf-on' : 'tf-off'}>
                                    {enabled ? 'ENABLED' : 'DISABLED'}
                                </strong>
                                {status?.is_required && ' (required for your role)'}
                            </p>
                        </div>
                        <div className={`tf-status-icon ${enabled ? 'on' : 'off'}`}>
                            {enabled ? '✓' : '✗'}
                        </div>
                    </div>
                </div>

                {enabled ? (
                    <>
                        <div className="tf-panel">
                            <h3 className="tf-panel-title">Backup Codes</h3>
                            <p className="tf-text">
                                You have <strong>{status.backup_codes_remaining} backup codes</strong> remaining
                            </p>

                            {newBackupCodes.length > 0 && (
                                <div className="tf-codes-box">
                                    <div className="tf-codes">
                                        {newBackupCodes.map((c) => (
                                            <div key={c}>{c}</div>
                                        ))}
                                    </div>
                                    <button type="button" className="tf-btn tf-btn--sm" onClick={() => downloadBackupCodes(newBackupCodes)}>
                                        📥 Download Backup Codes
                                    </button>
                                </div>
                            )}

                            {confirming !== 'regenerate' ? (
                                <button type="button" className="tf-btn" onClick={() => startConfirm('regenerate')}>
                                    Regenerate Backup Codes
                                </button>
                            ) : (
                                <form className="tf-confirm tf-confirm--warn" onSubmit={handleRegenerate}>
                                    <p>⚠️ This invalidates all existing backup codes</p>
                                    <CodeField label="Current 6-digit code from your app" code={code} setCode={setCode} disabled={isLoading} />
                                    <div className="tf-confirm-actions">
                                        <button type="submit" className="tf-btn tf-btn--solid-warn" disabled={isLoading || code.length !== 6}>
                                            {isLoading ? 'Generating...' : 'Confirm'}
                                        </button>
                                        <button type="button" className="tf-btn" onClick={cancelConfirm}>Cancel</button>
                                    </div>
                                </form>
                            )}
                        </div>

                        <div className="tf-panel">
                            <h3 className="tf-panel-title">Disable 2FA</h3>
                            {status.is_required ? (
                                <p className="tf-text" style={{ marginBottom: 0 }}>
                                    Two-factor authentication is mandatory for your role and cannot be disabled.
                                </p>
                            ) : (
                                <>
                                    <p className="tf-text">This will reduce your account security</p>
                                    {confirming !== 'disable' ? (
                                        <button type="button" className="tf-btn tf-btn--danger" onClick={() => startConfirm('disable')}>
                                            Disable Two-Factor Authentication
                                        </button>
                                    ) : (
                                        <form className="tf-confirm tf-confirm--danger" onSubmit={handleDisable}>
                                            <p>Enter a current code to disable 2FA</p>
                                            <CodeField label="6-digit code from your app" code={code} setCode={setCode} disabled={isLoading} />
                                            <div className="tf-confirm-actions">
                                                <button type="submit" className="tf-btn tf-btn--solid-danger" disabled={isLoading || code.length !== 6}>
                                                    {isLoading ? 'Disabling...' : 'Yes, Disable'}
                                                </button>
                                                <button type="button" className="tf-btn" onClick={cancelConfirm}>Cancel</button>
                                            </div>
                                        </form>
                                    )}
                                </>
                            )}
                        </div>
                    </>
                ) : (
                    <div className="tf-panel tf-panel--center">
                        <div className="tf-icon-lg">🔐</div>
                        <h3 className="tf-panel-title" style={{ fontSize: '1.1rem' }}>Secure Your Account</h3>
                        <p className="tf-text" style={{ marginBottom: '1.5rem' }}>
                            Enable Two-Factor Authentication for enhanced security
                        </p>
                        <button type="button" className="submit-btn" onClick={() => navigate('/2fa/setup')}>
                            Enable Two-Factor Authentication
                        </button>
                    </div>
                )}

                <p className="switch-auth" style={{ marginTop: '1.5rem' }}>
                    <button type="button" className="link-btn" onClick={() => navigate('/dashboard')}>
                        ← Back to Dashboard
                    </button>
                </p>
            </div>
        </div>
    );
};

export default TwoFactorSettings;
