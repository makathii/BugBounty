import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { profileAPI } from '../../services/api';
import { formatPoints } from '../../utils/points';
import Character from '../../components/character/Character';
import LevelChip from '../../components/levels/LevelChip';

const Stat = ({ label, value, tone }) => (
    <div className={`ui-stat tone-${tone}`}>
        <div className="ui-stat-value">{value}</div>
        <div className="ui-stat-label">{label}</div>
    </div>
);

// Your own bio and whether other researchers can open your page.
const OwnSettings = ({ initial, onSaved }) => {
    const [bio, setBio] = useState(initial.bio);
    const [isPublic, setIsPublic] = useState(initial.is_public);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState(null);

    const save = async (e) => {
        e.preventDefault();
        setSaving(true);
        setMessage(null);
        try {
            const { data } = await profileAPI.updateMySettings({ bio, is_public: isPublic });
            setMessage({ type: 'success', text: 'Saved.' });
            onSaved(data);
        } catch (err) {
            const detail = err.response?.data?.bio?.[0] || 'Could not save your profile.';
            setMessage({ type: 'error', text: detail });
        } finally {
            setSaving(false);
        }
    };

    return (
        <form className="ui-card ui-stack" onSubmit={save}>
            <h3 className="ui-section-title" style={{ margin: 0 }}>Your profile</h3>
            <div>
                <label className="ui-label" htmlFor="profile-bio">Short intro ({bio.length}/160)</label>
                <textarea id="profile-bio" className="ui-textarea" rows="2" maxLength={160} value={bio}
                          placeholder="What do you like to hunt?" onChange={(e) => setBio(e.target.value)} />
            </div>
            <label className="ui-row" style={{ gap: '0.6rem', alignItems: 'flex-start' }}>
                <input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} />
                <span>
                    Let other researchers open my profile page
                    <span className="ui-muted ui-small" style={{ display: 'block' }}>
                        The leaderboard still lists your username and points.
                    </span>
                </span>
            </label>
            {message && (
                <div className={`ui-alert ${message.type === 'success' ? 'tone-green' : 'tone-red'}`}
                     role="status" style={{ margin: 0 }}>{message.text}</div>
            )}
            <div><button className="ui-btn" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button></div>
        </form>
    );
};

// A researcher's public page: character, level, stats and the badges they have earned.
const ResearcherProfile = () => {
    const { username } = useParams();
    const [profile, setProfile] = useState(null);
    const [missing, setMissing] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        let cancelled = false;
        setProfile(null);
        setMissing(false);
        setError('');
        profileAPI.getResearcher(username)
            .then((res) => { if (!cancelled) setProfile(res.data); })
            .catch((err) => {
                if (cancelled) return;
                if (err.response?.status === 404) setMissing(true);
                else setError('Could not load this profile. Please try again.');
            });
        return () => { cancelled = true; };
    }, [username]);

    if (missing || error) {
        return (
            <div className="ui-page ui-page--narrow">
                <div className="ui-card ui-empty">
                    <p>{missing ? 'There is no researcher with that name.' : error}</p>
                    <Link to="/leaderboard" className="ui-btn ui-btn--ghost">Back to the leaderboard</Link>
                </div>
            </div>
        );
    }
    if (!profile) {
        return <div className="ui-loading"><div className="ui-spinner" /><p>Loading profile...</p></div>;
    }

    const { level, stats } = profile;
    return (
        <div className="ui-page">
            {!profile.is_public && (
                <div className="ui-alert tone-yellow" role="status">
                    {profile.is_self
                        ? 'Your profile is hidden: only you and the platform team can open this page.'
                        : 'This profile is hidden from other researchers.'}
                </div>
            )}

            <header className="ui-page-header ui-row" style={{ gap: '1.25rem' }}>
                <Character loadout={profile.loadout} size={140} label={`${profile.username}'s character`} />
                <div>
                    <h1 className="ui-title" style={{ marginBottom: '0.25rem' }}>{profile.username}</h1>
                    <div className="ui-row">
                        <LevelChip level={level.level} title={level.title} />
                        {profile.rank && <span className="ui-badge tone-yellow">Rank #{profile.rank}</span>}
                    </div>
                    {profile.bio && <p className="ui-pre" style={{ margin: '0.75rem 0 0' }}>{profile.bio}</p>}
                    <p className="ui-muted ui-small" style={{ margin: '0.5rem 0 0' }}>
                        Hunting since {new Date(profile.member_since).toLocaleDateString(undefined, { year: 'numeric', month: 'long' })}
                    </p>
                </div>
            </header>

            <div className="ui-grid ui-grid--stats">
                <Stat label="Lifetime points" value={formatPoints(profile.lifetime_points)} tone="accent" />
                <Stat label="Accepted reports" value={stats.accepted} tone="green" />
                <Stat label="Critical finds" value={stats.critical} tone="red" />
                <Stat label="Programs" value={stats.programs} tone="blue" />
            </div>

            <section className="ui-card ui-mb-lg" aria-label="Badges">
                <h3 className="ui-section-title">
                    Badges <span className="ui-muted ui-small">{profile.badges.length}/{profile.badge_total}</span>
                </h3>
                {profile.badges.length === 0 ? (
                    <p className="ui-muted ui-small" style={{ margin: 0 }}>No badges yet.</p>
                ) : (
                    <div className="ui-grid ui-grid--cards">
                        {profile.badges.map((b) => (
                            <div key={b.key} className="ui-badge-card is-earned" data-testid={`profile-badge-${b.key}`}>
                                <div className="ui-badge-art" aria-hidden="true">{b.icon}</div>
                                <div className="ui-strong">{b.name}</div>
                                <p className="ui-muted ui-small" style={{ margin: 0 }}>{b.description}</p>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {profile.is_self && (
                <OwnSettings
                    initial={{ bio: profile.bio, is_public: profile.is_public }}
                    onSaved={(s) => setProfile((p) => ({ ...p, bio: s.bio, is_public: s.is_public }))}
                />
            )}
        </div>
    );
};

export default ResearcherProfile;
