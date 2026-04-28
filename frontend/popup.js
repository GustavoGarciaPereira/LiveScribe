const API = 'http://127.0.0.1:8000';

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const loggedIn = document.getElementById('logged-in');
    const status = document.getElementById('status');
    const loginBtn = document.getElementById('login-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const displayEmail = document.getElementById('display-email');

    if (!loginForm || !loggedIn || !status) {
        console.error('PulsoDaLive: Elementos do DOM não encontrados no popup.');
        return;
    }

    function setStatus(msg, color) {
        status.textContent = msg;
        status.style.color = color || '#f1f5f9';
    }

    function updateUI() {
        chrome.storage.local.get(['token', 'user_email'], (result) => {
            if (result.token && result.user_email) {
                loginForm.style.display = 'none';
                loggedIn.style.display = 'block';
                displayEmail.textContent = result.user_email;
            } else {
                loginForm.style.display = 'block';
                loggedIn.style.display = 'none';
            }
        });
    }

    updateUI();

    loginBtn.addEventListener('click', async () => {
        const email = emailInput.value.trim();
        const password = passwordInput.value.trim();
        if (!email || !password) {
            setStatus('Preencha email e senha.', '#f87171');
            return;
        }
        setStatus('Autenticando...', '#f1f5f9');
        try {
            const resp = await fetch(`${API}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await resp.json();
            if (!resp.ok) {
                setStatus(data.detail || 'Erro ao autenticar.', '#f87171');
                return;
            }
            chrome.storage.local.set({ token: data.access_token, user_email: data.user.email }, () => {
                setStatus('Login efetuado! ✅', '#4ade80');
                updateUI();
            });
        } catch (e) {
            setStatus('Servidor offline.', '#f87171');
        }
    });

    logoutBtn.addEventListener('click', () => {
        chrome.storage.local.remove(['token', 'user_email'], () => {
            updateUI();
        });
    });
});
