/*
 * Harness minimo para executar app/static/js/dashboard.js (o script real,
 * sem mocks do proprio codigo) dentro de um DOM/fetch simulados, e checar
 * como checkAuthState()/loadLives() reagem a respostas 401 de
 * /api/auth/me e /api/chat/lives.
 *
 * Uso: node _dashboard_auth_harness.js <caminho para dashboard.js>
 * Imprime um JSON com o resultado em stdout.
 */
const vm = require('vm');
const fs = require('fs');

function createStub() {
    const classes = new Set();
    return {
        _classes: classes,
        classList: {
            add: (...cls) => cls.forEach(c => classes.add(c)),
            remove: (...cls) => cls.forEach(c => classes.delete(c)),
            toggle: (c, force) => {
                if (force === undefined) { classes.has(c) ? classes.delete(c) : classes.add(c); }
                else if (force) classes.add(c); else classes.delete(c);
            },
            contains: (c) => classes.has(c),
        },
        value: '',
        textContent: '',
        innerHTML: '',
        style: {},
        dataset: {},
        options: [],
        href: '',
        disabled: false,
        addEventListener: () => {},
        removeEventListener: () => {},
        appendChild: () => {},
        removeChild: () => {},
        querySelector: () => createStub(),
        querySelectorAll: () => [],
    };
}

const registry = {};
const document = {
    getElementById: (id) => {
        if (!registry[id]) registry[id] = createStub();
        return registry[id];
    },
    createElement: () => createStub(),
    body: createStub(),
    documentElement: createStub(),
    addEventListener: () => {},
};

// O script chama checkAuthState() automaticamente na ultima linha, de forma
// assincrona, no exato momento em que eh carregado (vm.runInContext logo
// abaixo). Por isso o mock de 401 precisa estar ativo ANTES do load —
// caso contrario a chamada automatica corre em paralelo com o cenario
// controlado abaixo usando um mock diferente (race condition real).
let fetchMock = async (url) => {
    const u = String(url);
    if (u.includes('/api/auth/me') || u.includes('/lives')) {
        return { ok: false, status: 401, json: async () => ({ detail: 'Not authenticated' }) };
    }
    return { ok: true, status: 200, json: async () => ({}) };
};

const sandbox = {
    document,
    fetch: (...args) => fetchMock(...args),
    Chart: function Chart() { this.destroy = () => {}; },
    getComputedStyle: () => ({ getPropertyValue: () => '' }),
    console,
    setTimeout, clearTimeout, setInterval, clearInterval,
    URL: { createObjectURL: () => '', revokeObjectURL: () => {} },
    alert: () => {},
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);

const scriptPath = process.argv[2];
const src = fs.readFileSync(scriptPath, 'utf8');
// Carrega o script real; isso ja dispara a chamada automatica a
// checkAuthState() da ultima linha, usando o fetchMock de 401 acima.
vm.runInContext(src, sandbox, { filename: 'dashboard.js' });

async function main() {
    const results = {};

    // ── Cenario: /api/auth/me E /api/chat/lives respondem 401 ──────
    let checkAuthThrew = false;
    try {
        await sandbox.checkAuthState();
    } catch (e) {
        checkAuthThrew = true;
        results.checkAuthStateError = String(e && e.stack || e);
    }
    results.checkAuthStateThrew = checkAuthThrew;
    results.loginFormVisible = !document.getElementById('login-form')._classes.has('hidden');
    results.userInfoHidden = document.getElementById('user-info')._classes.has('hidden');
    results.dataSectionHidden = document.getElementById('data-section')._classes.has('hidden');

    let loadLivesThrew = false;
    try {
        await sandbox.loadLives();
    } catch (e) {
        loadLivesThrew = true;
        results.loadLivesError = String(e && e.stack || e);
    }
    results.loadLivesThrew = loadLivesThrew;

    // Deixa qualquer handleUnauthorized() pendente (disparado pelo 401 de
    // /lives dentro de apiFetch) terminar antes de checar o estado final.
    try {
        if (sandbox.authCheckInFlight) await sandbox.authCheckInFlight;
    } catch (e) {}

    results.loginFormVisibleAfterLoadLives = !document.getElementById('login-form')._classes.has('hidden');
    results.dataSectionHiddenAfterLoadLives = document.getElementById('data-section')._classes.has('hidden');

    console.log(JSON.stringify(results));
}

main();
