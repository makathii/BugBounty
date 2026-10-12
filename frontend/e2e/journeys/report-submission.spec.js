const { test, expect, anonymousPage, loginViaForm, createVerifiedResearcher, api } = require('../helpers');
const fs = require('fs');
const path = require('path');

// Reports must be genuinely different from every earlier one (the app flags near-duplicates),
// so build the text from random words rather than a fixed sentence.
const WORDS = ['kestrel', 'basalt', 'ember', 'quartz', 'lantern', 'marble', 'thistle', 'walrus', 'cobalt', 'sparrow',
    'velvet', 'harbor', 'juniper', 'nimbus', 'orchid', 'pylon', 'ripple', 'saffron', 'tundra', 'umber', 'vortex', 'willow',
    'zephyr', 'anchor', 'beacon', 'cipher', 'dagger', 'fennel', 'gadget', 'hollow', 'ivory', 'jigsaw', 'kernel', 'locket'];
const pick = (n) => Array.from({ length: n }, () => WORDS[Math.floor(Math.random() * WORDS.length)]).join(' ');

const GOOD_REPORT = () => ({
    title: `${pick(6)} stored script`,
    description: `${pick(10)} ${pick(14)} ${pick(10)}`,
    steps: `${pick(8)}\n${pick(8)}\n${pick(8)}`,
    impact: `${pick(10)}`,
});

async function fillReport(page, report) {
    await page.locator('[name=title]').fill(report.title);
    await page.locator('[name=vulnerability_type]').selectOption({ index: 2 });
    await page.locator('[name=affected_url]').fill('https://acme.example/profile');
    await page.locator('textarea[name=description]').fill(report.description);
    await page.locator('[name=steps_to_reproduce]').fill(report.steps);
    await page.locator('[name=impact]').fill(report.impact);
    await page.locator('[name=is_human_generated]').check();
}

test.describe('a researcher finds a program and submits a report', () => {
    test('from the program page to a report that belongs to that program', async ({ browser, playwright }) => {
        const user = await createVerifiedResearcher(playwright, 'rep');
        const page = await anonymousPage(browser);
        await loginViaForm(page, user.username, user.password);
        await expect(page).toHaveURL(/\/dashboard/);

        // Find a program and open it.
        await page.getByRole('link', { name: 'Find Programs', exact: true }).click();
        await expect(page.locator('.ui-card', { hasText: 'Acme Web Platform' })).toBeVisible();
        await page.locator('.ui-card', { hasText: 'Acme Web Platform' }).getByRole('link', { name: /view|details|open/i }).first().click();
        await expect(page.getByRole('heading', { name: 'Acme Web Platform' })).toBeVisible();
        const programId = page.url().match(/\/programs\/(\d+)/)[1];

        // Join (public programs let anyone in), then go to submit a report for THIS program.
        await page.getByRole('button', { name: /join program/i }).click();
        await expect(page.getByText(/joined|success|welcome/i).first()).toBeVisible();
        await page.getByRole('button', { name: 'Submit Report' }).first().click();
        await expect(page).toHaveURL(new RegExp(`/submit\\?program=${programId}`));

        const report = GOOD_REPORT();
        await fillReport(page, report);
        await page.getByRole('button', { name: 'Submit Report' }).click();
        await expect(page).toHaveURL(/\/reports$/);
        await expect(page.getByText(report.title)).toBeVisible();

        // The report must actually be filed under the program the researcher chose.
        const researcherApi = await playwright.request.newContext({
            baseURL: (process.env.E2E_API_URL || 'http://localhost:8000/api') + '/',
            extraHTTPHeaders: { Authorization: `Bearer ${await page.evaluate(() => localStorage.getItem('access_token'))}` },
        });
        const mine = await (await researcherApi.get('reports/')).json();
        const created = (mine.results || mine).find((r) => r.title === report.title);
        expect(created, 'the new report is listed').toBeTruthy();
        expect(String(created.program), 'the report belongs to the program it was submitted to').toBe(programId);
        expect(created.status).toBe('open');
        expect(page.jsErrors).toEqual([]);
    });

    test('arriving without a program means choosing one first', async ({ browser, playwright }) => {
        const user = await createVerifiedResearcher(playwright, 'pick');
        const page = await anonymousPage(browser);
        await loginViaForm(page, user.username, user.password);
        await page.goto('/submit');
        await expect(page.getByText(/choose the program you are reporting to/i)).toBeVisible();
        await expect(page.locator('textarea[name=description]')).toHaveCount(0); // no form yet
        await page.locator('#program-select').selectOption({ label: 'Acme Web Platform' });
        await expect(page.locator('textarea[name=description]')).toBeVisible();
        await expect(page).toHaveURL(/\/submit\?program=\d+/);
    });

    test('a link to a program the researcher cannot use says so instead of filing nowhere', async ({ browser, playwright }) => {
        const user = await createVerifiedResearcher(playwright, 'nope');
        const page = await anonymousPage(browser);
        await loginViaForm(page, user.username, user.password);
        await page.goto('/submit?program=999999');
        await expect(page.getByText(/not available to you/i)).toBeVisible();
        await expect(page.locator('textarea[name=description]')).toHaveCount(0);
    });

    test('a likely duplicate is flagged, can be confirmed as different, and never reveals other people\'s reports', async ({ browser, playwright }) => {
        const first = await createVerifiedResearcher(playwright, 'dupa');
        const second = await createVerifiedResearcher(playwright, 'dupb');
        const report = GOOD_REPORT();

        const submitAs = async (user) => {
            const page = await anonymousPage(browser);
            await loginViaForm(page, user.username, user.password);
            await page.goto('/submit');
            await page.locator('#program-select').selectOption({ label: 'Acme Web Platform' });
            await fillReport(page, report);
            await page.getByRole('button', { name: 'Submit Report' }).click();
            return page;
        };

        // The first researcher files it.
        const page1 = await submitAs(first);
        await expect(page1).toHaveURL(/\/reports$/);

        // A second researcher files the same finding: warned, and told nothing about the first one.
        const page2 = await submitAs(second);
        const warning = page2.getByTestId('duplicates');
        await expect(warning).toBeVisible();
        await expect(warning).toContainText("Another researcher's report");
        await expect(warning).toContainText('% similar');
        await expect(page2.locator('body')).not.toContainText(first.username);
        await expect(page2.locator('li', { hasText: report.title })).toHaveCount(0);

        // They can still confirm it is different and file it.
        await page2.getByRole('button', { name: /submit anyway/i }).click();
        await expect(page2).toHaveURL(/\/reports$/);

        // The first researcher filing it AGAIN sees their own report named in the warning.
        const page1b = await submitAs(first);
        await expect(page1b.getByTestId('duplicates')).toContainText(report.title);
    });
});
