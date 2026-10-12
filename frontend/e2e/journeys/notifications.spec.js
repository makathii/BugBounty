const { test, expect, pageAs, anonymousPage, loginViaForm, createVerifiedResearcher, apiAsUser, api } = require('../helpers');

const WORDS = ['kestrel', 'basalt', 'ember', 'quartz', 'lantern', 'marble', 'thistle', 'walrus', 'cobalt', 'sparrow',
    'velvet', 'harbor', 'juniper', 'nimbus', 'orchid', 'pylon', 'ripple', 'saffron', 'tundra', 'umber', 'vortex', 'willow'];
const pick = (n) => Array.from({ length: n }, () => WORDS[Math.floor(Math.random() * WORDS.length)]).join(' ');

test.describe.configure({ mode: 'serial' });

const bellCount = (page) => page.getByTestId('bell-count');

test.describe('the notification bell', () => {
    const programName = `Beacon ${Date.now().toString(36)}`;
    let programId;
    let researcher;
    let researcherPage;
    let acme;

    test.beforeAll(async ({ playwright, browser }) => {
        const acmeApi = await api(playwright, 'acme');
        const created = await acmeApi.post('programs/programs/', { data: {
            name: programName, description: 'Signals.', short_description: 'Private.',
            scope_type: 'private', invitation_only: true,
        } });
        expect(created.status(), await created.text()).toBe(201);
        programId = (await created.json()).id;
        const scope = await acmeApi.post(`programs/${programId}/scopes/`, { data: { target: '*.beacon.example', target_type: 'web_application', is_in_scope: true } });
        expect(scope.status(), await scope.text()).toBe(201);
        expect((await acmeApi.post(`programs/programs/${programId}/activate/`)).status()).toBe(200);

        researcher = await createVerifiedResearcher(playwright, 'bell');
        researcherPage = await anonymousPage(browser);
        await loginViaForm(researcherPage, researcher.username, researcher.password);
        acme = await pageAs(browser, 'acme');
    });

    test('a fresh account has no badge and an empty list', async () => {
        await researcherPage.goto('/dashboard');
        await expect(bellCount(researcherPage)).toHaveCount(0);
        await researcherPage.getByRole('button', { name: 'Notifications' }).click();
        await expect(researcherPage.getByText(/nothing yet/i)).toBeVisible();
    });

    test('an invitation shows up on the bell and opens the program', async () => {
        await acme.goto(`/company/programs/${programId}/invitations`);
        await acme.getByLabel(/researcher's username/i).fill(researcher.username);
        await acme.getByRole('button', { name: 'Send invitation' }).click();
        await expect(acme.getByText(`Invitation sent to ${researcher.username}.`)).toBeVisible();

        await researcherPage.goto('/dashboard');
        await expect(bellCount(researcherPage)).toHaveText('1');
        await researcherPage.getByRole('button', { name: /notifications, 1 unread/i }).click();
        await researcherPage.getByText(`You've been invited to ${programName}`).click();
        await expect(researcherPage).toHaveURL(new RegExp(`/programs/${programId}$`));
        await expect(bellCount(researcherPage)).toHaveCount(0); // reading it clears the badge
    });

    test('re-inviting after a revoke tells the researcher again', async () => {
        await acme.goto(`/company/programs/${programId}/invitations`);
        await acme.getByTestId(`invitation-${researcher.username}`).getByRole('button', { name: 'Revoke' }).click();
        await expect(acme.getByText(/was revoked/)).toBeVisible();
        await acme.getByLabel(/researcher's username/i).fill(researcher.username);
        await acme.getByRole('button', { name: 'Send invitation' }).click();
        await expect(acme.getByText(`Invitation sent to ${researcher.username}.`)).toBeVisible();

        await researcherPage.goto('/notifications');
        await expect(researcherPage.getByText('Invitation withdrawn: ' + programName)).toBeVisible();
        await expect(researcherPage.getByText(`You've been invited to ${programName}`)).toHaveCount(2);
    });

    test('the company hears the answer', async () => {
        await researcherPage.goto('/dashboard');
        await researcherPage.getByTestId(`my-invitation-${programName}`).getByRole('button', { name: 'Decline' }).click();
        await expect(researcherPage.getByText(`You declined ${programName}.`)).toBeVisible();

        await acme.goto('/dashboard');
        await acme.getByRole('button', { name: /notifications/i }).click();
        await acme.getByText(`${researcher.username} declined your invitation`).click();
        await expect(acme).toHaveURL(new RegExp(`/company/programs/${programId}/invitations`));
    });

    test('a triager accepts a report through the dialog and the researcher is notified', async ({ browser, playwright }) => {
        const researcherApi = await apiAsUser(playwright, researcher);
        const listing = await (await researcherApi.get('programs/public/')).json();
        const acmeProgram = (listing.results || listing).find((p) => p.name === 'Acme Web Platform');
        const created = await researcherApi.post('reports/', { data: {
            title: `${pick(4)} bell finding`, description: `${pick(12)} ${pick(14)}`,
            steps_to_reproduce: pick(10), impact: pick(8),
            vulnerability_type: 'other', affected_url: 'https://acme.example/x', is_human_generated: true,
            program: acmeProgram.id, severity: 'low',
        } });
        expect(created.status(), await created.text()).toBe(201);
        const report = await created.json();

        const triager = await pageAs(browser, 'triager');
        await triager.goto(`/reports/${report.id}`);
        await triager.getByRole('button', { name: /start triage/i }).first().click();
        await triager.locator('.ui-modal select').selectOption('high');
        await triager.locator('.ui-modal').getByRole('button', { name: /start triage|confirm|triage/i }).click();
        await expect(triager.locator('.ui-badge', { hasText: 'triaged' })).toBeVisible();

        await triager.goto('/dashboard');
        const row = triager.locator('tr', { hasText: report.title });
        await row.getByRole('button', { name: 'Accept' }).click();
        const dialog = triager.getByRole('dialog', { name: /accept report/i });
        await dialog.getByRole('button', { name: 'Accept report' }).click();
        await expect(dialog.getByRole('alert')).toContainText(/short note/i); // validated, nothing sent
        await dialog.getByLabel(/verification notes/i).fill('Reproduced on staging.');
        await dialog.getByLabel(/bonus points/i).fill('20');
        await dialog.getByRole('button', { name: 'Accept report' }).click();
        await expect(triager.getByText(/accepted successfully/i)).toBeVisible();

        await researcherPage.goto('/dashboard');
        await researcherPage.getByRole('button', { name: /notifications/i }).click();
        await expect(researcherPage.getByText(new RegExp(`Your report was accepted: ${report.title}`))).toBeVisible();
    });
});
