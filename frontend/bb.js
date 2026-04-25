// content.js

console.log("Extensão de chat iniciada!");

// Função para enviar os dados para o seu backend
async function sendDataToBackend(author, message) {
  try {
    await fetch('http://127.0.0.1:8000/save-message', { // URL do seu backend FastAPI
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ author, message }),
    });
  } catch (error) {
    console.error("Erro ao enviar dados para o backend:", error);
  }
}

// Espera o iframe do chat carregar
const checkChatFrame = setInterval(() => {
  const chatFrame = document.getElementById('chatframe');
  if (chatFrame && chatFrame.contentDocument) {
    clearInterval(checkChatFrame);
    const chatDocument = chatFrame.contentDocument;
    const chatItemsContainer = chatDocument.querySelector("#items.yt-live-chat-item-list-renderer");

    if (chatItemsContainer) {
      console.log("Observador do chat ativado!");
      // Cria um observador para novas mensagens
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          mutation.addedNodes.forEach((node) => {
            // Cada mensagem nova é um 'yt-live-chat-text-message-renderer'
            if (node.tagName === 'YT-LIVE-CHAT-TEXT-MESSAGE-RENDERER') {
              const author = node.querySelector('#author-name')?.textContent.trim();
              const message = node.querySelector('#message')?.textContent.trim();

              if (author && message) {
                console.log(`[${author}]: ${message}`);
                sendDataToBackend(author, message);
              }
            }
          });
        });
      });

      // Começa a observar
      observer.observe(chatItemsContainer, { childList: true });
    }
  }
}, 1000);