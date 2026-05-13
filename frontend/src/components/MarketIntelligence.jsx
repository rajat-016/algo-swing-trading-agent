import React, { useState, useEffect, useCallback, useRef } from 'react';
import { regimeApi } from '../api';

const POLL_INTERVAL = 30000;

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

function ConfidenceBar({ confidence }) {
  const pct = Math.min(100, Math.max(0, (confidence || 0) * 100));
  const color = pct >= 70 ? 'var(--accent-primary)' : pct >= 40 ? 'var(--accent-warning)' : 'var(--accent-danger)';
  return (
    <div className="vizConfidenceBar">
      <div className="vizConfidenceTrack">
        <div className="vizConfidenceFill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="vizConfidenceLabel" style={{ color }}>{pct.toFixed(1)}%</span>
    </div>
  );
}

function VolatilityGauge({ ctx }) {
  if (!ctx) return null;
  const level = ctx.vix_level || ctx.atr_pct || 0;
  const label = level > 25 ? 'High' : level > 15 ? 'Medium' : 'Low';
  const color = level > 25 ? 'var(--accent-danger)' : level > 15 ? 'var(--accent-warning)' : 'var(--accent-primary)';
  const pct = Math.min(100, (level / 40) * 100);
  return (
    <div className="vizVolGauge">
      <div className="vizVolTrack">
        <div className="vizVolFill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="vizVolLabel" style={{ color }}>{label}</span>
    </div>
  );
}

function BreadthGauge({ label, value, highIsGood = true }) {
  if (value == null) return null;
  const pct = typeof value === 'number' && value <= 1 ? value * 100 : value;
  const color = highIsGood
    ? pct >= 60 ? 'var(--accent-primary)' : pct >= 40 ? 'var(--accent-warning)' : 'var(--accent-danger)'
    : pct <= 40 ? 'var(--accent-primary)' : pct <= 60 ? 'var(--accent-warning)' : 'var(--accent-danger)';
  return (
    <div className="breadthGauge">
      <div className="breadthGaugeLabel">{label}</div>
      <div className="breadthGaugeTrack">
        <div className="breadthGaugeFill" style={{ width: `${Math.min(100, Math.max(0, pct))}%`, background: color }} />
      </div>
      <span className="breadthGaugeValue" style={{ color }}>
        {typeof value === 'number' ? (value <= 1 ? (value * 100).toFixed(1) + '%' : value.toFixed(2)) : 'N/A'}
      </span>
    </div>
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
  const [pollActive, setPollActive] = useState(true);
  const [countdown, setCountdown] = useState(0);
  const intervalRef = useRef(null);
  const countdownRef = useRef(null);

  const fetchAll = useCallback(async () => {
    try {
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

  useEffect(() => {
    fetchAll();
    setCountdown(Math.floor(POLL_INTERVAL / 1000));
  }, [fetchAll]);

  useEffect(() => {
    if (!pollActive) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (countdownRef.current) clearInterval(countdownRef.current);
      return;
    }
    intervalRef.current = setInterval(() => {
      fetchAll();
      setCountdown(Math.floor(POLL_INTERVAL / 1000));
    }, POLL_INTERVAL);
    countdownRef.current = setInterval(() => {
      setCountdown(prev => Math.max(0, prev - 1));
    }, 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, [fetchAll, pollActive]);

  if (loading) return <div className="loadingBlock">Loading market intelligence...</div>;
  if (error) return <div className="errorBanner">Error: {error}</div>;

  const subTabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'history', label: 'History' },
    { id: 'transitions', label: 'Transitions' },
    { id: 'health', label: 'Health' },
  ];

  const bc = current?.breadth_context;
  const td = current?.transition_data;
  const vc = current?.volatility_context;
  const tc = current?.trend_context;
  const voc = current?.volume_context;

  const hasRiskFlags = td?.is_unstable || td?.is_transitioning || td?.vol_spike_detected || td?.confidence_degraded;

  return (
    <section className="intelligenceDashboard">
      <div className="intelHeader">
        <h2 className="sectionTitle">Market Intelligence</h2>
        <div className="intelHeaderRight">
          <span className={`pollIndicator ${pollActive ? 'active' : ''}`} title="Auto-refresh">
            <span className={`pollDot ${countdown === 0 ? 'refreshing' : ''}`} />
            {pollActive ? `${countdown}s` : 'paused'}
          </span>
          <button className="pollToggle" onClick={() => setPollActive(p => !p)} title={pollActive ? 'Pause auto-refresh' : 'Resume auto-refresh'}>
            {pollActive ? '⏸' : '▶'}
          </button>
          <button className="refreshBtn" onClick={fetchAll} title="Refresh now">↻</button>
        </div>
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
                    <span className="detailVal"><ConfidenceBar confidence={current.confidence} /></span>
                  </div>
                  <div className="detailRow">
                    <span className="detailKey">Risk Level</span>
                    <span className={`detailVal risk-${current.risk_level || 'unknown'}`}>
                      {(current.risk_level || 'unknown').toUpperCase()}
                    </span>
                  </div>
                  {current.stability && (
                    <div className="detailRow">
                      <span className="detailKey">Stability</span>
                      <span className={`detailVal ${current.stability === 'stable' ? 'risk-low' : current.stability === 'unstable' ? 'risk-high' : ''}`}>
                        {current.stability.toUpperCase()}
                      </span>
                    </div>
                  )}
                  {vc && (
                    <>
                      <div className="detailRow">
                        <span className="detailKey">Volatility</span>
                        <span className="detailVal"><VolatilityGauge ctx={vc} /></span>
                      </div>
                      {vc.atr_pct != null && (
                        <div className="detailRow">
                          <span className="detailKey">ATR %</span>
                          <span className="detailVal monoCell">{vc.atr_pct.toFixed(2)}%</span>
                        </div>
                      )}
                      {vc.bb_width != null && (
                        <div className="detailRow">
                          <span className="detailKey">BB Width</span>
                          <span className="detailVal monoCell">{vc.bb_width.toFixed(2)}</span>
                        </div>
                      )}
                    </>
                  )}
                  {tc && (
                    <>
                      {tc.ema_diff_pct != null && (
                        <div className="detailRow">
                          <span className="detailKey">EMA Diff %</span>
                          <span className={`detailVal monoCell ${tc.ema_diff_pct > 0 ? 'positive' : 'negative'}`}>
                            {tc.ema_diff_pct > 0 ? '+' : ''}{tc.ema_diff_pct.toFixed(2)}%
                          </span>
                        </div>
                      )}
                      {tc.adx != null && (
                        <div className="detailRow">
                          <span className="detailKey">ADX</span>
                          <span className="detailVal monoCell">{tc.adx.toFixed(1)}</span>
                        </div>
                      )}
                    </>
                  )}
                  {voc && (
                    <div className="detailRow">
                      <span className="detailKey">Volume</span>
                      <span className={`detailVal monoCell ${voc.is_spike ? 'risk-high' : ''}`}>
                        {voc.volume_ratio != null ? `${voc.volume_ratio.toFixed(2)}x` : '-'}
                        {voc.is_spike && ' ⚡'}
                      </span>
                    </div>
                  )}
                </div>
              )}
              {current?.suggested_behavior && current.suggested_behavior.length > 0 && (
                <div className="recommendations">
                  <div className="intelCardLabel">Recommendations</div>
                  <ul className="recList">
                    {current.suggested_behavior.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {(bc || td) && (
              <div className="intelCard">
                <div className="intelCardLabel">Breadth & Risk</div>
                <div className="intelCardDetails">
                  {bc && (
                    <>
                      <BreadthGauge label="Stocks Above MA50" value={bc.pct_above_ma50} highIsGood={true} />
                      <BreadthGauge label="Adv/Decl Ratio" value={bc.adv_decl_ratio != null ? bc.adv_decl_ratio : null} highIsGood={true} />
                    </>
                  )}
                  {!bc && <span className="noData">No breadth data</span>}
                </div>
                {hasRiskFlags && (
                  <div className="riskFlags" style={{ marginTop: bc ? '12px' : 0, paddingTop: bc ? '12px' : 0, borderTop: bc ? '1px solid var(--border-subtle)' : 'none' }}>
                    <div className="intelCardLabel">Risk Warnings</div>
                    {td?.is_unstable && <div className="alertBox danger">System unstable — regime may flip</div>}
                    {td?.is_transitioning && <div className="alertBox warning">Regime transitioning</div>}
                    {td?.vol_spike_detected && <div className="alertBox warning">Volatility spike detected {td.vol_spike_severity ? `(${td.vol_spike_severity})` : ''}</div>}
                    {td?.confidence_degraded && <div className="alertBox warning">Confidence degraded {td.confidence_trend ? `(${td.confidence_trend})` : ''}</div>}
                    {td?.persistence_alert && <div className="alertBox info">{td.persistence_alert}</div>}
                  </div>
                )}
                {!bc && !hasRiskFlags && <span className="noData">No breadth or risk data</span>}
              </div>
            )}

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
                  <div className="detailRow">
                    <span className="detailKey">Stability</span>
                    <span className={`detailVal ${
                      transitionData?.stability_assessment?.stability_label === 'stable' ? 'risk-low' :
                      transitionData?.stability_assessment?.stability_label === 'unstable' ? 'risk-high' : ''
                    }`}>
                      {(transitionData?.stability_assessment?.stability_label || 'unknown').toUpperCase()}
                    </span>
                  </div>
                  {transitionData?.stability_assessment?.is_transitioning && (
                    <div className="detailRow">
                      <span className="detailKey">Transitioning</span>
                      <span className="detailVal risk-high">YES</span>
                    </div>
                  )}
                  {transitionData?.most_likely_next_regime && (
                    <div className="detailRow">
                      <span className="detailKey">Next Likely</span>
                      <span className="detailVal">
                        <RegimeBadge regime={transitionData.most_likely_next_regime} />
                        {transitionData.most_likely_next_probability != null && (
                          <span className="monoCell" style={{ marginLeft: 6 }}>
                            ({(transitionData.most_likely_next_probability * 100).toFixed(0)}%)
                          </span>
                        )}
                      </span>
                    </div>
                  )}
                  {transitionData.regime_persistence_bars != null && (
                    <div className="detailRow">
                      <span className="detailKey">Persistence Bars</span>
                      <span className="detailVal monoCell">{transitionData.regime_persistence_bars}</span>
                    </div>
                  )}
                  {transitionData.avg_regime_duration != null && (
                    <div className="detailRow">
                      <span className="detailKey">Avg Duration</span>
                      <span className="detailVal monoCell">{transitionData.avg_regime_duration.toFixed(1)} bars</span>
                    </div>
                  )}
                  {transitionData.volatility_spike_score != null && (
                    <div className="detailRow">
                      <span className="detailKey">Vol Spike Score</span>
                      <span className={`detailVal monoCell ${(transitionData.volatility_spike_score || 0) > 0.5 ? 'risk-high' : ''}`}>
                        {(transitionData.volatility_spike_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                  {transitionData.vol_spike_detected && (
                    <div className="alertBox warning">Volatility spike detected</div>
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
                <span className={`healthBadge ${health?.status === 'healthy' || health?.status === 'available' ? 'ok' : health?.status === 'degraded' ? 'warn' : 'danger'}`}>
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
              <div className="intelCardDetails" style={{ marginTop: 12 }}>
                {health?.current_regime && (
                  <div className="detailRow">
                    <span className="detailKey">Current Regime</span>
                    <span className="detailVal"><RegimeBadge regime={health.current_regime} /></span>
                  </div>
                )}
                {health?.current_confidence != null && (
                  <div className="detailRow">
                    <span className="detailKey">Confidence</span>
                    <span className="detailVal"><ConfidenceBar confidence={health.current_confidence} /></span>
                  </div>
                )}
                {health?.tracker_total_transitions != null && (
                  <div className="detailRow">
                    <span className="detailKey">Total Transitions</span>
                    <span className="detailVal monoCell">{health.tracker_total_transitions}</span>
                  </div>
                )}
                {health?.persistence_ready != null && (
                  <div className="detailRow">
                    <span className="detailKey">Persistence</span>
                    <span className={`detailVal ${health.persistence_ready ? 'risk-low' : 'risk-high'}`}>
                      {health.persistence_ready ? 'Ready' : 'Not Ready'}
                    </span>
                  </div>
                )}
              </div>
              {health?.transition_detector && (
                <>
                  <div className="recommendations" style={{ marginTop: 12 }}>
                    <div className="intelCardLabel">Transition Detector</div>
                    <div className="intelCardDetails">
                      {Object.entries(health.transition_detector).map(([k, v]) => (
                        <div key={k} className="detailRow">
                          <span className="detailKey">{k.replace(/_/g, ' ')}</span>
                          <span className={`detailVal ${typeof v === 'boolean' ? (v ? 'risk-high' : 'risk-low') : ''}`}>
                            {typeof v === 'boolean' ? (v ? 'YES' : 'no') : String(v)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
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
