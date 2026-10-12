const { test, expect, pageAs, anonymousPage, loginViaForm, createVerifiedResearcher, api } = require('../helpers');

const WORDS = ['kestrel', 'basalt', 'ember', 'quartz', 'lantern', 'marble', 'thistle', 'walrus', 'cobalt', 'sparrow',
    'velvet', 'harbor', 'juniper', 'nimbus', 'orchid', 'pylon', 'ripple', 'saffron', 'tundra', 'umber', 'vortex', 'willow'];
const pick = (n) => Array.from({ length: n }, () => WORDS[Math.floor(Math.random() * WORDS.length)]).join(' ');

test.describe.configure({ mode: 'serial' });

test.describe('a private program that requires applications', () => {
    const programName = `Vault ${Date.now().toString(36)}`;
    let programId;
    let approved;   // researcher whose application is approved
    let refused;    // researcher whose application is rejected
    let approvedPage;
    let refusedPage;
    let acme;

    test.beforeAll(async ({ playwright, browser }) => {
        const acmeApi = await api(playwright, 'acme');
        const created = await acmeApi.post('programs/programs/', { data: {
            name: programName, description: 'Invitation-grade security work. ' + pick(10), short_description: 'Private.',
            scope_type: 'private', requires_application: true,
        } });
        expect(created.status(), await created.text()).toBe(201);
        programId = (await created.json()).id;
        const scope = await acmeApi.post(`programs/${programId}/scopes/`, { data: { target: '*.vault.example', target_type: 'web_application', is_in_scope: true } });
        expect(scope.status(), await scope.text()).toBe(201);
        expect((await acmeApi.post(`programs/programs/${programId}/activate/`)).status()).toBe(200);

        approved = await createVerifiedResearcher(playwright, 'yes');
        refused = await createVerifiedResearcher(playwright, 'no');
        approvedPage = await anonymousPage(browser);
        await loginViaForm(approvedPage, approved.username, approved.password);
        refusedPage = await anonymousPage(browser);
        await loginViaForm(refusedPage, refused.username, refused.password);
        acme = await pageAs(browser, 'acme');
    });

    test('researchers apply, and cannot report until accepted', async () => {
        for (const [page, who] of [[approvedPage, 'approved'], [refusedPage, 'refused']]) {
            await page.goto(`/programs/${programId}`);
            await page.getByRole('button', { name: /apply to program/i }).first().click();
            await page.getByRole('button', { name: /submit application/i }).click();
            await expect(page.getByText(/application submitted|pending|will be notified/i).first()).toBeVisible();

            // Not in yet: the report page refuses this program.
            await page.goto(`/submit?program=${programId}`);
            await expect(page.getByText(/not available to you/i), `${who} must not be able to report yet`).toBeVisible();
            await expect(page.locator('textarea[name=description]')).toHaveCount(0);
        }
    });

    test('the company reviews the applications: one approved, one rejected', async () => {
        await acme.goto('/company/programs');
        await acme.locator('.ui-card', { hasText: programName }).getByRole('link', { name: 'Applications' }).click();
        await expect(acme).toHaveURL(new RegExp(`/company/programs/${programId}/applications`));
        await expect(acme.getByText('Waiting for a decision (2)')).toBeVisible();

        const yes = acme.getByTestId(`application-${approved.username}`);
        await yes.getByPlaceholder(/note to the researcher/i).fill('Welcome aboard.');
        await yes.getByRole('button', { name: 'Approve' }).click();
        await expect(acme.getByText(`${approved.username} was approved`)).toBeVisible();

        const no = acme.getByTestId(`application-${refused.username}`);
        await no.getByRole('button', { name: 'Reject' }).click();
        await expect(acme.getByText(`${refused.username} was rejected`)).toBeVisible();
        await expect(acme.getByText('Waiting for a decision (0)')).toBeVisible();
        await expect(acme.getByText('Decided (2)')).toBeVisible();
        await expect(acme.getByText('Your note: Welcome aboard.')).toBeVisible();
    });

    test('the approved researcher can now report to it; the rejected one still cannot', async () => {
        await approvedPage.goto(`/submit?program=${programId}`);
        await expect(approvedPage.locator('textarea[name=description]')).toBeVisible();
        await approvedPage.locator('[name=title]').fill(`${pick(6)} vault bypass`);
        await approvedPage.locator('[name=vulnerability_type]').selectOption({ index: 6 });
        await approvedPage.locator('[name=affected_url]').fill('https://vault.example/api');
        await approvedPage.locator('textarea[name=description]').fill(`${pick(12)} ${pick(14)}`);
        await approvedPage.locator('[name=steps_to_reproduce]').fill(pick(10));
        await approvedPage.locator('[name=impact]').fill(pick(10));
        await approvedPage.locator('[name=is_human_generated]').check();
        await approvedPage.getByRole('button', { name: 'Submit Report' }).click();
        await expect(approvedPage).toHaveURL(/\/reports$/);

        await refusedPage.goto(`/submit?program=${programId}`);
        await expect(refusedPage.getByText(/not available to you/i)).toBeVisible();
    });

    test('researchers cannot approve applications, and other companies cannot see them', async ({ browser, playwright }) => {
        const outsider = await anonymousPage(browser);
        await loginViaForm(outsider, refused.username, refused.password);
        await outsider.goto(`/company/programs/${programId}/applications`);
        await expect(outsider).not.toHaveURL(/applications/); // researchers are sent away

        const techflow = await pageAs(browser, 'techflow');
        await techflow.goto(`/company/programs/${programId}/applications`);
        await expect(techflow.getByTestId(`application-${approved.username}`)).toHaveCount(0);
        await expect(techflow.getByText(/waiting for a decision \(0\)|could not load|not found|permission/i).first()).toBeVisible();
    });
});
