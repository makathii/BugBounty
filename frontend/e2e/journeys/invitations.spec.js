const { test, expect, pageAs, anonymousPage, loginViaForm, createVerifiedResearcher, api } = require('../helpers');

test.describe.configure({ mode: 'serial' });

test.describe('a company invites researchers to a private program', () => {
    const programName = `Citadel ${Date.now().toString(36)}`;
    let programId;
    let joiner;   // accepts
    let skeptic;  // declines
    let joinerPage;
    let skepticPage;
    let acme;

    test.beforeAll(async ({ playwright, browser }) => {
        const acmeApi = await api(playwright, 'acme');
        const created = await acmeApi.post('programs/programs/', { data: {
            name: programName, description: 'By invitation only.', short_description: 'Private.',
            scope_type: 'private', invitation_only: true,
        } });
        expect(created.status(), await created.text()).toBe(201);
        programId = (await created.json()).id;
        const scope = await acmeApi.post(`programs/${programId}/scopes/`, { data: { target: '*.citadel.example', target_type: 'web_application', is_in_scope: true } });
        expect(scope.status(), await scope.text()).toBe(201);
        expect((await acmeApi.post(`programs/programs/${programId}/activate/`)).status()).toBe(200);

        joiner = await createVerifiedResearcher(playwright, 'join');
        skeptic = await createVerifiedResearcher(playwright, 'skep');
        joinerPage = await anonymousPage(browser);
        await loginViaForm(joinerPage, joiner.username, joiner.password);
        skepticPage = await anonymousPage(browser);
        await loginViaForm(skepticPage, skeptic.username, skeptic.password);
        acme = await pageAs(browser, 'acme');
    });

    test('the company sends invitations by username and sees clear errors', async () => {
        await acme.goto('/company/programs');
        await acme.locator('.ui-card', { hasText: programName }).getByRole('link', { name: 'Invitations' }).click();
        await expect(acme).toHaveURL(new RegExp(`/company/programs/${programId}/invitations`));

        await acme.getByLabel(/researcher's username/i).fill('nobody-by-this-name');
        await acme.getByRole('button', { name: 'Send invitation' }).click();
        await expect(acme.getByText('No researcher with that username.')).toBeVisible();

        for (const user of [joiner, skeptic]) {
            await acme.getByLabel(/researcher's username/i).fill(user.username);
            await acme.getByLabel(/message/i).fill('We would love your help.');
            await acme.getByRole('button', { name: 'Send invitation' }).click();
            await expect(acme.getByText(`Invitation sent to ${user.username}.`)).toBeVisible();
        }

        await acme.getByLabel(/researcher's username/i).fill(joiner.username);
        await acme.getByRole('button', { name: 'Send invitation' }).click();
        await expect(acme.getByText(/already been invited/i)).toBeVisible();
        await expect(acme.getByTestId(`invitation-${joiner.username}`)).toContainText(/pending/i);
    });

    test('the program stays hidden until the invitation is accepted', async () => {
        await joinerPage.goto(`/submit?program=${programId}`);
        await expect(joinerPage.getByText(/not available to you/i)).toBeVisible();
    });

    test('a researcher accepts from the dashboard and can then report', async () => {
        await joinerPage.goto('/dashboard');
        const card = joinerPage.getByTestId(`my-invitation-${programName}`);
        await expect(card).toContainText('We would love your help.');
        await card.getByRole('button', { name: 'Accept' }).click();
        await expect(joinerPage.getByText(`You joined ${programName}.`)).toBeVisible();

        await joinerPage.goto(`/submit?program=${programId}`);
        await expect(joinerPage.locator('textarea[name=description]')).toBeVisible();
    });

    test('another researcher declines and still cannot report', async () => {
        await skepticPage.goto('/dashboard');
        await skepticPage.getByTestId(`my-invitation-${programName}`).getByRole('button', { name: 'Decline' }).click();
        await expect(skepticPage.getByText(`You declined ${programName}.`)).toBeVisible();
        await skepticPage.goto(`/submit?program=${programId}`);
        await expect(skepticPage.getByText(/not available to you/i)).toBeVisible();
    });

    test('the company sees the answers and can invite the decliner again, then revoke', async () => {
        await acme.goto(`/company/programs/${programId}/invitations`);
        await expect(acme.getByTestId(`invitation-${joiner.username}`)).toContainText(/accepted/i);
        await expect(acme.getByTestId(`invitation-${skeptic.username}`)).toContainText(/rejected|declined/i);

        await acme.getByLabel(/researcher's username/i).fill(skeptic.username);
        await acme.getByRole('button', { name: 'Send invitation' }).click();
        await expect(acme.getByText(`Invitation sent to ${skeptic.username}.`)).toBeVisible();
        await acme.getByTestId(`invitation-${skeptic.username}`).getByRole('button', { name: 'Revoke' }).click();
        await expect(acme.getByText(`The invitation for ${skeptic.username} was revoked.`)).toBeVisible();
        await expect(acme.getByTestId(`invitation-${skeptic.username}`)).toContainText(/revoked/i);
    });

    test('researchers cannot open the invitations screen', async () => {
        await skepticPage.goto(`/company/programs/${programId}/invitations`);
        await expect(skepticPage).not.toHaveURL(/invitations/);
    });
});
