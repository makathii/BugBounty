import { formatPoints } from './points';

describe('formatPoints', () => {
    test('formats numbers with a thousands separator and the unit', () => {
        expect(formatPoints(0)).toBe('0 pts');
        expect(formatPoints(265)).toBe('265 pts');
        expect(formatPoints(1500)).toBe((1500).toLocaleString() + ' pts');
    });

    test.each([undefined, null, '', 'abc', NaN])('treats %p as zero rather than showing NaN', (value) => {
        expect(formatPoints(value)).toBe('0 pts');
    });

    test('accepts numeric strings (API decimals)', () => {
        expect(formatPoints('40')).toBe('40 pts');
    });
});
