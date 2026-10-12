const { test, expect, pageAs, api } = require('./helpers');

const pts = (n) => `${n.toLocaleString()} pts`;

test.describe('the store', () => {
    test('browse, try on, buy, wear and take off', async ({ browser, playwright }) => {
        const researcherApi = await api(playwright, 'parsa');
        const before = await (await researcherApi.get('store/items/')).json();
        const hat = before.items.find((i) => i.slug === 'detective-hat');
        expect(hat.owned).toBe(false);
        const ownedBefore = before.items.filter((i) => i.owned).length;
        expect(before.balance).toBeGreaterThanOrEqual(hat.price); // the demo researcher can afford it

        const page = await pageAs(browser, 'parsa');
        await page.goto('/dashboard');
        await page.getByRole('link', { name: 'Store', exact: true }).click();
        const card = (name) => page.locator('.ui-item-card', { has: page.locator('strong', { hasText: new RegExp(`^${name}$`) }) });

        await expect(page.locator('.ui-item-card')).toHaveCount(before.items.length);
        await expect(page.getByText(pts(before.balance), { exact: true }).first()).toBeVisible();
        // A level-gated item explains itself and cannot be bought.
        const gated = before.items.find((i) => i.locked);
        if (gated) await expect(card(gated.name).getByRole('button', { name: `Level ${gated.min_level} needed` })).toBeDisabled();

        // Try on previews it on the character without buying.
        await card('Detective Hat').getByRole('button', { name: 'Try on' }).click();
        await expect(page.locator('.ui-store-side .ui-character-hat')).toHaveText('🕵️');
        await expect(page.getByText(/Trying on/)).toBeVisible();

        // Buy: toast, balance drops by exactly the price, can't buy twice.
        await card('Detective Hat').getByRole('button', { name: 'Buy' }).click();
        await expect(page.getByRole('status')).toContainText('You bought Detective Hat');
        await expect(card('Detective Hat').getByRole('button', { name: 'Wear' })).toBeVisible();
        await expect(card('Detective Hat').getByRole('button', { name: 'Buy' })).toHaveCount(0);
        const after = await (await researcherApi.get('store/items/')).json();
        expect(before.balance - after.balance).toBe(hat.price);
        const wallet = await (await researcherApi.get('wallet/')).json();
        expect(wallet.total_spent).toBe(hat.price);

        // Wear it: it shows on the dashboard and the leaderboard; take it off again.
        await card('Detective Hat').getByRole('button', { name: 'Wear' }).click();
        await expect(card('Detective Hat').getByRole('button', { name: 'Take off' })).toBeVisible();
        await page.getByRole('link', { name: 'Leaderboard', exact: true }).click();
        await expect(page.locator('.lb-entry', { hasText: 'parsa' }).locator('.ui-character-hat')).toHaveText('🕵️');
        await page.getByRole('link', { name: 'Dashboard', exact: true }).first().click();
        await expect(page.locator('header .ui-character-hat')).toHaveText('🕵️');
        await page.getByRole('link', { name: 'Store', exact: true }).click();
        await card('Detective Hat').getByRole('button', { name: 'Take off' }).click();
        await expect(card('Detective Hat').getByRole('button', { name: 'Wear' })).toBeVisible();
        await expect(page.locator('.ui-store-side .ui-character-hat')).toHaveCount(0);

        // My items lists only what is owned.
        await page.getByRole('button', { name: /My items/ }).click();
        await expect(page.locator('.ui-item-card')).toHaveCount(ownedBefore + 1);
        expect(page.jsErrors).toEqual([]);
    });

    test('someone who cannot afford an item is told how short they are', async ({ browser, playwright }) => {
        // nova has fewer points than the priciest unlocked item; the API tells us which.
        const novaApi = await api(playwright, 'nova');
        const shop = await (await novaApi.get('store/items/')).json();
        const tooPricey = shop.items.find((i) => !i.locked && !i.can_afford);
        test.skip(!tooPricey, 'the demo researcher can afford everything they are allowed to buy');
        const page = await pageAs(browser, 'nova');
        await page.goto('/store');
        const short = tooPricey.price - shop.balance;
        await expect(page.getByRole('button', { name: `${pts(short)} short` }).first()).toBeDisabled();
    });
});
