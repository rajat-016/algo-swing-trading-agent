import React, { useState, useEffect } from 'react';
import { stocksApi, tradingApi, wsManager } from './api';
import {
  EquityCurveChart,
  DailyPnLChart,
  PositionDistributionChart,
  PerformanceMetrics,
} from './components/Charts';
import Monitoring from './components/Monitoring';

function App() {
  const [stocks, setStocks] = useState([]);
  const [portfolio, setPortfolio] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [tradingStatus, setTradingStatus] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  const [countdown, setCountdown] = useState(60);
  const [cycleInterval, setCycleInterval] = useState(60);
  const [lastRefresh, setLastRefresh] = useState(Date.now());

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [stocksData, portfolioData] = await Promise.all([
        stocksApi.getAll(),
        stocksApi.getPortfolio(),
      ]).catch(() => ({ stocks: [], total: 0 }));

      setStocks(stocksData.stocks || []);
      setPortfolio(portfolioData);
    } catch (err) {
      console.error('Fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const analyticsData = await stocksApi.getAnalytics();
      setAnalytics(analyticsData);
    } catch (err) {
      console.error('Analytics error:', err);
    }
  };

  const fetchStatus = async () => {
    try {
      const statusData = await tradingApi.getStatus();
      setTradingStatus(statusData);
      if (statusData.cycle_interval_seconds) {
        setCycleInterval(statusData.cycle_interval_seconds);
        setCountdown(statusData.cycle_interval_seconds);
      }
    } catch (err) {
      console.error('Status error:', err);
    }
  };

  useEffect(() => {
    document.body.className = theme === 'light' ? 'theme-light' : '';
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  useEffect(() => {
    fetchData();
    fetchStatus();
    wsManager.connect();

    const unsubscribe = wsManager.subscribe((data) => {
      console.log('Real-time update:', data);
      setWsConnected(wsManager.isConnected());

      if (data.type === 'entry') {
        setStocks(prev => [{
          symbol: data.symbol,
          status: 'ENTERED',
          entry_price: data.price,
          target_price: data.target,
          stop_loss: data.sl,
          entry_quantity: data.quantity,
          original_quantity: data.quantity,
          remaining_quantity: data.quantity,
          current_tier: 1,
          entry_reason: data.reason,
          entry_date: new Date().toISOString(),
          pnl: 0,
          pnl_percentage: 0,
          realized_pnl: 0,
          sl_breach_severity: 'SAFE',
        }, ...prev]);
      } else if (data.type === 'exit') {
        setStocks(prev => prev.map(s =>
          s.symbol === data.symbol
            ? { ...s, status: 'EXITED', pnl: data.pnl, pnl_percentage: data.pnl_pct }
            : s
        ));
      } else if (data.type === 'tier_exit') {
        setStocks(prev => prev.map(s =>
          s.symbol === data.symbol
            ? {
                ...s,
                remaining_quantity: data.remaining,
                current_tier: data.tier + 1,
                realized_pnl: data.realized_pnl,
                pnl: data.pnl,
                pnl_percentage: data.pnl_pct,
                ...(data.remaining <= 0 ? { status: 'EXITED' } : {}),
              }
            : s
        ));
      } else if (data.type === 'price_update') {
        setStocks(prev => prev.map(s =>
          s.symbol === data.symbol
            ? {
                ...s,
                current_price: data.current_price,
                pnl_pct: data.pnl_pct,
                ...(data.tier ? { current_tier: data.tier } : {}),
                ...(data.remaining !== undefined ? { remaining_quantity: data.remaining } : {}),
                ...(data.sl_severity ? { sl_breach_severity: data.sl_severity } : {}),
              }
            : s
        ));
      }
    });

    const statusInterval = setInterval(fetchStatus, 60000);

    return () => {
      unsubscribe();
      wsManager.disconnect();
      clearInterval(statusInterval);
    };
  }, []);

  useEffect(() => {
    if (activeTab === 'analytics') {
      fetchAnalytics();
    }
  }, [activeTab]);

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          fetchData();
          fetchStatus();
          setLastRefresh(Date.now());
          return cycleInterval;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [cycleInterval]);

  const handleSwitchMode = async (mode) => {
    try {
      await tradingApi.switchMode(mode);
      await fetchStatus();
    } catch (err) {
      setError(err.message);
    }
  };

  const filteredStocks = stocks.filter(stock => {
    if (activeTab === 'dashboard') return true;
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

  const calculateLivePnL = (stock) => {
    if (!stock.current_price || !stock.entry_price || !stock.entry_quantity) return null;
    return (stock.current_price - stock.entry_price) * stock.entry_quantity;
  };

  const calculateLivePnLPct = (stock) => {
    if (!stock.current_price || !stock.entry_price || stock.current_price === 0) return null;
    return ((stock.current_price - stock.entry_price) / stock.entry_price) * 100;
  };

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: '◈' },
    { id: 'positions', label: 'Positions', icon: '▲' },
    { id: 'history', label: 'History', icon: '◷' },
    { id: 'analytics', label: 'Analytics', icon: '◇' },
    { id: 'monitoring', label: 'Monitoring', icon: '◎' },
  ];

  if (loading && stocks.length === 0) {
    return (
      <div className="app">
        <div className="loader">
          <div className="loader-ring"></div>
          <div className="loader-text">Initializing...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <div className="glow-bg"></div>
      <div className="grid-overlay"></div>
      
      <aside className="sidebar">
        <div className="logo">
          <span className="logoIcon">◉</span>
          <span className="logoText">AST</span>
        </div>
        
        <nav className="nav">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`navItem ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className="navIcon">{tab.icon}</span>
              <span className="navLabel">{tab.label}</span>
            </button>
          ))}
        </nav>
        
        <div className="sidebarFooter">
          <div className="connectionStatus">
            <span className={`statusDot ${wsConnected ? 'connected' : ''}`}></span>
            <span className="statusText">{wsConnected ? 'Live' : 'Offline'}</span>
          </div>
          {tradingStatus && (
            <div className={`modeBadge ${tradingStatus.mode}`}>
              <span className="modeDot"></span>
              {tradingStatus.mode.toUpperCase()}
            </div>
          )}
        </div>
      </aside>
      
      <main className="main">
        <header className="header">
          <div className="headerLeft">
            <h1 className="pageTitle">
              {tabs.find(t => t.id === activeTab)?.label}
            </h1>
            <span className="pageSubtitle">
              {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
            </span>
          </div>
          <div className="headerRight">
            <div className="countdownTimer" title="Auto-refresh countdown">
              <span className="countdownValue">{countdown}</span>
              <span className="countdownLabel">s</span>
            </div>
            <button className="iconBtn" onClick={toggleTheme} title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>
              <span>{theme === 'dark' ? '☀' : '☾'}</span>
            </button>
            <button className="iconBtn" onClick={fetchData}>
              <span>↻</span>
            </button>
            <button 
              className={`modeBtn ${tradingStatus?.mode === 'paper' ? 'active' : ''}`}
              onClick={() => handleSwitchMode('paper')}
            >
              Paper
            </button>
            <button 
              className={`modeBtn live ${tradingStatus?.mode === 'live' ? 'active' : ''}`}
              onClick={() => handleSwitchMode('live')}
            >
              Live
            </button>
          </div>
        </header>
        
        {error && <div className="errorBanner">{error}</div>}
        
        <div className="statsGrid">
          <div className="statCard">
            <div className="statHeader">
              <span className="statLabel">Portfolio Value</span>
              <span className="statTrend neutral"></span>
            </div>
            <div className="statValue">{formatCurrency(portfolio?.total || 0)}</div>
            <div className="statSubtext">Total deployed capital</div>
          </div>
          
          <div className="statCard">
            <div className="statHeader">
              <span className="statLabel">Total P&L</span>
            </div>
            <div className={`statValue ${(portfolio?.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
              {formatCurrency(portfolio?.total_pnl || 0)}
            </div>
            <div className="statSubtext">
              {formatPercent(portfolio?.avg_pnl_percentage)} avg per trade
            </div>
          </div>
          
          <div className="statCard">
            <div className="statHeader">
              <span className="statLabel">Win Rate</span>
            </div>
            <div className={`statValue ${(portfolio?.win_rate || 0) >= 50 ? 'positive' : 'negative'}`}>
              {portfolio?.win_rate?.toFixed(1) || 0}%
            </div>
            <div className="statSubtext">{portfolio?.total_trades || 0} total trades</div>
          </div>
          
          <div className="statCard">
            <div className="statHeader">
              <span className="statLabel">Open Positions</span>
            </div>
            <div className="statValue neutral">{portfolio?.open_positions || 0}</div>
            <div className="statSubtext">
              {stocks.filter(s => s.status === 'ENTERED').length} active
            </div>
          </div>
        </div>
        
        {activeTab === 'monitoring' ? (
          <section className="monitoringSection">
            <Monitoring />
          </section>
        ) : activeTab === 'analytics' ? (
          <section className="analyticsSection">
            <h2 className="sectionTitle">Performance Analytics</h2>
            {!analytics ? (
              <div className="loadingBlock">Loading analytics...</div>
            ) : (
              <>
                <PerformanceMetrics metrics={analytics.metrics} />
                <div className="chartsGrid">
                  <div className="chartCard">
                    <div className="chartHeader">
                      <h3>Equity Curve</h3>
                      <span className="chartSubtitle">Cumulative P&L over time</span>
                    </div>
                    <EquityCurveChart data={analytics.equity_curve} />
                  </div>
                  
                  <div className="chartCard">
                    <div className="chartHeader">
                      <h3>Daily P&L</h3>
                      <span className="chartSubtitle">Profit/Loss per trade day</span>
                    </div>
                    <DailyPnLChart data={analytics.daily_pnl} />
                  </div>
                  
                  <div className="chartCard">
                    <div className="chartHeader">
                      <h3>Position Distribution</h3>
                      <span className="chartSubtitle">Open vs Closed positions</span>
                    </div>
                    <PositionDistributionChart data={analytics.status_distribution} />
                  </div>
                </div>
              </>
            )}
          </section>
        ) : (
          <section className="tableSection">
            <div className="tableCard">
              <table className="dataTable">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Status</th>
                    <th>Qty</th>
                    <th>Remaining</th>
                    <th>Tier</th>
                    <th>Entry</th>
                    <th>Current</th>
                    <th>Target</th>
                    <th>SL</th>
                    <th>SL Status</th>
                    <th>Realized P&L</th>
                    <th>P&L</th>
                    <th>P&L %</th>
                    <th>Reason</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredStocks.map((stock, idx) => {
                    const currentPrice = stock.current_price || stock.average_price || 0;
                    const livePnl = calculateLivePnL({...stock, current_price: currentPrice});
                    const livePnlPct = calculateLivePnLPct({...stock, current_price: currentPrice});
                    const pnl = stock.pnl !== undefined && stock.pnl !== null && stock.pnl !== 0 ? stock.pnl : livePnl;
                    const pnlPct = stock.pnl_percentage !== undefined && stock.pnl_percentage !== null && stock.pnl_percentage !== 0
                      ? stock.pnl_percentage
                      : livePnlPct;
                    const originalQty = stock.original_quantity || stock.entry_quantity;
                    const remaining = stock.remaining_quantity || stock.entry_quantity;
                    const tier = stock.current_tier || 1;
                    const tierDisplay = stock.status === 'EXITED' ? '-' : `${tier}/4`;
                    const remainingDisplay = stock.status === 'EXITED' ? '-' : `${remaining}/${originalQty}`;
                    const realizedPnl = stock.realized_pnl || 0;
                    const slSeverity = stock.sl_breach_severity || 'SAFE';
                    const slSeverityClass = `slSeverity ${slSeverity.toLowerCase()}`;
                    const slSeverityLabel = {safe: 'SAFE', yellow: 'WATCH', orange: 'BELOW', red: 'DEEP', critical: 'CRIT'}[slSeverity.toLowerCase()] || slSeverity;

                    return (
                      <tr key={stock.id || `${stock.symbol}-${idx}`}>
                        <td className="symbolCell">{stock.symbol}</td>
                        <td>
                          <span className={`statusPill ${stock.status?.toLowerCase()}`}>
                            {stock.status}
                          </span>
                        </td>
                        <td>{originalQty || '-'}</td>
                        <td className="monoCell">{remainingDisplay}</td>
                        <td className="tierCell">{tierDisplay}</td>
                        <td>{formatCurrency(stock.average_price)}</td>
                        <td className="priceCell">{formatCurrency(currentPrice)}</td>
                        <td className="targetCell">{formatCurrency(stock.target_price)}</td>
                        <td className="slCell">{formatCurrency(stock.stop_loss)}</td>
                        <td className={slSeverityClass}>{slSeverityLabel}</td>
                        <td className={`pnlCell ${(realizedPnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                          {stock.status !== 'EXITED' && realizedPnl !== 0 ? formatCurrency(realizedPnl) : '-'}
                        </td>
                        <td className={`pnlCell ${(pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                          {pnl !== null ? formatCurrency(pnl) : '-'}
                        </td>
                        <td className={`pnlCell ${(pnlPct || 0) >= 0 ? 'positive' : 'negative'}`}>
                          {formatPercent(pnlPct)}
                        </td>
                        <td className="reasonCell">{stock.entry_reason || '-'}</td>
                        <td className="dateCell">
                          {stock.entry_date ? new Date(stock.entry_date).toLocaleDateString() : '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {filteredStocks.length === 0 && (
                <div className="emptyState">No positions found</div>
              )}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;