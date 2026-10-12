import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { notificationAPI } from '../../services/api';
import { NotificationItem } from '../../components/notifications/NotificationBell';

// The full list behind the bell.
const Notifications = () => {
    const navigate = useNavigate();
    const [notes, setNotes] = useState(null);
    const [error, setError] = useState('');

    useEffect(() => {
        notificationAPI.getAll()
            .then(({ data }) => setNotes(data.results || data))
            .catch(() => { setError('Could not load your notifications.'); setNotes([]); });
    }, []);

    const open = async (note) => {
        if (!note.read) {
            setNotes((list) => list.map((n) => (n.id === note.id ? { ...n, read: true } : n)));
            await notificationAPI.markRead(note.id).catch(() => {});
        }
        if (note.link) navigate(note.link);
    };

    const markAll = async () => {
        setNotes((list) => list.map((n) => ({ ...n, read: true })));
        try { await notificationAPI.markAllRead(); } catch (e) { setError('Could not mark them as read.'); }
    };

    if (notes === null) return <div className="ui-loading"><div className="ui-spinner" /><p>Loading...</p></div>;

    return (
        <div className="ui-page ui-page--narrow">
            <header className="ui-page-header ui-row ui-row--between">
                <div>
                    <h1 className="ui-title">Notifications</h1>
                    <p className="ui-muted">Invitations, report decisions and new comments.</p>
                </div>
                <button className="ui-btn ui-btn--ghost ui-btn--sm" onClick={markAll} disabled={!notes.some((n) => !n.read)}>
                    Mark all read
                </button>
            </header>
            {error && <div className="ui-alert tone-red" role="alert">{error}</div>}
            {notes.length === 0 ? (
                <div className="ui-card ui-empty"><p>You're all caught up.</p></div>
            ) : (
                <div className="ui-card ui-card--flush">
                    {notes.map((n) => <NotificationItem key={n.id} note={n} onOpen={open} />)}
                </div>
            )}
        </div>
    );
};

export default Notifications;
