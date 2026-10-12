const { test, expect, anonymousPage, loginViaForm, totp, letCodeWindowPass } = require('../helpers');

const STAFF = { username: 'e2e_triager', password: 'Demo1234!' };
// A one-time code is single-use. Between steps we let the "30 seconds" pass for the account (see the
// helper) instead of really waiting, then use the current code.
const freshCode = (secret) => { letCodeWindowPass(STAFF.username); return totp(secret); };

test.describe.configure({ mode: 'serial' });

test.describe('two-factor authentication for staff', () => {
    let secret;
    let backupCodes;

    test('a triager must enrol before they can use the app', async ({ browser }) => {
        const page = await anonymousPage(browser);
        await loginViaForm(page, STAFF.username, STAFF.password);

        // Password accepted, but no session yet: they are sent to enrolment.
        await expect(page).toHaveURL(/\/2fa\/enroll/);
        await expect(page.getByText('Setup Two-Factor Authentication')).toBeVisible();
        await expect(page.locator('code.tf-secret')).toHaveText(/^[A-Z2-7]{16,}$/); // loaded from the server
        secret = (await page.locator('code.tf-secret').innerText()).trim();
        await expect(page.getByRole('button', { name: /verify & enable/i })).toBeDisabled(); // needs 6 digits

        // A wrong code is refused and nothing is enabled.
        await page.getByPlaceholder('000000').fill('000000');
        await page.getByRole('button', { name: /verify & enable/i }).click();
        await expect(page.locator('.error-message, .tf-error, [role=alert]').first()).toBeVisible();
        await expect(page.getByText('Save Your Backup Codes')).toHaveCount(0);

        // The right code enables it and hands over backup codes once.
        await page.getByPlaceholder('000000').fill(freshCode(secret));
        await page.getByRole('button', { name: /verify & enable/i }).click();
        await expect(page.getByText('Save Your Backup Codes')).toBeVisible();
        backupCodes = await page.locator('.tf-codes div').allInnerTexts();
        expect(backupCodes.length).toBeGreaterThanOrEqual(8);
        expect(new Set(backupCodes).size).toBe(backupCodes.length);

        // Still no session: they have to sign in again, now with the second factor.
        await page.getByRole('button', { name: 'Continue to Sign In' }).click();
        await expect(page).toHaveURL(/\/login/);
        expect(page.jsErrors).toEqual([]);
    });

    test('signing in then needs the one-time code (wrong code refused, right one accepted)', async ({ browser }) => {
        const page = await anonymousPage(browser);
        await loginViaForm(page, STAFF.username, STAFF.password);
        await expect(page).toHaveURL(/\/2fa\/verify/);

        await page.locator('#code').fill('123456');
        await page.getByRole('button', { name: /verify|sign in/i }).click();
        await expect(page).toHaveURL(/\/2fa\/verify/);
        await expect(page.locator('.error-message, .tf-error, [role=alert]').first()).toBeVisible();

        await page.locator('#code').fill(freshCode(secret));
        await page.getByRole('button', { name: /verify|sign in/i }).click();
        await expect(page).toHaveURL(/\/dashboard/);
        await expect(page.getByRole('link', { name: 'Triage Reports' })).toBeVisible();
    });

    test('a backup code works once and only once', async ({ browser }) => {
        const code = backupCodes[0];
        for (const attempt of [1, 2]) {
            const page = await anonymousPage(browser);
            await loginViaForm(page, STAFF.username, STAFF.password);
            await expect(page).toHaveURL(/\/2fa\/verify/);
            await page.getByRole('button', { name: /backup code/i }).click();
            await page.locator('#code').fill(code);
            await page.getByRole('button', { name: /verify|sign in/i }).click();
            if (attempt === 1) {
                await expect(page).toHaveURL(/\/dashboard/);
            } else {
                await expect(page).toHaveURL(/\/2fa\/verify/); // already used
                await expect(page.locator('.error-message, .tf-error, [role=alert]').first()).toBeVisible();
            }
        }
    });

    test('staff cannot switch 2FA off, and settings shows what is left', async ({ browser }) => {
        const page = await anonymousPage(browser);
        await loginViaForm(page, STAFF.username, STAFF.password);
        await page.locator('#code').fill(freshCode(secret));
        await page.getByRole('button', { name: /verify|sign in/i }).click();
        await expect(page).toHaveURL(/\/dashboard/);

        await page.goto('/2fa/settings');
        await expect(page.getByText('Two-Factor Authentication Settings')).toBeVisible();
        await expect(page.getByText(/required for your role/i)).toBeVisible();
        await expect(page.getByRole('button', { name: /disable two-factor/i })).toHaveCount(0);
        await expect(page.getByText(/backup codes remaining/i)).toContainText(String(backupCodes.length - 1));
    });

    test('a code that was just used cannot be used again (no replay)', async ({ browser }) => {
        letCodeWindowPass(STAFF.username);
        const code = totp(secret);
        const first = await anonymousPage(browser);
        await loginViaForm(first, STAFF.username, STAFF.password);
        await first.locator('#code').fill(code);
        await first.getByRole('button', { name: /verify|sign in/i }).click();
        await expect(first).toHaveURL(/\/dashboard/);

        // Someone who saw that code a moment ago tries it too.
        const attacker = await anonymousPage(browser);
        await loginViaForm(attacker, STAFF.username, STAFF.password);
        await attacker.locator('#code').fill(code);
        await attacker.getByRole('button', { name: /verify|sign in/i }).click();
        await expect(attacker).toHaveURL(/\/2fa\/verify/);
        await expect(attacker.locator('.error-message, .tf-error, [role=alert]').first()).toBeVisible();
    });
});
