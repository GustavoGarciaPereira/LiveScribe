console.log("PulsoDaLive v4 - content.js injetado e ativo.");

// Função que contém a lógica principal de monitoramento
function startMonitoring(chatDocument) {
    const chatContainerSelector = "#items.yt-live-chat-item-list-renderer";
    const chatContainer = chatDocument.querySelector(chatContainerSelector);

    if (!chatContainer) {
        console.error("PulsoDaLive: Erro crítico! O contêiner do chat não foi encontrado DENTRO do iframe. A estrutura do YouTube pode ter mudado.");
        return;
    }

    console.log("PulsoDaLive: Contêiner do chat encontrado DENTRO do iframe. Observador ativado!");

    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType !== Node.ELEMENT_NODE) return;

                const authorElement = node.querySelector("#author-name");
                const messageElement = node.querySelector("#message");

                if (authorElement && messageElement) {
                    // O live_id ainda é pego da URL da janela principal (top window)
                    let liveId = null;
                    const url = new URL(window.location.href);
                    if (url.pathname.startsWith('/live/')) {
                        liveId = url.pathname.split('/')[2];
                    } else if (url.pathname === '/watch') {
                        liveId = url.searchParams.get('v');
                    }

                    const author = authorElement.textContent.trim();
                    const message = messageElement.textContent.trim();

                    if (author && message && liveId) {
                        console.log(`%c[DADO VÁLIDO] Live ID: ${liveId}, Autor: ${author}`, 'color: green');
                        fetch('http://127.0.0.1:8000/save-message', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ author, message, live_id: liveId }),
                        })
                        .then(response => response.json())
                        .then(data => console.log('%c[RESPOSTA API]', 'color: blue', data))
                        .catch((error) => console.error('%c[ERRO FETCH]', 'color: red', error));
                    }
                }
            });
        });
    });

    observer.observe(chatContainer, { childList: true });
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