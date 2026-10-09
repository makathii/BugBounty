import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { badgeAPI } from '../../services/api';
import { useAuth } from '../../features/auth/AuthContext';

const seenKey = (userId) => `bb_seen_badges_${userId}`;

const readSeen = (userId) => {
    try {
        const raw = localStorage.getItem(seenKey(userId));
        return raw === null ? null : JSON.parse(raw);
    } catch (e) { return null; }
};
const writeSeen = (userId, keys) => {
    try { localStorage.setItem(seenKey(userId), JSON.stringify(keys)); } catch (e) { /* storage blocked */ }
};

/**
 * Compact row of the researcher's earned badges. Badges earned since this browser last
 * looked are announced once ("New badge: First Blood"). The first ever visit just records
 * what is already earned, so nobody is greeted with a pile of old badges.
 */
const BadgeShelf = () => {
    const { user } = useAuth();
    const [data, setData] = useState(null);
    const [fresh, setFresh] = useState([]);

    useEffect(() => {
        let cancelled = false;
        badgeAPI.getBadges()
            .then((res) => { if (!cancelled) setData(res.data); })
            .catch(() => {});
        return () => { cancelled = true; };
    }, []);

    useEffect(() => {
        if (!data || !user?.id) return;
        const earned = data.badges.filter((b) => b.earned);
        const seen = readSeen(user.id);
        if (seen !== null) {
            setFresh(earned.filter((b) => !seen.includes(b.key)));
        }
        writeSeen(user.id, earned.map((b) => b.key));
    }, [data, user?.id]);

    if (!data) return null;
    const earned = data.badges.filter((b) => b.earned);

    return (
        <div className="ui-card ui-badge-shelf">
            {fresh.length > 0 && (
                <div className="ui-level-up" role="status">
                    <span>
                        🎉 New badge{fresh.length > 1 ? 's' : ''}:{' '}
                        {fresh.map((b) => `${b.icon} ${b.name}`).join(', ')}
                    </span>
                    <button className="ui-link-btn" onClick={() => setFresh([])}>Dismiss</button>
                </div>
            )}
            <div className="ui-row ui-row--between">
                <h3 className="ui-section-title" style={{ margin: 0 }}>
                    Badges <span className="ui-muted ui-small">{data.earned_count}/{data.total}</span>
                </h3>
                <Link to="/badges" className="ui-small">View all</Link>
            </div>
            {earned.length === 0 ? (
                <p className="ui-muted ui-small" style={{ margin: 0 }}>
                    No badges yet. Get a report accepted to earn your first one!
                </p>
            ) : (
                <div className="ui-row" style={{ flexWrap: 'wrap' }}>
                    {earned.map((b) => (
                        <span key={b.key} className="ui-badge-icon" title={`${b.name}: ${b.description}`}>
                            {b.icon}
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
};

export default BadgeShelf;
