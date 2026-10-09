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
                <div className="register-container tf-medium">
                    <div className="auth-header">
                        <h2>Save Your Backup Codes</h2>
                        <p>Store these codes in a safe place. Each can only be used once.</p>
                    </div>

                    <div className="success-message">✓ Two-Factor Authentication Enabled</div>

                    <div className="tf-panel">
                        <div className="tf-codes">
                            {backupCodes.map((code, idx) => (
                                <div key={idx}>{code}</div>
                            ))}
                        </div>
                    </div>

                    <button type="button" className="tf-btn tf-btn--block" onClick={downloadBackupCodes}>
                        📥 Download Backup Codes
                    </button>

                    <button type="button" className="submit-btn" onClick={handleComplete}>
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
                        {qrCode ? (
                            <img src={qrCode} alt="QR Code" />
                        ) : (
                            <div className="tf-qr-placeholder">
                                <span className="loading-spinner"></span>
                            </div>
                        )}
                    </div>

                    <p className="tf-text" style={{ marginBottom: '0.5rem' }}>Or enter this key manually:</p>
                    <code className="tf-secret">{secret}</code>
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
                                required
                                disabled={isLoading}
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
                    <button type="button" className="link-btn" onClick={() => navigate('/dashboard')}>
                        Skip for now
                    </button>
                </p>
            </div>
        </div>
    );
};

export default TwoFactorSetup;
