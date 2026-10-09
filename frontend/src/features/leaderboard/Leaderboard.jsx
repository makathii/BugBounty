import React, { useState, useEffect, useCallback } from 'react';
import './leaderboard.css';
import { leaderboardAPI } from '../../services/api';
import LevelChip from '../../components/levels/LevelChip';
import Character from '../../components/character/Character';

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const DEFAULT_LIMIT = 50;

const PERIOD_OPTIONS = [
    { value: 'all',     label: 'All time' },
    { value: 'monthly', label: '30 days'  },
    { value: 'weekly',  label: '7 days'   },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------
function StatCards({ total, count, me, meRank }) {
    return (
        <div className="lb-stats-row">
            <div className="lb-stat-card purple">
                <div className="lb-stat-label">My rank</div>
                <div className="lb-stat-value">{meRank != null ? `#${meRank}` : '—'}</div>
                <div className="lb-stat-sub">{me ? `${me.total_points.toLocaleString()} pts` : 'not ranked'}</div>
            </div>
            <div className="lb-stat-card">
                <div className="lb-stat-label">Researchers</div>
                <div className="lb-stat-value">{count}</div>
                <div className="lb-stat-sub">{total.toLocaleString()} pts total</div>
            </div>
            <div className="lb-stat-card green">
                <div className="lb-stat-label">Top score</div>
                <div className="lb-stat-value">
                    {me && meRank === 1 ? me.total_points.toLocaleString() : '—'}
                </div>
                <div className="lb-stat-sub">{me && meRank === 1 ? "that's you 🎉" : 'keep hunting'}</div>
            </div>
        </div>
    );
}

function Podium({ rows }) {
    if (rows.length === 0) return null;

    // visual order: 2nd | 1st | 3rd
    const slots =
        rows.length >= 3
            ? [
                { row: rows[1], cls: 'second', emoji: '🥈' },
                { row: rows[0], cls: 'first',  emoji: '🥇' },
                { row: rows[2], cls: 'third',  emoji: '🥉' },
            ]
            : rows.map((r, i) => ({
                row: r,
                cls:   ['first', 'second', 'third'][i],
                emoji: ['🥇', '🥈', '🥉'][i],
            }));

    return (
        <div className="lb-podium">
            {slots.map(({ row, cls, emoji }) => (
                <div key={row.researcher_id} className={`lb-pod lb-pod-${cls}`}>
                    <div className="lb-pod-emoji">{emoji}</div>
                    <div style={{ display: 'flex', justifyContent: 'center' }}>
                        <Character loadout={row.loadout} size={52} label={`${row.username}'s character`} />
                    </div>
                    <div className="lb-pod-name">{row.username}</div>
                    <LevelChip level={row.level} title={row.level_title} />
                    <div className="lb-pod-pts">{row.total_points.toLocaleString()}</div>
                    <div className="lb-pod-sub">{row.report_count} reports</div>
                </div>
            ))}
        </div>
    );
}

function EntryRow({ row, rank, isMe }) {
    return (
        <div className={`lb-entry${isMe ? ' lb-entry-me' : ''}`}>
            <div className={`lb-rank${rank <= 3 ? ' lb-rank-top' : ''}`}>{rank}</div>

            <div className="lb-user-cell">
                <Character loadout={row.loadout} size={34} label={`${row.username}'s character`} />
                <span className="lb-username">{row.username}</span>
                <LevelChip level={row.level} title={row.level_title} />
                {isMe && <span className="lb-you-tag">you</span>}
            </div>

            <div className="lb-pts-cell">{row.total_points.toLocaleString()}</div>
            <div className="lb-num-cell">{row.report_count}</div>
            <div className="lb-num-cell lb-last-awarded">
                {row.last_awarded_at
                    ? new Date(row.last_awarded_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
                    : '—'}
            </div>
        </div>
    );
}

function Skeleton() {
    return (
        <div className="lb-skeleton-list">
            {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="lb-skeleton-row">
                    <div className="lb-sk lb-sk-rank" />
                    <div className="lb-sk lb-sk-avatar" style={{ borderRadius: '50%' }} />
                    <div className="lb-sk lb-sk-name" />
                    <div className="lb-sk lb-sk-pts" />
                </div>
            ))}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export default function Leaderboard({ programId = null }) {
    const [period, setPeriod]    = useState('all');
    const [rows, setRows]        = useState([]);
    const [totalCount, setTotal] = useState(0);
    const [offset, setOffset]    = useState(0);
    const [loading, setLoading]  = useState(true);
    const [error, setError]      = useState(null);
    const [meData, setMeData]    = useState(null);  // { ranked, result? }

    const load = useCallback(async (newOffset = 0) => {
        setLoading(true);
        setError(null);
        try {
            const [board, me] = await Promise.all([
                leaderboardAPI.getLeaderboard({
                    period,
                    program: programId,
                    limit: DEFAULT_LIMIT,
                    offset: newOffset,
                }),
                leaderboardAPI.getMe({ period, program: programId }),
            ]);

            setRows(newOffset === 0
                ? board.data.results
                : prev => [...prev, ...board.data.results]
            );
            setTotal(board.data.count);
            setOffset(newOffset);
            setMeData(me.data);
        } catch (err) {
            setError(err.response?.data?.error || err.message);
        } finally {
            setLoading(false);
        }
    }, [period, programId]);

    useEffect(() => {
        load(0);
    }, [load]);

    const handlePeriod = (p) => {
        if (p === period) return;
        setPeriod(p);
        setRows([]);
    };

    const meRow    = meData?.ranked ? meData.result : null;
    const meRank   = meRow
        ? (rows.findIndex(r => r.researcher_id === meRow.researcher_id) + 1) || null
        : null;
    const totalPts = rows.reduce((a, r) => a + (r.total_points || 0), 0);
    const hasMore  = rows.length < totalCount;

    return (
        <div className="lb-wrap">
            {/* Header */}
            <div className="lb-top-bar">
                <h1 className="lb-title">
                    <span className="lb-live-badge">Live</span>
                    Leaderboard
                </h1>
                <div className="lb-pill-group">
                    {PERIOD_OPTIONS.map(opt => (
                        <button
                            key={opt.value}
                            className={`lb-pill${period === opt.value ? ' lb-pill-active' : ''}`}
                            onClick={() => handlePeriod(opt.value)}
                        >
                            {opt.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Error */}
            {error && (
                <div className="lb-error">
                    Could not load leaderboard — {error}.{' '}
                    <button className="lb-retry" onClick={() => load(0)}>Retry</button>
                </div>
            )}

            {/* Stats */}
            <StatCards total={totalPts} count={totalCount} me={meRow} meRank={meRank} />

            {/* Podium */}
            {!loading && rows.length > 0 && <Podium rows={rows.slice(0, 3)} />}

            {/* Period label */}
            <div className="lb-period-label">
                <span className="lb-period-dot" />
                {PERIOD_OPTIONS.find(o => o.value === period)?.label} rankings
            </div>

            {/* Table header */}
            <div className="lb-table-header">
                <span>#</span>
                <span>Researcher</span>
                <span className="r">Points</span>
                <span className="r">Reports</span>
                <span className="r">Last active</span>
            </div>

            {/* Rows */}
            {loading && rows.length === 0 ? (
                <Skeleton />
            ) : rows.length === 0 ? (
                <div className="lb-empty">No researchers ranked in this window yet.</div>
            ) : (
                <>
                    {rows.map((row, i) => (
                        <EntryRow
                            key={row.researcher_id}
                            row={row}
                            rank={i + 1}
                            isMe={meRow?.researcher_id === row.researcher_id}
                        />
                    ))}
                    {hasMore && (
                        <button
                            className="lb-load-more"
                            onClick={() => load(offset + DEFAULT_LIMIT)}
                            disabled={loading}
                        >
                            {loading ? 'Loading…' : `Load more (${totalCount - rows.length} remaining)`}
                        </button>
                    )}
                </>
            )}
        </div>
    );
}