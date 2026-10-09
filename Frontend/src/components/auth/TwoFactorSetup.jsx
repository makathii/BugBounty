// src/components/auth/TwoFactorSetup.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './auth.css';

const TwoFactorSetup = () => {
    const navigate = useNavigate();
    const [step, setStep] = useState(1); // 1: QR Code, 2: Verify Code
    const [qrCode, setQrCode] = useState('');
    const [secret, setSecret] = useState('');
    const [verificationCode, setVerificationCode] = useState('');
    const [backupCodes, setBackupCodes] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        // Load QR code and secret from backend
        loadQRCode();
    }, []);

    const loadQRCode = async () => {
        try {
            // TODO: Replace with actual API call
            // const response = await api.post('/users/2fa/setup/');
            // setQrCode(response.data.qr_code);
            // setSecret(response.data.secret);

            // Simulate API response
            setQrCode('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==');
            setSecret('JBSWY3DPEHPK3PXP');
        } catch (err) {
            setError('Failed to load 2FA setup');
        }
    };

    const handleVerify = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setError('');

        try {
            // TODO: Replace with actual API call
            // const response = await api.post('/users/2fa/verify/', {
            //     code: verificationCode
            // });
            // setBackupCodes(response.data.backup_codes);

            // Simulate API response
            await new Promise(resolve => setTimeout(resolve, 1000));
            setBackupCodes([
                'A1B2-C3D4-E5F6',
                'G7H8-I9J0-K1L2',
                'M3N4-O5P6-Q7R8',
                'S9T0-U1V2-W3X4',
                'Y5Z6-A7B8-C9D0',
                'E1F2-G3H4-I5J6',
                'K7L8-M9N0-O1P2',
                'Q3R4-S5T6-U7V8'
            ]);
            setStep(2);
        } catch (err) {
            setError(err.response?.data?.error || 'Invalid verification code');
        } finally {
            setIsLoading(false);
        }
    };

    const handleComplete = () => {
        navigate('/dashboard');
    };

    const downloadBackupCodes = () => {
        const text = backupCodes.join('\n');
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'bugbounty-backup-codes.txt';
        link.click();
    };

    if (step === 2) {
        return (
            <div className="auth-container">
                <div className="register-container" style={{ maxWidth: '500px' }}>
                    <div className="auth-header">
                        <h2>Save Your Backup Codes</h2>
                        <p>Store these codes in a safe place. Each can only be used once.</p>
                    </div>

                    <div className="success-message">
                        ✓ Two-Factor Authentication Enabled
                    </div>

                    <div style={{
                        background: 'var(--color-surface-2)',
                        border: '1px solid var(--color-border)',
                        borderRadius: 'var(--radius-md)',
                        padding: '1.5rem',
                        marginBottom: '1.5rem'
                    }}>
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(2, 1fr)',
                            gap: '0.75rem',
                            fontFamily: 'monospace',
                            fontSize: '0.9rem',
                            color: 'var(--color-text)'
                        }}>
                            {backupCodes.map((code, idx) => (
                                <div key={idx} style={{
                                    padding: '0.5rem',
                                    background: 'var(--color-bg)',
                                    borderRadius: '4px',
                                    textAlign: 'center'
                                }}>
                                    {code}
                                </div>
                            ))}
                        </div>
                    </div>

                    <button
                        onClick={downloadBackupCodes}
                        className="btn-ghost"
                        style={{
                            width: '100%',
                            marginBottom: '0.75rem',
                            background: 'rgba(255,255,255,0.06)',
                            border: '1px solid var(--color-border)',
                            padding: '0.75rem',
                            borderRadius: 'var(--radius-sm)',
                            color: 'var(--color-text)',
                            cursor: 'pointer',
                            fontWeight: 600
                        }}
                    >
                        📥 Download Backup Codes
                    </button>

                    <button
                        onClick={handleComplete}
                        className="submit-btn"
                    >
                        Continue to Dashboard
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="auth-container">
            <div className="register-container" style={{ maxWidth: '500px' }}>
                <div className="auth-header">
                    <h2>Setup Two-Factor Authentication</h2>
                    <p>Scan the QR code with your authenticator app</p>
                </div>

                {error && <div className="error-message">{error}</div>}

                <div style={{
                    background: 'var(--color-surface-2)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-md)',
                    padding: '1.5rem',
                    marginBottom: '1.5rem',
                    textAlign: 'center'
                }}>
                    <h3 style={{
                        color: 'var(--color-text)',
                        fontSize: '0.9rem',
                        fontWeight: 600,
                        marginBottom: '1rem'
                    }}>
                        Step 1: Scan QR Code
                    </h3>

                    <div style={{
                        background: '#fff',
                        padding: '1rem',
                        borderRadius: 'var(--radius-sm)',
                        display: 'inline-block',
                        marginBottom: '1rem'
                    }}>
                        {qrCode ? (
                            <img src={qrCode} alt="QR Code" style={{ width: '200px', height: '200px' }} />
                        ) : (
                            <div style={{ width: '200px', height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <span className="loading-spinner" style={{ borderColor: '#000', borderTopColor: 'transparent' }}></span>
                            </div>
                        )}
                    </div>

                    <p style={{
                        color: 'var(--color-text-muted)',
                        fontSize: '0.85rem',
                        margin: '0 0 0.5rem 0'
                    }}>
                        Or enter this key manually:
                    </p>
                    <code style={{
                        background: 'var(--color-bg)',
                        padding: '0.5rem 1rem',
                        borderRadius: '4px',
                        color: 'var(--color-accent-2)',
                        fontFamily: 'monospace',
                        fontSize: '0.9rem',
                        display: 'inline-block'
                    }}>
                        {secret}
                    </code>
                </div>

                <form onSubmit={handleVerify}>
                    <div style={{
                        background: 'var(--color-surface-2)',
                        border: '1px solid var(--color-border)',
                        borderRadius: 'var(--radius-md)',
                        padding: '1.5rem',
                        marginBottom: '1.5rem'
                    }}>
                        <h3 style={{
                            color: 'var(--color-text)',
                            fontSize: '0.9rem',
                            fontWeight: 600,
                            marginBottom: '1rem'
                        }}>
                            Step 2: Enter Verification Code
                        </h3>

                        <div className="form-group" style={{ marginBottom: 0 }}>
                            <label htmlFor="code">6-Digit Code from App</label>
                            <input
                                type="text"
                                id="code"
                                name="code"
                                placeholder="000000"
                                value={verificationCode}
                                onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                maxLength="6"
                                pattern="[0-9]{6}"
                                required
                                disabled={isLoading}
                                style={{
                                    textAlign: 'center',
                                    fontSize: '1.5rem',
                                    letterSpacing: '0.5rem',
                                    fontFamily: 'monospace'
                                }}
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={isLoading || verificationCode.length !== 6}
                        className="submit-btn"
                    >
                        {isLoading && <span className="loading-spinner"></span>}
                        {isLoading ? 'Verifying...' : 'Verify & Enable 2FA'}
                    </button>
                </form>

                <p className="switch-auth">
                    <button
                        onClick={() => navigate('/dashboard')}
                        className="link-btn"
                        style={{ background: 'none', border: 'none' }}
                    >
                        Skip for now
                    </button>
                </p>
            </div>
        </div>
    );
};

export default TwoFactorSetup;
