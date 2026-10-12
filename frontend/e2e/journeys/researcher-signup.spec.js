const { test, expect, freshUser, anonymousPage, emailedLink, loginViaForm, PASSWORD } = require('../helpers');

async function fillResearcherForm(page, user, overrides = {}) {
    await page.goto('/register/researcher');
    await page.locator('#username').fill(overrides.username ?? user.username);
    await page.locator('#email').fill(overrides.email ?? user.email);
    await page.locator('#password').fill(overrides.password ?? user.password);
    await page.locator('#confirmPassword').fill(overrides.confirm ?? overrides.password ?? user.password);
    await page.locator('#firstName').fill(user.first);
    await page.locator('#lastName').fill(user.last);
    await page.locator('input[type=checkbox]').check();
}

test.describe('a new researcher joins', () => {
    test('register, verify the email, log in, and land on an empty-but-friendly dashboard', async ({ browser }) => {
        const user = freshUser('res');
        const page = await anonymousPage(browser);

        // Register.
        await fillResearcherForm(page, user);
        await page.getByRole('button', { name: /register as researcher/i }).click();
        const popup = page.getByRole('dialog');
        await expect(popup).toContainText('Successfully registered');
        await expect(popup).toContainText(user.email);

        // The account cannot be used before the email link is opened.
        await popup.getByRole('button', { name: 'Go to Login' }).click();
        await loginViaForm(page, user.username, user.password);
        await expect(page).toHaveURL(/\/login/);
        await expect(page.locator('.error-message, .alert, [role=alert]').first()).toBeVisible();

        // Open the emailed verification link.
        const link = await emailedLink(user.email, /\/verify-email\/[\w-]+/);
        await page.goto(link);
        await expect(page.getByText(/verified/i).first()).toBeVisible();

        // Now logging in works and the dashboard welcomes them.
        await loginViaForm(page, user.username, user.password);
        await expect(page).toHaveURL(/\/dashboard/);
        await expect(page.getByText(`Welcome back, ${user.first}`)).toBeVisible();
        await expect(page.locator('.ui-level-card')).toContainText('Bug Sprout');
        await expect(page.locator('.ui-stat', { hasText: 'Points Balance' })).toContainText('0 pts');
        await expect(page.locator('.ui-badge-shelf')).toContainText('0/');
        await expect(page.locator('.ui-badge-shelf')).toContainText('No badges yet');
        expect(page.jsErrors).toEqual([]);
    });

    test('the form explains what is wrong', async ({ browser }) => {
        const user = freshUser('bad');
        const page = await anonymousPage(browser);

        await fillResearcherForm(page, user, { confirm: 'Different-pw-123!' });
        await page.getByRole('button', { name: /register as researcher/i }).click();
        await expect(page.getByText(/do not match/i)).toBeVisible();

        await fillResearcherForm(page, user, { password: 'short', confirm: 'short' });
        await page.getByRole('button', { name: /register as researcher/i }).click();
        await expect(page.getByText(/at least 8 characters/i)).toBeVisible();

        await fillResearcherForm(page, user, { email: 'a@b' });
        await page.getByRole('button', { name: /register as researcher/i }).click();
        await expect(page.getByText(/email is invalid/i)).toBeVisible();
        await expect(page.getByRole('dialog')).toHaveCount(0); // nothing was created
    });

    test('a username or email that is taken is refused, and the first account keeps working', async ({ browser }) => {
        const user = freshUser('dup');
        const first = await anonymousPage(browser);
        await fillResearcherForm(first, user);
        await first.getByRole('button', { name: /register as researcher/i }).click();
        await expect(first.getByRole('dialog')).toContainText('Successfully registered');

        const second = await anonymousPage(browser);
        await fillResearcherForm(second, user, { email: `other-${user.email}` });
        await second.getByRole('button', { name: /register as researcher/i }).click();
        await expect(second.getByRole('dialog')).toHaveCount(0);
        await expect(second.locator('.error-text, .alert-danger').first()).toBeVisible();

        const third = await anonymousPage(browser);
        await fillResearcherForm(third, user, { username: `${user.username}x` });
        await third.getByRole('button', { name: /register as researcher/i }).click();
        await expect(third.getByRole('dialog')).toHaveCount(0);
        await expect(third.locator('.error-text, .alert-danger').first()).toBeVisible();
    });

    test('the emailed link only works the way it should', async ({ browser }) => {
        const page = await anonymousPage(browser);
        await page.goto('/verify-email/this-is-not-a-real-token');
        // A garbage link must say it is invalid, never claim success.
        await expect(page.getByText(/invalid|expired|not found/i).first()).toBeVisible();
        await expect(page.getByRole('heading', { name: 'Email Verified!' })).toHaveCount(0);
    });

    test('wrong password and unknown users get the same polite refusal', async ({ browser }) => {
        const page = await anonymousPage(browser);
        await loginViaForm(page, 'parsa', 'definitely-wrong');
        const wrongPassword = await page.locator('.error-message').first().innerText();
        await loginViaForm(page, 'nobody-by-this-name', 'definitely-wrong');
        const unknownUser = await page.locator('.error-message').first().innerText();
        expect(wrongPassword).toBe(unknownUser); // no hint about which usernames exist
        await expect(page).toHaveURL(/\/login/);
    });
});
