// "5 minutes ago", for notification lists. `now` is a parameter so tests need no fake clock.
export const timeAgo = (iso, now = Date.now()) => {
    const seconds = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
    if (Number.isNaN(seconds)) return '';
    if (seconds < 60) return 'just now';
    const units = [['day', 86400], ['hour', 3600], ['minute', 60]];
    for (const [name, size] of units) {
        if (seconds >= size) {
            const n = Math.floor(seconds / size);
            return `${n} ${name}${n === 1 ? '' : 's'} ago`;
        }
    }
    return '';
};
