const { test, expect, anonymousPage, loginViaForm, emailedLink, createVerifiedResearcher, latestMailTo, MAIL_DIR } = require('../helpers');
const fs = require('fs');

const NEW_PASSWORD = 'Brand-New-Pw-456!';

async function requestReset(page, email) {
    await page.goto('/forgot-password');
    await page.locator('#email').fill(email);
    await page.getByRole('button', { name: /send|reset|submit/i }).click();
    await expect(page.getByText('Check Your Email')).toBeVisible();
}

test.describe('forgot and reset password', () => {
    test('reset through the emailed link: old password stops working, new one works, link is single-use', async ({ browser, playwright }) => {
        const user = await createVerifiedResearcher(playwright, 'pw');
        const page = await anonymousPage(browser);

        await requestReset(page, user.email);
        const link = await emailedLink(user.email, /\/reset-password\/[\w-]+/);

        // Bad input is explained and nothing changes.
        await page.goto(link);
        await page.locator('#password').fill(NEW_PASSWORD);
        await page.locator('#confirmPassword').fill('Something-else-789!');
        await page.getByRole('button', { name: 'Reset Password' }).click();
        await expect(page.getByText(/do not match|don't match/i)).toBeVisible();

        await page.locator('#password').fill('short');
        await page.locator('#confirmPassword').fill('short');
        await page.getByRole('button', { name: 'Reset Password' }).click();
        await expect(page.locator('.error-text, .error-message').first()).toBeVisible();
        await expect(page.getByText('Password Reset Successful')).toHaveCount(0);

        // A good password goes through and sends them to the login.
        await page.locator('#password').fill(NEW_PASSWORD);
        await page.locator('#confirmPassword').fill(NEW_PASSWORD);
        await page.getByRole('button', { name: 'Reset Password' }).click();
        await expect(page.getByText('Password Reset Successful')).toBeVisible();
        await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });

        // Old password refused, new one accepted.
        await loginViaForm(page, user.username, user.password);
        await expect(page).toHaveURL(/\/login/);
        await expect(page.locator('.error-message')).toBeVisible();
        await loginViaForm(page, user.username, NEW_PASSWORD);
        await expect(page).toHaveURL(/\/dashboard/);

        // The same link cannot be used again.
        const again = await anonymousPage(browser);
        await again.goto(link);
        await again.locator('#password').fill('Yet-Another-Pw-123!');
        await again.locator('#confirmPassword').fill('Yet-Another-Pw-123!');
        await again.getByRole('button', { name: 'Reset Password' }).click();
        await expect(again.getByText(/expired|invalid|already/i).first()).toBeVisible();
        await expect(again.getByRole('link', { name: /request a new link/i })).toBeVisible();
        expect(page.jsErrors).toEqual([]);
    });

    test('asking for a reset never reveals whether an email is registered', async ({ browser, playwright }) => {
        const user = await createVerifiedResearcher(playwright, 'pwx');
        const known = await anonymousPage(browser);
        const unknown = await anonymousPage(browser);
        await requestReset(known, user.email);
        await requestReset(unknown, `nobody-${Date.now()}@example.test`);
        // Same screen either way...
        expect(await known.locator('.auth-header').innerText()).toContain('Check Your Email');
        expect(await unknown.locator('.auth-header').innerText()).toContain('Check Your Email');
        // ...but only the real account got an email.
        expect(latestMailTo(user.email)).toContain('reset-password');
    });

    test('a made-up reset link is refused', async ({ browser }) => {
        const page = await anonymousPage(browser);
        await page.goto('/reset-password/not-a-real-token');
        await page.locator('#password').fill(NEW_PASSWORD);
        await page.locator('#confirmPassword').fill(NEW_PASSWORD);
        await page.getByRole('button', { name: 'Reset Password' }).click();
        await expect(page.getByText(/expired|invalid/i).first()).toBeVisible();
        await expect(page.getByText('Password Reset Successful')).toHaveCount(0);
    });
});
