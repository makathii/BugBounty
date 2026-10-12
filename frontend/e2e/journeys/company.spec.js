const { test, expect, freshUser, anonymousPage, loginViaForm, emailedLink, createVerifiedResearcher, apiAsUser } = require('../helpers');

const WORDS = ['kestrel', 'basalt', 'ember', 'quartz', 'lantern', 'marble', 'thistle', 'walrus', 'cobalt', 'sparrow',
    'velvet', 'harbor', 'juniper', 'nimbus', 'orchid', 'pylon', 'ripple', 'saffron', 'tundra', 'umber', 'vortex', 'willow'];
const pick = (n) => Array.from({ length: n }, () => WORDS[Math.floor(Math.random() * WORDS.length)]).join(' ');

test.describe.configure({ mode: 'serial' });

test.describe('a company joins, launches a program and receives a report', () => {
    const company = freshUser('co');
    const programName = `Launchpad ${Date.now().toString(36)}`;
    let page;           // the company's browser
    let programId;

    test('sign up, verify the email, complete the company profile', async ({ browser }) => {
        page = await anonymousPage(browser);
        await page.goto('/register/company');
        await page.locator('#username').fill(company.username);
        await page.locator('#email').fill(company.email);
        await page.locator('#password').fill(company.password);
        await page.locator('#confirmPassword').fill(company.password);
        await page.locator('#firstName').fill('Casey');
        await page.locator('#lastName').fill('Owner');
        await page.locator('#companyName').fill('Launchpad Ltd');
        await page.locator('input[type=checkbox]').check();
        await page.getByRole('button', { name: /create company account/i }).click();
        await expect(page.getByRole('dialog')).toContainText('Successfully registered');

        await page.goto(await emailedLink(company.email, /\/verify-email\/[\w-]+/));
        await expect(page.getByText(/verified/i).first()).toBeVisible();

        // First login: the company profile is required before anything else.
        await loginViaForm(page, company.username, company.password);
        await expect(page).toHaveURL(/\/company-registration/);
        await page.goto('/company-dashboard');
        await expect(page).toHaveURL(/\/company-registration/); // cannot skip it by typing the address

        await page.locator('#company_name').fill('Launchpad Ltd');
        await page.locator('#website').fill('https://launchpad.example');
        await page.locator('#industry').selectOption({ index: 1 });
        await page.locator('#contact_email').fill('security@launchpad.example');
        await page.locator('#country').fill('Netherlands');
        await page.locator('#description').fill('We build rocket-grade software and want it tested.');
        await page.getByRole('button', { name: 'Complete Profile' }).click();
        await expect(page).toHaveURL(/\/company-dashboard/);
        await expect(page.getByText(/no programs|create your first/i).first()).toBeVisible();
    });

    test('create a program with the wizard; it stays hidden from researchers until activated', async ({ browser, playwright }) => {
        await page.goto('/company/programs/create');
        // Step 1: basics
        await page.locator('input[name=name]').fill(programName);
        await page.locator('input[name=short_description]').fill('Break our rockets (digitally).');
        await page.locator('textarea[name=description]').fill('Everything under *.launchpad.example is in scope. ' + pick(12));
        await page.getByRole('button', { name: /next/i }).click();
        // Step 2: scope
        await page.locator('input[placeholder*="example.com"]').first().fill('*.launchpad.example');
        await page.getByRole('button', { name: /next/i }).click();
        // Step 3: rewards
        await page.locator('textarea[name=reward_notes]').fill('Bonus points for well-written reports.');
        await page.locator('input[name=min_points]').fill('10');
        await page.locator('input[name=max_points]').fill('150');
        await page.getByRole('button', { name: /review/i }).click();
        // Step 4: review and create
        await expect(page.getByText(programName).first()).toBeVisible();
        await page.getByRole('button', { name: /create program/i }).click();
        await expect(page.getByText('Program created!')).toBeVisible();
        await expect(page.getByText(/draft/i).first()).toBeVisible();

        // A draft is invisible to researchers.
        const peeker = await createVerifiedResearcher(playwright, 'peek');
        const peekApi = await apiAsUser(playwright, peeker);
        const names = async () => (await (await peekApi.get('programs/researcher/')).json()).map((p) => p.name);
        expect(await names()).not.toContain(programName);

        // Activate: now they can see it.
        const activation = page.waitForResponse((r) => /\/programs\/\d+\/activate\//.test(r.url()));
        await page.getByRole('button', { name: /activate now/i }).click();
        expect((await activation).status(), 'activation request').toBe(200);
        await expect(page).toHaveURL(/\/company\/programs|\/programs\/\d+|\/company-dashboard/);
        expect(await names()).toContain(programName);

        const mine = await apiAsUser(playwright, company);
        const list = await (await mine.get('programs/company/')).json();
        const created = (list.results || list).find((p) => p.name === programName);
        expect(created.status).toBe('active');
        programId = created.id;
        expect(created.points_range).toBe('10 - 150 pts');
    });

    test('a researcher reports to it; the company sees the report and can talk to the researcher', async ({ browser, playwright }) => {
        const researcher = await createVerifiedResearcher(playwright, 'finder');
        const rPage = await anonymousPage(browser);
        await loginViaForm(rPage, researcher.username, researcher.password);
        await rPage.goto(`/submit?program=${programId}`);
        const title = `${pick(6)} order tampering`;
        await rPage.locator('[name=title]').fill(title);
        await rPage.locator('[name=vulnerability_type]').selectOption({ index: 5 });
        await rPage.locator('[name=affected_url]').fill('https://shop.launchpad.example/orders');
        await rPage.locator('textarea[name=description]').fill(`${pick(12)} ${pick(14)}`);
        await rPage.locator('[name=steps_to_reproduce]').fill(pick(10));
        await rPage.locator('[name=impact]').fill(pick(10));
        await rPage.locator('[name=is_human_generated]').check();
        await rPage.getByRole('button', { name: 'Submit Report' }).click();
        await expect(rPage).toHaveURL(/\/reports$/);

        // The company sees it on its dashboard and in its report list.
        await page.goto('/company-dashboard');
        await expect(page.locator('.ui-stat', { hasText: 'Total Reports' })).toContainText('1');
        await page.goto('/company/reports');
        await expect(page.getByText(title)).toBeVisible();
        await page.getByText(title).first().click();
        await expect(page).toHaveURL(/\/reports\/\d+/);
        await expect(page.getByRole('heading', { name: title })).toBeVisible();
        const reportUrl = page.url();

        // Companies read and discuss; they do not triage or pay out.
        await expect(page.getByRole('button', { name: /start triage|accept|reject/i })).toHaveCount(0);
        await page.getByPlaceholder('Add a comment...').fill('Thanks! Can you share the exact request?');
        await page.getByRole('button', { name: 'Add Comment' }).click();
        await expect(page.locator('.ui-comment', { hasText: 'exact request' })).toBeVisible();
        await expect(page.getByLabel('Internal note (staff only)')).toHaveCount(0);

        await rPage.goto(reportUrl.replace(/^https?:\/\/[^/]+/, ''));
        await expect(rPage.locator('.ui-comment', { hasText: 'exact request' })).toBeVisible();
    });

    test('a company only ever sees its own programs and reports', async ({ browser }) => {
        // Acme's demo report (id 1) belongs to someone else's program.
        await page.goto('/reports/1');
        await expect(page.getByText(/not found|don't have access/i).first()).toBeVisible();
        await expect(page.getByText('Stored XSS in product review')).toHaveCount(0);
        await page.goto('/company/reports');
        await expect(page.getByText('Stored XSS in product review')).toHaveCount(0);
        await page.goto('/company/programs');
        await expect(page.getByText('Acme Web Platform')).toHaveCount(0);
        await expect(page.getByText(programName)).toBeVisible();
    });
});
