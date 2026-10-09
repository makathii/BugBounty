import React, { useState, useEffect, useCallback, useRef } from 'react';
import { storeAPI } from '../../services/api';
import { formatPoints } from '../../utils/points';
import Character from '../../components/character/Character';

const RARITY_TONE = { common: 'tone-gray', rare: 'tone-blue', epic: 'tone-accent', legendary: 'tone-yellow' };
const SLOTS = [
    { value: '', label: 'All' },
    { value: 'hat', label: 'Hats' },
    { value: 'face', label: 'Faces' },
    { value: 'body', label: 'Bodies' },
    { value: 'pet', label: 'Pets' },
    { value: 'background', label: 'Backgrounds' },
];

// Friendly text for the API's purchase error codes.
const purchaseMessage = (error) => {
    const data = error.response?.data;
    switch (data?.code) {
        case 'insufficient_points':
            return `Not enough points: you have ${data.balance}, this costs ${data.needed}.`;
        case 'level_too_low':
            return `You need to be level ${data.required_level} for this (you are level ${data.level}).`;
        case 'already_owned':
            return 'You already own this item.';
        case 'item_unavailable':
            return 'This item is no longer for sale.';
        default:
            return data?.error || 'Something went wrong. Please try again.';
    }
};

const ItemArt = ({ item }) => (
    <div className={`ui-item-art ${RARITY_TONE[item.rarity] || 'tone-gray'}`}>
        {item.image_url
            ? <img src={item.image_url} alt={item.name} />
            : <span role="img" aria-label={item.name}>{item.art || '🎁'}</span>}
    </div>
);

const Store = () => {
    const [tab, setTab] = useState('shop');
    const [slot, setSlot] = useState('');
    const [shop, setShop] = useState({ items: [], balance: 0, level: 1 });
    const [inventory, setInventory] = useState([]);
    const [loadout, setLoadout] = useState({});
    const [preview, setPreview] = useState({});
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState('');
    const [busy, setBusy] = useState('');
    const [toast, setToast] = useState(null);
    const toastTimer = useRef(null);

    const showToast = useCallback((text, isError = false) => {
        setToast({ text, isError });
        clearTimeout(toastTimer.current);
        toastTimer.current = setTimeout(() => setToast(null), 4000);
    }, []);
    useEffect(() => () => clearTimeout(toastTimer.current), []);

    const load = useCallback(async () => {
        try {
            const [itemsRes, invRes, loadoutRes] = await Promise.all([
                storeAPI.getItems(),
                storeAPI.getInventory(),
                storeAPI.getLoadout(),
            ]);
            setShop(itemsRes.data);
            setInventory(invRes.data);
            setLoadout(loadoutRes.data);
            setLoadError('');
        } catch (e) {
            setLoadError('Could not load the store. Please try again.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const buy = async (item) => {
        if (!window.confirm(`Buy ${item.name} for ${formatPoints(item.price)}?`)) return;
        setBusy(item.slug);
        try {
            await storeAPI.purchase(item.slug);
            showToast(`🎉 You bought ${item.name}!`);
            setPreview((p) => ({ ...p, [item.slot]: item }));
            await load();
        } catch (e) {
            showToast(purchaseMessage(e), true);
            await load(); // the shop may have changed under us (price, balance, ownership)
        } finally {
            setBusy('');
        }
    };

    const wear = async (item, on) => {
        setBusy(item.slug);
        try {
            const res = on ? await storeAPI.equip(item.slug) : await storeAPI.unequip(item.slug);
            setLoadout(res.data);
            setPreview({});
            await load();
        } catch (e) {
            showToast(purchaseMessage(e), true);
        } finally {
            setBusy('');
        }
    };

    const togglePreview = (item) => setPreview((p) => (
        p[item.slot]?.slug === item.slug
            ? Object.fromEntries(Object.entries(p).filter(([k]) => k !== item.slot))
            : { ...p, [item.slot]: item }
    ));

    if (loading) {
        return (
            <div className="ui-loading">
                <div className="ui-spinner" />
                <p>Loading store...</p>
            </div>
        );
    }
    if (loadError && shop.items.length === 0 && inventory.length === 0) {
        return (
            <div className="ui-page ui-page--narrow">
                <div className="ui-card ui-empty">
                    <p>{loadError}</p>
                    <button className="ui-btn" onClick={load}>Retry</button>
                </div>
            </div>
        );
    }

    const wornSlugs = new Set(Object.values(loadout).map((i) => i.slug));
    const list = (tab === 'shop' ? shop.items : inventory).filter((i) => !slot || i.slot === slot);
    const previewing = Object.keys(preview).length > 0;

    const actions = (item) => {
        const loading = busy === item.slug;
        if (item.owned) {
            const worn = wornSlugs.has(item.slug);
            return (
                <button
                    className={`ui-btn ui-btn--sm ${worn ? 'ui-btn--ghost' : ''}`}
                    onClick={() => wear(item, !worn)}
                    disabled={loading}
                >
                    {worn ? 'Take off' : 'Wear'}
                </button>
            );
        }
        if (item.locked) {
            return <button className="ui-btn ui-btn--sm ui-btn--ghost" disabled>Level {item.min_level} needed</button>;
        }
        if (!item.can_afford) {
            return (
                <button className="ui-btn ui-btn--sm ui-btn--ghost" disabled>
                    {formatPoints(item.price - shop.balance)} short
                </button>
            );
        }
        return (
            <button className="ui-btn ui-btn--sm ui-btn--green" onClick={() => buy(item)} disabled={loading}>
                {loading ? 'Buying...' : item.price === 0 ? 'Get it free' : 'Buy'}
            </button>
        );
    };

    return (
        <div className="ui-page">
            <header className="ui-page-header">
                <h1 className="ui-title">Store</h1>
                <p className="ui-muted">
                    Spend your points on looks for your character. Your balance is{' '}
                    <strong className="ui-tone-text tone-accent">{formatPoints(shop.balance)}</strong>; buying never
                    lowers your level or leaderboard rank.
                </p>
            </header>

            <div className="ui-store-layout">
                <aside className="ui-card ui-store-side">
                    <Character loadout={{ ...loadout, ...preview }} size={200} label="Your character" />
                    <div className="ui-muted ui-small">
                        {previewing ? 'Trying on (not bought or worn yet)' : 'What you are wearing'}
                    </div>
                    {previewing && (
                        <button className="ui-btn ui-btn--sm ui-btn--ghost" onClick={() => setPreview({})}>
                            Reset preview
                        </button>
                    )}
                </aside>

                <section>
                    <div className="ui-tabs">
                        {[['shop', 'Shop'], ['mine', `My items (${inventory.length})`]].map(([value, label]) => (
                            <button
                                key={value}
                                className={`ui-tab${tab === value ? ' is-active' : ''}`}
                                onClick={() => setTab(value)}
                            >
                                {label}
                            </button>
                        ))}
                    </div>

                    <div className="ui-row" style={{ flexWrap: 'wrap', margin: '1rem 0' }}>
                        {SLOTS.map((s) => (
                            <button
                                key={s.value}
                                className={`ui-btn ui-btn--sm ${slot === s.value ? '' : 'ui-btn--ghost'}`}
                                onClick={() => setSlot(s.value)}
                            >
                                {s.label}
                            </button>
                        ))}
                    </div>

                    {list.length === 0 ? (
                        <div className="ui-card ui-empty">
                            <div className="ui-empty-icon">{tab === 'shop' ? '🛍️' : '🎒'}</div>
                            <p>
                                {tab === 'shop'
                                    ? 'Nothing for sale here right now.'
                                    : 'You do not own anything here yet. Visit the shop!'}
                            </p>
                        </div>
                    ) : (
                        <div className="ui-store-grid">
                            {list.map((item) => (
                                <div
                                    key={item.slug}
                                    className={
                                        `ui-card ui-item-card${item.locked && !item.owned ? ' is-locked' : ''}` +
                                        `${preview[item.slot]?.slug === item.slug ? ' is-previewing' : ''}`
                                    }
                                >
                                    <ItemArt item={item} />
                                    <div className="ui-row ui-row--between">
                                        <strong className="ui-strong">{item.name}</strong>
                                        <span className={`ui-badge ${RARITY_TONE[item.rarity] || 'tone-gray'}`}>
                                            {item.rarity_display}
                                        </span>
                                    </div>
                                    <div className="ui-muted ui-small" style={{ minHeight: '2.4em' }}>{item.description}</div>
                                    <div className="ui-row ui-row--between">
                                        <span className="ui-item-price">
                                            {item.owned && tab === 'mine'
                                                ? 'Owned'
                                                : item.price === 0 ? 'Free' : formatPoints(item.price)}
                                        </span>
                                        <span className="ui-muted ui-small">{item.slot_display}</span>
                                    </div>
                                    <div className="ui-row">
                                        {actions(item)}
                                        <button className="ui-link-btn" onClick={() => togglePreview(item)}>
                                            {preview[item.slot]?.slug === item.slug ? 'Undo try-on' : 'Try on'}
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </section>
            </div>

            {toast && (
                <div className={`ui-toast${toast.isError ? ' is-error' : ''}`} role="status">{toast.text}</div>
            )}
        </div>
    );
};

export default Store;
