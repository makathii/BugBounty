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
