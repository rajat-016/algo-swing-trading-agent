import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import TradeIntelligence from '../components/TradeIntelligence';

jest.mock('../api', () => ({
  stocksApi: {
    getAll: jest.fn(),
  },
  tradeApi: {
    explain: jest.fn(),
    getIntelligence: jest.fn(),
    getPostMortem: jest.fn(),
  },
  journalApi: {
    getTrades: jest.fn(),
    getStats: jest.fn(),
  },
  memoryApi: {
    search: jest.fn(),
  },
  regimeApi: {
    getCurrent: jest.fn(),
  },
}));

const api = require('../api');

const mockStocks = [
  { symbol: 'RELIANCE', id: 1 },
  { symbol: 'TCS', id: 2 },
  { symbol: 'HDFCBANK', id: 3 },
];

const mockTradeData = {
  symbol: 'RELIANCE',
  status: 'ok',
  explanation: {
    trade_id: 'pred_123',
    symbol: 'RELIANCE',
    timestamp: '2026-05-13T10:30:00',
    prediction: {
      decision: 'BUY',
      confidence: 0.78,
      probabilities: { buy: 0.78, hold: 0.15, sell: 0.07 },
      confidence_level: 'high',
      margin_over_second: 0.63,
      entropy: 0.35,
      model_version: 'v1.2',
      feature_version: 'v3',
    },
    top_positive_features: [
      { feature: 'momentum_14d', shap_value: 0.45, contribution_pct: 22.5 },
      { feature: 'relative_strength', shap_value: 0.32, contribution_pct: 16.0 },
    ],
    top_negative_features: [
      { feature: 'volatility_atr', shap_value: -0.12, contribution_pct: -6.0 },
    ],
    regime_context: {
      regime: 'bull_trend',
      confidence: 0.85,
      risk_level: 'low',
      stability: 'stable',
      suggested_behavior: ['reduce position sizing'],
    },
    historical_trade_similarity: {
      similar_trades_found: 2,
      similar_trades: [
        { trade_id: 'T1', ticker: 'RELIANCE', outcome: 'WIN', confidence: 0.8, relevance_score: 0.92 },
        { trade_id: 'T2', ticker: 'RELIANCE', outcome: 'LOSS', confidence: 0.6, relevance_score: 0.75 },
      ],
    },
  },
  reasoning: {
    entry_rationale: {
      primary_reason: 'Model predicted BUY with high confidence',
      supporting_factors: ['momentum_14d', 'relative_strength'],
      regime_alignment: 'Market in bull_trend regime',
    },
    outcome_analysis: {
      outcome: 'WIN',
      exit_reason: 'TARGET',
      pnl_analysis: 'Profitable trade: +3.45%',
    },
    risk_factors: ['Significant negative feature contributions opposing the decision'],
    confidence_assessment: {
      verdict: 'strong',
      strength: 0.78,
      details: ['High confidence (0.78)', 'Low prediction entropy'],
    },
    summary: 'Trade decision: BUY. Outcome: WIN. +3.45%.',
  },
  similar_trades: {
    similar_trades_found: 2,
    similar_trades: [
      {
        ticker: 'RELIANCE', outcome: 'WIN', confidence: 0.8, relevance_score: 0.92,
        regime: 'bull_trend',
        match_factors: { regime_similarity: 1.0, volatility_match: 0.4, feature_similarity: 0.33, sector_alignment: 1.0, breakout_structure: 0.2, composite_score: 0.62 },
      },
      {
        ticker: 'TCS', outcome: 'LOSS', confidence: 0.6, relevance_score: 0.75,
        regime: 'bull_trend',
        match_factors: { regime_similarity: 1.0, volatility_match: 0.4, feature_similarity: 0.25, sector_alignment: 0.5, breakout_structure: 0.2, composite_score: 0.52 },
      },
    ],
    factor_weights: { regime_similarity: 0.25, volatility_match: 0.20, feature_similarity: 0.25, sector_alignment: 0.15, breakout_structure: 0.15 },
    scoring_enabled: true,
  },
  latency_ms: 320.45,
};

const mockPostMortemData = {
  symbol: 'RELIANCE',
  status: 'ok',
  trade_summary: {
    trade_id: 'pred_123',
    symbol: 'RELIANCE',
    timestamp: '2026-05-13T10:30:00',
    decision: 'BUY',
    outcome: 'LOSS',
  },
  reasoning: {
    entry_rationale: { primary_reason: 'Model predicted BUY' },
    outcome_analysis: { pnl_analysis: 'Loss: -2.1%' },
    summary: 'Trade decision: BUY. Outcome: LOSS.',
  },
  failure_analysis: {
    failure_detected: true,
    failure_reasons: ['BUY in bear trend', 'Weak momentum detection'],
    severity: 'high',
    primary_cause: 'BUY in bear trend environment',
    regime_mismatch: { mismatch_detected: true, description: 'BUY in bear trend' },
    weak_momentum: { weak_momentum_detected: true, description: 'ADX below 20' },
    volatility_expansion: { expansion_detected: true, description: 'ATR spike detected' },
    weak_confirmations: { weak_detected: true, description: 'Low confidence' },
    stop_loss_analysis: { sl_hit: true, description: 'SL triggered' },
    regime_instability: { instability_detected: false },
    feature_alignment: { poor_alignment_detected: false },
  },
  failure_patterns: {
    patterns_found: 3,
    total_trades_analyzed: 50,
    patterns: [
      { category: 'regime_mismatch', count: 12, frequency: 0.24 },
      { category: 'weak_momentum', count: 8, frequency: 0.16 },
    ],
    recurring_patterns: ['Frequent regime_mismatch detected in sideways markets'],
    most_common_regime: 'sideways',
    regime_breakdown: { bull_trend: 20, sideways: 15, bear_trend: 10 },
    outcome_breakdown: { WIN: 15, LOSS: 20, stop_loss_hit: 15 },
  },
  similar_trades: {
    similar_trades_found: 1,
    similar_trades: [{ ticker: 'RELIANCE', outcome: 'LOSS', relevance_score: 0.85 }],
  },
  latency_ms: 450.8,
};

const mockJournalStats = { total_trades: 10, with_regime: 7, available: true };
const mockJournalTrades = [
  { trade_id: 'T1', ticker: 'RELIANCE', timestamp: '2026-05-01', market_regime: 'bull_trend', confidence: 0.78, outcome: 'WIN' },
  { trade_id: 'T2', ticker: 'TCS', timestamp: '2026-05-02', market_regime: 'sideways', confidence: 0.55, outcome: 'LOSS' },
];
const mockRegimeData = { regime: 'bull_trend', confidence: 0.82, risk_level: 'low', recommended_behavior: ['Hold positions'] };

function setupMocks() {
  api.stocksApi.getAll.mockResolvedValue({ stocks: mockStocks });
  api.journalApi.getStats.mockResolvedValue(mockJournalStats);
  api.journalApi.getTrades.mockResolvedValue(mockJournalTrades);
  api.regimeApi.getCurrent.mockResolvedValue(mockRegimeData);
  api.tradeApi.getIntelligence.mockResolvedValue(mockTradeData);
  api.tradeApi.getPostMortem.mockResolvedValue(mockPostMortemData);
}

function getExplainActionBtn() {
  const btns = screen.getAllByText('Explain Trade');
  return btns.find(b => b.classList.contains('actionBtn')) || btns[btns.length - 1];
}

describe('TradeIntelligence - Scenario 1: Basic Rendering', () => {
  beforeEach(() => {
    setupMocks();
    jest.clearAllMocks();
  });

  test('Renders all 5 sub-tabs', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    expect(screen.getByText('Explain Trade')).toBeInTheDocument();
    expect(screen.getByText('Post-Mortem & Reflection')).toBeInTheDocument();
    expect(screen.getByText('Trade Journal')).toBeInTheDocument();
    expect(screen.getByText('Memory Search')).toBeInTheDocument();
    expect(screen.getByText('Regime Context')).toBeInTheDocument();
  });

  test('Renders section title and symbol selector', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    expect(screen.getByText('Trade Explanation Dashboard')).toBeInTheDocument();
    const selects = screen.getAllByRole('combobox');
    expect(selects.length).toBeGreaterThanOrEqual(1);
  });

  test('Explain Trade is the active tab by default', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    const subTabs = screen.getAllByRole('button');
    const explainTab = subTabs.find(b => b.textContent === 'Explain Trade');
    expect(explainTab.classList.contains('active')).toBe(true);
  });
});

describe('TradeIntelligence - Scenario 2: Trade Explanation Flow', () => {
  beforeEach(() => {
    setupMocks();
    jest.clearAllMocks();
  });

  test('Calls getIntelligence API on explain button click', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    const select = screen.getAllByRole('combobox')[0];
    await act(async () => { fireEvent.change(select, { target: { value: 'RELIANCE' } }); });
    await act(async () => { fireEvent.click(getExplainActionBtn()); });
    await waitFor(() => {
      expect(api.tradeApi.getIntelligence).toHaveBeenCalledWith({ symbol: 'RELIANCE' });
    });
  });

  test('Displays trade summary after explanation', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    const select = screen.getAllByRole('combobox')[0];
    await act(async () => { fireEvent.change(select, { target: { value: 'RELIANCE' } }); });
    await act(async () => { fireEvent.click(getExplainActionBtn()); });
    await waitFor(() => {
      expect(screen.getByText('Trade Summary')).toBeInTheDocument();
      expect(screen.getByText('RELIANCE')).toBeInTheDocument();
      expect(screen.getByText('pred_123')).toBeInTheDocument();
    });
  });

  test('Displays confidence metrics with probability bars', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    const select = screen.getAllByRole('combobox')[0];
    await act(async () => { fireEvent.change(select, { target: { value: 'RELIANCE' } }); });
    await act(async () => { fireEvent.click(getExplainActionBtn()); });
    await waitFor(() => {
      expect(screen.getByText('Confidence Metrics')).toBeInTheDocument();
      expect(screen.getByText('BUY')).toBeInTheDocument();
      expect(screen.getByText('HIGH')).toBeInTheDocument();
      expect(screen.getByText('78.0%')).toBeInTheDocument();
    });
  });

  test('Displays trade reasoning with entry rationale', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    const select = screen.getAllByRole('combobox')[0];
    await act(async () => { fireEvent.change(select, { target: { value: 'RELIANCE' } }); });
    await act(async () => { fireEvent.click(getExplainActionBtn()); });
    await waitFor(() => {
      expect(screen.getByText('Trade Reasoning')).toBeInTheDocument();
      expect(screen.getByText('Entry Rationale')).toBeInTheDocument();
      expect(screen.getByText(/Model predicted BUY/)).toBeInTheDocument();
    });
  });

  test('Displays feature attribution with positive and negative features', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    const select = screen.getAllByRole('combobox')[0];
    await act(async () => { fireEvent.change(select, { target: { value: 'RELIANCE' } }); });
    await act(async () => { fireEvent.click(getExplainActionBtn()); });
    await waitFor(() => {
      expect(screen.getByText('Feature Attribution')).toBeInTheDocument();
      expect(screen.getByText('Top Positive Features')).toBeInTheDocument();
      expect(screen.getByText('Top Negative Features')).toBeInTheDocument();
      expect(screen.getByText('momentum_14d')).toBeInTheDocument();
      expect(screen.getByText('volatility_atr')).toBeInTheDocument();
    });
  });

  test('Displays similar historical trades', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    const select = screen.getAllByRole('combobox')[0];
    await act(async () => { fireEvent.change(select, { target: { value: 'RELIANCE' } }); });
    await act(async () => { fireEvent.click(getExplainActionBtn()); });
    await waitFor(() => {
      expect(screen.getByText('Similar Historical Trades')).toBeInTheDocument();
      expect(screen.getAllByText('RELIANCE').length).toBeGreaterThanOrEqual(1);
    });
  });

  test('Displays regime context in explanation', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    const select = screen.getAllByRole('combobox')[0];
    await act(async () => { fireEvent.change(select, { target: { value: 'RELIANCE' } }); });
    await act(async () => { fireEvent.click(getExplainActionBtn()); });
    await waitFor(() => {
      expect(screen.getByText('Regime Context')).toBeInTheDocument();
      expect(screen.getByText('bull trend')).toBeInTheDocument();
      expect(screen.getByText('85.0%')).toBeInTheDocument();
    });
  });

  test('Displays latency footer', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    const select = screen.getAllByRole('combobox')[0];
    await act(async () => { fireEvent.change(select, { target: { value: 'RELIANCE' } }); });
    await act(async () => { fireEvent.click(getExplainActionBtn()); });
    await waitFor(() => {
      expect(screen.getByText(/320ms/)).toBeInTheDocument();
    });
  });
});

describe('TradeIntelligence - Scenario 3: Post-Mortem & Reflection Flow', () => {
  beforeEach(() => {
    setupMocks();
    jest.clearAllMocks();
  });

  test('Switches to post-mortem tab and shows form', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    await act(async () => { fireEvent.click(screen.getByText('Post-Mortem & Reflection')); });
    expect(screen.getByText('Run Post-Mortem')).toBeInTheDocument();
  });

  test('Calls getPostMortem API on button click', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    await act(async () => { fireEvent.click(screen.getByText('Post-Mortem & Reflection')); });
    const select = screen.getByRole('combobox');
    await act(async () => { fireEvent.change(select, { target: { value: 'RELIANCE' } }); });
    await act(async () => { fireEvent.click(screen.getByText('Run Post-Mortem')); });
    await waitFor(() => {
      expect(api.tradeApi.getPostMortem).toHaveBeenCalledWith({ symbol: 'RELIANCE' });
    });
  });

  test('Displays reflection summary with failure patterns', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    await act(async () => { fireEvent.click(screen.getByText('Post-Mortem & Reflection')); });
    const select = screen.getByRole('combobox');
    await act(async () => { fireEvent.change(select, { target: { value: 'RELIANCE' } }); });
    await act(async () => { fireEvent.click(screen.getByText('Run Post-Mortem')); });
    await waitFor(() => {
      expect(screen.getByText('Reflection: Failure Pattern Analysis')).toBeInTheDocument();
      expect(screen.getByText(/50 trades/)).toBeInTheDocument();
      expect(screen.getByText('regime mismatch')).toBeInTheDocument();
      expect(screen.getByText('24% (12)')).toBeInTheDocument();
      expect(screen.getByText('sideways')).toBeInTheDocument();
    });
  });

  test('Displays recurring patterns in reflection', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    await act(async () => { fireEvent.click(screen.getByText('Post-Mortem & Reflection')); });
    const select = screen.getByRole('combobox');
    await act(async () => { fireEvent.change(select, { target: { value: 'RELIANCE' } }); });
    await act(async () => { fireEvent.click(screen.getByText('Run Post-Mortem')); });
    await waitFor(() => {
      expect(screen.getByText(/Frequent regime_mismatch/)).toBeInTheDocument();
    });
  });

  test('Displays regime and outcome breakdowns', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    await act(async () => { fireEvent.click(screen.getByText('Post-Mortem & Reflection')); });
    const select = screen.getByRole('combobox');
    await act(async () => { fireEvent.change(select, { target: { value: 'RELIANCE' } }); });
    await act(async () => { fireEvent.click(screen.getByText('Run Post-Mortem')); });
    await waitFor(() => {
      expect(screen.getByText('Regime Breakdown')).toBeInTheDocument();
      expect(screen.getByText('Outcome Breakdown')).toBeInTheDocument();
      expect(screen.getByText('WIN')).toBeInTheDocument();
      expect(screen.getByText('15')).toBeInTheDocument();
    });
  });
});

describe('TradeIntelligence - Scenario 4: Error & Edge Cases', () => {
  beforeEach(() => {
    setupMocks();
    jest.clearAllMocks();
  });

  test('Shows loading state while explaining', async () => {
    api.tradeApi.getIntelligence.mockImplementation(() => new Promise(() => {}));
    await act(async () => { render(<TradeIntelligence />); });
    const select = screen.getAllByRole('combobox')[0];
    await act(async () => { fireEvent.change(select, { target: { value: 'RELIANCE' } }); });
    await act(async () => { fireEvent.click(getExplainActionBtn()); });
    expect(screen.getByText('Running trade intelligence analysis...')).toBeInTheDocument();
  });

  test('Falls back to explain API if getIntelligence fails', async () => {
    api.tradeApi.getIntelligence.mockRejectedValue(new Error('Intelligence engine unavailable'));
    api.tradeApi.explain.mockResolvedValue(mockTradeData);
    await act(async () => { render(<TradeIntelligence />); });
    const select = screen.getAllByRole('combobox')[0];
    await act(async () => { fireEvent.change(select, { target: { value: 'RELIANCE' } }); });
    await act(async () => { fireEvent.click(getExplainActionBtn()); });
    await waitFor(() => {
      expect(api.tradeApi.explain).toHaveBeenCalled();
    });
  });

  test('Shows error banner on API failure', async () => {
    api.tradeApi.getIntelligence.mockRejectedValue(new Error('API Error'));
    api.tradeApi.explain.mockRejectedValue(new Error('API Error'));
    await act(async () => { render(<TradeIntelligence />); });
    const select = screen.getAllByRole('combobox')[0];
    await act(async () => { fireEvent.change(select, { target: { value: 'RELIANCE' } }); });
    await act(async () => { fireEvent.click(getExplainActionBtn()); });
    await waitFor(() => {
      expect(screen.getByText('API Error')).toBeInTheDocument();
    });
  });

  test('Disables button when no symbol selected', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    const btns = screen.getAllByText('Explain Trade');
    const actionBtn = btns.find(b => b.closest('button').classList.contains('actionBtn') || b.closest('button').disabled);
    expect(actionBtn.closest('button')).toBeDisabled();
  });

  test('Shows empty state when no trade data', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    expect(screen.getByText(/Select a symbol and click/)).toBeInTheDocument();
  });
});

describe('TradeIntelligence - Scenario 5: Trade Journal Tab', () => {
  beforeEach(() => {
    setupMocks();
    jest.clearAllMocks();
  });

  test('Displays journal stats cards', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    await act(async () => { fireEvent.click(screen.getByText('Trade Journal')); });
    await waitFor(() => {
      expect(screen.getByText('Journaled Trades')).toBeInTheDocument();
      expect(screen.getByText('With Regime')).toBeInTheDocument();
      expect(screen.getByText('Available')).toBeInTheDocument();
      expect(screen.getByText('YES')).toBeInTheDocument();
    });
  });

  test('Displays journal entries table', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    await act(async () => { fireEvent.click(screen.getByText('Trade Journal')); });
    await waitFor(() => {
      expect(screen.getByText('T1')).toBeInTheDocument();
      expect(screen.getByText('RELIANCE')).toBeInTheDocument();
      expect(screen.getByText('78%')).toBeInTheDocument();
    });
  });
});

describe('TradeIntelligence - Scenario 6: Memory Search Tab', () => {
  beforeEach(() => {
    setupMocks();
    jest.clearAllMocks();
    api.memoryApi.search.mockResolvedValue({
      results: [
        { memory_type: 'trade', relevance_score: 0.85, content: 'Failed breakout trade', ticker: 'RELIANCE' },
        { memory_type: 'market', relevance_score: 0.72, content: 'High volatility period', ticker: 'INFY' },
      ],
    });
  });

  test('Searches memory on Enter key', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    await act(async () => { fireEvent.click(screen.getByText('Memory Search')); });
    const input = screen.getByPlaceholderText(/Search trade memory/);
    await act(async () => { fireEvent.change(input, { target: { value: 'failed breakout' } }); });
    await act(async () => { fireEvent.keyDown(input, { key: 'Enter' }); });
    await waitFor(() => {
      expect(api.memoryApi.search).toHaveBeenCalledWith({ query: 'failed breakout', limit: 10 });
    });
  });

  test('Displays memory results', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    await act(async () => { fireEvent.click(screen.getByText('Memory Search')); });
    const input = screen.getByPlaceholderText(/Search trade memory/);
    await act(async () => { fireEvent.change(input, { target: { value: 'breakout' } }); });
    await act(async () => { fireEvent.click(screen.getByText('Search')); });
    await waitFor(() => {
      expect(screen.getByText('Failed breakout trade')).toBeInTheDocument();
      expect(screen.getByText('85%')).toBeInTheDocument();
    });
  });
});

describe('TradeIntelligence - Scenario 7: Regime Context Tab', () => {
  beforeEach(() => {
    setupMocks();
    jest.clearAllMocks();
  });

  test('Displays current regime data', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    await act(async () => { fireEvent.click(screen.getByText('Regime Context')); });
    await waitFor(() => {
      expect(screen.getByText('Current Market Regime')).toBeInTheDocument();
      expect(screen.getByText('bull trend')).toBeInTheDocument();
      expect(screen.getByText('82.0%')).toBeInTheDocument();
      expect(screen.getByText('LOW')).toBeInTheDocument();
    });
  });

  test('Displays trading recommendations', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    await act(async () => { fireEvent.click(screen.getByText('Regime Context')); });
    await waitFor(() => {
      expect(screen.getByText('Trading Recommendations')).toBeInTheDocument();
      expect(screen.getByText('Hold positions')).toBeInTheDocument();
    });
  });
});

describe('TradeIntelligence - Scenario 8: Initialization with API Data', () => {
  beforeEach(() => {
    setupMocks();
    jest.clearAllMocks();
  });

  test('Loads stocks on mount', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    await waitFor(() => {
      expect(api.stocksApi.getAll).toHaveBeenCalledTimes(1);
    });
  });

  test('Loads journal data on mount', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    await waitFor(() => {
      expect(api.journalApi.getStats).toHaveBeenCalledTimes(1);
      expect(api.journalApi.getTrades).toHaveBeenCalledTimes(1);
    });
  });

  test('Loads regime data on mount', async () => {
    await act(async () => { render(<TradeIntelligence />); });
    await waitFor(() => {
      expect(api.regimeApi.getCurrent).toHaveBeenCalledTimes(1);
    });
  });

  test('Handles empty stocks gracefully', async () => {
    api.stocksApi.getAll.mockResolvedValue({ stocks: [] });
    await act(async () => { render(<TradeIntelligence />); });
    await waitFor(() => {
      const select = screen.getAllByRole('combobox')[0];
      expect(select.options.length).toBe(1);
      expect(select.options[0].text).toBe('Select a symbol...');
    });
  });
});
