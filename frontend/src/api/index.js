const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

export const api = {
  async get(endpoint) {
    const response = await fetch(`${API_BASE}${endpoint}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  },

  async post(endpoint, data) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  },
};

export const stocksApi = {
  getAll: () => api.get('/stocks/'),
  getBySymbol: (symbol) => api.get(`/stocks/${symbol}`),
  getByStatus: (status) => api.get(`/stocks/status/${status}`),
  getPortfolio: () => api.get('/stocks/summary/portfolio'),
  exitStock: (symbol, reason) => api.post(`/stocks/${symbol}/exit`, { reason }),
};

export const tradingApi = {
  getStatus: () => api.get('/trading/status'),
  switchMode: (mode) => api.post('/trading/mode', { mode }),
  start: () => api.post('/trading/start'),
  stop: () => api.post('/trading/stop'),
};

export class WebSocketManager {
  constructor() {
    this.ws = null;
    this.listeners = [];
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 3000;
    this.autoReconnect = true;
  }

  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      this.ws = new WebSocket(`${WS_URL}/ws`);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.ws.send('subscribe');
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.notifyListeners(data);
        } catch (e) {
          console.log('WebSocket message:', event.data);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        if (this.autoReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
          setTimeout(() => this.connect(), this.reconnectDelay);
        }
      };
    } catch (error) {
      console.error('WebSocket connection error:', error);
    }
  }

  disconnect() {
    this.autoReconnect = false;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  subscribe(callback) {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter(l => l !== callback);
    };
  }

  notifyListeners(data) {
    this.listeners.forEach(callback => callback(data));
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(message);
    }
  }

  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}

export const wsManager = new WebSocketManager();