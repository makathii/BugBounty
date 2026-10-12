// Browser end-to-end tests: a real browser against a real backend (PostgreSQL) with demo data.
// See e2e/README.md. In CI the servers are started by .github/workflows/ci.yml; locally start
// them yourself (docs in the README) and run `npm run e2e`.
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
    testDir: './e2e',
    globalSetup: require.resolve('./e2e/global-setup.js'),
    // The specs share one database and change it (buying, accepting), so run them in order.
    workers: 1,
    fullyParallel: false,
    retries: process.env.CI ? 1 : 0,
    timeout: 30_000,
    expect: { timeout: 7_000 },
    reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
    use: {
        baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
        trace: 'retain-on-failure',
        screenshot: 'only-on-failure',
        // Locally the browser may be pre-installed at a custom path.
        launchOptions: process.env.PLAYWRIGHT_CHROMIUM_PATH
            ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH, args: ['--no-sandbox'] }
            : { args: ['--no-sandbox'] },
    },
});
