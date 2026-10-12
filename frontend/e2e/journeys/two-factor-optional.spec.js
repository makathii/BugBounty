const { test, expect, anonymousPage, loginViaForm, createVerifiedResearcher, totp, letCodeWindowPass } = require('../helpers');

// A one-time code is single-use. Between steps we let the "30 seconds" pass for the user (see helper)
// instead of really waiting, then use the current code.
const codeFor = (username, secret) => { letCodeWindowPass(username); return totp(secret); };

test.describe('optional two-factor authentication for a researcher', () => {
    test('enable it, sign in with a code, regenerate backup codes, then disable it', async ({ browser, playwright }) => {
        const user = await createVerifiedResearcher(playwright, 'tfa');
        const page = await anonymousPage(browser);
        await loginViaForm(page, user.username, user.password);
        await expect(page).toHaveURL(/\/dashboard/);

        // Off by default; the settings page offers to enable it.
        await page.goto('/2fa/settings');
        await expect(page.getByText('Secure Your Account')).toBeVisible();
        await page.getByRole('button', { name: 'Enable Two-Factor Authentication' }).click();
        await expect(page).toHaveURL(/\/2fa\/setup/);

        await expect(page.locator('code.tf-secret')).toHaveText(/^[A-Z2-7]{16,}$/);
        const secret = (await page.locator('code.tf-secret').innerText()).trim();
        await page.getByPlaceholder('000000').fill(codeFor(user.username, secret));
        await page.getByRole('button', { name: /verify & enable/i }).click();
        await expect(page.getByText('Save Your Backup Codes')).toBeVisible();
        const codes = await page.locator('.tf-codes div').allInnerTexts();
        expect(codes.length).toBeGreaterThanOrEqual(8);
        await page.getByRole('button', { name: 'Continue to Dashboard' }).click();
        await expect(page).toHaveURL(/\/dashboard/);

        // Settings now says it is on.
        await page.goto('/2fa/settings');
        await expect(page.getByText(/enabled/i).first()).toBeVisible();
        await expect(page.getByText(new RegExp(`${codes.length} backup codes`))).toBeVisible();

        // A fresh sign-in now needs the code.
        const second = await anonymousPage(browser);
        await loginViaForm(second, user.username, user.password);
        await expect(second).toHaveURL(/\/2fa\/verify/);
        await second.locator('#code').fill(codeFor(user.username, secret));
        await second.getByRole('button', { name: /verify|sign in/i }).click();
        await expect(second).toHaveURL(/\/dashboard/);

        // Regenerate the backup codes (needs a code); the old ones stop working.
        await page.getByRole('button', { name: 'Regenerate Backup Codes' }).click();
        await page.locator('#mfa-code').fill(codeFor(user.username, secret));
        await page.getByRole('button', { name: /regenerate|confirm|yes/i }).last().click();
        await expect(page.locator('.tf-codes div').first()).toBeVisible();
        const fresh = await page.locator('.tf-codes div').allInnerTexts();
        expect(fresh).not.toEqual(codes);
        const third = await anonymousPage(browser);
        await loginViaForm(third, user.username, user.password);
        await third.getByRole('button', { name: /backup code/i }).click();
        await third.locator('#code').fill(codes[0]);
        await third.getByRole('button', { name: /verify|sign in/i }).click();
        await expect(third).toHaveURL(/\/2fa\/verify/); // the old code is dead
        await expect(third.locator('.error-message, .tf-error, [role=alert]').first()).toBeVisible();

        // Disable it (needs a code too) and sign-in goes back to password-only.
        await page.getByRole('button', { name: /disable two-factor/i }).click();
        await page.locator('#mfa-code').fill(codeFor(user.username, secret));
        await page.getByRole('button', { name: 'Yes, Disable' }).click();
        await expect(page.getByText('Secure Your Account')).toBeVisible();
        const fourth = await anonymousPage(browser);
        await loginViaForm(fourth, user.username, user.password);
        await expect(fourth).toHaveURL(/\/dashboard/);
    });

    test('the wrong code cannot switch it off', async ({ browser, playwright }) => {
        const user = await createVerifiedResearcher(playwright, 'tfb');
        const page = await anonymousPage(browser);
        await loginViaForm(page, user.username, user.password);
        await page.goto('/2fa/setup');
        await expect(page.locator('code.tf-secret')).toHaveText(/^[A-Z2-7]{16,}$/);
        const secret = (await page.locator('code.tf-secret').innerText()).trim();
        await page.getByPlaceholder('000000').fill(codeFor(user.username, secret));
        await page.getByRole('button', { name: /verify & enable/i }).click();
        await expect(page.getByText('Save Your Backup Codes')).toBeVisible();

        await page.goto('/2fa/settings');
        await page.getByRole('button', { name: /disable two-factor/i }).click();
        await page.locator('#mfa-code').fill('000000');
        await page.getByRole('button', { name: 'Yes, Disable' }).click();
        await expect(page.locator('.error-message, .tf-error, [role=alert]').first()).toBeVisible();
        await expect(page.getByText(/enabled/i).first()).toBeVisible(); // still on
    });
});
