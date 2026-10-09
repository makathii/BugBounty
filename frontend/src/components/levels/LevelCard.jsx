import React, { useState, useEffect } from 'react';
import { levelAPI } from '../../services/api';
import { useAuth } from '../../features/auth/AuthContext';

const seenKey = (userId) => `bb_last_level_${userId}`;

// Remember the highest level this browser has already celebrated, per user.
const readSeen = (userId) => {
    try { return Number(localStorage.getItem(seenKey(userId))) || 0; } catch (e) { return 0; }
};
const writeSeen = (userId, level) => {
    try { localStorage.setItem(seenKey(userId), String(level)); } catch (e) { /* storage blocked: skip */ }
};

/**
 * The researcher's level with a progress bar to the next one. When the level is higher
 * than the last one this browser saw, a one-time "Level up!" banner is shown.
 * `level` can be passed in (e.g. from /wallet/); otherwise it is fetched.
 */
const LevelCard = ({ level: provided }) => {
    const { user } = useAuth();
    const [fetched, setFetched] = useState(null);
    const [celebrate, setCelebrate] = useState(false);
    const info = provided || fetched;

    useEffect(() => {
        if (provided) return undefined;
        let cancelled = false;
        levelAPI.getMine()
            .then((res) => { if (!cancelled) setFetched(res.data); })
            .catch(() => {});
        return () => { cancelled = true; };
    }, [provided]);

    useEffect(() => {
        if (!info || !user?.id) return;
        const seen = readSeen(user.id);
        // First visit (seen = 0) only records the level; celebrating needs a real step up.
        if (seen > 0 && info.level > seen) setCelebrate(true);
        if (info.level > seen) writeSeen(user.id, info.level);
    }, [info, user?.id]);

    if (!info) return null;

    const percent = Math.round(info.progress * 100);
    return (
        <div className="ui-card ui-level-card">
            {celebrate && (
                <div className="ui-level-up" role="status">
                    <span>🎉 Level up! You're now a <strong>{info.title}</strong>!</span>
                    <button className="ui-link-btn" onClick={() => setCelebrate(false)}>Dismiss</button>
                </div>
            )}
            <div className="ui-row ui-row--between">
                <div>
                    <div className="ui-eyebrow">Level {info.level}</div>
                    <div className="ui-level-title">{info.title}</div>
                </div>
                <div className="ui-muted ui-small" style={{ textAlign: 'right' }}>
                    {info.next_title
                        ? <>{info.points_to_next.toLocaleString()} pts to <strong>{info.next_title}</strong></>
                        : 'Max level reached!'}
                </div>
            </div>
            <div
                className="ui-progress"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={percent}
                aria-label={`Progress to ${info.next_title || 'max level'}`}
            >
                <div className="ui-progress-bar" style={{ width: `${percent}%` }} />
            </div>
        </div>
    );
};

export default LevelCard;
