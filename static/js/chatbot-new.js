class ChatBot {
    constructor({ baseUrl, apiKey }) {
      this.baseUrl = baseUrl || `${window.location.protocol}//${window.location.hostname}:8000`;
      this.apiKey = apiKey || '';
      this.sessionId = this._generateSessionId();
      this.lastMessage = null;
  
      this._cacheDOM();
      this._bindEvents();
      this._showWelcomeMessage();
    }
  
    _generateSessionId() {
      return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = (Math.random() * 16) | 0;
        return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
      });
    }
  
    _cacheDOM() {
      this.toggleBtn = document.getElementById('chatToggle');
      this.container = document.getElementById('chatContainer');
      this.overlay = document.getElementById('chatOverlay');
      this.input = document.getElementById('messageInput');
      this.sendBtn = document.getElementById('sendBtn');
      this.messagesEl = document.getElementById('chatMessages');
      this.typingEl = document.getElementById('typingIndicator');
      this.badge = document.getElementById('notificationBadge');
    }
  
    _bindEvents() {
      this.toggleBtn.addEventListener('click', () => this._toggleChat());
      this.overlay.addEventListener('click', () => this._closeChat());
      this.sendBtn.addEventListener('click', () => this._sendMessage());
      this.input.addEventListener('keypress', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this._sendMessage();
        }
      });
    }
  
    _toggleChat() {
      const opened = this.container.classList.toggle('active');
      this.overlay.classList.toggle('active', opened);
      this.toggleBtn.classList.toggle('active', opened);
      if (opened) {
        this.badge.style.display = 'none';
        document.body.style.overflow = 'hidden';
        this.input.focus();
      } else {
        document.body.style.overflow = '';
      }
    }
  
    _closeChat() {
      this.container.classList.remove('active');
      this.overlay.classList.remove('active');
      this.toggleBtn.classList.remove('active');
      document.body.style.overflow = '';
    }
  
    _showWelcomeMessage() {
      const welcome = `Hello! 👋 Welcome to Lotus Electronics!\n\nWhat are you shopping for today?`;
      setTimeout(() => this._addMessage(welcome, 'bot', true), 500);
      setTimeout(() => {
        this.badge.textContent = '1';
        this.badge.style.display = 'flex';
      }, 2000);
    }
  
    _sendMessage() {
      const text = this.input.value.trim();
      if (!text || text === this.lastMessage) return;
      this.lastMessage = text;
  
      this._addMessage(text, 'user');
      this.input.value = '';
      this._showTyping();
      this._callAPI(text);
    }
  
    _addMessage(content, sender, isSystem = false) {
      const wrapper = document.createElement('div');
      wrapper.className = `message-wrapper ${sender}-wrapper`;
  
      const timeLine = document.createElement('div');
      timeLine.className = 'message-time-line';
      timeLine.textContent = isSystem ? 'Just now' : this._getTime();
      wrapper.appendChild(timeLine);
  
      const msg = document.createElement('div');
      msg.className = `message ${sender}-message`;
      msg.textContent = content;
      wrapper.appendChild(msg);
  
      this.messagesEl.appendChild(wrapper);
      this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
    }
  
    _addProductCard(product) {
      const card = document.createElement('div');
      card.className = 'product-card';
      card.innerHTML = `
        <a href="${product.product_link}" target="_blank" class="product-link">
          <img src="${product.product_image}" alt="${product.product_name}" class="product-img" />
          <div class="product-info">
            <h4 class="product-title">${product.product_name}</h4>
            <p class="product-price">₹${product.product_mrp}</p>
          </div>
        </a>
      `;
      this.messagesEl.appendChild(card);
      this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
    }
  
    _showTyping() {
      this.typingEl.classList.add('active');
    }
  
    _hideTyping() {
      this.typingEl.classList.remove('active');
    }
  
    async _callAPI(message) {
      try {
        const res = await fetch(`${this.baseUrl}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': this.apiKey
          },
          body: JSON.stringify({ message, session_id: this.sessionId })
        });
        const { response } = await res.json();
        this._hideTyping();
  
        response.messages
          .filter(msg => msg.role === 'assistant')
          .forEach(msg => {
            // Detect JSON product list
            if (msg.content.trim().startsWith('[')) {
              let products;
              try {
                products = JSON.parse(msg.content);
              } catch (e) {
                console.error('Invalid product JSON', e);
              }
              if (Array.isArray(products)) {
                products.forEach(p => this._addProductCard(p));
                return;
              }
            }
            this._addMessage(msg.content, 'bot');
          });
      } catch (err) {
        this._hideTyping();
        this._addMessage('Sorry, something went wrong.', 'bot');
        console.error(err);
      }
    }
  
    _getTime() {
      return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
  }
  
  // On DOM ready
  window.addEventListener('DOMContentLoaded', () => {
    window.chatBot = new ChatBot({ apiKey: 'nawabkhan' });
  });
  