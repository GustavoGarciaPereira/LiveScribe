const API = '/api/chat';

function getHeaders() {
    return {};
}

// ── Sessao / autenticacao: fonte unica de verdade ──────────────────
// setAuthUI() eh o UNICO lugar que alterna a visibilidade de login-form /
// user-info / data-section. checkAuthState() (resultado de /api/auth/me)
// e handleUnauthorized() (qualquer fetch autenticado que responda 401)
// convergem para ca, evitando estados dessincronizados ("Logado como X"
// e o formulario de login visiveis ao mesmo tempo).
function setAuthUI(loggedIn, email) {
    if (loggedIn) {
        loginForm.classList.add('hidden');
        userInfo.classList.remove('hidden');
        displayEmail.textContent = email || '';
        dataSection.classList.remove('hidden');
    } else {
        loginForm.classList.remove('hidden');
        userInfo.classList.add('hidden');
        dataSection.classList.add('hidden');
        hideLoading();
    }
}

let authCheckInFlight = null;

// Reavalia o estado de autenticacao (via checkAuthState) quando qualquer
// chamada autenticada retorna 401. Deduplicado para nao disparar N
// requisicoes simultaneas a /api/auth/me quando varios cards falham juntos.
function handleUnauthorized() {
    if (!authCheckInFlight) {
        authCheckInFlight = checkAuthState().finally(() => { authCheckInFlight = null; });
    }
    return authCheckInFlight;
}

// Wrapper de fetch para todos os endpoints autenticados do dashboard.
// `credentials: 'same-origin'` garante que o cookie httpOnly access_token
// seja enviado mesmo apos reload/navegacao direta. Um 401 aciona
// handleUnauthorized() automaticamente, entao os chamadores so precisam
// checar `res.ok` para decidir como renderizar o proprio card.
async function apiFetch(url, options = {}) {
    const res = await fetch(url, {
        ...options,
        credentials: 'same-origin',
        headers: { ...getHeaders(), ...(options.headers || {}) },
    });
    if (res.status === 401) {
        handleUnauthorized();
    }
    return res;
}

// ── Design tokens (mirrors CSS custom properties in dashboard.css) ─
function cssVar(name, fallback) {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name);
    return v && v.trim() ? v.trim() : fallback;
}

const COLORS = {
    positive: cssVar('--color-positive', '#22c55e'),
    positiveStrong: cssVar('--color-positive-strong', '#16a34a'),
    positiveSoft: cssVar('--color-positive-soft', '#4ade80'),
    negative: cssVar('--color-negative', '#ef4444'),
    negativeStrong: cssVar('--color-negative-strong', '#dc2626'),
    negativeSoft: cssVar('--color-negative-soft', '#f87171'),
    neutral: cssVar('--color-neutral', '#94a3b8'),
    accent: cssVar('--color-accent', '#3b82f6'),
    accent2: cssVar('--color-accent-2', '#f97316'),
    accent3: cssVar('--color-accent-3', '#8b5cf6'),
    accent4: cssVar('--color-accent-4', '#f59e0b'),
    accent5: cssVar('--color-accent-5', '#6366f1'),
    accent6: cssVar('--color-accent-6', '#84cc16'),
};

// ── Loading indicator ──────────────────────────────
function showLoading(msg) {
    const overlay = document.getElementById('loading-overlay');
    if (!overlay) return;
    overlay.querySelector('span').textContent = msg || 'Carregando dados da live...';
    overlay.classList.remove('hidden');
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.classList.add('hidden');
}

// ── Debounce utility ───────────────────────────────
function debounce(fn, delay) {
    let timer;
    return function(...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

// ── Contextual empty state messages ────────────────
const EMPTY_MESSAGES = {
    timeline: 'Nenhum dado de sentimento disponivel para esta live',
    peaks: 'Nenhum pico de engajamento detectado nesta live',
    words: 'Nenhuma palavra frequente encontrada nesta live',
    topics: 'Nenhum topico extraido para esta live',
    emojis: 'Nenhum emoji identificado nas mensagens desta live',
    authors: 'Nenhum autor encontrado nesta live',
    'term-timeline': 'Adicione termos acima para ver sua evolucao',
    questions: 'Nenhuma pergunta detectada nesta live',
    modality: 'Nenhum dado de modalidade disponivel para esta live',
    emotion: 'Nenhum dado de emocao disponivel para esta live',
    'topic-sentiment': 'Nenhum dado de sentimento por topico disponivel',
    framing: 'Nenhum enquadramento identificado nesta live',
    sarcasm: 'Nenhum dado de sarcasmo disponivel para esta live',
    aspects: 'Nenhum aspecto/entidade encontrado nesta live',
};

let timelineChart, peaksChart, wordsChart, topicsChart, emojisChart, termTimelineChart, modalityChart, emotionChart, topicSentimentChart, framingChart, sarcasmChart, aspectsChart;

let livesData = [];
let cachedData = {};
let activeTerms = [];
let currentFilters = { sentiment: 'Todos', timeStart: '', timeEnd: '' };
let questionsShowAll = false;

// ── Shared empty/loading state renderers (used by every card) ─────
function renderEmptyState(container, message) {
    if (!container) return;
    container.innerHTML = '<span class="state-icon" aria-hidden="true">📭</span><span class="state-message">' + escapeHtml(message) + '</span>';
}

function renderLoadingState(sectionId) {
    const loadingEl = document.getElementById(sectionId + '-loading');
    const emptyEl = document.getElementById(sectionId + '-empty');
    const canvasEl = document.getElementById(sectionId + '-chart');
    const listEl = document.getElementById(sectionId + '-list');
    if (loadingEl) loadingEl.classList.remove('hidden');
    if (emptyEl) emptyEl.classList.add('hidden');
    if (canvasEl) canvasEl.classList.add('hidden');
    if (listEl) listEl.classList.add('hidden');
}

function showEmpty(sectionId, show) {
    const loadingEl = document.getElementById(sectionId + '-loading');
    if (loadingEl) loadingEl.classList.add('hidden');
    const emptyEl = document.getElementById(sectionId + '-empty');
    if (emptyEl && show && EMPTY_MESSAGES[sectionId]) {
        renderEmptyState(emptyEl, EMPTY_MESSAGES[sectionId]);
    }
    const canvasEl = document.getElementById(sectionId + '-chart');
    const listEl = document.getElementById(sectionId + '-list');
    if (emptyEl) emptyEl.classList.toggle('hidden', !show);
    if (canvasEl) canvasEl.classList.toggle('hidden', show);
    if (listEl) listEl.classList.toggle('hidden', show);
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function matchesTimeFilter(timeStr) {
    if (!currentFilters.timeStart && !currentFilters.timeEnd) return true;
    const hhmm = timeStr ? timeStr.slice(0, 5) : '';
    if (currentFilters.timeStart && hhmm < currentFilters.timeStart) return false;
    if (currentFilters.timeEnd && hhmm > currentFilters.timeEnd) return false;
    return true;
}

async function loadLives() {
    try {
        const res = await apiFetch(`${API}/lives`);
        if (!res.ok) {
            // 401 ja foi tratado por apiFetch (handleUnauthorized esconde o
            // dashboard); qualquer outro erro so evita renderizar lives.
            return;
        }
        const data = await res.json();
        livesData = Array.isArray(data.lives) ? data.lives : [];
        renderLiveOptions('');
    } catch (e) {
        livesData = [];
    }
}

function renderLiveOptions(filter) {
    const select = document.getElementById('live-select');
    const current = select.value;
    select.innerHTML = '<option value="">-- Selecione uma live --</option>';
    const f = filter.toLowerCase();
    (Array.isArray(livesData) ? livesData : []).forEach(l => {
        if (f && !l.live_id.toLowerCase().includes(f)) return;
        select.innerHTML += `<option value="${escapeHtml(l.live_id)}">${escapeHtml(l.live_id)} (${l.total_messages} msgs)</option>`;
    });
    select.value = current;
}

document.getElementById('live-search').addEventListener('input', (e) => {
    renderLiveOptions(e.target.value);
});

document.getElementById('live-select').addEventListener('change', async (e) => {
    const liveId = e.target.value;
    const badge = document.getElementById('live-status');
    const filterBar = document.getElementById('filter-bar');
    const linkBtn = document.getElementById('live-link-btn');
    currentFilters = { sentiment: 'Todos', timeStart: '', timeEnd: '' };
    document.getElementById('filter-sentiment').value = 'Todos';
    document.getElementById('filter-time-start').value = '';
    document.getElementById('filter-time-end').value = '';
    if (!liveId) {
        badge.classList.add('hidden');
        filterBar.classList.add('hidden');
        linkBtn.classList.add('hidden');
        const liveContext = document.getElementById('live-context');
        if (liveContext) liveContext.classList.add('hidden');
        return;
    }
    linkBtn.href = 'https://www.youtube.com/watch?v=' + liveId;
    linkBtn.classList.remove('hidden');
    const live = livesData.find(l => l.live_id === liveId);
    if (live) {
        const isLive = live.last_message_at && (Date.now() - new Date(live.last_message_at).getTime()) < 10 * 60 * 1000;
        badge.textContent = (isLive ? 'Ao vivo' : 'Encerrada') + ' · ' + live.total_messages + ' msgs';
        badge.className = 'badge ' + (isLive ? 'badge-live' : 'badge-ended');
        badge.classList.remove('hidden');
    }
    filterBar.classList.remove('hidden');
    activeTerms = [];
    renderTermTags();
    showLoading('Carregando analises da live...');
    await Promise.all([
        loadTimeline(liveId),
        loadPeaks(liveId),
        loadWords(liveId),
        loadTopics(liveId),
        loadEmojis(liveId),
        loadTopAuthors(liveId),
        loadTermTimeline(liveId),
        loadQuestions(liveId),
        loadModalityTimeline(liveId),
        loadEmotionTimeline(liveId),
        loadTopicSentiment(liveId),
        loadSentimentSummary(liveId),
        loadFraming(liveId),
        loadSarcasm(liveId),
        loadAspects(liveId),
    ]);
    hideLoading();
    updateFooterStats(liveId);
});

function updateFooterStats(liveId) {
    const footer = document.getElementById('stats-footer');
    const liveContext = document.getElementById('live-context');
    const live = livesData.find(l => l.live_id === liveId);
    if (!live) {
        footer.classList.add('hidden');
        if (liveContext) liveContext.classList.add('hidden');
        return;
    }
    footer.classList.remove('hidden');
    document.getElementById('footer-total-msgs').textContent = live.total_messages;
    const authorsData = cachedData.authors;
    const uniqueAuthors = authorsData && authorsData.authors ? authorsData.authors.length : '?';
    document.getElementById('footer-unique-authors').textContent = uniqueAuthors;
    let duration = '—';
    if (live.first_message_at && live.last_message_at) {
        const diff = new Date(live.last_message_at) - new Date(live.first_message_at);
        const hrs = Math.floor(diff / 3600000);
        const mins = Math.floor((diff % 3600000) / 60000);
        duration = (hrs > 0 ? hrs + 'h ' : '') + mins + 'min';
    }
    document.getElementById('footer-duration').textContent = duration;

    // Indicador de live selecionada, fixado no topo (barra sticky) para dar contexto ao rolar a pagina
    if (liveContext) {
        document.getElementById('live-context-id').textContent = liveId;
        document.getElementById('live-context-msgs').textContent = '📊 ' + live.total_messages + ' mensagens';
        document.getElementById('live-context-duration').textContent = '⏱️ ' + duration;
        liveContext.classList.remove('hidden');
    }
}
function applyTimeFilters(timeline) {
    if (!currentFilters.timeStart && !currentFilters.timeEnd) return timeline;
    return timeline.filter(b => matchesTimeFilter(b.start_time));
}

async function loadTimeline(liveId) {
    renderLoadingState('timeline');
    try {
        const res = await apiFetch(`${API}/${liveId}/sentiment-timeline?interval_minutes=5&sentiment_filter=${currentFilters.sentiment}&time_start=${currentFilters.timeStart}&time_end=${currentFilters.timeEnd}`);
        if (!res.ok) { showEmpty('timeline', true); return; }
        const data = await res.json();
        cachedData.timeline = data;
        renderTimeline();
    } catch (e) { showEmpty('timeline', true); }
}

function renderTimeline() {
    const data = cachedData.timeline;
    if (!data || !data.timeline || data.timeline.length === 0) {
        showEmpty('timeline', true);
        return;
    }
    showEmpty('timeline', false);
    const filtered = applyTimeFilters(data.timeline);
    if (filtered.length === 0) { showEmpty('timeline', true); return; }
    const labels = filtered.map(b => b.start_time.slice(11,16));
    const datasets = [];
    const colors = { Positivo: COLORS.positive, Negativo: COLORS.negative, Neutro: COLORS.neutral };
    for (const [name, color] of Object.entries(colors)) {
        if (currentFilters.sentiment !== 'Todos' && currentFilters.sentiment !== name) continue;
        const values = filtered.map(b => b.sentiments[name]);
        // Marcadores nos pontos com mudanca significativa
        const pointBg = filtered.map(b => {
            if (!b.significant_change) return color;
            if (b.change_direction === 'rise') return COLORS.positiveSoft;
            if (b.change_direction === 'drop') return COLORS.negativeSoft;
            return color;
        });
        const pointRadius = filtered.map(b => b.significant_change ? 7 : 3);
        const pointBorderColor = filtered.map(b => {
            if (!b.significant_change) return color;
            if (b.change_direction === 'rise') return COLORS.positiveStrong;
            if (b.change_direction === 'drop') return COLORS.negativeStrong;
            return COLORS.neutral;
        });
        const pointBorderWidth = filtered.map(b => b.significant_change ? 3 : 1);
        datasets.push({
            label: name,
            data: values,
            borderColor: color,
            fill: false,
            pointBackgroundColor: pointBg,
            pointRadius: pointRadius,
            pointBorderColor: pointBorderColor,
            pointBorderWidth: pointBorderWidth,
            pointHoverRadius: filtered.map(b => b.significant_change ? 10 : 5),
        });
    }
    if (timelineChart) timelineChart.destroy();
    timelineChart = new Chart(document.getElementById('timeline-chart'), {
        type: 'line', data: { labels, datasets }, options: {
            responsive: true, scales: { y: { beginAtZero: true } },
            plugins: {
                tooltip: {
                    callbacks: {
                        afterLabel: function(ctx) {
                            const b = filtered[ctx.dataIndex];
                            if (!b || !b.significant_change) return '';
                            const dir = b.change_direction === 'rise' ? 'subida' : b.change_direction === 'drop' ? 'queda' : 'estavel';
                            return 'Mudanca significativa (p=' + b.p_value + ') — ' + dir + ' de ' + b.change_magnitude + ' pontos';
                        }
                    }
                }
            }
        }
    });
}

async function loadSentimentSummary(liveId) {
    try {
        const res = await apiFetch(`${API}/${liveId}/sentiment`);
        if (!res.ok) {
            const el = document.getElementById('sentiment-stats');
            if (el) el.classList.add('hidden');
            return;
        }
        const data = await res.json();
        cachedData.sentimentSummary = data;
        renderSentimentStats();
    } catch (e) {
        const el = document.getElementById('sentiment-stats');
        if (el) el.classList.add('hidden');
    }
}

function renderSentimentStats() {
    const data = cachedData.sentimentSummary;
    const el = document.getElementById('sentiment-stats');
    if (!el) return;
    if (!data || !data.statistics) { el.classList.add('hidden'); return; }
    const stats = data.statistics;
    if (stats.mean === undefined || stats.mean === null) { el.classList.add('hidden'); return; }
    el.classList.remove('hidden');
    const color = stats.mean > 0.05 ? COLORS.positive : stats.mean < -0.05 ? COLORS.negative : COLORS.neutral;
    let html = '<span style="color:' + color + ';font-weight:600;">M\u00e9dia: ' + stats.mean.toFixed(2) + '</span>';
    if (stats.ci_95) {
        html += ' &nbsp;\u00b7&nbsp; <span style="color:#64748b;">IC 95%: [' + stats.ci_95[0].toFixed(2) + ', ' + stats.ci_95[1].toFixed(2) + ']</span>';
    }
    el.innerHTML = html;
}

async function loadPeaks(liveId) {
    renderLoadingState('peaks');
    try {
        const res = await apiFetch(`${API}/${liveId}/engagement-peaks?top_n=10&window_minutes=1`);
        if (!res.ok) { showEmpty('peaks', true); return; }
        const data = await res.json();
        cachedData.peaks = data;
        renderPeaks();
    } catch (e) { showEmpty('peaks', true); }
}

function renderPeaks() {
    const data = cachedData.peaks;
    if (!data || !data.peaks || data.peaks.length === 0) {
        showEmpty('peaks', true);
        return;
    }
    showEmpty('peaks', false);
    const filtered = data.peaks.filter(p => matchesTimeFilter(p.time));
    if (filtered.length === 0) { showEmpty('peaks', true); return; }
    const labels = filtered.map(p => p.time.slice(11,16));
    const counts = filtered.map(p => p.message_count);
    if (peaksChart) peaksChart.destroy();
    peaksChart = new Chart(document.getElementById('peaks-chart'), {
        type: 'bar', data: { labels, datasets: [{ label: 'Mensagens', data: counts, backgroundColor: COLORS.accent2 }] },
        options: { responsive: true, scales: { y: { beginAtZero: true } } }
    });
}

async function loadWords(liveId) {
    renderLoadingState('words');
    try {
        const res = await apiFetch(`${API}/${liveId}/word-frequency?top_n=10`);
        if (!res.ok) { showEmpty('words', true); return; }
        const data = await res.json();
        cachedData.words = data;
        renderWords();
    } catch (e) { showEmpty('words', true); }
}

function renderWords() {
    const data = cachedData.words;
    if (!data || !data.word_frequency || data.word_frequency.length === 0) {
        showEmpty('words', true);
        return;
    }
    showEmpty('words', false);
    const labels = data.word_frequency.map(w => w.palavra);
    const counts = data.word_frequency.map(w => w.frequencia);
    if (wordsChart) wordsChart.destroy();
    wordsChart = new Chart(document.getElementById('words-chart'), {
        type: 'bar', data: { labels, datasets: [{ label: 'Frequencia', data: counts, backgroundColor: COLORS.accent }] },
        options: { responsive: true, indexAxis: 'y' }
    });
}

async function loadTopics(liveId) {
    renderLoadingState('topics');
    try {
        const res = await apiFetch(`${API}/${liveId}/topics?top_n=10`);
        if (!res.ok) { showEmpty('topics', true); return; }
        const data = await res.json();
        cachedData.topics = data;
        renderTopics();
    } catch (e) { showEmpty('topics', true); }
}

function renderTopics() {
    const data = cachedData.topics;
    if (!data || !data.topics || data.topics.length === 0) {
        showEmpty('topics', true);
        return;
    }
    showEmpty('topics', false);
    const labels = data.topics.map(t => t.term);
    const scores = data.topics.map(t => t.score);
    if (topicsChart) topicsChart.destroy();
    topicsChart = new Chart(document.getElementById('topics-chart'), {
        type: 'bar', data: { labels, datasets: [{ label: 'Score TF-IDF', data: scores, backgroundColor: COLORS.accent3 }] },
        options: { responsive: true, indexAxis: 'y' }
    });
}

async function loadEmojis(liveId) {
    renderLoadingState('emojis');
    try {
        const res = await apiFetch(API + '/' + liveId + '/emojis?top_n=10');
        if (!res.ok) { showEmpty('emojis', true); return; }
        const data = await res.json();
        cachedData.emojis = data;
        renderEmojis();
    } catch (e) { showEmpty('emojis', true); }
}

function renderEmojis() {
    const data = cachedData.emojis;
    if (!data || !data.emojis || data.emojis.length === 0) {
        showEmpty('emojis', true);
        return;
    }
    showEmpty('emojis', false);
    const labels = data.emojis.map(e => e.emoji);
    const counts = data.emojis.map(e => e.count);
    const colors = data.emojis.map(e => e.sentiment === 'Positivo' ? COLORS.positive : e.sentiment === 'Negativo' ? COLORS.negative : COLORS.neutral);
    if (emojisChart) emojisChart.destroy();
    emojisChart = new Chart(document.getElementById('emojis-chart'), {
        type: 'bar', data: { labels, datasets: [{ label: 'Ocorrencias', data: counts, backgroundColor: colors }] },
        options: { responsive: true, scales: { y: { beginAtZero: true } } }
    });
}

async function loadTopAuthors(liveId) {
    renderLoadingState('authors');
    try {
        const res = await apiFetch(API + '/' + liveId + '/top-authors?top_n=20');
        if (!res.ok) { showEmpty('authors', true); return; }
        const data = await res.json();
        cachedData.authors = data;
        renderAuthors();
    } catch (e) { showEmpty('authors', true); }
}

function renderAuthors() {
    const data = cachedData.authors;
    const list = document.getElementById('top-authors-list');
    if (!data || !data.authors || data.authors.length === 0) {
        showEmpty('authors', true);
        list.innerHTML = '';
        return;
    }
    showEmpty('authors', false);
    let html = '<table style="width:100%; border-collapse:collapse;"><tr style="color:var(--color-text-muted);font-size:13px;"><th style="text-align:left;padding:4px;">Autor</th><th style="text-align:right;padding:4px;">Msgs</th><th style="text-align:right;padding:4px;">Sentimento</th></tr>';
    data.authors.forEach(a => {
        const cls = a.avg_sentiment === 'Positivo' ? 'sent-pos' : a.avg_sentiment === 'Negativo' ? 'sent-neg' : 'sent-neu';
        html += '<tr><td style="padding:4px;">' + escapeHtml(a.author) + '</td><td style="text-align:right;padding:4px;">' + a.messages + '</td><td style="text-align:right;padding:4px;"><span class="sent-badge ' + cls + '">' + escapeHtml(a.avg_sentiment || 'Neutro') + '</span></td></tr>';
    });
    html += '</table>';
    list.innerHTML = html;
}

async function loadTermTimeline(liveId) {
    if (activeTerms.length === 0) {
        if (termTimelineChart) termTimelineChart.destroy();
        termTimelineChart = null;
        showEmpty('term-timeline', true);
        return;
    }
    renderLoadingState('term-timeline');
    cachedData.termTimelines = {};
    try {
        const results = await Promise.all(activeTerms.map(async term => {
            const r = await apiFetch(API + '/' + liveId + '/topic-timeline?term=' + encodeURIComponent(term) + '&interval_minutes=5');
            if (!r.ok) throw new Error('Falha ao carregar evolucao do termo ' + term);
            return r.json();
        }));
        const colors = [COLORS.accent, COLORS.accent2, COLORS.accent3, COLORS.positive, COLORS.negative, COLORS.accent4, COLORS.accent5, COLORS.accent6];
        const datasets = [];
        results.forEach((data, i) => {
            cachedData.termTimelines[activeTerms[i]] = data;
            datasets.push({
                label: activeTerms[i],
                data: data.timeline.map(b => b.count),
                borderColor: colors[i % colors.length],
                fill: false,
                tension: 0.2,
            });
        });
        const labels = results[0].timeline.map(b => b.start_time.slice(11,16));
        if (termTimelineChart) termTimelineChart.destroy();
        termTimelineChart = new Chart(document.getElementById('term-timeline-chart'), {
            type: 'line', data: { labels, datasets },
            options: { responsive: true, scales: { y: { beginAtZero: true } } }
        });
    } catch (e) { showEmpty('term-timeline', true); }
}

function addTermTag(term) {
    term = term.trim().toLowerCase();
    if (!term || activeTerms.includes(term)) return;
    activeTerms.push(term);
    renderTermTags();
    const liveId = document.getElementById('live-select').value;
    if (liveId) loadTermTimeline(liveId);
}

function removeTermTag(term) {
    activeTerms = activeTerms.filter(t => t !== term);
    renderTermTags();
    const liveId = document.getElementById('live-select').value;
    if (liveId) loadTermTimeline(liveId);
}

function renderTermTags() {
    const container = document.getElementById('term-tags-container');
    const input = document.getElementById('term-tag-input');
    let html = '';
    activeTerms.forEach(t => {
        html += '<span class="tag">' + escapeHtml(t) + '<span class="tag-remove" onclick="removeTermTag(\'' + t.replace(/'/g, '\\\'') + '\')">&times;</span></span>';
    });
    input.value = '';
    container.innerHTML = html;
    container.appendChild(input);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); addTermTag(input.value); }
    });
}

async function loadQuestions(liveId) {
    renderLoadingState('questions');
    try {
        const res = await apiFetch(API + '/' + liveId + '/questions?min_length=10');
        if (!res.ok) { showEmpty('questions', true); return; }
        const data = await res.json();
        cachedData.questions = data;
        renderQuestions();
    } catch (e) { showEmpty('questions', true); }
}

function renderQuestions() {
    const data = cachedData.questions;
    const list = document.getElementById('questions-list');
    const searchEl = document.getElementById('questions-search');
    const filter = (searchEl.value || '').toLowerCase();
    if (!data || !data.questions || data.questions.length === 0) {
        showEmpty('questions', true);
        list.innerHTML = '';
        return;
    }
    const filtered = filter ? data.questions.filter(q => q.text.toLowerCase().includes(filter) || q.examples.some(e => e.toLowerCase().includes(filter))) : data.questions;
    if (filtered.length === 0) {
        showEmpty('questions', true);
        list.innerHTML = '';
        return;
    }
    showEmpty('questions', false);

    // Se nao ha filtro ativo, limita a 10 itens por padrao (expansivel)
    const showAll = filter || questionsShowAll;
    const displayItems = showAll ? filtered : filtered.slice(0, 10);

    let html = '<table style="width:100%; border-collapse:collapse;">';
    html += '<tr style="color:var(--color-text-muted);font-size:13px;"><th style="text-align:left;padding:4px;">Pergunta</th><th style="text-align:right;padding:4px;">Mencoes</th></tr>';
    displayItems.forEach(q => {
        const examplesStr = q.examples.length > 1 ? ' (ex: ' + q.examples.slice(0,2).map(e => '"' + e + '"').join(', ') + ')' : '';
        html += '<tr><td style="padding:4px;font-size:14px;">' + escapeHtml(q.text) + '<br><span style="font-size:11px;color:#64748b;">' + escapeHtml(examplesStr) + '</span></td><td style="text-align:right;padding:4px;">' + q.count + '</td></tr>';
    });
    html += '</table>';

    // Botao "Ver mais" / "Ver menos" (so quando nao ha filtro ativo)
    if (!filter && filtered.length > 10) {
        const label = showAll ? '▲ Ver menos' : '▼ Ver mais (' + (filtered.length - 10) + ' ocultas)';
        html += '<div style="text-align:center;margin-top:0.5rem;"><button id="questions-toggle-btn" style="font-size:0.8rem;padding:0.3rem 1rem;background:transparent;border:1px solid var(--color-accent);color:var(--color-accent);border-radius:6px;cursor:pointer;">' + label + '</button></div>';
    }

    list.innerHTML = html;

    // Vincula o evento depois de inserir no DOM
    const toggleBtn = document.getElementById('questions-toggle-btn');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            questionsShowAll = !questionsShowAll;
            renderQuestions();
        });
    }
}

document.getElementById('questions-search').addEventListener('input', debounce(function() {
    questionsShowAll = false;
    if (cachedData.questions) renderQuestions();
}, 300));

async function loadModalityTimeline(liveId) {
    renderLoadingState('modality');
    try {
        const res = await apiFetch(API + '/' + liveId + '/modality-timeline?interval_minutes=5');
        if (!res.ok) { showEmpty('modality', true); return; }
        const data = await res.json();
        cachedData.modality = data;
        renderModality();
    } catch (e) { showEmpty('modality', true); }
}

function renderModality() {
    const data = cachedData.modality;
    if (!data || !data.timeline || data.timeline.length === 0) {
        showEmpty('modality', true);
        return;
    }
    showEmpty('modality', false);
    const filtered = applyTimeFilters(data.timeline);
    if (filtered.length === 0) { showEmpty('modality', true); return; }
    const labels = filtered.map(b => b.start_time.slice(11,16));
    if (modalityChart) modalityChart.destroy();
    modalityChart = new Chart(document.getElementById('modality-chart'), {
        type: 'line',
        data: {
            labels,
            datasets: [
                { label: 'Certeza', data: filtered.map(b => b.certeza), borderColor: COLORS.positive, fill: false, tension: 0.3 },
                { label: 'Duvida', data: filtered.map(b => b.duvida), borderColor: COLORS.accent2, fill: false, tension: 0.3 },
                { label: 'Enfase', data: filtered.map(b => b.enfase), borderColor: COLORS.accent3, fill: false, tension: 0.3 },
            ]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true } } }
    });
}

async function loadEmotionTimeline(liveId) {
    renderLoadingState('emotion');
    try {
        const res = await apiFetch(API + '/' + liveId + '/emotion-timeline?interval_minutes=1');
        if (!res.ok) { showEmpty('emotion', true); return; }
        const data = await res.json();
        cachedData.emotion = data;
        renderEmotion();
    } catch (e) { showEmpty('emotion', true); }
}

function renderEmotion() {
    const data = cachedData.emotion;
    if (!data || !data.timeline || data.timeline.length === 0) {
        showEmpty('emotion', true);
        return;
    }
    showEmpty('emotion', false);
    const filtered = applyTimeFilters(data.timeline);
    if (filtered.length === 0) { showEmpty('emotion', true); return; }
    const labels = filtered.map(b => b.start_time.slice(11,16));
    if (emotionChart) emotionChart.destroy();
    emotionChart = new Chart(document.getElementById('emotion-chart'), {
        type: 'line',
        data: {
            labels,
            datasets: [
                { label: 'Alegria', data: filtered.map(b => b.alegria), borderColor: COLORS.positive, fill: false, tension: 0.3 },
                { label: 'Raiva', data: filtered.map(b => b.raiva), borderColor: COLORS.negative, fill: false, tension: 0.3 },
                { label: 'Medo', data: filtered.map(b => b.medo), borderColor: COLORS.accent5, fill: false, tension: 0.3 },
                { label: 'Surpresa', data: filtered.map(b => b.surpresa), borderColor: COLORS.accent4, fill: false, tension: 0.3 },
                { label: 'Tristeza', data: filtered.map(b => b.tristeza), borderColor: COLORS.accent, fill: false, tension: 0.3 },
                { label: 'Nojo', data: filtered.map(b => b.nojo), borderColor: COLORS.accent6, fill: false, tension: 0.3 },
            ]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true } } }
    });
}

async function loadTopicSentiment(liveId) {
    const videoId = document.getElementById('video-id-input').value.trim();
    let url = API + '/' + liveId + '/topic-sentiment?top_n=10';
    if (videoId) url += '&video_id=' + encodeURIComponent(videoId);
    renderLoadingState('topic-sentiment');
    try {
        const res = await apiFetch(url);
        if (!res.ok) { showEmpty('topic-sentiment', true); return; }
        const data = await res.json();
        cachedData.topicSentiment = data;
        renderTopicSentiment();
    } catch (e) { showEmpty('topic-sentiment', true); }
}

document.getElementById('video-id-apply').addEventListener('click', () => {
    const liveId = document.getElementById('live-select').value;
    if (liveId) loadTopicSentiment(liveId);
});

function renderTopicSentiment() {
    const data = cachedData.topicSentiment;
    if (!data || !data.topics || data.topics.length === 0) {
        showEmpty('topic-sentiment', true);
        document.getElementById('topic-sentiment-detail').innerHTML = '';
        return;
    }
    showEmpty('topic-sentiment', false);
    const labels = data.topics.map(t => t.topic + ' (' + t.message_count + ')');
    const pos = data.topics.map(t => t.sentiment.Positivo || 0);
    const neg = data.topics.map(t => t.sentiment.Negativo || 0);
    const neu = data.topics.map(t => t.sentiment.Neutro || 0);
    if (topicSentimentChart) topicSentimentChart.destroy();
    topicSentimentChart = new Chart(document.getElementById('topic-sentiment-chart'), {
        type: 'bar',
        data: {
            labels,
            datasets: [
                { label: 'Positivo', data: pos, backgroundColor: COLORS.positive },
                { label: 'Negativo', data: neg, backgroundColor: COLORS.negative },
                { label: 'Neutro', data: neu, backgroundColor: COLORS.neutral },
            ]
        },
        options: {
            responsive: true,
            indexAxis: 'y',
            scales: { x: { stacked: true }, y: { stacked: true } },
            plugins: {
                tooltip: {
                    callbacks: {
                        afterLabel: function(ctx) {
                            const t = data.topics[ctx.dataIndex];
                            let lines = ['Pico: ' + (t.peak_minute || 'N/D') + ' | Emoção: ' + t.dominant_emotion];
                            if (t.transcript_snippet) {
                                lines.push('🎤 ' + t.transcript_snippet.substring(0, 120) + (t.transcript_snippet.length > 120 ? '...' : ''));
                            }
                            return lines;
                        }
                    }
                }
            }
        }
    });

    // Detalhes abaixo do gráfico com trechos transcritos
    let detailHtml = '';
    data.topics.forEach(t => {
        if (t.transcript_snippet) {
            detailHtml += '<div style="margin-bottom:0.3rem;"><strong>' + escapeHtml(t.topic) + '</strong> <span style="color:#64748b;">(' + escapeHtml(t.peak_minute || '') + ')</span>: ' + escapeHtml(t.transcript_snippet) + '</div>';
        }
    });
    document.getElementById('topic-sentiment-detail').innerHTML = detailHtml;
}

async function loadFraming(liveId) {
    renderLoadingState('framing');
    try {
        const res = await apiFetch(API + '/' + liveId + '/framing');
        if (!res.ok) { showEmpty('framing', true); return; }
        const data = await res.json();
        cachedData.framing = data;
        renderFraming();
    } catch (e) { showEmpty('framing', true); }
}

function renderFraming() {
    const data = cachedData.framing;
    if (!data || !data.framing) {
        showEmpty('framing', true);
        return;
    }
    showEmpty('framing', false);
    const labels = ['Ataque', 'Defesa', 'Ironia', 'Elogio', 'Pergunta', 'Neutro'];
    const keys = ['ataque', 'defesa', 'ironia', 'elogio', 'pergunta', 'neutro'];
    const values = keys.map(k => data.framing[k] || 0);
    const colors = [COLORS.negative, COLORS.accent, COLORS.accent4, COLORS.positive, COLORS.accent3, COLORS.neutral];
    if (framingChart) framingChart.destroy();
    framingChart = new Chart(document.getElementById('framing-chart'), {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Mensagens',
                data: values,
                backgroundColor: colors,
                borderColor: colors,
                borderWidth: 1,
            }]
        },
        options: {
            responsive: true,
            indexAxis: 'y',
            scales: { x: { beginAtZero: true } },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            const total = data.total_messages;
                            const pct = total > 0 ? ((ctx.raw / total) * 100).toFixed(1) : 0;
                            return ctx.raw + ' (' + pct + '%)';
                        }
                    }
                }
            }
        }
    });
}

async function loadSarcasm(liveId) {
    renderLoadingState('sarcasm');
    try {
        const res = await apiFetch(API + '/' + liveId + '/sarcasm');
        if (!res.ok) { showEmpty('sarcasm', true); return; }
        const data = await res.json();
        cachedData.sarcasm = data;
        renderSarcasm();
    } catch (e) { showEmpty('sarcasm', true); }
}

function renderSarcasm() {
    const data = cachedData.sarcasm;
    if (!data || !data.sarcasm) {
        showEmpty('sarcasm', true);
        return;
    }
    showEmpty('sarcasm', false);
    const labels = ['Sarcastico', 'Nao sarcastico'];
    const values = [data.sarcasm.sarcastic || 0, data.sarcasm.non_sarcastic || 0];
    const colors = [COLORS.accent4, COLORS.neutral];
    if (sarcasmChart) sarcasmChart.destroy();
    sarcasmChart = new Chart(document.getElementById('sarcasm-chart'), {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 1,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom' },
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            const total = data.total_messages;
                            const pct = total > 0 ? ((ctx.raw / total) * 100).toFixed(1) : 0;
                            return ctx.label + ': ' + ctx.raw + ' (' + pct + '%)';
                        }
                    }
                }
            }
        }
    });
}

async function loadAspects(liveId) {
    const entities = document.getElementById('aspect-entities-input').value.trim();
    let url = API + '/' + liveId + '/aspect-sentiment';
    if (entities) url += '?entities=' + encodeURIComponent(entities);
    renderLoadingState('aspects');
    try {
        const res = await apiFetch(url);
        if (!res.ok) { showEmpty('aspects', true); return; }
        const data = await res.json();
        cachedData.aspects = data;
        renderAspects();
    } catch (e) { showEmpty('aspects', true); }
}

function renderAspects() {
    const data = cachedData.aspects;
    if (!data || !data.aspects || Object.keys(data.aspects).length === 0) {
        showEmpty('aspects', true);
        return;
    }
    showEmpty('aspects', false);
    const entities = Object.keys(data.aspects).filter(e => data.aspects[e].messages > 0);
    if (entities.length === 0) { showEmpty('aspects', true); return; }
    const labels = entities;
    const pos = entities.map(e => data.aspects[e].sentiment.Positivo || 0);
    const neg = entities.map(e => data.aspects[e].sentiment.Negativo || 0);
    const neu = entities.map(e => data.aspects[e].sentiment.Neutro || 0);
    if (aspectsChart) aspectsChart.destroy();
    aspectsChart = new Chart(document.getElementById('aspects-chart'), {
        type: 'bar',
        data: {
            labels,
            datasets: [
                { label: 'Positivo', data: pos, backgroundColor: COLORS.positive },
                { label: 'Negativo', data: neg, backgroundColor: COLORS.negative },
                { label: 'Neutro', data: neu, backgroundColor: COLORS.neutral },
            ]
        },
        options: {
            responsive: true,
            indexAxis: 'y',
            scales: { x: { stacked: true }, y: { stacked: true } },
        }
    });
}

document.getElementById('aspect-apply').addEventListener('click', () => {
    const liveId = document.getElementById('live-select').value;
    if (liveId) loadAspects(liveId);
});

function applyFilters() {
    currentFilters.sentiment = document.getElementById('filter-sentiment').value;
    currentFilters.timeStart = document.getElementById('filter-time-start').value.trim();
    currentFilters.timeEnd = document.getElementById('filter-time-end').value.trim();
    const liveId = document.getElementById('live-select').value;
    if (!liveId) return;
    renderTimeline();
    renderPeaks();
    renderModality();
    renderEmotion();
}

document.getElementById('filter-apply-btn').addEventListener('click', applyFilters);

async function exportData(format) {
    const liveId = document.getElementById('live-select').value;
    if (!liveId) return;
    try {
        const endpoint = API + '/' + liveId + '/export?format=' + format;
        const ext = format === 'xlsx' ? 'xlsx' : format;
        const res = await apiFetch(endpoint);
        if (!res.ok) { alert('Erro ao exportar: ' + res.status); return; }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = liveId + '.' + ext;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (e) { alert('Falha ao exportar'); }
}

async function requestPdfReport() {
    const liveId = document.getElementById('live-select').value;
    if (!liveId) return;
    const btn = document.getElementById('export-pdf');
    const progressDiv = document.getElementById('pdf-progress');

    btn.disabled = true;
    progressDiv.textContent = 'Criando job...';

    try {
        // 1. Criar job
        const createRes = await apiFetch('/api/reports?live_id=' + encodeURIComponent(liveId), {
            method: 'POST',
        });
        if (!createRes.ok) {
            const err = await createRes.json();
            throw new Error(err.detail || 'Erro ao criar relatório');
        }
        const { job_id } = await createRes.json();

        // 2. Polling a cada 2s
        const pollInterval = setInterval(async () => {
            try {
                const statusRes = await apiFetch('/api/reports/' + job_id);
                if (!statusRes.ok) {
                    clearInterval(pollInterval);
                    throw new Error('Falha ao consultar status');
                }
                const job = await statusRes.json();
                progressDiv.textContent = 'Gerando relatório... ' + job.progress + '%';

                if (job.status === 'done') {
                    clearInterval(pollInterval);
                    // Download via fetch para enviar token JWT no header
                    const downloadUrl = '/api/reports/' + job_id + '/download';
                    try {
                        const dlRes = await apiFetch(downloadUrl);
                        if (!dlRes.ok) throw new Error('Erro ao baixar PDF');
                        const blob = await dlRes.blob();
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = liveId + '_report.pdf';
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                        progressDiv.innerHTML = '<span style="color:var(--color-positive);">Relatório baixado com sucesso.</span>';
                    } catch (e) {
                        progressDiv.innerHTML = '<span style="color:var(--color-negative);">Erro ao baixar: ' + escapeHtml(e.message) + '</span>';
                    }
                    btn.disabled = false;
                } else if (job.status === 'failed') {
                    clearInterval(pollInterval);
                    progressDiv.innerHTML = '<span style="color:var(--color-negative);">Erro: ' + escapeHtml(job.error || 'falha desconhecida') + '</span>';
                    btn.disabled = false;
                }
            } catch (e) {
                clearInterval(pollInterval);
                progressDiv.innerHTML = '<span style="color:var(--color-negative);">' + escapeHtml(e.message) + '</span>';
                btn.disabled = false;
            }
        }, 2000);
    } catch (e) {
        progressDiv.innerHTML = '<span style="color:var(--color-negative);">' + escapeHtml(e.message) + '</span>';
        btn.disabled = false;
    }
}

renderTermTags();
// Nao chamar loadLives() aqui: essa chamada corria antes de qualquer
// checagem de autenticacao (e antes do cookie de sessao estar
// confirmado), disparando 401 nao tratado em renderLiveOptions() e
// deixando a UI em estado inconsistente. loadLives() agora so roda
// depois que checkAuthState() confirma a sessao (ver final do arquivo).

const API_BASE = '';
const authSection = document.getElementById('auth-section');
const dataSection = document.getElementById('data-section');
const loginForm = document.getElementById('login-form');
const userInfo = document.getElementById('user-info');
const displayEmail = document.getElementById('display-email');

async function checkAuthState() {
    try {
        const resp = await fetch(`${API_BASE}/api/auth/me`, { credentials: 'same-origin' });
        if (resp.ok) {
            const user = await resp.json();
            setAuthUI(true, user.email);
            loadLives();
            return;
        }
    } catch (e) {}
    setAuthUI(false);
}

function doLogin() {
    var btn = document.getElementById('login-btn');
    if (btn.disabled) return;
    btn.disabled = true;
    var email = document.getElementById('login-email').value;
    var password = document.getElementById('login-password').value;
    var errorDiv = document.getElementById('login-error');
    errorDiv.textContent = '';
    fetch(API_BASE + '/api/auth/login', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, password: password })
    }).then(function(resp) {
        if (!resp.ok) { return resp.json().then(function(d) { throw new Error(d.detail || 'Falha no login'); }); }
        btn.disabled = false;
        checkAuthState();
    }).catch(function(e) { errorDiv.textContent = e.message; btn.disabled = false; });
}

document.getElementById('login-btn').addEventListener('click', doLogin);

document.getElementById('logout-btn').addEventListener('click', async () => {
    await fetch(`${API_BASE}/api/auth/logout`, { method: 'POST', credentials: 'same-origin' });
    checkAuthState();
});

checkAuthState();