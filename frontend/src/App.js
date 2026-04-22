import React, { useState, useEffect } from 'react';
import { stocksApi, tradingApi } from './api';

function App() {
  const [stocks, setStocks] = useState([]);
  const [portfolio, setPortfolio] = useState(null);
  const [tradingStatus, setTradingStatus] = useState(null);
  const [activeTab, setActiveTab] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [stocksData, portfolioData, statusData] = await Promise.all([
        stocksApi.getAll(),
        stocksApi.getPortfolio(),
        tradingApi.getStatus(),
      ]);

      setStocks(stocksData.stocks || []);
      setPortfolio(portfolioData);
      setTradingStatus(statusData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSwitchMode = async (mode) => {
    try {
      await tradingApi.switchMode(mode);
      await fetchData();
    } catch (err) {
      setError(err.message);
    }
  };

  const filteredStocks = stocks.filter(stock => {
    if (activeTab === 'all') return true;
    if (activeTab === 'positions') return stock.status === 'ENTERED';
    if (activeTab === 'history') return stock.status === 'EXITED';
    return true;
  });

  const formatCurrency = (value) => {
    if (value === null || value === undefined) return '-';
    return `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPercent = (value) => {
    if (value === null || value === undefined) return '-';
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  if (loading && stocks.length === 0) {
    return (
      <div className="app">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Algo Swing Trading Agent</h1>
        {tradingStatus && (
          <span className={`mode ${tradingStatus.mode}`}>
            {tradingStatus.mode.toUpperCase()} TRADING
          </span>
        )}
      </header>

      {error && <div className="error">{error}</div>}

      <div className="stats">
        <div className="stat-card">
          <div className="label">Total Trades</div>
          <div className="value neutral">{portfolio?.total_trades || 0}</div>
        </div>
        <div className="stat-card">
          <div className="label">Open Positions</div>
          <div className="value">{portfolio?.open_positions || 0}</div>
        </div>
        <div className="stat-card">
          <div className="label">Total P&L</div>
          <div className={`value ${(portfolio?.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
            {formatCurrency(portfolio?.total_pnl || 0)}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">Win Rate</div>
          <div className="value">{portfolio?.win_rate?.toFixed(1) || 0}%</div>
        </div>
        <div className="stat-card">
          <div className="label">Avg Return</div>
          <div className={`value ${(portfolio?.avg_pnl_percentage || 0) >= 0 ? 'positive' : 'negative'}`}>
            {formatPercent(portfolio?.avg_pnl_percentage || 0)}
          </div>
        </div>
      </div>

      <div className="actions">
        <button className="btn secondary" onClick={() => handleSwitchMode('paper')}>
          Paper Mode
        </button>
        <button className="btn danger" onClick={() => handleSwitchMode('live')}>
          Live Mode
        </button>
        <button className="btn primary" onClick={fetchData}>
          Refresh
        </button>
      </div>

      <div className="tabs">
        <button
          className={`tab ${activeTab === 'all' ? 'active' : ''}`}
          onClick={() => setActiveTab('all')}
        >
          All Stocks
        </button>
        <button
          className={`tab ${activeTab === 'positions' ? 'active' : ''}`}
          onClick={() => setActiveTab('positions')}
        >
          Open Positions
        </button>
        <button
          className={`tab ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          Trade History
        </button>
      </div>

      <div className="stocks-table">
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Status</th>
              <th>Entry Price</th>
              <th>Target</th>
              <th>Stop Loss</th>
              <th>P&L</th>
              <th>Entry Reason</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {filteredStocks.map(stock => (
              <tr key={stock.id || stock.symbol}>
                <td className="symbol">{stock.symbol}</td>
                <td>
                  <span className={`status ${stock.status?.toLowerCase()}`}>
                    {stock.status}
                  </span>
                </td>
                <td>{formatCurrency(stock.entry_price)}</td>
                <td>{formatCurrency(stock.target_price)}</td>
                <td>{formatCurrency(stock.stop_loss)}</td>
                <td className={`pnl ${stock.pnl >= 0 ? 'positive' : 'negative'}`}>
                  {formatCurrency(stock.pnl)} ({formatPercent(stock.pnl_percentage)})
                </td>
                <td className="reason">{stock.entry_reason || '-'}</td>
                <td>{stock.entry_date ? new Date(stock.entry_date).toLocaleDateString() : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredStocks.length === 0 && (
          <div className="loading">No stocks found</div>
        )}
      </div>
    </div>
  );
}

export default App;