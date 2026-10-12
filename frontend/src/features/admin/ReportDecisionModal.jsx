import React, { useState } from 'react';
import Modal from '../../components/ui/Modal';

const SEVERITIES = ['low', 'medium', 'high', 'critical'];
const MAX_BONUS = 1000;

// Accept or reject a triaged report (replaces the old browser prompt() boxes).
// onSubmit(data) resolves to an error message, or nothing when it worked.
const ReportDecisionModal = ({ mode, report, onSubmit, onClose }) => {
    const accepting = mode === 'accept';
    const [notes, setNotes] = useState('');
    const [bonus, setBonus] = useState('0');
    const [severity, setSeverity] = useState(report.severity || 'low');
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false);

    const submit = async (e) => {
        e.preventDefault();
        const text = notes.trim();
        if (!text) {
            setError(accepting ? 'Add a short note for the researcher.' : 'Tell the researcher why it was rejected.');
            return;
        }
        const data = accepting
            ? { verification_notes: text, severity, bonus_points: bonus === '' ? 0 : Number(bonus) }
            : { rejection_reason: text };
        if (accepting && !(Number.isInteger(data.bonus_points) && data.bonus_points >= 0 && data.bonus_points <= MAX_BONUS)) {
            setError(`Bonus points must be a whole number from 0 to ${MAX_BONUS}.`);
            return;
        }
        setBusy(true);
        setError('');
        const failure = await onSubmit(data);
        if (failure) {
            setError(failure);
            setBusy(false);
        }
    };

    return (
        <Modal title={`${accepting ? 'Accept' : 'Reject'} report`} onClose={onClose} busy={busy}
               footer={(
                   <>
                       <button type="button" className="ui-btn ui-btn--ghost" onClick={onClose} disabled={busy}>Cancel</button>
                       <button type="submit" form="decision-form" disabled={busy}
                               className={`ui-btn ${accepting ? 'ui-btn--green' : 'ui-btn--danger'}`}>
                           {busy ? 'Saving…' : accepting ? 'Accept report' : 'Reject report'}
                       </button>
                   </>
               )}>
            <form id="decision-form" className="ui-stack" onSubmit={submit} noValidate>
                <p className="ui-muted ui-small" style={{ margin: 0 }}>{report.title}</p>
                {error && <div className="ui-alert tone-red" role="alert" style={{ margin: 0 }}>{error}</div>}

                {accepting && (
                    <div>
                        <label className="ui-label" htmlFor="decision-severity">Severity (decides the base points)</label>
                        <select id="decision-severity" className="ui-select ui-select--block" value={severity}
                                onChange={(e) => setSeverity(e.target.value)}>
                            {SEVERITIES.map((s) => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}
                        </select>
                    </div>
                )}
                <div>
                    <label className="ui-label" htmlFor="decision-notes">
                        {accepting ? 'Verification notes' : 'Reason for rejecting'}
                    </label>
                    <textarea id="decision-notes" className="ui-textarea" rows="3" value={notes}
                              onChange={(e) => setNotes(e.target.value)} />
                </div>
                {accepting && (
                    <div>
                        <label className="ui-label" htmlFor="decision-bonus">Bonus points on top (optional, up to {MAX_BONUS})</label>
                        <input id="decision-bonus" className="ui-input ui-input--block" inputMode="numeric" value={bonus}
                               onChange={(e) => setBonus(e.target.value)} />
                    </div>
                )}
            </form>
        </Modal>
    );
};

export default ReportDecisionModal;
