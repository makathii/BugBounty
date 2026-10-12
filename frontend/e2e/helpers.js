const fs = require('fs');
const path = require('path');
const { test: base, expect } = require('@playwright/test');

const API = process.env.E2E_API_URL || 'http://localhost:8000/api';

const state = () => JSON.parse(fs.readFileSync(path.join(__dirname, '.state.json'), 'utf8'));

/** Logged-in browser page for a demo user (the app reads its JWTs from localStorage). */
async function pageAs(browser, username, viewport = { width: 1280, height: 900 }) {
    const { access, refresh } = state().tokens[username];
    const context = await browser.newContext({ viewport });
    await context.addInitScript(([a, r]) => {
        localStorage.setItem('access_token', a);
        localStorage.setItem('refresh_token', r);
    }, [access, refresh]);
    const page = await context.newPage();
    page.on('dialog', (dialog) => dialog.accept()); // confirm() / alert()
    const errors = [];
    page.on('pageerror', (error) => errors.push(String(error)));
    page.jsErrors = errors;
    return page;
}

/** Call the API as a demo user, for setup and for numbers to assert against. */
async function api(playwright, username) {
    return playwright.request.newContext({
        baseURL: API.endsWith('/') ? API : `${API}/`,
        extraHTTPHeaders: { Authorization: `Bearer ${state().tokens[username].access}` },
    });
}

const test = base;
module.exports = { test, expect, pageAs, api, state };

// ---------------------------------------------------------------------------------------------
// Journeys that start from nothing: unique users, emailed links, one-time 2FA codes.
// ---------------------------------------------------------------------------------------------
const crypto = require('crypto');

const MAIL_DIR = process.env.E2E_MAIL_DIR || '/tmp/bugbounty-e2e-mail';
const PASSWORD = 'Sup3r-Secret-pw!';

let counter = 0;
/** A username/email nobody has used yet (unique per test run and per call). */
function freshUser(prefix = 'user') {
    counter += 1;
    const id = `${prefix}${Date.now().toString(36)}${counter}`;
    return { username: id, email: `${id}@example.test`, password: PASSWORD, first: 'Test', last: 'Person' };
}

/** Newest email to `address` as text, or null. Emails are written as files by e2e_settings. */
function latestMailTo(address) {
    if (!fs.existsSync(MAIL_DIR)) return null;
    const files = fs.readdirSync(MAIL_DIR)
        .map((name) => ({ name, mtime: fs.statSync(path.join(MAIL_DIR, name)).mtimeMs }))
        .sort((a, b) => b.mtime - a.mtime);
    for (const { name } of files) {
        const text = fs.readFileSync(path.join(MAIL_DIR, name), 'utf8');
        if (new RegExp(`^To: .*${address.replace(/[.+]/g, '\\$&')}`, 'm').test(text)) return text;
    }
    return null;
}

/** Wait for an email to `address` containing a link matching `pattern`; returns the path part. */
async function emailedLink(address, pattern, timeoutMs = 10_000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        const mail = latestMailTo(address);
        // quoted-printable mail may wrap long lines with "=\n"
        const match = mail && mail.replace(/=\r?\n/g, '').match(pattern);
        if (match) return match[0];
        await new Promise((resolve) => setTimeout(resolve, 250));
    }
    throw new Error(`No email to ${address} with a link matching ${pattern}`);
}

/** The current 6-digit TOTP code for a base32 secret (RFC 6238: SHA-1, 30 s, 6 digits). */
function totp(secretBase32, atMs = Date.now()) {
    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
    let bits = '';
    for (const char of secretBase32.replace(/=+$/, '').replace(/\s/g, '').toUpperCase()) {
        bits += alphabet.indexOf(char).toString(2).padStart(5, '0');
    }
    const key = Buffer.from(bits.match(/.{8}/g).map((byte) => parseInt(byte, 2)));
    const counterBuf = Buffer.alloc(8);
    counterBuf.writeBigUInt64BE(BigInt(Math.floor(atMs / 1000 / 30)));
    const hmac = crypto.createHmac('sha1', key).update(counterBuf).digest();
    const offset = hmac[hmac.length - 1] & 0xf;
    const code = (hmac.readUInt32BE(offset) & 0x7fffffff) % 1_000_000;
    return String(code).padStart(6, '0');
}

/** A fresh browser page that is NOT logged in. */
async function anonymousPage(browser, viewport = { width: 1280, height: 900 }) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    page.on('dialog', (dialog) => dialog.accept());
    page.jsErrors = [];
    page.on('pageerror', (error) => page.jsErrors.push(String(error)));
    return page;
}

/** Log in through the real login form. */
async function loginViaForm(page, username, password) {
    await page.goto('/login');
    await page.locator('#username').fill(username);
    await page.locator('#password').fill(password);
    await page.getByRole('button', { name: /^sign in$/i }).click();
    // Return once the attempt has played out: we left /login (success, 2FA step, enrolment) or the
    // page showed an error. Navigating away earlier would abort a login that is still in flight.
    await Promise.race([
        page.waitForURL((url) => !/\/login\/?$/.test(url.pathname), { timeout: 8_000 }),
        page.locator('.error-message').first().waitFor({ timeout: 8_000 }),
    ]).catch(() => {});
}

Object.assign(module.exports, { freshUser, latestMailTo, emailedLink, totp, anonymousPage, loginViaForm, PASSWORD, MAIL_DIR });

/** A researcher who already finished sign-up and email verification (done through the API). */
async function createVerifiedResearcher(playwright, prefix = 'api') {
    const user = freshUser(prefix);
    const anon = await playwright.request.newContext({ baseURL: API.endsWith('/') ? API : `${API}/` });
    const registered = await anon.post('users/register/', {
        data: {
            username: user.username, email: user.email, password: user.password, password2: user.password,
            first_name: user.first, last_name: user.last, role: 'researcher',
        },
    });
    if (registered.status() !== 201) throw new Error(`register failed: ${registered.status()} ${await registered.text()}`);
    const link = await emailedLink(user.email, /\/verify-email\/[\w-]+/);
    const token = link.split('/').pop();
    const verified = await anon.get(`users/verify-email/${token}/`);
    if (!verified.ok()) throw new Error(`verify failed: ${verified.status()}`);
    return user;
}

Object.assign(module.exports, { createVerifiedResearcher });

/** An API client authenticated as `user` (logs in through the API; header auth, no cookies). */
async function apiAsUser(playwright, user) {
    const baseURL = API.endsWith('/') ? API : `${API}/`;
    const anon = await playwright.request.newContext({ baseURL });
    const login = await anon.post('token/', { data: { username: user.username, password: user.password } });
    if (!login.ok()) throw new Error(`API login failed for ${user.username}: ${login.status()}`);
    const { access } = await login.json();
    await anon.dispose();
    return playwright.request.newContext({ baseURL, extraHTTPHeaders: { Authorization: `Bearer ${access}` } });
}

Object.assign(module.exports, { apiAsUser });

const { execFileSync } = require('child_process');

/**
 * Pretend 30+ seconds have passed for `username`'s 2FA: forget which one-time code was used last, so
 * the current code can be used again. (A code is single-use; a test that needs several codes in a
 * row would otherwise have to wait out each 30-second window.) Test database only.
 */
function letCodeWindowPass(username) {
    const backend = path.resolve(process.env.E2E_BACKEND_DIR || path.join(__dirname, '..', '..', 'backend'));
    execFileSync(process.env.E2E_PYTHON || 'python', ['manage.py', 'shell'], {
        cwd: backend,
        input: `from users.models import UserMFA\nUserMFA.objects.filter(user__username=${JSON.stringify(username)}).update(last_used_step=None)\n`,
        env: { ...process.env, E2E_RESET: '1' },
        stdio: ['pipe', 'ignore', 'inherit'],
    });
}

Object.assign(module.exports, { letCodeWindowPass });
