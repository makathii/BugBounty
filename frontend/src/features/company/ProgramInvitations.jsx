import React, { useState, useEffect, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import api, { invitationAPI } from '../../services/api';
import { statusTone } from '../../utils/tones';

const firstError = (value) => (Array.isArray(value) ? value[0] : value);

const errorText = (error, fallback) => {
    const data = error?.response?.data;
    if (typeof data === 'string') return data;
    return firstError(data?.username) || firstError(data?.non_field_errors) || firstError(data?.message)
        || data?.error || data?.detail || fallback;
};

// A company invites researchers (by username) to one of its private programs.
const ProgramInvitations = () => {
    const { id } = useParams();
    const [program, setProgram] = useState(null);
    const [invitations, setInvitations] = useState(null);
    const [username, setUsername] = useState('');
    const [note, setNote] = useState('');
    const [sending, setSending] = useState(false);
    const [busy, setBusy] = useState(null);
    const [message, setMessage] = useState(null); // { type: 'success' | 'error', text }
    const [loadError, setLoadError] = useState('');

    const load = useCallback(async () => {
        try {
            const [programRes, invRes] = await Promise.all([api.get(`/programs/${id}/`), invitationAPI.list(id)]);
            setProgram(programRes.data);
            setInvitations(invRes.data.results ?? invRes.data);
            setLoadError('');
        } catch (e) {
            setLoadError(errorText(e, 'Could not load the invitations.'));
            setInvitations([]);
        }
    }, [id]);

    useEffect(() => { load(); }, [load]);

    const send = async (e) => {
        e.preventDefault();
        setSending(true);
        setMessage(null);
        const name = username.trim();
        try {
            await invitationAPI.send(id, { username: name, message: note });
            setMessage({ type: 'success', text: `Invitation sent to ${name}.` });
            setUsername('');
            setNote('');
            await load();
        } catch (err) {
            setMessage({ type: 'error', text: errorText(err, 'Could not send the invitation.') });
        } finally {
            setSending(false);
        }
    };

    const revoke = async (invitation) => {
        setBusy(invitation.id);
        setMessage(null);
        try {
            await invitationAPI.revoke(id, invitation.id);
            setMessage({ type: 'success', text: `The invitation for ${invitation.researcher.username} was revoked.` });
            await load();
        } catch (err) {
            setMessage({ type: 'error', text: errorText(err, 'Could not revoke the invitation.') });
        } finally {
            setBusy(null);
        }
    };

    if (invitations === null) {
        return <div className="ui-loading"><div className="ui-spinner" /><p>Loading invitations...</p></div>;
    }

    return (
        <div className="ui-page ui-page--narrow">
            <header className="ui-page-header">
                <Link to="/company/programs" className="ui-small">← My programs</Link>
                <h1 className="ui-title">Invitations{program ? `: ${program.name}` : ''}</h1>
                <p className="ui-muted">
                    Invite researchers to this private program. They get an email and can accept or decline
                    from their dashboard. Once they accept, they can see the targets and submit reports.
                </p>
            </header>

            {loadError && <div className="ui-alert tone-red" role="alert">{loadError}</div>}
            {message && (
                <div className={`ui-alert ${message.type === 'success' ? 'tone-green' : 'tone-red'}`} role="status">
                    {message.text}
                </div>
            )}

            <form className="ui-card ui-stack" onSubmit={send}>
                <h3 className="ui-section-title" style={{ margin: 0 }}>Invite a researcher</h3>
                <label className="ui-label" htmlFor="invite-username">Researcher's username</label>
                <input id="invite-username" className="ui-input" value={username} required autoComplete="off"
                       onChange={(e) => setUsername(e.target.value)} />
                <label className="ui-label" htmlFor="invite-note">Message (optional)</label>
                <textarea id="invite-note" className="ui-textarea" rows="2" value={note}
                          placeholder="Why you'd like them on this program"
                          onChange={(e) => setNote(e.target.value)} />
                <div>
                    <button className="ui-btn" type="submit" disabled={sending || !username.trim()}>
                        {sending ? 'Sending...' : 'Send invitation'}
                    </button>
                </div>
            </form>

            <h3 className="ui-section-title" style={{ marginTop: '2rem' }}>Sent invitations ({invitations.length})</h3>
            {invitations.length === 0 ? (
                <div className="ui-card ui-empty"><p>No invitations yet.</p></div>
            ) : (
                <div className="ui-stack">
                    {invitations.map((inv) => (
                        <div key={inv.id} className="ui-card" data-testid={`invitation-${inv.researcher.username}`}>
                            <div className="ui-row ui-row--between">
                                <strong className="ui-strong">{inv.researcher.username}</strong>
                                <span className={`ui-badge ${statusTone(inv.status)}`}>{inv.status_display || inv.status}</span>
                            </div>
                            {inv.message && <p className="ui-pre" style={{ margin: '0.75rem 0 0' }}>{inv.message}</p>}
                            {inv.status === 'pending' && (
                                <div style={{ marginTop: '1rem' }}>
                                    <button className="ui-btn ui-btn--danger ui-btn--sm" disabled={busy === inv.id}
                                            onClick={() => revoke(inv)}>Revoke</button>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default ProgramInvitations;
