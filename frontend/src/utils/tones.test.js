import { statusTone, severityTone, scopeTone } from './tones';

describe('tones', () => {
    test('maps known values to their tone class', () => {
        expect(statusTone('accepted')).toBe('tone-green');
        expect(statusTone('rejected')).toBe('tone-red');
        expect(severityTone('critical')).toBe('tone-red');
        expect(scopeTone('vdp')).toBe('tone-orange');
    });

    test('is case-insensitive', () => {
        expect(statusTone('OPEN')).toBe('tone-blue');
        expect(severityTone('High')).toBe('tone-orange');
    });

    test.each([undefined, null, '', 'something-new'])('falls back to gray for %p', (value) => {
        expect(statusTone(value)).toBe('tone-gray');
        expect(severityTone(value)).toBe('tone-gray');
        expect(scopeTone(value)).toBe('tone-gray');
    });
});
