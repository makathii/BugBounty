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
            <div className="register-container" style={{ maxWidth: '600px' }}>
                <div className="auth-header">
                    <h2>Two-Factor Authentication Settings</h2>
                    <p>Manage your 2FA security settings</p>
                </div>

                {error && <div className="error-message">{error}</div>}
                {success && <div className="success-message">{success}</div>}

                {/* Status Card */}
                <div style={{
                    background: 'var(--color-surface-2)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-md)',
                    padding: '1.5rem',
                    marginBottom: '1.5rem'
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <h3 style={{ 
                                color: 'var(--color-text)', 
                                fontSize: '1rem', 
                                fontWeight: 600,
                                marginBottom: '0.25rem'
                            }}>
                                Status
                            </h3>
                            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', margin: 0 }}>
                                Two-Factor Authentication is currently{' '}
                                <strong style={{ color: is2FAEnabled ? 'var(--color-green)' : 'var(--color-text-muted)' }}>
                                    {is2FAEnabled ? 'ENABLED' : 'DISABLED'}
                                </strong>
                            </p>
                        </div>
                        <div style={{
                            width: '48px',
                            height: '48px',
                            borderRadius: '50%',
                            background: is2FAEnabled 
                                ? 'rgba(34, 197, 94, 0.15)' 
                                : 'rgba(239, 68, 68, 0.15)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '1.5rem'
                        }}>
                            {is2FAEnabled ? '✓' : '✗'}
                        </div>
                    </div>
                </div>

                {is2FAEnabled ? (
                    <>
                        {/* Backup Codes Card */}
                        <div style={{
                            background: 'var(--color-surface-2)',
                            border: '1px solid var(--color-border)',
                            borderRadius: 'var(--radius-md)',
                            padding: '1.5rem',
                            marginBottom: '1.5rem'
                        }}>
                            <h3 style={{ 
                                color: 'var(--color-text)', 
                                fontSize: '1rem', 
                                fontWeight: 600,
                                marginBottom: '0.5rem'
                            }}>
                                Backup Codes
                            </h3>
                            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
                                You have <strong style={{ color: 'var(--color-text)' }}>{backupCodesCount} backup codes</strong> remaining
                            </p>

                            {newBackupCodes.length > 0 && (
                                <div style={{
                                    background: 'var(--color-bg)',
                                    border: '1px solid var(--color-border)',
                                    borderRadius: 'var(--radius-sm)',
                                    padding: '1rem',
                                    marginBottom: '1rem'
                                }}>
                                    <div style={{
                                        display: 'grid',
                                        gridTemplateColumns: 'repeat(2, 1fr)',
                                        gap: '0.5rem',
                                        fontFamily: 'monospace',
                                        fontSize: '0.85rem',
                                        color: 'var(--color-text)',
                                        marginBottom: '1rem'
                                    }}>
                                        {newBackupCodes.map((code, idx) => (
                                            <div key={idx} style={{
                                                padding: '0.4rem',
                                                background: 'var(--color-surface-2)',
                                                borderRadius: '4px',
                                                textAlign: 'center'
                                            }}>
                                                {code}
                                            </div>
                                        ))}
                                    </div>
                                    <button
                                        onClick={downloadBackupCodes}
                                        style={{
                                            width: '100%',
                                            background: 'rgba(255,255,255,0.06)',
                                            border: '1px solid var(--color-border)',
                                            padding: '0.5rem',
                                            borderRadius: 'var(--radius-sm)',
                                            color: 'var(--color-text)',
                                            cursor: 'pointer',
                                            fontSize: '0.85rem'
                                        }}
                                    >
                                        📥 Download Backup Codes
                                    </button>
                                </div>
                            )}

                            {!showRegenerateConfirm ? (
                                <button
                                    onClick={() => setShowRegenerateConfirm(true)}
                                    style={{
                                        background: 'rgba(255,255,255,0.06)',
                                        border: '1px solid var(--color-border)',
                                        padding: '0.75rem 1.5rem',
                                        borderRadius: 'var(--radius-sm)',
                                        color: 'var(--color-text)',
                                        cursor: 'pointer',
                                        fontWeight: 600
                                    }}
                                >
                                    Regenerate Backup Codes
                                </button>
                            ) : (
                                <div style={{
                                    background: 'rgba(251, 191, 36, 0.1)',
                                    border: '1px solid rgba(251, 191, 36, 0.3)',
                                    borderRadius: 'var(--radius-sm)',
                                    padding: '1rem'
                                }}>
                                    <p style={{ 
                                        color: 'var(--color-warning)', 
                                        fontSize: '0.9rem', 
                                        marginBottom: '1rem',
                                        fontWeight: 600
                                    }}>
                                        ⚠️ This will invalidate all existing backup codes
                                    </p>
                                    <div style={{ display: 'flex', gap: '0.75rem' }}>
                                        <button
                                            onClick={handleRegenerateBackupCodes}
                                            disabled={isLoading}
                                            style={{
                                                flex: 1,
                                                background: 'var(--color-warning)',
                                                border: 'none',
                                                padding: '0.75rem',
                                                borderRadius: 'var(--radius-sm)',
                                                color: '#000',
                                                cursor: 'pointer',
                                                fontWeight: 600
                                            }}
                                        >
                                            {isLoading ? 'Generating...' : 'Confirm'}
                                        </button>
                                        <button
                                            onClick={() => setShowRegenerateConfirm(false)}
                                            style={{
                                                flex: 1,
                                                background: 'rgba(255,255,255,0.06)',
                                                border: '1px solid var(--color-border)',
                                                padding: '0.75rem',
                                                borderRadius: 'var(--radius-sm)',
                                                color: 'var(--color-text)',
                                                cursor: 'pointer'
                                            }}
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Disable 2FA Section */}
                        <div style={{
                            background: 'var(--color-surface-2)',
                            border: '1px solid var(--color-border)',
                            borderRadius: 'var(--radius-md)',
                            padding: '1.5rem'
                        }}>
                            <h3 style={{ 
                                color: 'var(--color-text)', 
                                fontSize: '1rem', 
                                fontWeight: 600,
                                marginBottom: '0.5rem'
                            }}>
                                Disable 2FA
                            </h3>
                            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
                                This will reduce your account security
                            </p>

                            {!showDisableConfirm ? (
                                <button
                                    onClick={() => setShowDisableConfirm(true)}
                                    style={{
                                        background: 'transparent',
                                        border: '1px solid var(--color-red)',
                                        padding: '0.75rem 1.5rem',
                                        borderRadius: 'var(--radius-sm)',
                                        color: 'var(--color-red)',
                                        cursor: 'pointer',
                                        fontWeight: 600
                                    }}
                                >
                                    Disable Two-Factor Authentication
                                </button>
                            ) : (
                                <div style={{
                                    background: 'rgba(239, 68, 68, 0.1)',
                                    border: '1px solid rgba(239, 68, 68, 0.3)',
                                    borderRadius: 'var(--radius-sm)',
                                    padding: '1rem'
                                }}>
                                    <p style={{ 
                                        color: 'var(--color-red)', 
                                        fontSize: '0.9rem', 
                                        marginBottom: '1rem',
                                        fontWeight: 600
                                    }}>
                                        Are you sure you want to disable 2FA?
                                    </p>
                                    <div style={{ display: 'flex', gap: '0.75rem' }}>
                                        <button
                                            onClick={handleDisable2FA}
                                            disabled={isLoading}
                                            style={{
                                                flex: 1,
                                                background: 'var(--color-red)',
                                                border: 'none',
                                                padding: '0.75rem',
                                                borderRadius: 'var(--radius-sm)',
                                                color: '#fff',
                                                cursor: 'pointer',
                                                fontWeight: 600
                                            }}
                                        >
                                            {isLoading ? 'Disabling...' : 'Yes, Disable'}
                                        </button>
                                        <button
                                            onClick={() => setShowDisableConfirm(false)}
                                            style={{
                                                flex: 1,
                                                background: 'rgba(255,255,255,0.06)',
                                                border: '1px solid var(--color-border)',
                                                padding: '0.75rem',
                                                borderRadius: 'var(--radius-sm)',
                                                color: 'var(--color-text)',
                                                cursor: 'pointer'
                                            }}
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </>
                ) : (
                    /* Enable 2FA Card */
                    <div style={{
                        background: 'var(--color-surface-2)',
                        border: '1px solid var(--color-border)',
                        borderRadius: 'var(--radius-md)',
                        padding: '1.5rem',
                        textAlign: 'center'
                    }}>
                        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔐</div>
                        <h3 style={{ 
                            color: 'var(--color-text)', 
                            fontSize: '1.1rem', 
                            fontWeight: 600,
                            marginBottom: '0.5rem'
                        }}>
                            Secure Your Account
                        </h3>
                        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                            Enable Two-Factor Authentication for enhanced security
                        </p>
                        <button
                            onClick={() => navigate('/2fa/setup')}
                            className="submit-btn"
                        >
                            Enable Two-Factor Authentication
                        </button>
                    </div>
                )}

                <p className="switch-auth" style={{ marginTop: '1.5rem' }}>
                    <button
                        onClick={() => navigate('/dashboard')}
                        className="link-btn"
                        style={{ background: 'none', border: 'none' }}
                    >
                        ← Back to Dashboard
                    </button>
                </p>
            </div>
        </div>
    );
};

export default TwoFactorSettings;
