const { test, expect, pageAs, anonymousPage, loginViaForm, createVerifiedResearcher, latestMailTo } = require('../helpers');

const pts = (n) => `${n.toLocaleString()} pts`;
const WORDS = ['kestrel', 'basalt', 'ember', 'quartz', 'lantern', 'marble', 'thistle', 'walrus', 'cobalt', 'sparrow',
    'velvet', 'harbor', 'juniper', 'nimbus', 'orchid', 'pylon', 'ripple', 'saffron', 'tundra', 'umber', 'vortex', 'willow'];
const pick = (n) => Array.from({ length: n }, () => WORDS[Math.floor(Math.random() * WORDS.length)]).join(' ');

async function submitReport(page, programLabel = 'Acme Web Platform') {
    const report = {
        title: `${pick(6)} authentication bypass`,
        description: `${pick(10)} ${pick(14)} ${pick(10)}`,
        steps: `${pick(8)}\n${pick(8)}\n${pick(8)}`,
        impact: `${pick(10)}`,
    };
    await page.goto('/submit');
    await page.locator('#program-select').selectOption({ label: programLabel });
    await page.locator('[name=title]').fill(report.title);
    await page.locator('[name=vulnerability_type]').selectOption({ index: 4 });
    await page.locator('[name=affected_url]').fill('https://acme.example/login');
    await page.locator('textarea[name=description]').fill(report.description);
    await page.locator('[name=steps_to_reproduce]').fill(report.steps);
    await page.locator('[name=impact]').fill(report.impact);
    await page.locator('[name=is_human_generated]').check();
    await page.getByRole('button', { name: 'Submit Report' }).click();
    await expect(page).toHaveURL(/\/reports$/);
    return report;
}

async function reportIdByTitle(playwrightApiPage, title) {
    // The researcher's own list links to the report; read the id from the link.
    const href = await playwrightApiPage.locator('tr', { hasText: title }).getByRole('link').first().getAttribute('href');
    return href.match(/\/reports\/(\d+)/)[1];
}

test.describe('from a submitted report to points in the wallet', () => {
    test('triager reviews a new report, sets its severity, accepts it with a bonus; the researcher is told and paid', async ({ browser, playwright }) => {
        const researcher = await createVerifiedResearcher(playwright, 'earn');
        const researcherPage = await anonymousPage(browser);
        await loginViaForm(researcherPage, researcher.username, researcher.password);
        const report = await submitReport(researcherPage);
        const reportId = await reportIdByTitle(researcherPage, report.title);

        // The triager finds it, starts triage and decides on a severity.
        const triager = await pageAs(browser, 'triager');
        await triager.goto(`/reports/${reportId}`);
        await expect(triager.getByRole('heading', { name: report.title })).toBeVisible();
        await expect(triager.locator('.ui-badge', { hasText: 'open' })).toBeVisible();
        await triager.getByRole('button', { name: /start triage/i }).first().click();
        await triager.locator('.ui-modal select').selectOption('high');
        await triager.locator('.ui-modal').getByRole('button', { name: /start triage|confirm|triage/i }).click();
        await expect(triager.locator('.ui-badge', { hasText: 'triaged' })).toBeVisible();
        await expect(triager.locator('.ui-badge', { hasText: /high/ }).first()).toBeVisible();

        // Accept with bonus points.
        await triager.getByRole('button', { name: 'Accept' }).first().click();
        await triager.locator('.ui-modal input[type=number]').fill('15');
        await triager.locator('.ui-modal textarea').fill('Confirmed and well written.');
        await triager.locator('.ui-modal').getByRole('button', { name: 'Accept' }).click();
        await expect(triager.locator('.ui-badge', { hasText: 'accepted' })).toBeVisible();
        await expect(triager.locator('.ui-badge', { hasText: '+85 pts' })).toBeVisible(); // 70 (high) + 15 bonus

        // The researcher is paid, levelled and told by email.
        await researcherPage.goto('/wallet');
        await expect(researcherPage.locator('.ui-stat', { hasText: 'Balance' })).toContainText(pts(85));
        await researcherPage.goto('/badges');
        await expect(researcherPage.locator('.ui-badge-card.is-earned', { hasText: 'First Blood' })).toBeVisible();
        const mail = latestMailTo(researcher.email);
        expect(mail, 'the researcher gets an email about the decision').toBeTruthy();
        expect(mail).toMatch(/accepted/i);
        expect(mail).toContain('85');
    });

    test('a rejection gives the researcher the reason, and no points', async ({ browser, playwright }) => {
        const researcher = await createVerifiedResearcher(playwright, 'nope');
        const researcherPage = await anonymousPage(browser);
        await loginViaForm(researcherPage, researcher.username, researcher.password);
        const report = await submitReport(researcherPage);
        const reportId = await reportIdByTitle(researcherPage, report.title);

        const triager = await pageAs(browser, 'triager');
        await triager.goto(`/reports/${reportId}`);
        await triager.getByRole('button', { name: /start triage/i }).first().click();
        await triager.locator('.ui-modal').getByRole('button', { name: /start triage|confirm|triage/i }).click();
        await expect(triager.locator('.ui-badge', { hasText: 'triaged' })).toBeVisible();
        await triager.getByRole('button', { name: 'Reject' }).first().click();
        await triager.locator('.ui-modal textarea').fill('Not reproducible on the current build.');
        await triager.locator('.ui-modal').getByRole('button', { name: 'Reject' }).click();
        await expect(triager.locator('.ui-badge', { hasText: 'rejected' })).toBeVisible();

        await researcherPage.goto('/wallet');
        await expect(researcherPage.locator('.ui-stat', { hasText: 'Balance' })).toContainText(pts(0));
        await researcherPage.goto(`/reports/${reportId}`);
        await expect(researcherPage.locator('.ui-badge', { hasText: 'rejected' })).toBeVisible();
        const mail = latestMailTo(researcher.email);
        expect(mail).toMatch(/rejected|not accepted/i);
        expect(mail).toContain('Not reproducible on the current build');
    });

    test('researchers cannot triage, accept or reject their own reports', async ({ browser, playwright }) => {
        const researcher = await createVerifiedResearcher(playwright, 'self');
        const page = await anonymousPage(browser);
        await loginViaForm(page, researcher.username, researcher.password);
        const report = await submitReport(page);
        const reportId = await reportIdByTitle(page, report.title);
        await page.goto(`/reports/${reportId}`);
        await expect(page.getByRole('button', { name: /start triage|accept|reject|assign to me/i })).toHaveCount(0);
    });
});
