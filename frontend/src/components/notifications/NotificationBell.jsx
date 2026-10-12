import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { notificationAPI } from '../../services/api';
import { timeAgo } from '../../utils/time';

const POLL_MS = 60000;
const SHOWN = 8;

export const NotificationItem = ({ note, onOpen }) => (
    <button type="button" className={`ui-note ${note.read ? '' : 'ui-note--unread'}`} onClick={() => onOpen(note)}>
        <span className="ui-note-title">{note.title}</span>
        {note.message && <span className="ui-note-text">{note.message}</span>}
        <span className="ui-note-time">{timeAgo(note.created_at)}</span>
    </button>
);

// The bell in the navbar: unread count (polled), and a dropdown with the latest notifications.
const NotificationBell = () => {
    const navigate = useNavigate();
    const [unread, setUnread] = useState(0);
    const [open, setOpen] = useState(false);
    const [notes, setNotes] = useState(null);
    const [failed, setFailed] = useState(false);
    const wrapper = useRef(null);
    // Bumped whenever the user changes the count locally, so an older server answer that was
    // still in flight cannot bring back a number that is already out of date.
    const edits = useRef(0);

    const refreshCount = useCallback(async () => {
        const seen = edits.current;
        try {
            const { data } = await notificationAPI.getUnreadCount();
            if (seen === edits.current) setUnread(data.unread_count || 0);
        } catch (e) {
            // offline or logged out: keep the last number, try again next time
        }
    }, []);

    useEffect(() => {
        refreshCount();
        const timer = setInterval(refreshCount, POLL_MS);
        const onVisible = () => { if (!document.hidden) refreshCount(); };
        document.addEventListener('visibilitychange', onVisible);
        return () => { clearInterval(timer); document.removeEventListener('visibilitychange', onVisible); };
    }, [refreshCount]);

    useEffect(() => {
        if (!open) return undefined;
        const onDown = (e) => { if (wrapper.current && !wrapper.current.contains(e.target)) setOpen(false); };
        const onKey = (e) => { if (e.key === 'Escape') setOpen(false); };
        document.addEventListener('mousedown', onDown);
        document.addEventListener('keydown', onKey);
        return () => { document.removeEventListener('mousedown', onDown); document.removeEventListener('keydown', onKey); };
    }, [open]);

    const toggle = async () => {
        const next = !open;
        setOpen(next);
        if (!next) return;
        setFailed(false);
        try {
            const { data } = await notificationAPI.getAll();
            setNotes((data.results || data).slice(0, SHOWN));
        } catch (e) {
            setFailed(true);
            setNotes([]);
        }
        refreshCount();
    };

    const openNote = async (note) => {
        setOpen(false);
        if (!note.read) {
            edits.current += 1;
            setNotes((list) => (list || []).map((n) => (n.id === note.id ? { ...n, read: true } : n)));
            setUnread((n) => Math.max(0, n - 1));
            // wait for it: the next page may mount a new bell that asks the server for the count
            await notificationAPI.markRead(note.id).catch(() => refreshCount());
        }
        if (note.link) navigate(note.link);
    };

    const markAll = async () => {
        edits.current += 1;
        setNotes((list) => (list || []).map((n) => ({ ...n, read: true })));
        setUnread(0);
        try { await notificationAPI.markAllRead(); } catch (e) { refreshCount(); }
    };

    return (
        <div className="ui-bell" ref={wrapper}>
            <button type="button" className="ui-bell-btn" onClick={toggle} aria-expanded={open}
                    aria-label={unread ? `Notifications, ${unread} unread` : 'Notifications'}>
                <span aria-hidden="true">🔔</span>
                {unread > 0 && <span className="ui-bell-count" data-testid="bell-count">{unread > 99 ? '99+' : unread}</span>}
            </button>
            {open && (
                <div className="ui-bell-panel" role="region" aria-label="Notifications">
                    <div className="ui-bell-head">
                        <strong>Notifications</strong>
                        <button type="button" className="ui-link-btn" onClick={markAll} disabled={unread === 0}>Mark all read</button>
                    </div>
                    <div className="ui-bell-list">
                        {notes === null && <p className="ui-muted ui-small" style={{ padding: '1rem' }}>Loading…</p>}
                        {failed && <p className="ui-muted ui-small" style={{ padding: '1rem' }}>Could not load notifications.</p>}
                        {notes && !failed && notes.length === 0 && (
                            <p className="ui-muted ui-small" style={{ padding: '1rem' }}>Nothing yet. Invitations, decisions and comments show up here.</p>
                        )}
                        {notes && notes.map((n) => <NotificationItem key={n.id} note={n} onOpen={openNote} />)}
                    </div>
                    <div className="ui-bell-foot">
                        <Link to="/notifications" className="ui-small" onClick={() => setOpen(false)}>See all notifications</Link>
                    </div>
                </div>
            )}
        </div>
    );
};

export default NotificationBell;
