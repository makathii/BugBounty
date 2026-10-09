import React, { useState, useEffect, useCallback } from 'react';
import { reportAPI } from '../../services/api';
import Character from '../../components/character/Character';

const errorText = (error, fallback) => {
    const data = error?.response?.data;
    if (!data) return fallback;
    if (typeof data === 'string') return data;
    return data.detail || data.text?.[0] || data.parent || fallback;
};

// Composer used for new comments, replies and edits.
const CommentForm = ({ initial = '', allowInternal = false, forceInternal = false,
                       submitLabel, onSubmit, onCancel, placeholder }) => {
    const [text, setText] = useState(initial);
    const [internal, setInternal] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');

    const submit = async () => {
        if (!text.trim()) return;
        setBusy(true);
        setError('');
        try {
            await onSubmit(text, forceInternal || internal);
            setText('');
            setInternal(false);
        } catch (e) {
            setError(errorText(e, 'Could not save the comment.'));
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="ui-comment-form">
            <textarea
                className="ui-textarea"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={placeholder}
                rows="3"
                maxLength={5000}
            />
            {error && <div className="ui-muted ui-small" style={{ color: '#f87171' }}>{error}</div>}
            <div className="ui-row ui-row--between" style={{ marginTop: '0.5rem' }}>
                {allowInternal && !forceInternal ? (
                    <label className="ui-check">
                        <input type="checkbox" checked={internal} onChange={(e) => setInternal(e.target.checked)} />
                        Internal note (staff only)
                    </label>
                ) : <span />}
                <div className="ui-row">
                    {onCancel && (
                        <button className="ui-btn ui-btn--ghost ui-btn--sm" onClick={onCancel} disabled={busy}>
                            Cancel
                        </button>
                    )}
                    <button className="ui-btn ui-btn--sm" onClick={submit} disabled={busy || !text.trim()}>
                        {busy ? 'Saving...' : submitLabel}
                    </button>
                </div>
            </div>
        </div>
    );
};

const Comment = ({ comment, canModerate, onReply, onEdit, onDelete }) => {
    const [mode, setMode] = useState(null); // 'reply' | 'edit' | null
    const close = () => setMode(null);

    const classes = ['ui-comment'];
    if (comment.is_internal) classes.push('ui-comment--internal');
    if (comment.is_deleted) classes.push('ui-comment--deleted');

    return (
        <div className={classes.join(' ')}>
            <div className="ui-row ui-row--between" style={{ marginBottom: '0.4rem' }}>
                <span className="ui-row">
                    <Character
                        loadout={comment.author_loadout}
                        size={32}
                        label={`${comment.author || 'deleted user'}'s character`}
                    />
                    <strong className="ui-strong">{comment.author || 'deleted user'}</strong>
                    {comment.is_internal && <span className="ui-badge tone-yellow">Internal</span>}
                </span>
                <span className="ui-muted ui-small">
                    {new Date(comment.created_at).toLocaleString()}
                    {comment.edited_at && ' (edited)'}
                </span>
            </div>

            {comment.is_deleted ? (
                <p className="ui-pre">[comment deleted]</p>
            ) : mode === 'edit' ? (
                <CommentForm
                    initial={comment.text}
                    submitLabel="Save"
                    onCancel={close}
                    onSubmit={async (text) => { await onEdit(comment.id, text); close(); }}
                />
            ) : (
                <p className="ui-pre">{comment.text}</p>
            )}

            {!comment.is_deleted && mode !== 'edit' && (
                <div className="ui-comment-actions">
                    <button className="ui-link-btn" onClick={() => setMode(mode === 'reply' ? null : 'reply')}>Reply</button>
                    {comment.can_edit && <button className="ui-link-btn" onClick={() => setMode('edit')}>Edit</button>}
                    {comment.can_delete && (
                        <button
                            className="ui-link-btn ui-link-btn--danger"
                            onClick={() => window.confirm('Delete this comment?') && onDelete(comment.id)}
                        >
                            Delete
                        </button>
                    )}
                </div>
            )}

            {mode === 'reply' && (
                <CommentForm
                    allowInternal={canModerate}
                    forceInternal={comment.is_internal}
                    submitLabel="Reply"
                    placeholder={`Reply to ${comment.author || 'comment'}...`}
                    onCancel={close}
                    onSubmit={async (text, internal) => { await onReply(text, internal, comment.id); close(); }}
                />
            )}

            {comment.replies?.length > 0 && (
                <div className="ui-comment-replies">
                    {comment.replies.map((reply) => (
                        <Comment
                            key={reply.id}
                            comment={reply}
                            canModerate={canModerate}
                            onReply={onReply}
                            onEdit={onEdit}
                            onDelete={onDelete}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};

/**
 * Threaded comments for a report. `canModerate` (Triager/Admin) unlocks internal notes.
 * `onChange` lets the parent refresh things that depend on comments (the activity log).
 */
const CommentThread = ({ reportId, canModerate, onChange }) => {
    const [comments, setComments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState('');

    const load = useCallback(async () => {
        try {
            const response = await reportAPI.getComments(reportId);
            setComments(response.data);
            setLoadError('');
        } catch (e) {
            setLoadError(errorText(e, 'Failed to load comments.'));
        } finally {
            setLoading(false);
        }
    }, [reportId]);

    useEffect(() => { load(); }, [load]);

    const refresh = async () => {
        await load();
        if (onChange) onChange();
    };

    const create = async (text, internal, parent = null) => {
        await reportAPI.addComment(reportId, { text, is_internal: internal, parent });
        await refresh();
    };
    const edit = async (commentId, text) => {
        await reportAPI.editComment(reportId, commentId, { text });
        await refresh();
    };
    const remove = async (commentId) => {
        try {
            await reportAPI.deleteComment(reportId, commentId);
        } catch (e) {
            window.alert(errorText(e, 'Could not delete the comment.'));
        }
        await refresh();
    };

    return (
        <div>
            <CommentForm
                allowInternal={canModerate}
                submitLabel="Add Comment"
                placeholder="Add a comment..."
                onSubmit={(text, internal) => create(text, internal)}
            />

            <hr className="ui-divider" />

            {loading ? (
                <p className="ui-muted">Loading comments...</p>
            ) : loadError ? (
                <p className="ui-muted" style={{ color: '#f87171' }}>{loadError}</p>
            ) : comments.length > 0 ? (
                <div className="ui-thread">
                    {comments.map((comment) => (
                        <Comment
                            key={comment.id}
                            comment={comment}
                            canModerate={canModerate}
                            onReply={create}
                            onEdit={edit}
                            onDelete={remove}
                        />
                    ))}
                </div>
            ) : (
                <p className="ui-empty" style={{ padding: '1rem' }}>No comments yet. Be the first to comment!</p>
            )}
        </div>
    );
};

export default CommentThread;
