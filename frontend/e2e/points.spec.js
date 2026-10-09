const { test, expect, pageAs, api, state } = require('./helpers');

const pts = (n) => `${n.toLocaleString()} pts`;

test.describe('points, levels, badges and the leaderboard', () => {
    test('a researcher sees a consistent wallet, level, badges and rank', async ({ browser, playwright }) => {
        const researcherApi = await api(playwright, 'parsa');
        const wallet = await (await researcherApi.get('wallet/')).json();
        const badges = await (await researcherApi.get('badges/')).json();
        expect(wallet.balance).toBeGreaterThan(0);

        const page = await pageAs(browser, 'parsa');
        await page.goto('/dashboard');
        // Level card matches the API.
        const levelCard = page.locator('.ui-level-card');
        await expect(levelCard).toContainText(`Level ${wallet.level.level}`);
        await expect(levelCard).toContainText(wallet.level.title);
        await expect(levelCard.getByRole('progressbar'))
            .toHaveAttribute('aria-valuenow', String(Math.round(wallet.level.progress * 100)));
        // Balance card and badge shelf match too.
        await expect(page.locator('.ui-stat', { hasText: 'Points Balance' })).toContainText(pts(wallet.balance));
        await expect(page.locator('.ui-badge-shelf')).toContainText(`${badges.earned_count}/${badges.total}`);
        await expect(page.locator('.ui-badge-icon')).toHaveCount(badges.earned_count);

        // Wallet page.
        await page.getByRole('link', { name: 'Wallet', exact: true }).click();
        await expect(page.getByRole('heading', { name: 'My Wallet' })).toBeVisible();
        await expect(page.locator('.ui-stat', { hasText: 'Balance' })).toContainText(pts(wallet.balance));
        await expect(page.locator('.ui-stat', { hasText: 'Lifetime Earned' })).toContainText(pts(wallet.lifetime_earned));

        // Badges page: earned ones are marked, locked ones show progress.
        await page.getByRole('link', { name: 'Badges', exact: true }).click();
        await expect(page.locator('.ui-badge-card')).toHaveCount(badges.total);
        await expect(page.locator('.ui-badge-card.is-earned')).toHaveCount(badges.earned_count);
        await expect(page.locator('.ui-badge-card.is-locked [role=progressbar]').first()).toBeVisible();

        // Leaderboard: every row has a level chip and a character; our row is marked.
        await page.getByRole('link', { name: 'Leaderboard', exact: true }).click();
        await expect(page.locator('.lb-entry').first()).toBeVisible();
        const rows = await page.locator('.lb-entry').count();
        await expect(page.locator('.lb-entry .ui-level-chip')).toHaveCount(rows);
        await expect(page.locator('.lb-entry .ui-character')).toHaveCount(rows);
        await expect(page.locator('.lb-entry', { hasText: 'parsa' })).toContainText('you');
        expect(page.jsErrors).toEqual([]);
    });

    test('accepting a report with bonus points pays the researcher exactly severity + bonus', async ({ browser, playwright }) => {
        const reportId = state().reports.triaged;
        const researcherApi = await api(playwright, 'parsa');
        const before = await (await researcherApi.get('wallet/')).json();

        const triager = await pageAs(browser, 'triager');
        await triager.goto(`/reports/${reportId}`);
        await triager.getByRole('button', { name: 'Accept' }).first().click();
        const dialog = triager.locator('.ui-modal');
        await dialog.getByPlaceholder('0').fill('5000'); // absurd: must be refused with a message
        await dialog.locator('textarea').fill('Confirmed, reproduced locally');
        await dialog.getByRole('button', { name: 'Accept' }).click();
        await expect(dialog.getByText(/bonus_points must be/)).toBeVisible();
        await dialog.getByPlaceholder('0').fill('20');
        await dialog.getByRole('button', { name: 'Accept' }).click();
        await expect(triager.locator('.ui-badge', { hasText: 'pts' })).toBeVisible();

        const report = await (await (await api(playwright, 'triager')).get(`reports/${reportId}/`)).json();
        expect(report.status).toBe('accepted');
        expect(report.bonus_points).toBe(20);
        expect(report.points_awarded).toBeGreaterThanOrEqual(20);
        const after = await (await researcherApi.get('wallet/')).json();
        expect(after.balance - before.balance).toBe(report.points_awarded);
        expect(after.lifetime_earned - before.lifetime_earned).toBe(report.points_awarded);

        // The researcher sees the points on their report and in the wallet.
        const researcher = await pageAs(browser, 'parsa');
        await researcher.goto(`/reports/${reportId}`);
        await expect(researcher.locator('.ui-badge', { hasText: `+${pts(report.points_awarded)}` })).toBeVisible();
        expect(triager.jsErrors).toEqual([]);
    });
});
