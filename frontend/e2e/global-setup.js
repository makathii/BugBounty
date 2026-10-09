// Resets the demo state and mints login tokens (the app keeps its JWTs in localStorage).
// Needs a migrated database seeded with scripts/seed_demo.py. Configure with:
//   E2E_BACKEND_DIR  path to backend/ (default ../backend)
//   E2E_PYTHON       python with the backend requirements (default `python`)
// plus the usual DJANGO_SETTINGS_MODULE (config.e2e_settings) and POSTGRES_* variables.
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

module.exports = async () => {
    const backend = path.resolve(process.env.E2E_BACKEND_DIR || path.join(__dirname, '..', '..', 'backend'));
    const script = fs.readFileSync(path.join(backend, 'scripts', 'e2e_prepare.py'), 'utf8');
    const out = execFileSync(process.env.E2E_PYTHON || 'python', ['manage.py', 'shell'], {
        cwd: backend,
        input: script,
        env: { ...process.env, E2E_RESET: '1' },
        encoding: 'utf8',
    });
    const json = out.trim().split('\n').pop();
    fs.writeFileSync(path.join(__dirname, '.state.json'), json);
};
