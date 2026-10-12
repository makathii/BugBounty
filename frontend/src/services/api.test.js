import api, { isExpiredSession } from './api';

// Regression: a wrong password made the login page reload with no error message, because every
// 401 was treated as an expired session (refresh -> fail -> redirect to /login).

const failWith = (status, url, data = { detail: 'nope' }) => (config) =>
    Promise.reject(Object.assign(new Error(`HTTP ${status}`), {
        config: { ...config, url },
        response: { status, data, config },
    }));

let redirects;
const realLocation = window.location;

beforeEach(() => {
    localStorage.clear();
    redirects = [];
    delete window.location;
    window.location = { origin: 'http://localhost', set href(value) { redirects.push(value); }, get href() { return 'http://localhost/'; } };
});

afterEach(() => {
    window.location = realLocation;
});

describe('which 401s mean "session expired"', () => {
    const err = (status, url, extra = {}) => ({ response: { status }, config: { url, ...extra } });

    test('a plain 401 with a refresh token on hand does', () => {
        localStorage.setItem('refresh_token', 'r');
        expect(isExpiredSession(err(401, '/reports/'))).toBe(true);
    });

    test('not without a refresh token (nothing to refresh)', () => {
        expect(isExpiredSession(err(401, '/reports/'))).toBe(false);
    });

    test.each([
        '/token/', '/token/refresh/', '/users/password-reset/confirm/', '/users/verify-email/abc/',
        '/users/register/', '/users/mfa/enroll/confirm/',
    ])('never for the credential call %s', (url) => {
        localStorage.setItem('refresh_token', 'r');
        expect(isExpiredSession(err(401, url))).toBe(false);
    });

    test('session calls that need a login still count (two-factor settings)', () => {
        localStorage.setItem('refresh_token', 'r');
        expect(isExpiredSession(err(401, '/users/mfa/confirm/'))).toBe(true);
    });

    test('not for other statuses, and not twice for the same request', () => {
        localStorage.setItem('refresh_token', 'r');
        expect(isExpiredSession(err(403, '/reports/'))).toBe(false);
        expect(isExpiredSession(err(500, '/reports/'))).toBe(false);
        expect(isExpiredSession(err(401, '/reports/', { _retry: true }))).toBe(false);
    });
});

describe('the response interceptor', () => {
    test('a rejected login surfaces its error and does not redirect or clear anything', async () => {
        localStorage.setItem('access_token', 'stale');
        api.defaults.adapter = failWith(401, '/token/', { detail: 'No active account found with the given credentials' });
        await expect(api.post('/token/', { username: 'a', password: 'b' })).rejects.toMatchObject({
            response: { status: 401, data: { detail: expect.stringContaining('No active account') } },
        });
        expect(redirects).toEqual([]);
        expect(localStorage.getItem('access_token')).toBe('stale');
    });

    test('a 401 with no session at all is just an error (the route guards handle logged-out users)', async () => {
        api.defaults.adapter = failWith(401, '/reports/');
        await expect(api.get('/reports/')).rejects.toMatchObject({ response: { status: 401 } });
        expect(redirects).toEqual([]);
    });

    test('an expired session whose refresh also fails ends the session and goes to login', async () => {
        localStorage.setItem('access_token', 'old');
        localStorage.setItem('refresh_token', 'also-old');
        api.defaults.adapter = failWith(401, '/reports/');
        // the refresh call goes through plain axios, which has no network here -> fails
        const quiet = jest.spyOn(console, 'error').mockImplementation(() => {});
        await api.get('/reports/').catch(() => {});
        quiet.mockRestore();
        expect(localStorage.getItem('access_token')).toBeNull();
        expect(localStorage.getItem('refresh_token')).toBeNull();
        expect(redirects).toEqual(['/login']);
    });

    test('other failures pass straight through', async () => {
        api.defaults.adapter = failWith(400, '/users/register/', { email: ['A user with this email already exists.'] });
        await expect(api.post('/users/register/', {})).rejects.toMatchObject({
            response: { status: 400, data: { email: ['A user with this email already exists.'] } },
        });
        expect(redirects).toEqual([]);
    });
});
