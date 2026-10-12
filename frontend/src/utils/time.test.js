import { timeAgo } from './time';

const NOW = new Date('2026-10-12T12:00:00Z').getTime();
const ago = (seconds) => new Date(NOW - seconds * 1000).toISOString();

test.each([
    [5, 'just now'], [59, 'just now'], [60, '1 minute ago'], [150, '2 minutes ago'],
    [3600, '1 hour ago'], [7200, '2 hours ago'], [86400, '1 day ago'], [3 * 86400, '3 days ago'],
])('%i seconds -> %s', (seconds, expected) => {
    expect(timeAgo(ago(seconds), NOW)).toBe(expected);
});

test('a time in the future (clock skew) reads "just now"; garbage reads empty', () => {
    expect(timeAgo(ago(-30), NOW)).toBe('just now');
    expect(timeAgo('not a date', NOW)).toBe('');
});
