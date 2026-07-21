/* ── Navbar — menu de navegação com estado de auth ── */
(async function () {
    // ── Conteúdo do navbar ──────────────────────────────
    const NAV_HTML = `
    <nav class="navbar">
        <a href="/dashboard" class="navbar-brand">🔴 <span>PulsoDaLive</span></a>
        <button class="navbar-toggle" id="nav-toggle" aria-label="Menu">☰</button>
        <div class="navbar-links" id="nav-links">
            <a href="/dashboard" data-page="dashboard">📊 Dashboard</a>
            <a href="/youtube-comments" data-page="youtube-comments">📺 Comentários</a>
        </div>
        <div class="navbar-right" id="nav-right">
            <div class="navbar-user" id="nav-user" style="display:none;">
                <div class="avatar" id="nav-avatar"></div>
                <span id="nav-email"></span>
            </div>
            <a href="/login" class="navbar-btn primary" id="nav-login-btn">Entrar</a>
            <button class="navbar-btn logout" id="nav-logout-btn" style="display:none;">Sair</button>
        </div>
    </nav>`;

    // ── Injetar no topo do body ─────────────────────────
    document.body.insertAdjacentHTML('afterbegin', NAV_HTML);

    // ── Toggle mobile ───────────────────────────────────
    const toggle = document.getElementById('nav-toggle');
    const links = document.getElementById('nav-links');
    if (toggle && links) {
        toggle.addEventListener('click', () => {
            links.classList.toggle('open');
        });
        // Fecha ao clicar em um link
        links.querySelectorAll('a').forEach(a => {
            a.addEventListener('click', () => links.classList.remove('open'));
        });
    }

    // ── Destacar página atual ───────────────────────────
    const currentPath = window.location.pathname;
    document.querySelectorAll('.navbar-links a').forEach(a => {
        const page = a.dataset.page;
        if (page && currentPath.startsWith('/' + page === '/dashboard' ? '/' : '/' + page)) {
            a.classList.add('active');
        }
        // Ajuste para /dashboard ser raiz
        if (page === 'dashboard' && (currentPath === '/dashboard' || currentPath === '/')) {
            a.classList.add('active');
        }
    });

    // ── Verificar auth ──────────────────────────────────
    try {
        const resp = await fetch('/api/auth/me');
        if (resp.ok) {
            const user = await resp.json();
            const navUser = document.getElementById('nav-user');
            const navEmail = document.getElementById('nav-email');
            const navAvatar = document.getElementById('nav-avatar');
            const loginBtn = document.getElementById('nav-login-btn');
            const logoutBtn = document.getElementById('nav-logout-btn');

            if (navUser) navUser.style.display = 'flex';
            if (navEmail) navEmail.textContent = user.name || user.email || '';
            if (navAvatar) navAvatar.textContent = (user.name || user.email || '?')[0].toUpperCase();
            if (loginBtn) loginBtn.style.display = 'none';
            if (logoutBtn) logoutBtn.style.display = 'inline-block';

            // Logout
            if (logoutBtn) {
                logoutBtn.addEventListener('click', async () => {
                    await fetch('/api/auth/logout', { method: 'POST' });
                    window.location.href = '/login';
                });
            }
        }
    } catch (e) {
        // Offline ou erro — só não mostra o usuario
    }
})();
