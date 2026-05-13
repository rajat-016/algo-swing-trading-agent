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
  getAnalytics: () => api.get('/stocks/summary/analytics'),
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

export const monitoringApi = {
  getPredictions: (limit = 50) => api.get(`/monitoring/predictions?limit=${limit}`),
  getAccuracy: (lookbackDays = 30) => api.get(`/monitoring/accuracy?lookback_days=${lookbackDays}`),
  getDriftStatus: () => api.get('/monitoring/drift'),
  createBaseline: () => api.post('/monitoring/drift/baseline'),
  getHealthDashboard: () => api.get('/monitoring/health'),
  getMetrics: () => api.get('/monitoring/metrics'),
  getLatency: () => api.get('/monitoring/latency'),
  getPerformance: () => api.get('/monitoring/performance'),
  getSystemHealth: () => api.get('/health'),
};

export const stressTestApi = {
  runScenario: (scenario) => api.post(`/stress/run/${scenario}`),
  runMonteCarlo: (params) => api.post('/stress/monte-carlo', params),
};

export const regimeApi = {
  getCurrent: () => api.get('/regime/current'),
  analyze: (data) => api.post('/regime/analyze', data),
  getHistory: () => api.get('/regime/history'),
  getStats: () => api.get('/regime/stats'),
  getTransitions: () => api.get('/regime/transitions'),
  getDistribution: () => api.get('/regime/distribution'),
  getTransitionData: () => api.get('/regime/transition'),
  getHealth: () => api.get('/regime/health'),
};

export const portfolioApi = {
  getRisk: () => api.get('/portfolio/risk'),
  getExposure: () => api.get('/portfolio/exposure'),
  getCorrelation: () => api.get('/portfolio/correlation'),
  getHistory: () => api.get('/portfolio/history'),
  getLatest: () => api.get('/portfolio/latest'),
  getHealth: () => api.get('/portfolio/health'),
};

export const correlationApi = {
  analyze: (data) => api.post('/correlation/analyze', data),
  getRolling: () => api.get('/correlation/rolling'),
  getClusters: () => api.get('/correlation/clusters'),
  getInstability: () => api.get('/correlation/instability'),
  getDiversification: () => api.get('/correlation/diversification'),
  getHistory: () => api.get('/correlation/history'),
  getLatest: () => api.get('/correlation/latest'),
};

export const tradeApi = {
  explain: (data) => api.post('/trade/explain', data),
  getIntelligence: (data) => api.post('/trade/intelligence', data),
  getFailure: (data) => api.post('/trade/intelligence/failure', data),
  getReasoning: (data) => api.post('/trade/intelligence/reasoning', data),
  getPostMortem: (data) => api.post('/trade/intelligence/post-mortem', data),
};

export const journalApi = {
  getTrades: () => api.get('/journal/trades'),
  getTrade: (id) => api.get(`/journal/trades/${id}`),
  search: (data) => api.post('/journal/search', data),
  getStats: () => api.get('/journal/stats'),
  searchText: (q) => api.post('/journal/search/text', q ? { query: q } : null),
};

export const researchApi = {
  query: (data) => api.post('/research/query', data),
  getDrift: (data) => api.post('/research/drift', data),
  compareStrategies: (data) => api.post('/research/strategies/compare', data),
  summarizeExperiment: (data) => api.post('/research/experiment/summarize', data),
  getHypotheses: (data) => api.post('/research/hypotheses', data),
  getRegimeDegradation: (data) => api.post('/research/regime/degradation', data),
  health: () => api.get('/research/health'),
};

export const intelligenceApi = {
  getHealth: () => api.get('/intelligence/health'),
  getCapabilities: () => api.get('/intelligence/capabilities'),
};

export const reflectionApi = {
  reflectTrade: (tradeId) => api.post(`/reflection/trade/${tradeId}`),
  batchReflect: (data) => api.post('/reflection/batch', data),
  generateSummaries: () => api.post('/reflection/summaries'),
  getLogs: () => api.get('/reflection/logs'),
};

export const driftApi = {
  getStatus: () => api.get('/drift/status'),
  getAlerts: () => api.get('/drift/alerts'),
  getAlertSummary: () => api.get('/drift/alerts/summary'),
  getBaselines: () => api.get('/drift/baselines'),
};

export const memoryApi = {
  search: (data) => api.post('/memory/search', data),
  searchText: (data) => api.post('/memory/search/text', data),
  getStats: () => api.get('/memory/stats'),
  getHealth: () => api.get('/memory/health'),
};

export const wsManager = new WebSocketManager();