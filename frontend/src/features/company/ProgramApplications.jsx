import React, { useState, useEffect, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import api, { applicationAPI } from '../../services/api';
import { statusTone } from '../../utils/tones';

const errorText = (error, fallback) => {
    const data = error?.response?.data;
    return (typeof data === 'string' ? data : data?.error || data?.detail) || fallback;
};

// A company reviews the researchers who asked to join one of its private programs.
const ProgramApplications = () => {
    const { id } = useParams();
    const [program, setProgram] = useState(null);
    const [applications, setApplications] = useState(null);
    const [notes, setNotes] = useState({});
    const [busy, setBusy] = useState(null);
    const [message, setMessage] = useState(null); // { type: 'success' | 'error', text }
    const [loadError, setLoadError] = useState('');

    const load = useCallback(async () => {
        try {
            const [programRes, appsRes] = await Promise.all([api.get(`/programs/${id}/`), applicationAPI.list(id)]);
            setProgram(programRes.data);
            setApplications(appsRes.data.results ?? appsRes.data);
            setLoadError('');
        } catch (e) {
            setLoadError(errorText(e, 'Could not load the applications.'));
            setApplications([]);
        }
    }, [id]);

    useEffect(() => { load(); }, [load]);

    const decide = async (application, decision) => {
        setBusy(application.id);
        setMessage(null);
        try {
            const call = decision === 'approve' ? applicationAPI.approve : applicationAPI.reject;
            await call(id, application.id, notes[application.id] || '');
            setMessage({
                type: 'success',
                text: `${application.researcher.username} was ${decision === 'approve' ? 'approved' : 'rejected'}.`,
            });
            await load();
        } catch (e) {
            setMessage({ type: 'error', text: errorText(e, `Could not ${decision} the application.`) });
        } finally {
            setBusy(null);
        }
    };

    if (applications === null) {
        return <div className="ui-loading"><div className="ui-spinner" /><p>Loading applications...</p></div>;
    }

    const pending = applications.filter((a) => a.status === 'pending');
    const decided = applications.filter((a) => a.status !== 'pending');

    const Card = ({ application, showActions }) => (
        <div className="ui-card" data-testid={`application-${application.researcher.username}`}>
            <div className="ui-row ui-row--between">
                <strong className="ui-strong">{application.researcher.username}</strong>
                <span className={`ui-badge ${statusTone(application.status)}`}>{application.status_display || application.status}</span>
            </div>
            {application.message && <p className="ui-pre" style={{ margin: '0.75rem 0 0' }}>{application.message}</p>}
            {application.experience && (
                <p className="ui-muted ui-small" style={{ margin: '0.5rem 0 0' }}><strong>Experience:</strong> {application.experience}</p>
            )}
            {application.qualifications && (
                <p className="ui-muted ui-small" style={{ margin: '0.25rem 0 0' }}><strong>Qualifications:</strong> {application.qualifications}</p>
            )}
            {application.review_notes && !showActions && (
                <p className="ui-muted ui-small" style={{ margin: '0.5rem 0 0' }}><strong>Your note:</strong> {application.review_notes}</p>
            )}
            {showActions && (
                <div className="ui-stack" style={{ marginTop: '1rem' }}>
                    <textarea
                        className="ui-textarea"
                        rows="2"
                        placeholder="Optional note to the researcher"
                        value={notes[application.id] || ''}
                        onChange={(e) => setNotes((n) => ({ ...n, [application.id]: e.target.value }))}
                    />
                    <div className="ui-row">
                        <button className="ui-btn ui-btn--green ui-btn--sm" disabled={busy === application.id}
                                onClick={() => decide(application, 'approve')}>Approve</button>
                        <button className="ui-btn ui-btn--danger ui-btn--sm" disabled={busy === application.id}
                                onClick={() => decide(application, 'reject')}>Reject</button>
                    </div>
                </div>
            )}
        </div>
    );

    return (
        <div className="ui-page ui-page--narrow">
            <header className="ui-page-header">
                <Link to="/company/programs" className="ui-small">← My programs</Link>
                <h1 className="ui-title">Applications{program ? `: ${program.name}` : ''}</h1>
                <p className="ui-muted">
                    Researchers who asked to join this program. Approved researchers can submit reports to it.
                </p>
            </header>

            {loadError && <div className="ui-alert tone-red" role="alert">{loadError}</div>}
            {message && (
                <div className={`ui-alert ${message.type === 'success' ? 'tone-green' : 'tone-red'}`} role="status">
                    {message.text}
                </div>
            )}

            <h3 className="ui-section-title">Waiting for a decision ({pending.length})</h3>
            {pending.length === 0 ? (
                <div className="ui-card ui-empty"><p>No applications are waiting.</p></div>
            ) : (
                <div className="ui-stack">{pending.map((a) => <Card key={a.id} application={a} showActions />)}</div>
            )}

            {decided.length > 0 && (
                <>
                    <h3 className="ui-section-title" style={{ marginTop: '2rem' }}>Decided ({decided.length})</h3>
                    <div className="ui-stack">{decided.map((a) => <Card key={a.id} application={a} />)}</div>
                </>
            )}
        </div>
    );
};

export default ProgramApplications;
