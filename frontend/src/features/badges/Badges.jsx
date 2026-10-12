import React, { useState, useEffect } from 'react';
import { badgeAPI } from '../../services/api';

const Badges = () => {
    const [data, setData] = useState(null);
    const [error, setError] = useState('');

    useEffect(() => {
        badgeAPI.getBadges()
            .then((res) => setData(res.data))
            .catch(() => setError('Could not load your badges. Please try again.'));
    }, []);

    if (error) {
        return (
            <div className="ui-page ui-page--narrow">
                <div className="ui-card ui-empty"><p>{error}</p></div>
            </div>
        );
    }
    if (!data) {
        return (
            <div className="ui-loading">
                <div className="ui-spinner" />
                <p>Loading badges...</p>
            </div>
        );
    }

    return (
        <div className="ui-page">
            <header className="ui-page-header">
                <h1 className="ui-title">Badges</h1>
                <p className="ui-muted">
                    {data.earned_count} of {data.total} earned. Badges are yours to keep, even if a
                    report is reviewed again later.
                </p>
            </header>

            <div className="ui-grid ui-grid--cards">
                {data.badges.map((badge) => {
                    const { current, target } = badge.progress;
                    const percent = Math.round((current / target) * 100);
                    return (
                        <div
                            key={badge.key}
                            className={`ui-card ui-badge-card${badge.earned ? ' is-earned' : ' is-locked'}`}
                        >
                            <div className="ui-badge-art" aria-hidden="true">{badge.icon}</div>
                            <div className="ui-strong">{badge.name}</div>
                            <p className="ui-muted ui-small" style={{ margin: 0 }}>{badge.description}</p>
                            {badge.earned ? (
                                <div className="ui-tone-text tone-green ui-small ui-strong">
                                    Earned {new Date(badge.awarded_at).toLocaleDateString()}
                                </div>
                            ) : (
                                <>
                                    <div
                                        className="ui-progress"
                                        role="progressbar"
                                        aria-valuemin={0}
                                        aria-valuemax={target}
                                        aria-valuenow={current}
                                        aria-label={`${badge.name} progress`}
                                    >
                                        <div className="ui-progress-bar" style={{ width: `${percent}%` }} />
                                    </div>
                                    <div className="ui-muted ui-small">{current} / {target}</div>
                                </>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default Badges;
