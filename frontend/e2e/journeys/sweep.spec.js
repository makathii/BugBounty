// A crawl, not a story: every page, as every role, on a laptop and on a phone. It cannot know what a
// page is *supposed* to say, but it catches the broken kind of thing quickly: script errors, failed
// API calls, "undefined" / "NaN" / "[object Object]" in the text, and content wider than the screen.
const { test, expect, pageAs, anonymousPage, api } = require('../helpers');

const DESKTOP = { width: 1280, height: 900 };
const PHONE = { width: 390, height: 844 };

const PUBLIC = ['/', '/login', '/register/researcher', '/register/company', '/forgot-password', '/leaderboard'];
const RESEARCHER = ['/dashboard', '/reports', '/reports/1', '/submit', '/programs', '/wallet', '/store', '/badges',
    '/leaderboard', '/2fa/settings', '/2fa/setup'];
const COMPANY = ['/company-dashboard', '/company/programs', '/company/programs/create', '/company/reports'];
const STAFF = ['/dashboard', '/triage', '/reports', '/reports/1', '/2fa/settings'];

// API calls that are allowed to fail on a page (the page handles them).
const EXPECTED_FAILURES = [/\/2fa\/|mfa\/status/];

const JUNK = /\bundefined\b|\bNaN\b|\[object Object\]|\bnull\b(?! pointer)/;

async function inspect(page, path, label) {
    const problems = [];
    const failed = [];
    const onResponse = (r) => {
        if (r.url().includes('/api/') && r.status() >= 400 && !EXPECTED_FAILURES.some((re) => re.test(r.url()))) {
            failed.push(`${r.status()} ${r.request().method()} ${new URL(r.url()).pathname}`);
        }
    };
    page.on('response', onResponse);
    await page.goto(path, { waitUntil: 'networkidle' });
    page.off('response', onResponse);

    const text = await page.locator('body').innerText();
    const junk = text.match(JUNK);
    if (junk) problems.push(`shows "${junk[0]}"`);
    if (failed.length) problems.push(`failed API calls: ${[...new Set(failed)].join(', ')}`);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    if (overflow > 1) problems.push(`content is ${overflow}px wider than the screen`);
    if (page.jsErrors.length) problems.push(`script errors: ${page.jsErrors.join(' | ').slice(0, 200)}`);
    page.jsErrors.length = 0;
    return problems.map((p) => `${label} ${path}: ${p}`);
}

async function sweep(makePage, paths, label) {
    const page = await makePage();
    const found = [];
    for (const path of paths) found.push(...await inspect(page, path, label));
    return found;
}

for (const [name, viewport] of [['laptop', DESKTOP], ['phone', PHONE]]) {
    test(`public pages on a ${name}`, async ({ browser }) => {
        const found = await sweep(() => anonymousPage(browser, viewport), PUBLIC, `anonymous/${name}`);
        expect(found, found.join('\n')).toEqual([]);
    });

    test(`researcher pages on a ${name}`, async ({ browser }) => {
        const found = await sweep(() => pageAs(browser, 'parsa', viewport), RESEARCHER, `researcher/${name}`);
        expect(found, found.join('\n')).toEqual([]);
    });

    test(`company pages on a ${name}`, async ({ browser }) => {
        const found = await sweep(() => pageAs(browser, 'acme', viewport), COMPANY, `company/${name}`);
        expect(found, found.join('\n')).toEqual([]);
    });

    test(`staff pages on a ${name}`, async ({ browser }) => {
        const found = await sweep(() => pageAs(browser, 'triager', viewport), STAFF, `triager/${name}`);
        expect(found, found.join('\n')).toEqual([]);
    });
}

test('detail pages for every program and report the demo users can see', async ({ browser, playwright }) => {
    const found = [];
    const researcherApi = await api(playwright, 'parsa');
    const programs = await (await researcherApi.get('programs/researcher/')).json();
    const page = await pageAs(browser, 'parsa');
    for (const p of programs) found.push(...await inspect(page, `/programs/${p.id}`, 'researcher/program'));
    const mine = await (await researcherApi.get('reports/')).json();
    for (const r of (mine.results || mine)) found.push(...await inspect(page, `/reports/${r.id}`, 'researcher/report'));
    expect(found, found.join('\n')).toEqual([]);
});
