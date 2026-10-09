// src/components/auth/TwoFactorSettings.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './auth.css';

const TwoFactorSettings = () => {
    const navigate = useNavigate();
    const [is2FAEnabled, setIs2FAEnabled] = useState(false);
    const [backupCodesCount, setBackupCodesCount] = useState(0);
    const [showDisableConfirm, setShowDisableConfirm] = useState(false);
    const [showRegenerateConfirm, setShowRegenerateConfirm] = useState(false);
    const [newBackupCodes, setNewBackupCodes] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    useEffect(() => {
        load2FAStatus();
    }, []);

    const load2FAStatus = async () => {
        try {
            // TODO: Replace with actual API call
            // const response = await api.get('/users/2fa/status/');
            // setIs2FAEnabled(response.data.enabled);
            // setBackupCodesCount(response.data.backup_codes_remaining);

            // Simulate API response
            setIs2FAEnabled(true);
            setBackupCodesCount(5);
        } catch (err) {
            setError('Failed to load 2FA status');
        }
    };

    const handleDisable2FA = async () => {
        setIsLoading(true);
        setError('');
        setSuccess('');

        try {
            // TODO: Replace with actual API call
            // await api.post('/users/2fa/disable/');

            // Simulate API response
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            setIs2FAEnabled(false);
            setShowDisableConfirm(false);
            setSuccess('Two-Factor Authentication has been disabled');
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to disable 2FA');
        } finally {
            setIsLoading(false);
        }
    };

    const handleRegenerateBackupCodes = async () => {
        setIsLoading(true);
        setError('');
        setSuccess('');

        try {
            // TODO: Replace with actual API call
            // const response = await api.post('/users/2fa/regenerate-codes/');
            // setNewBackupCodes(response.data.backup_codes);

            // Simulate API response
            await new Promise(resolve => setTimeout(resolve, 1000));
            setNewBackupCodes([
                'A1B2-C3D4-E5F6',
                'G7H8-I9J0-K1L2',
                'M3N4-O5P6-Q7R8',
                'S9T0-U1V2-W3X4',
                'Y5Z6-A7B8-C9D0',
                'E1F2-G3H4-I5J6',
                'K7L8-M9N0-O1P2',
                'Q3R4-S5T6-U7V8'
            ]);
            setBackupCodesCount(8);
            setShowRegenerateConfirm(false);
            setSuccess('New backup codes generated successfully');
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to regenerate backup codes');
        } finally {
            setIsLoading(false);
        }
    };

    const downloadBackupCodes = () => {
        const text = newBackupCodes.join('\n');
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'bugbounty-backup-codes.txt';
        link.click();
    };

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
                                <strong className={is2FAEnabled ? 'tf-on' : 'tf-off'}>
                                    {is2FAEnabled ? 'ENABLED' : 'DISABLED'}
                                </strong>
                            </p>
                        </div>
                        <div className={`tf-status-icon ${is2FAEnabled ? 'on' : 'off'}`}>
                            {is2FAEnabled ? '✓' : '✗'}
                        </div>
                    </div>
                </div>

                {is2FAEnabled ? (
                    <>
                        <div className="tf-panel">
                            <h3 className="tf-panel-title">Backup Codes</h3>
                            <p className="tf-text">
                                You have <strong>{backupCodesCount} backup codes</strong> remaining
                            </p>

                            {newBackupCodes.length > 0 && (
                                <div className="tf-codes-box">
                                    <div className="tf-codes">
                                        {newBackupCodes.map((code, idx) => (
                                            <div key={idx}>{code}</div>
                                        ))}
                                    </div>
                                    <button type="button" className="tf-btn tf-btn--sm" onClick={downloadBackupCodes}>
                                        📥 Download Backup Codes
                                    </button>
                                </div>
                            )}

                            {!showRegenerateConfirm ? (
                                <button type="button" className="tf-btn" onClick={() => setShowRegenerateConfirm(true)}>
                                    Regenerate Backup Codes
                                </button>
                            ) : (
                                <div className="tf-confirm tf-confirm--warn">
                                    <p>⚠️ This will invalidate all existing backup codes</p>
                                    <div className="tf-confirm-actions">
                                        <button type="button" className="tf-btn tf-btn--solid-warn"
                                                onClick={handleRegenerateBackupCodes} disabled={isLoading}>
                                            {isLoading ? 'Generating...' : 'Confirm'}
                                        </button>
                                        <button type="button" className="tf-btn" onClick={() => setShowRegenerateConfirm(false)}>
                                            Cancel
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="tf-panel">
                            <h3 className="tf-panel-title">Disable 2FA</h3>
                            <p className="tf-text">This will reduce your account security</p>

                            {!showDisableConfirm ? (
                                <button type="button" className="tf-btn tf-btn--danger" onClick={() => setShowDisableConfirm(true)}>
                                    Disable Two-Factor Authentication
                                </button>
                            ) : (
                                <div className="tf-confirm tf-confirm--danger">
                                    <p>Are you sure you want to disable 2FA?</p>
                                    <div className="tf-confirm-actions">
                                        <button type="button" className="tf-btn tf-btn--solid-danger"
                                                onClick={handleDisable2FA} disabled={isLoading}>
                                            {isLoading ? 'Disabling...' : 'Yes, Disable'}
                                        </button>
                                        <button type="button" className="tf-btn" onClick={() => setShowDisableConfirm(false)}>
                                            Cancel
                                        </button>
                                    </div>
                                </div>
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
