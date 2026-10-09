import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { walletAPI } from '../../services/api';
import { formatPoints } from '../../utils/points';
import LevelCard from '../../components/levels/LevelCard';

const PAGE_SIZE = 25;

const KIND_TONE = { purchase: 'tone-orange', refund: 'tone-green', adjustment: 'tone-blue' };

const Wallet = () => {
    const [wallet, setWallet] = useState(null);
    const [transactions, setTransactions] = useState([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [error, setError] = useState('');

    const load = useCallback(async () => {
        try {
            const [walletRes, txRes] = await Promise.all([
                walletAPI.getWallet(),
                walletAPI.getTransactions({ limit: PAGE_SIZE, offset: 0 }),
            ]);
            setWallet(walletRes.data);
            setTransactions(txRes.data.results);
            setTotal(txRes.data.count);
            setError('');
        } catch (e) {
            setError('Could not load your wallet. Please try again.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const loadMore = async () => {
        setLoadingMore(true);
        try {
            const res = await walletAPI.getTransactions({ limit: PAGE_SIZE, offset: transactions.length });
            setTransactions((prev) => [...prev, ...res.data.results]);
            setTotal(res.data.count);
        } catch (e) {
            setError('Could not load more activity.');
        } finally {
            setLoadingMore(false);
        }
    };

    if (loading) {
        return (
            <div className="ui-loading">
                <div className="ui-spinner" />
                <p>Loading wallet...</p>
            </div>
        );
    }

    if (error && !wallet) {
        return (
            <div className="ui-page ui-page--narrow">
                <div className="ui-card ui-empty">
                    <p>{error}</p>
                    <button className="ui-btn" onClick={load}>Retry</button>
                </div>
            </div>
        );
    }

    const cards = [
        { label: 'Balance', value: formatPoints(wallet.balance), tone: 'accent' },
        { label: 'Lifetime Earned', value: formatPoints(wallet.lifetime_earned), tone: 'green' },
        { label: 'Spent', value: formatPoints(wallet.total_spent), tone: 'orange' },
    ];

    return (
        <div className="ui-page">
            <header className="ui-page-header">
                <h1 className="ui-title">My Wallet</h1>
                <p className="ui-muted">
                    Earn points for every accepted report. Spending points never changes your
                    leaderboard rank, which is based on lifetime points.
                </p>
            </header>

            <LevelCard level={wallet.level} />

            <div className="ui-grid ui-grid--stats">
                {cards.map(({ label, value, tone }) => (
                    <div key={label} className={`ui-stat tone-${tone}`}>
                        <div className="ui-stat-value">{value}</div>
                        <div className="ui-stat-label">{label}</div>
                    </div>
                ))}
            </div>

            <div className="ui-card">
                <h3 className="ui-section-title">Activity</h3>
                {transactions.length === 0 ? (
                    <div className="ui-empty" style={{ padding: '1.5rem' }}>
                        <div className="ui-empty-icon">🪙</div>
                        <p>
                            Nothing spent yet. Your balance grows with every accepted report
                            {' '}— <Link to="/programs">find a program</Link> to start earning.
                            The store is coming soon!
                        </p>
                    </div>
                ) : (
                    <div className="ui-stack">
                        {transactions.map((tx) => (
                            <div key={tx.id} className="ui-card--inset ui-row ui-row--between">
                                <div>
                                    <div className="ui-strong">{tx.reason}</div>
                                    <div className="ui-muted ui-small">
                                        <span className={`ui-badge ${KIND_TONE[tx.kind] || 'tone-gray'}`}>{tx.kind_display}</span>
                                        {' '}{new Date(tx.created_at).toLocaleString()}
                                    </div>
                                </div>
                                <div
                                    className={`ui-strong ui-tone-text ${tx.amount < 0 ? 'tone-orange' : 'tone-green'}`}
                                    style={{ whiteSpace: 'nowrap' }}
                                >
                                    {tx.amount > 0 ? '+' : ''}{tx.amount.toLocaleString()} pts
                                </div>
                            </div>
                        ))}
                        {transactions.length < total && (
                            <button className="ui-btn ui-btn--ghost" onClick={loadMore} disabled={loadingMore}>
                                {loadingMore ? 'Loading...' : 'Show more'}
                            </button>
                        )}
                    </div>
                )}
                {error && <p className="ui-muted ui-small" style={{ color: '#f87171' }}>{error}</p>}
            </div>
        </div>
    );
};

export default Wallet;
