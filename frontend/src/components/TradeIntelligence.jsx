import React, { useState, useEffect, useCallback } from 'react';
import { stocksApi, tradeApi, journalApi, memoryApi, regimeApi } from '../api';

function TradeIntelligence() {
  const [activeSubTab, setActiveSubTab] = useState('explain');
  const [stocks, setStocks] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [tradeResult, setTradeResult] = useState(null);
  const [journalTrades, setJournalTrades] = useState([]);
  const [journalStats, setJournalStats] = useState(null);
  const [memorySearchQuery, setMemorySearchQuery] = useState('');
  const [memoryResults, setMemoryResults] = useState([]);
  const [currentRegime, setCurrentRegime] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    stocksApi.getAll().then(d => setStocks(d.stocks || [])).catch(() => {});
    regimeApi.getCurrent().then(r => setCurrentRegime(r)).catch(() => {});
    journalApi.getStats().then(s => setJournalStats(s)).catch(() => {});
    journalApi.getTrades().then(t => setJournalTrades(Array.isArray(t) ? t : t?.trades || [])).catch(() => {});
  }, []);

  const handleExplain = useCallback(async () => {
    if (!selectedSymbol) return;
    try {
      setLoading(true);
      setError(null);
      const result = await tradeApi.explain({ symbol: selectedSymbol });
      setTradeResult(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedSymbol]);

  const handleMemorySearch = useCallback(async () => {
    if (!memorySearchQuery.trim()) return;
    try {
      setLoading(true);
      const results = await memoryApi.search({ query: memorySearchQuery, limit: 10 });
      setMemoryResults(results?.results || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [memorySearchQuery]);

  const subTabs = [
    { id: 'explain', label: 'Explain Trade' },
    { id: 'journal', label: 'Trade Journal' },
    { id: 'memory', label: 'Memory Search' },
    { id: 'regime', label: 'Regime Context' },
  ];

  return (
    <section className="intelligenceDashboard">
      <div className="intelHeader">
        <h2 className="sectionTitle">Trade Intelligence</h2>
      </div>

      <div className="sub-tabs">
        {subTabs.map(t => (
          <button key={t.id} className={`sub-tab ${activeSubTab === t.id ? 'active' : ''}`} onClick={() => setActiveSubTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {error && <div className="errorBanner">{error}</div>}

      {activeSubTab === 'explain' && (
        <div className="intelExplain">
          <div className="explainForm">
            <select className="intelSelect" value={selectedSymbol} onChange={e => setSelectedSymbol(e.target.value)}>
              <option value="">Select a symbol...</option>
              {stocks.map(s => (
                <option key={s.symbol} value={s.symbol}>{s.symbol}</option>
              ))}
            </select>
            <button className="actionBtn" onClick={handleExplain} disabled={loading || !selectedSymbol}>
              {loading ? 'Analyzing...' : 'Explain Trade'}
            </button>
          </div>

          {tradeResult && (
            <div className="explainResult">
              {tradeResult.explanation && (
                <div className="intelCards">
                  <div className="intelCard">
                    <div className="intelCardLabel">Trade Explanation</div>
                    <div className="explanationText">{tradeResult.explanation}</div>
                  </div>
                </div>
              )}

              {tradeResult.top_features && tradeResult.top_features.length > 0 && (
                <div className="intelCards" style={{ marginTop: 16 }}>
                  <div className="intelCard">
                    <div className="intelCardLabel">Key Features</div>
                    <div className="featureList">
                      {tradeResult.top_features.map((f, i) => {
                        const feat = typeof f === 'string' ? { name: f, importance: 0 } : f;
                        return (
                          <div key={i} className="featureRow">
                            <span className="featureName">{feat.name || feat.feature || feat}</span>
                            {feat.importance != null && (
                              <div className="featureBar">
                                <div className="featureBarFill" style={{
                                  width: `${Math.abs(feat.importance) * 100}%`,
                                  background: feat.importance >= 0 ? 'var(--accent-primary)' : 'var(--accent-danger)'
                                }}></div>
                              </div>
                            )}
                            {feat.importance != null && (
                              <span className={`featureVal ${feat.importance >= 0 ? 'positive' : 'negative'}`}>
                                {feat.importance.toFixed(3)}
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {tradeResult.confidence != null && (
                <div className="metricCards" style={{ marginTop: 16 }}>
                  <div className="metricCard">
                    <div className="metricTitle">Confidence</div>
                    <div className={`metricValue ${tradeResult.confidence >= 0.65 ? 'positive' : tradeResult.confidence >= 0.5 ? '' : 'negative'}`}>
                      {(tradeResult.confidence * 100).toFixed(1)}%
                    </div>
                  </div>
                  {tradeResult.prediction && (
                    <div className="metricCard">
                      <div className="metricTitle">Prediction</div>
                      <div className={`metricValue ${
                        tradeResult.prediction === 'BUY' || tradeResult.prediction === 2 ? 'positive' :
                        tradeResult.prediction === 'SELL' || tradeResult.prediction === 0 ? 'negative' : ''
                      }`}>{tradeResult.prediction}</div>
                    </div>
                  )}
                  {tradeResult.similar_trades && (
                    <div className="metricCard">
                      <div className="metricTitle">Similar Trades</div>
                      <div className="metricValue neutral">{tradeResult.similar_trades.length}</div>
                    </div>
                  )}
                </div>
              )}

              {tradeResult.similar_trades && tradeResult.similar_trades.length > 0 && (
                <div className="intelCards" style={{ marginTop: 16 }}>
                  <div className="intelCard">
                    <div className="intelCardLabel">Similar Historical Trades</div>
                    <div className="simTrades">
                      {tradeResult.similar_trades.map((t, i) => (
                        <div key={i} className="simTradeRow">
                          <span className="simTradeSymbol">{t.ticker || t.symbol}</span>
                          <span className="simTradeOutcome">
                            <span className={`badge ${t.outcome === 'WIN' || t.outcome === 'win' ? 'risk-low' : 'risk-high'}`}>
                              {t.outcome || 'UNKNOWN'}
                            </span>
                          </span>
                          {t.relevance_score != null && (
                            <span className="simTradeRelevance">{(t.relevance_score * 100).toFixed(0)}% match</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeSubTab === 'journal' && (
        <div className="intelJournal">
          {journalStats && (
            <div className="metricCards" style={{ marginBottom: 16 }}>
              <div className="metricCard">
                <div className="metricTitle">Journaled Trades</div>
                <div className="metricValue neutral">{journalStats.total_trades || journalStats.count || 0}</div>
              </div>
              <div className="metricCard">
                <div className="metricTitle">With Regime</div>
                <div className="metricValue neutral">{journalStats.with_regime || 0}</div>
              </div>
              <div className="metricCard">
                <div className="metricTitle">Available</div>
                <div className={`metricValue ${journalStats.available ? 'positive' : 'negative'}`}>
                  {journalStats.available ? 'YES' : 'NO'}
                </div>
              </div>
            </div>
          )}
          {journalTrades.length === 0 ? (
            <div className="emptyState">No journal entries found</div>
          ) : (
            <div className="tableCard">
              <table className="dataTable">
                <thead>
                  <tr>
                    <th>Trade ID</th>
                    <th>Symbol</th>
                    <th>Date</th>
                    <th>Regime</th>
                    <th>Confidence</th>
                    <th>Outcome</th>
                  </tr>
                </thead>
                <tbody>
                  {journalTrades.slice(0, 50).map((t, i) => (
                    <tr key={t.trade_id || i}>
                      <td className="monoCell">{t.trade_id || '-'}</td>
                      <td className="symbolCell">{t.ticker || t.symbol}</td>
                      <td className="dateCell">{new Date(t.timestamp || t.entry_date).toLocaleDateString()}</td>
                      <td>{t.market_regime ? t.market_regime.replace(/_/g, ' ') : '-'}</td>
                      <td className="monoCell">{t.confidence != null ? `${(t.confidence * 100).toFixed(0)}%` : '-'}</td>
                      <td>
                        <span className={`badge ${t.outcome === 'WIN' ? 'risk-low' : t.outcome === 'LOSS' ? 'risk-high' : ''}`}>
                          {t.outcome || 'OPEN'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeSubTab === 'memory' && (
        <div className="intelMemory">
          <div className="explainForm">
            <input
              type="text"
              className="intelInput"
              placeholder="Search trade memory (e.g., 'failed breakout during high volatility')..."
              value={memorySearchQuery}
              onChange={e => setMemorySearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleMemorySearch()}
            />
            <button className="actionBtn" onClick={handleMemorySearch} disabled={loading || !memorySearchQuery.trim()}>
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>

          {memoryResults.length === 0 && memorySearchQuery && !loading && (
            <div className="emptyState">No matching results</div>
          )}

          {memoryResults.length > 0 && (
            <div className="memoryResults">
              {memoryResults.map((r, i) => (
                <div key={i} className="memoryCard">
                  <div className="memoryHeader">
                    <span className="memoryType">{r.memory_type || r.collection || 'trade'}</span>
                    <span className="memoryRelevance">{(r.relevance_score * 100).toFixed(0)}%</span>
                  </div>
                  <div className="memoryContent">{r.content || r.text || JSON.stringify(r.metadata || {})}</div>
                  {r.ticker && <div className="memoryFooter"><span className="symbolCell">{r.ticker}</span></div>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeSubTab === 'regime' && (
        <div className="intelRegimeContext">
          {currentRegime ? (
            <div className="intelCards">
              <div className="intelCard">
                <div className="intelCardLabel">Current Market Regime</div>
                <div className="intelCardValue">
                  <span className="regimeBadge" style={{
                    background: `${currentRegime.regime?.includes('bull') || currentRegime.regime?.includes('breakout') ? 'var(--accent-primary)' :
                      currentRegime.regime?.includes('bear') || currentRegime.regime?.includes('high_vol') ? 'var(--accent-danger)' :
                      'var(--accent-warning)'}15`,
                    color: currentRegime.regime?.includes('bull') || currentRegime.regime?.includes('breakout') ? 'var(--accent-primary)' :
                      currentRegime.regime?.includes('bear') || currentRegime.regime?.includes('high_vol') ? 'var(--accent-danger)' :
                      'var(--accent-warning)',
                    border: `1px solid ${currentRegime.regime?.includes('bull') || currentRegime.regime?.includes('breakout') ? 'var(--accent-primary)' :
                      currentRegime.regime?.includes('bear') || currentRegime.regime?.includes('high_vol') ? 'var(--accent-danger)' :
                      'var(--accent-warning)'}30`,
                    padding: '8px 16px', borderRadius: 'var(--radius-sm)', fontWeight: 600, textTransform: 'capitalize'
                  }}>
                    {currentRegime.regime?.replace(/_/g, ' ') || currentRegime.regime_type?.replace(/_/g, ' ')}
                  </span>
                </div>
                <div className="intelCardDetails">
                  <div className="detailRow">
                    <span className="detailKey">Confidence</span>
                    <span className="detailVal">{(currentRegime.confidence * 100).toFixed(1)}%</span>
                  </div>
                  <div className="detailRow">
                    <span className="detailKey">Risk Level</span>
                    <span className={`detailVal risk-${currentRegime.risk_level || 'unknown'}`}>
                      {(currentRegime.risk_level || 'unknown').toUpperCase()}
                    </span>
                  </div>
                  {currentRegime.recommended_behavior && (
                    <div style={{ marginTop: 12 }}>
                      <div className="intelCardLabel" style={{ fontSize: 12, marginBottom: 8 }}>Trading Recommendations</div>
                      <ul className="recList">
                        {currentRegime.recommended_behavior.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="emptyState">No regime data available</div>
          )}
        </div>
      )}
    </section>
  );
}

export default TradeIntelligence;
