// Maps domain values to the `tone-*` colour classes defined in styles/theme.css.
// One place instead of a getStatusColor()/getSeverityColor() copy per page.

const STATUS = {
    open: 'blue', triaged: 'accent', accepted: 'green', resolved: 'green',
    rejected: 'red', duplicate: 'orange', closed: 'gray',
    active: 'green', draft: 'yellow', paused: 'red',
    pending: 'yellow', approved: 'green', declined: 'red',
};
const SEVERITY = { critical: 'red', high: 'orange', medium: 'yellow', low: 'green', info: 'blue' };
const SCOPE = { public: 'blue', private: 'accent', vdp: 'orange' };

export const statusTone = (v) => `tone-${STATUS[(v || '').toLowerCase()] || 'gray'}`;
export const severityTone = (v) => `tone-${SEVERITY[(v || '').toLowerCase()] || 'gray'}`;
export const scopeTone = (v) => `tone-${SCOPE[(v || '').toLowerCase()] || 'gray'}`;
