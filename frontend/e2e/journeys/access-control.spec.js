const { test, expect, pageAs, anonymousPage, loginViaForm, emailedLink, createVerifiedResearcher } = require('../helpers');

test.describe('who can see what', () => {
    test('logged-out visitors are sent to the login page from every private page', async ({ browser }) => {
        const page = await anonymousPage(browser);
        for (const path of ['/dashboard', '/reports', '/submit', '/wallet', '/store', '/badges', '/programs',
            '/triage', '/company-dashboard', '/company/programs', '/2fa/settings', '/leaderboard']) {
            await page.goto(path);
            await expect(page, `${path} should require login`).toHaveURL(/\/login|\/$/);
            await expect(page.getByRole('heading', { name: /welcome back|bug bounty|sign in/i }).first()).toBeVisible();
        }
        // The public pages stay public.
        for (const path of ['/', '/register/researcher', '/register/company', '/forgot-password']) {
            await page.goto(path);
            await expect(page).toHaveURL(new RegExp(`${path === '/' ? '/$' : path}`));
        }
    });

    test('a researcher cannot open staff or company pages', async ({ browser }) => {
        const page = await pageAs(browser, 'parsa');
        for (const path of ['/triage', '/company-dashboard', '/company/programs', '/company/programs/create', '/company/reports']) {
            await page.goto(path);
            await expect(page, `researcher must not stay on ${path}`).not.toHaveURL(new RegExp(`${path}$`));
        }
    });

    test('a triager cannot open researcher-only pages (store, wallet) or company pages', async ({ browser }) => {
        const page = await pageAs(browser, 'triager');
        for (const path of ['/store', '/wallet', '/badges', '/company-dashboard']) {
            await page.goto(path);
            await expect(page, `triager must not stay on ${path}`).not.toHaveURL(new RegExp(`${path}$`));
        }
        await page.goto('/triage');
        await expect(page).toHaveURL(/\/triage/);
    });

    test('a researcher cannot read another researcher\'s report, even by guessing its address', async ({ browser, playwright }) => {
        // nova owns report 4; parsa does not.
        const page = await pageAs(browser, 'parsa');
        await page.goto('/reports/4');
        await expect(page.getByText(/not found|don't have access/i).first()).toBeVisible();
        await expect(page.getByText('IDOR allows reading')).toHaveCount(0);
    });

    test('logging out really ends the session, not just the screen', async ({ browser, playwright }) => {
        const user = await createVerifiedResearcher(playwright, 'out');
        const page = await anonymousPage(browser);
        await loginViaForm(page, user.username, user.password);
        await expect(page).toHaveURL(/\/dashboard/);

        // Remember the credentials the browser holds right now.
        const access = await page.evaluate(() => localStorage.getItem('access_token'));
        const cookies = await page.context().cookies();
        const accessCookie = cookies.find((c) => c.name === 'bb_access');
        expect(access || accessCookie).toBeTruthy();
        const withStolenCredentials = async () => {
            const ctx = await playwright.request.newContext({
                baseURL: (process.env.E2E_API_URL || 'http://localhost:8000/api') + '/',
                extraHTTPHeaders: access ? { Authorization: `Bearer ${access}` } : { Cookie: `bb_access=${accessCookie.value}` },
            });
            return (await ctx.get('users/profile/')).status();
        };
        expect(await withStolenCredentials()).toBe(200);

        const loggedOut = page.waitForResponse((r) => /\/users\/logout\//.test(r.url()) && r.request().method() === 'POST');
        await page.getByRole('button', { name: 'Logout' }).click();
        expect((await loggedOut).status(), 'the server is told about the logout').toBe(200);
        await expect(page).toHaveURL(/\/login|\/$/);
        await page.goto('/dashboard');
        await expect(page).toHaveURL(/\/login|\/$/);
        // Anyone who copied the token before logout gets nothing from it.
        expect(await withStolenCredentials()).toBe(401);
    });

    test('resetting a password signs out whoever was logged in with the old one', async ({ browser, playwright }) => {
        const user = await createVerifiedResearcher(playwright, 'hijack');
        const victimsOldSession = await anonymousPage(browser);
        await loginViaForm(victimsOldSession, user.username, user.password);
        await expect(victimsOldSession).toHaveURL(/\/dashboard/);

        // The owner resets the password from somewhere else.
        const owner = await anonymousPage(browser);
        await owner.goto('/forgot-password');
        await owner.locator('#email').fill(user.email);
        await owner.getByRole('button', { name: /send|reset|submit/i }).click();
        await expect(owner.getByText('Check Your Email')).toBeVisible();
        await owner.goto(await emailedLink(user.email, /\/reset-password\/[\w-]+/));
        await owner.locator('#password').fill('Totally-New-Pw-321!');
        await owner.locator('#confirmPassword').fill('Totally-New-Pw-321!');
        await owner.getByRole('button', { name: 'Reset Password' }).click();
        await expect(owner.getByText('Password Reset Successful')).toBeVisible();

        // The old browser session is dead: it is thrown out to the login page.
        await victimsOldSession.goto('/dashboard');
        await expect(victimsOldSession).toHaveURL(/\/login|\/$/, { timeout: 10_000 });
    });
});

test.describe('the admin dashboard', () => {
    test('every card leads somewhere that exists', async ({ browser }) => {
        const page = await pageAs(browser, 'admin');
        await page.goto('/dashboard');
        await expect(page.getByRole('heading', { name: 'Admin Dashboard' })).toBeVisible();
        const cards = page.locator('.ui-card.ui-card--hover');
        expect(await cards.count()).toBeGreaterThanOrEqual(3);
        // Cards that open the Django admin are real links to it...
        for (const link of await page.locator('.ui-card--hover a.ui-btn').all()) {
            expect(await link.getAttribute('href')).toMatch(/\/admin\//);
        }
        // ...and the in-app ones land on a real page, not the home page the router falls back to.
        for (const label of ['Go to Triage Dashboard', 'View All Reports']) {
            await page.goto('/dashboard');
            await page.getByRole('button', { name: label }).click();
            await expect(page).not.toHaveURL(/localhost:3000\/?$/);
            await expect(page.getByRole('heading').first()).toBeVisible();
        }
    });
});
