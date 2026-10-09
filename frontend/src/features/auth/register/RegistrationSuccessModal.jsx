import React, { useState } from 'react';
import { authAPI } from '../../../services/api';

// Shown after a successful registration. The account is inactive until the emailed link is
// opened, so the only way forward is the login page (there is no session to continue with).
const RegistrationSuccessModal = ({ email, onLogin }) => {
    const [resendState, setResendState] = useState(null); // { type: 'success' | 'error', text }
    const [resending, setResending] = useState(false);

    const handleResend = async () => {
        setResending(true);
        setResendState(null);
        try {
            await authAPI.resendVerification(email);
            setResendState({ type: 'success', text: 'Verification email sent again.' });
        } catch (err) {
            // 429: "Please wait N seconds..." (one resend every 2 minutes), 503: mail server down
            setResendState({
                type: 'error',
                text: err.response?.data?.detail || 'Could not resend the email. Please try again later.',
            });
        } finally {
            setResending(false);
        }
    };

    return (
        <div className="ui-overlay" role="dialog" aria-modal="true" aria-labelledby="registered-title">
            <div className="ui-modal" style={{ textAlign: 'center' }}>
                <div className="ui-empty-icon" style={{ opacity: 1 }}>✉️</div>
                <h2 id="registered-title" className="ui-title" style={{ fontSize: '1.4rem' }}>
                    Successfully registered!
                </h2>
                <p className="ui-muted" style={{ lineHeight: 1.6 }}>
                    We sent a verification link to <strong className="ui-strong">{email}</strong>.
                    Please open it to verify your email address, then log in.
                </p>

                {resendState && (
                    <div className={`ui-alert ${resendState.type === 'success' ? 'tone-green' : 'tone-red'}`}>
                        {resendState.text}
                    </div>
                )}

                <div className="ui-stack" style={{ marginTop: '1.25rem' }}>
                    <button type="button" className="ui-btn ui-btn--block ui-btn--lg" onClick={onLogin}>
                        Go to Login
                    </button>
                    <button type="button" className="ui-btn ui-btn--ghost ui-btn--block" onClick={handleResend} disabled={resending}>
                        {resending ? 'Sending...' : "Didn't get it? Resend email"}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default RegistrationSuccessModal;
