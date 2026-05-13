import React, { useState, useEffect, useCallback } from 'react';
import { regimeApi } from '../api';

function RegimeBadge({ regime }) {
  const colors = {
    bull_trend: 'var(--accent-primary)',
    bear_trend: 'var(--accent-danger)',
    sideways: 'var(--accent-warning)',
    high_volatility: 'var(--accent-danger)',
    low_volatility: 'var(--accent-info)',
    event_driven: 'var(--accent-warning)',
    mean_reversion: 'var(--accent-info)',
    breakout: 'var(--accent-primary)',
  };
  const color = colors[regime] || 'var(--text-muted)';
  return (
    <span className="regimeBadge" style={{ background: `${color}15`, color, border: `1px solid ${color}30` }}>
      {regime ? regime.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) : 'Unknown'}
    </span>
  );
}

function MarketIntelligence() {
  const [current, setCurrent] = useState(null);
  const [history, setHistory] = useState([]);
  const [distribution, setDistribution] = useState({});
  const [transitions, setTransitions] = useState([]);
  const [transitionData, setTransitionData] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeSubTab, setActiveSubTab] = useState('overview');

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [cur, hist, dist, trans, transData, hlth] = await Promise.all([
        regimeApi.getCurrent().catch(() => null),
        regimeApi.getHistory().catch(() => null),
        regimeApi.getDistribution().catch(() => null),
        regimeApi.getTransitions().catch(() => null),
        regimeApi.getTransitionData().catch(() => null),
        regimeApi.getHealth().catch(() => null),
      ]);
      setCurrent(cur);
      setHistory(Array.isArray(hist?.history) ? hist.history : Array.isArray(hist) ? hist : []);
      setDistribution(dist?.distribution || dist || {});
      setTransitions(Array.isArray(trans?.transitions) ? trans.transitions : Array.isArray(trans) ? trans : []);
      setTransitionData(transData || null);
      setHealth(hlth || null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  if (loading) return <div className="loadingBlock">Loading market intelligence...</div>;
  if (error) return <div className="errorBanner">Error: {error}</div>;

  const subTabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'history', label: 'History' },
    { id: 'transitions', label: 'Transitions' },
    { id: 'health', label: 'Health' },
  ];

  return (
    <section className="intelligenceDashboard">
      <div className="intelHeader">
        <h2 className="sectionTitle">Market Intelligence</h2>
        <button className="refreshBtn" onClick={fetchAll}>↻</button>
      </div>

      <div className="sub-tabs">
        {subTabs.map(t => (
          <button key={t.id} className={`sub-tab ${activeSubTab === t.id ? 'active' : ''}`} onClick={() => setActiveSubTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {activeSubTab === 'overview' && (
        <div className="intelOverview">
          <div className="intelCards">
            <div className="intelCard currentRegimeCard">
              <div className="intelCardLabel">Current Regime</div>
              <div className="intelCardValue">
                {current ? <RegimeBadge regime={current.regime || current.regime_type} /> : 'N/A'}
              </div>
              {current && (
                <div className="intelCardDetails">
                  <div className="detailRow">
                    <span className="detailKey">Confidence</span>
                    <span className="detailVal">{(current.confidence * 100).toFixed(1)}%</span>
                  </div>
                  <div className="detailRow">
                    <span className="detailKey">Risk Level</span>
                    <span className={`detailVal risk-${current.risk_level || 'unknown'}`}>
                      {(current.risk_level || 'unknown').toUpperCase()}
                    </span>
                  </div>
                  {current.regime_stability && (
                    <div className="detailRow">
                      <span className="detailKey">Stability</span>
                      <span className="detailVal">{(current.regime_stability * 100).toFixed(0)}%</span>
                    </div>
                  )}
                  {current.volatility_context && (
                    <div className="detailRow">
                      <span className="detailKey">Volatility</span>
                      <span className="detailVal">{current.volatility_context.level || 'N/A'}</span>
                    </div>
                  )}
                </div>
              )}
              {current?.recommended_behavior && (
                <div className="recommendations">
                  <div className="intelCardLabel">Recommendations</div>
                  <ul className="recList">
                    {current.recommended_behavior.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="intelCard">
              <div className="intelCardLabel">Regime Distribution</div>
              <div className="distList">
                {Object.entries(distribution).length === 0 && <span className="noData">No data</span>}
                {Object.entries(distribution).sort((a, b) => b[1] - a[1]).map(([regime, count]) => (
                  <div key={regime} className="distRow">
                    <RegimeBadge regime={regime} />
                    <span className="distCount">{count}</span>
                    <div className="distBar">
                      <div className="distBarFill" style={{
                        width: `${Math.min(100, (count / Math.max(...Object.values(distribution))) * 100)}%`,
                        background: regime.includes('bull') || regime.includes('breakout') ? 'var(--accent-primary)' :
                          regime.includes('bear') || regime.includes('high_vol') ? 'var(--accent-danger)' :
                          regime.includes('sideways') ? 'var(--accent-warning)' : 'var(--accent-info)'
                      }}></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {transitionData && (
              <div className="intelCard">
                <div className="intelCardLabel">Transition Detection</div>
                <div className="intelCardDetails">
                  {transitionData.stability_assessment && (
                    <div className="detailRow">
                      <span className="detailKey">Stability</span>
                      <span className={`detailVal ${
                        transitionData.stability_assessment.stability_label === 'stable' ? 'risk-low' :
                        transitionData.stability_assessment.stability_label === 'unstable' ? 'risk-high' : ''
                      }`}>
                        {(transitionData.stability_assessment.stability_label || 'unknown').toUpperCase()}
                      </span>
                    </div>
                  )}
                  {transitionData.stability_assessment?.is_transitioning && (
                    <div className="detailRow">
                      <span className="detailKey">Transitioning</span>
                      <span className="detailVal risk-high">YES</span>
                    </div>
                  )}
                  {transitionData.most_likely_next_regime && (
                    <div className="detailRow">
                      <span className="detailKey">Next Likely</span>
                      <span className="detailVal">
                        <RegimeBadge regime={transitionData.most_likely_next_regime} />
                      </span>
                    </div>
                  )}
                  {transitionData.volatility_spike_alert && (
                    <div className="alertBox warning">
                      ⚠ Volatility spike detected
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {activeSubTab === 'history' && (
        <div className="intelHistory">
          {history.length === 0 ? (
            <div className="emptyState">No regime history available</div>
          ) : (
            <div className="tableCard">
              <table className="dataTable">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Regime</th>
                    <th>Confidence</th>
                    <th>Risk Level</th>
                    <th>Volatility</th>
                  </tr>
                </thead>
                <tbody>
                  {history.slice(0, 100).map((entry, i) => (
                    <tr key={i}>
                      <td className="dateCell">{new Date(entry.timestamp || entry.recorded_at).toLocaleString()}</td>
                      <td><RegimeBadge regime={entry.regime || entry.regime_type} /></td>
                      <td className="monoCell">{((entry.confidence || 0) * 100).toFixed(1)}%</td>
                      <td><span className={`badge risk-${entry.risk_level || 'unknown'}`}>{(entry.risk_level || 'N/A').toUpperCase()}</span></td>
                      <td className="monoCell">{entry.volatility_context?.level || entry.volatility_level || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeSubTab === 'transitions' && (
        <div className="intelTransitions">
          {transitions.length === 0 ? (
            <div className="emptyState">No transitions recorded</div>
          ) : (
            <div className="tableCard">
              <table className="dataTable">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>From</th>
                    <th>To</th>
                    <th>Type</th>
                  </tr>
                </thead>
                <tbody>
                  {transitions.slice(0, 50).map((t, i) => (
                    <tr key={i}>
                      <td className="dateCell">{new Date(t.timestamp || t.recorded_at).toLocaleString()}</td>
                      <td><RegimeBadge regime={t.from_regime || t.previous_regime} /></td>
                      <td><RegimeBadge regime={t.to_regime || t.current_regime} /></td>
                      <td><span className="badge">{(t.transition_type || 'change').toUpperCase()}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeSubTab === 'health' && (
        <div className="intelHealth">
          <div className="intelCards">
            <div className="intelCard">
              <div className="intelCardLabel">Engine Status</div>
              <div className="intelCardValue">
                <span className={`healthBadge ${health?.status === 'healthy' ? 'ok' : health?.status === 'degraded' ? 'warn' : 'danger'}`}>
                  {(health?.status || 'unknown').toUpperCase()}
                </span>
              </div>
              {health?.details && (
                <div className="intelCardDetails">
                  {Object.entries(health.details).map(([k, v]) => (
                    <div key={k} className="detailRow">
                      <span className="detailKey">{k.replace(/_/g, ' ')}</span>
                      <span className="detailVal">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            {transitionData?.transition_probabilities && (
              <div className="intelCard">
                <div className="intelCardLabel">Transition Probabilities</div>
                <div className="probMatrix">
                  {Object.entries(transitionData.transition_probabilities).map(([from, tos]) => (
                    <div key={from} className="probRow">
                      <span className="probFrom"><RegimeBadge regime={from} /></span>
                      <div className="probTos">
                        {Object.entries(tos).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([to, prob]) => (
                          <span key={to} className="probItem">
                            <RegimeBadge regime={to} />
                            <span className="probVal">{(prob * 100).toFixed(0)}%</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

export default MarketIntelligence;
