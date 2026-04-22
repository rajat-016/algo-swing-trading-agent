const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

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