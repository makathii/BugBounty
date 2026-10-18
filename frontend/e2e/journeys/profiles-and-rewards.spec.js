const { test, expect, pageAs, anonymousPage, loginViaForm, createVerifiedResearcher, apiAsUser, api } = require('../helpers');

test.describe.configure({ mode: 'serial' });

const WORDS = ['kestrel', 'basalt', 'ember', 'quartz', 'lantern', 'marble', 'thistle', 'walrus', 'cobalt', 'sparrow',
    'velvet', 'harbor', 'juniper', 'nimbus', 'orchid', 'pylon', 'ripple', 'saffron', 'tundra', 'umber', 'vortex', 'willow'];
const pick = (n) => Array.from({ length: n }, () => WORDS[Math.floor(Math.random() * WORDS.length)]).join(' ');

test.describe('public profiles', () => {
    let hunter;
    let hunterPage;
    let visitor;
    let visitorPage;

    test.beforeAll(async ({ playwright, browser }) => {
        hunter = await createVerifiedResearcher(playwright, 'prof');
        visitor = await createVerifiedResearcher(playwright, 'peek');
        hunterPage = await anonymousPage(browser);
        await loginViaForm(hunterPage, hunter.username, hunter.password);
        visitorPage = await anonymousPage(browser);
        await loginViaForm(visitorPage, visitor.username, visitor.password);
    });

    test('the leaderboard links to a researcher\'s page with character, level and badges', async () => {
        await visitorPage.goto('/leaderboard');
        await visitorPage.getByRole('link', { name: 'nova' }).first().click();
        await expect(visitorPage).toHaveURL(/\/researchers\/nova$/);
        await expect(visitorPage.getByRole('heading', { name: 'nova' })).toBeVisible();
        await expect(visitorPage.getByText(/^Lv \d/)).toBeVisible();
        await expect(visitorPage.getByRole('img', { name: "nova's character" })).toBeVisible();
        await expect(visitorPage.getByText('Lifetime points')).toBeVisible();
        await expect(visitorPage.getByRole('region', { name: 'Badges' })).toBeVisible();
        await expect(visitorPage.getByText('Your profile')).toHaveCount(0); // someone else's page: no settings
    });

    test('an unknown name is a plain not-found', async () => {
        await visitorPage.goto('/researchers/nobody-by-this-name');
        await expect(visitorPage.getByText(/no researcher with that name/i)).toBeVisible();
    });

    test('a researcher sets a bio and hides the page; others can no longer open it', async () => {
        await hunterPage.goto('/dashboard');
        await hunterPage.getByRole('button', { name: /my profile/i }).click();
        await expect(hunterPage).toHaveURL(new RegExp(`/researchers/${hunter.username}$`));
        await hunterPage.getByLabel(/short intro/i).fill('Breaking things politely.');
        await hunterPage.getByRole('button', { name: 'Save' }).click();
        await expect(hunterPage.getByText('Saved.')).toBeVisible();

        await visitorPage.goto(`/researchers/${hunter.username}`);
        await expect(visitorPage.getByText('Breaking things politely.')).toBeVisible();

        await hunterPage.getByRole('checkbox').uncheck();
        await hunterPage.getByRole('button', { name: 'Save' }).click();
        await expect(hunterPage.getByText(/your profile is hidden/i)).toBeVisible();

        await visitorPage.goto(`/researchers/${hunter.username}`);
        await expect(visitorPage.getByText(/no researcher with that name/i)).toBeVisible();
    });
});

test.describe('badges that unlock items', () => {
    test('a first accepted report earns First Blood and its reward lands in the inventory', async ({ browser, playwright }) => {
        const researcher = await createVerifiedResearcher(playwright, 'gift');
        const page = await anonymousPage(browser);
        await loginViaForm(page, researcher.username, researcher.password);

        // Before: the reward is listed, locked.
        await page.goto('/store');
        await page.getByRole('button', { name: /badge rewards/i }).click();
        const plaster = page.locator('.ui-item-card', { hasText: 'Battle Plaster' });
        await expect(plaster.getByRole('button', { name: /earn the first blood badge/i })).toBeDisabled();

        // A report gets accepted (API: the browser journeys for triage live in triage.spec.js).
        const researcherApi = await apiAsUser(playwright, researcher);
        const listing = await (await researcherApi.get('programs/public/')).json();
        const program = (listing.results || listing).find((p) => p.name === 'Acme Web Platform');
        const created = await researcherApi.post('reports/', { data: {
            title: `${pick(4)} gift finding`, description: `${pick(12)} ${pick(14)}`, steps_to_reproduce: pick(10),
            impact: pick(8), vulnerability_type: 'other', affected_url: 'https://acme.example/x',
            is_human_generated: true, program: program.id, severity: 'low',
        } });
        expect(created.status(), await created.text()).toBe(201);
        const report = await created.json();
        const triager = await api(playwright, 'triager');
        expect((await triager.post(`reports/${report.id}/triage/`, { data: { severity: 'low' } })).status()).toBe(200);
        const accepted = await triager.post(`reports/${report.id}/accept/`, { data: { verification_notes: 'ok' } });
        expect(accepted.status(), await accepted.text()).toBe(200);

        // After: the badge, and the item is already theirs.
        await page.goto('/badges');
        await expect(page.getByTestId('rewards-first_blood')).toContainText('Unlocked');
        await page.goto('/store');
        await page.getByRole('button', { name: /my items \(1\)/i }).click();
        const mine = page.locator('.ui-item-card', { hasText: 'Battle Plaster' });
        await mine.getByRole('button', { name: 'Wear' }).click();
        await expect(mine.getByRole('button', { name: 'Take off' })).toBeVisible();

        // ...and it shows on their public page.
        await page.goto(`/researchers/${researcher.username}`);
        await expect(page.getByTestId('profile-badge-first_blood')).toBeVisible();
        await expect(page.getByRole('img', { name: 'Battle Plaster' })).toBeVisible();
    });

    test('the shop has plenty to choose from', async ({ browser }) => {
        const page = await pageAs(browser, 'parsa');
        await page.goto('/store');
        await expect(page.locator('.ui-item-card').first()).toBeVisible();
        expect(await page.locator('.ui-item-card').count()).toBeGreaterThan(25);
    });
});
