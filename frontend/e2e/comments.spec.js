const { test, expect, pageAs, api, state } = require('./helpers');

test.describe('report comment threads', () => {
    test('researcher and triager talk, internal notes stay internal, authors wear their outfits', async ({ browser, playwright }) => {
        const reportId = state().reports.own;
        // Dress the researcher with the free starter cap so there is an outfit to see.
        const researcherApi = await api(playwright, 'parsa');
        expect((await researcherApi.post('store/items/starter-cap/purchase/')).status()).toBe(201);
        expect((await researcherApi.post('store/items/starter-cap/equip/')).status()).toBe(200);

        // 1. The researcher starts the thread.
        const researcher = await pageAs(browser, 'parsa');
        await researcher.goto(`/reports/${reportId}`);
        await expect(researcher.getByText('No comments yet')).toBeVisible();
        await expect(researcher.getByLabel('Internal note (staff only)')).toHaveCount(0);
        await researcher.getByPlaceholder('Add a comment...').fill('Here is more detail on the XSS');
        await researcher.getByRole('button', { name: 'Add Comment' }).click();
        const rootComment = researcher.locator('.ui-comment', { hasText: 'more detail on the XSS' });
        await expect(rootComment).toBeVisible();
        await expect(rootComment.locator('.ui-character-hat').first()).toHaveText('🧢'); // the cap

        // 2. The triager replies and leaves a staff-only note.
        const triager = await pageAs(browser, 'triager');
        await triager.goto(`/reports/${reportId}`);
        const parent = triager.locator('.ui-comment', { hasText: 'more detail on the XSS' }).first();
        await parent.getByRole('button', { name: 'Reply' }).first().click();
        await parent.locator('.ui-comment-form textarea').fill('Thanks, can you share a PoC?');
        await parent.locator('.ui-comment-form').getByRole('button', { name: 'Reply' }).click();
        await expect(triager.locator('.ui-comment-replies .ui-comment', { hasText: 'share a PoC' })).toBeVisible();

        await triager.getByPlaceholder('Add a comment...').fill('Looks like a duplicate, check history');
        await triager.getByLabel('Internal note (staff only)').check();
        await triager.getByRole('button', { name: 'Add Comment' }).click();
        const note = triager.locator('.ui-comment--internal', { hasText: 'check history' });
        await expect(note).toBeVisible();
        await expect(note.getByText('Internal', { exact: true })).toBeVisible();
        await expect(triager.getByText('Internal note added by triager')).toBeVisible(); // activity log

        // 3. The researcher sees the reply, but never the internal note or its log entry.
        await researcher.reload();
        await expect(researcher.locator('.ui-comment-replies .ui-comment', { hasText: 'share a PoC' })).toBeVisible();
        await expect(researcher.getByText('check history')).toHaveCount(0);
        await expect(researcher.getByText('Internal note added')).toHaveCount(0);
        await expect(researcher.locator('.ui-comment-replies .ui-comment', { hasText: 'share a PoC' })
            .getByRole('button', { name: 'Delete' })).toHaveCount(0);

        // 4. Edit, then delete the root: it stays as a placeholder and keeps its reply.
        await rootComment.getByRole('button', { name: 'Edit' }).first().click();
        await researcher.locator('.ui-comment textarea').first().fill('Edited: full XSS details attached');
        await researcher.getByRole('button', { name: 'Save' }).click();
        await expect(researcher.getByText('(edited)')).toBeVisible();
        await researcher.locator('.ui-comment', { hasText: 'Edited: full XSS' })
            .locator('> .ui-comment-actions').getByRole('button', { name: 'Delete' }).click();
        await expect(researcher.getByText('[comment deleted]')).toBeVisible();
        await expect(researcher.locator('.ui-comment-replies', { hasText: 'share a PoC' })).toBeVisible();

        expect(researcher.jsErrors).toEqual([]);
        expect(triager.jsErrors).toEqual([]);
    });
});
