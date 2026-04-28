console.log("PulsoDaLive v4 - content.js injetado e ativo.");

// Função que contém a lógica principal de monitoramento
function startMonitoring(chatDocument) {
    // Extrai o live_id da URL da janela principal (uma vez só, no escopo da função)
    let liveId = null;
    try {
        const url = new URL(window.top.location.href);
        if (url.pathname.startsWith('/live/')) {
            liveId = url.pathname.split('/')[2];
        } else if (url.pathname === '/watch') {
            liveId = url.searchParams.get('v');
        }
    } catch (e) {
        // Fallback: se não conseguir acessar window.top, tenta a própria window
        const url = new URL(window.location.href);
        if (url.pathname.startsWith('/live/')) {
            liveId = url.pathname.split('/')[2];
        } else if (url.pathname === '/watch') {
            liveId = url.searchParams.get('v');
        }
    }
    console.log('[DEBUG] liveId extraído:', liveId);

    const selectors = [
        "#items.yt-live-chat-item-list-renderer",
        "#items",
        "yt-live-chat-item-list-renderer #items",
        "#item-scroller #items",
        "yt-live-chat-item-list-renderer #item-scroller #items",
    ];

    let chatContainer = null;
    for (const sel of selectors) {
        chatContainer = chatDocument.querySelector(sel);
        if (chatContainer) {
            console.log("PulsoDaLive: Contêiner encontrado com seletor:", sel);
            break;
        }
    }

    if (!chatContainer) {
        console.error("PulsoDaLive: Nenhum contêiner do chat encontrado.");
        console.log("PulsoDaLive: Seletores tentados:", selectors);
        return;
    }

    console.log("PulsoDaLive: Monitoramento ativado!");

    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType !== Node.ELEMENT_NODE) return;

                // O container da mensagem tem tag YT-LIVE-CHAT-TEXT-MESSAGE-RENDERER
                const msgContainer = node.tagName === 'YT-LIVE-CHAT-TEXT-MESSAGE-RENDERER'
                    ? node
                    : node.querySelector('yt-live-chat-text-message-renderer');

                if (!msgContainer) return;

                const authorEl = msgContainer.querySelector('#author-name, .author-name, span[id*=\"author\"]');
                const messageEl = msgContainer.querySelector('#message, span[id*=\"message\"]');

                if (!authorEl || !messageEl) return;

                if (authorEl && messageEl) {
                    const author = authorEl.textContent.trim();
                    const message = messageEl.textContent.trim();

                    if (author && message && liveId) {
                        console.log(`%c[DADO VÁLIDO] Live ID: ${liveId}, Autor: ${author}`, 'color: green');
                        chrome.storage.local.get(['token'], (result) => {
                            const headers = { 'Content-Type': 'application/json' };
                            if (result.token) {
                                headers['Authorization'] = `Bearer ${result.token}`;
                            }
                            fetch('http://localhost:8000/api/chat/messages', {
                                method: 'POST',
                                headers,
                                body: JSON.stringify({ author, message, live_id: liveId, platform: "youtube" }),
                            })
                            .then(response => response.json())
                            .then(data => console.log('%c[RESPOSTA API]', 'color: blue', data))
                            .catch((error) => console.error('%c[ERRO FETCH]', 'color: red', error));
                        });
                    }
                }
            });
        });
    });

    observer.observe(chatContainer, { childList: true, subtree: true });
}

// Função de inicialização que encontra o iframe
function initializeChatMonitor() {
    const iframe = document.querySelector('iframe#chatframe');

    if (!iframe) {
        console.log("PulsoDaLive: Aguardando o iframe do chat (#chatframe) aparecer...");
        setTimeout(initializeChatMonitor, 2000);
        return;
    }

    console.log("PulsoDaLive: Iframe do chat encontrado!");
    // Checa se o iframe já carregou seu conteúdo
    if (iframe.contentDocument && iframe.contentDocument.readyState === 'complete') {
        console.log("PulsoDaLive: O conteúdo do iframe já estava carregado. Iniciando monitoramento.");
        startMonitoring(iframe.contentDocument);
    } else {
        // Se não, esperamos pelo evento 'onload'
        console.log("PulsoDaLive: Aguardando o conteúdo do iframe carregar...");
        iframe.onload = () => {
            console.log("PulsoDaLive: Conteúdo do iframe carregado. Iniciando monitoramento.");
            startMonitoring(iframe.contentDocument);
        };
    }
}

// Inicia todo o processo
initializeChatMonitor();