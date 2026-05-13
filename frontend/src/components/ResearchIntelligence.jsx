import React, { useState, useEffect, useCallback } from 'react';
import { researchApi, driftApi, stocksApi } from '../api';

function ResearchIntelligence() {
  const [activeSubTab, setActiveSubTab] = useState('drift');
  const [driftStatus, setDriftStatus] = useState(null);
  const [driftAlerts, setDriftAlerts] = useState([]);
  const [degradation, setDegradation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [strategyCompare, setStrategyCompare] = useState(null);
  const [strategies, setStrategies] = useState('strategy_a,strategy_b');
  const [symbols, setSymbols] = useState('');
  const [stockList, setStockList] = useState([]);

  const [hypothesisResult, setHypothesisResult] = useState(null);

  useEffect(() => {
    stocksApi.getAll().then(d => setStockList(d.stocks || [])).catch(() => {});
    loadDriftData();
    loadDegradation();
  }, []);

  const loadDriftData = useCallback(async () => {
    try {
      const [status, alerts] = await Promise.all([
        driftApi.getStatus().catch(() => null),
        driftApi.getAlerts().catch(() => null),
      ]);
      setDriftStatus(status);
      setDriftAlerts(Array.isArray(alerts) ? alerts : alerts?.alerts || []);
    } catch (e) { /* ignore */ }
  }, []);

  const loadDegradation = useCallback(async () => {
    try {
      const deg = await researchApi.getRegimeDegradation({}).catch(() => null);
      setDegradation(deg);
    } catch (e) { /* ignore */ }
  }, []);

  const handleCompare = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await researchApi.compareStrategies({
        strategies: strategies.split(',').map(s => s.trim()).filter(Boolean),
        symbols: symbols ? symbols.split(',').map(s => s.trim()).filter(Boolean) : undefined,
      });
      setStrategyCompare(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [strategies, symbols]);

  const handleGenerateHypotheses = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await researchApi.getHypotheses({
        drift_data: driftStatus || undefined,
        regime_degradation: degradation?.analysis || degradation || undefined,
      });
      setHypothesisResult(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [driftStatus, degradation]);

  const subTabs = [
    { id: 'drift', label: 'Drift Detection' },
    { id: 'degradation', label: 'Regime Degradation' },
    { id: 'compare', label: 'Strategy Compare' },
    { id: 'hypotheses', label: 'Hypotheses' },
  ];

  const driftData = driftStatus?.analysis || driftStatus;
  const degData = degradation?.analysis || degradation;

  return (
    <section className="intelligenceDashboard">
      <div className="intelHeader">
        <h2 className="sectionTitle">Research Intelligence</h2>
        <button className="refreshBtn" onClick={() => { loadDriftData(); loadDegradation(); }}>↻</button>
      </div>

      <div className="sub-tabs">
        {subTabs.map(t => (
          <button key={t.id} className={`sub-tab ${activeSubTab === t.id ? 'active' : ''}`} onClick={() => setActiveSubTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {error && <div className="errorBanner">{error}</div>}

      {activeSubTab === 'drift' && (
        <div className="intelDrift">
          <div className="intelCards">
            <div className="intelCard">
              <div className="intelCardLabel">Drift Status</div>
              <div className="intelCardValue">
                <span className={`healthBadge ${
                  driftData?.status === 'normal' || driftData?.overall_status === 'normal' ? 'ok' :
                  driftData?.status === 'warning' || driftData?.overall_status === 'warning' ? 'warn' : 'danger'
                }`}>
                  {driftData?.status || driftData?.overall_status || 'UNKNOWN'}
                </span>
              </div>
              {driftData?.drifted_features && (
                <div className="intelCardDetails">
                  <div className="detailRow">
                    <span className="detailKey">Drifted Features</span>
                    <span className="detailVal">{driftData.drifted_features.length}</span>
                  </div>
                </div>
              )}
              {driftData?.total_features && (
                <div className="detailRow">
                  <span className="detailKey">Total Tracked</span>
                  <span className="detailVal">{driftData.total_features}</span>
                </div>
              )}
            </div>

            {driftData?.groups && Object.keys(driftData.groups).length > 0 && (
              <div className="intelCard" style={{ gridColumn: 'span 2' }}>
                <div className="intelCardLabel">Feature Groups</div>
                <div className="featureGroups">
                  {Object.entries(driftData.groups).map(([group, info]) => (
                    <div key={group} className={`groupRow ${(info.status || info) === 'DRIFT' ? 'drifted' : ''}`}>
                      <span className="groupName">{group.replace(/_/g, ' ')}</span>
                      <span className={`groupStatus ${
                        (info.status || info) === 'NORMAL' || (info.status || info) === 'normal' ? 'ok' :
                        (info.status || info) === 'WARNING' || (info.status || info) === 'warning' ? 'warn' : 'danger'
                      }`}>
                        {info.status || info}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {driftAlerts.length > 0 && (
            <div className="intelCards" style={{ marginTop: 16 }}>
              <div className="intelCard">
                <div className="intelCardLabel">Active Alerts ({driftAlerts.length})</div>
                {driftAlerts.slice(0, 20).map((alert, i) => (
                  <div key={i} className="alertRow">
                    <span className={`alertSeverity ${
                      alert.severity === 'CRITICAL' ? 'danger' :
                      alert.severity === 'WARNING' ? 'warn' : ''
                    }`}>{alert.severity}</span>
                    <span className="alertMessage">{alert.message || alert.description}</span>
                    <span className="alertDate">{alert.created_at ? new Date(alert.created_at).toLocaleDateString() : ''}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(!driftData && driftAlerts.length === 0) && (
            <div className="emptyState">No drift data available. Create a baseline first.</div>
          )}
        </div>
      )}

      {activeSubTab === 'degradation' && (
        <div className="intelDegradation">
          {degData ? (
            <div className="intelCards">
              <div className="intelCard" style={{ gridColumn: 'span 2' }}>
                <div className="intelCardLabel">Regime Performance</div>
                {degData.regime_performances || degData.performances ? (
                  <div className="tableCard" style={{ border: 'none', background: 'transparent' }}>
                    <table className="dataTable">
                      <thead>
                        <tr>
                          <th>Regime</th>
                          <th>Trades</th>
                          <th>Win Rate</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(degData.regime_performances || degData.performances || []).map((p, i) => (
                          <tr key={i}>
                            <td><span className="badge">{p.regime?.replace(/_/g, ' ')}</span></td>
                            <td className="monoCell">{p.trade_count || p.count || 0}</td>
                            <td className={`monoCell ${(p.win_rate || 0) >= 0.5 ? 'positive' : 'negative'}`}>
                              {((p.win_rate || 0) * 100).toFixed(1)}%
                            </td>
                            <td>
                              <span className={`badge ${(p.win_rate || 0) >= 0.5 ? 'risk-low' : 'risk-high'}`}>
                                {(p.win_rate || 0) >= 0.5 ? 'HEALTHY' : 'DEGRADED'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="emptyState">No regime performance data</div>
                )}
              </div>

              {degData.degraded_regimes && degData.degraded_regimes.length > 0 && (
                <div className="intelCard">
                  <div className="intelCardLabel">Degraded Regimes</div>
                  {degData.degraded_regimes.map((r, i) => (
                    <div key={i} className="alertRow">
                      <span className="badge risk-high">{r.regime || r}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="emptyState">No degradation data available</div>
          )}
        </div>
      )}

      {activeSubTab === 'compare' && (
        <div className="intelCompare">
          <div className="explainForm">
            <input
              type="text"
              className="intelInput"
              placeholder="Strategy names (comma-separated, e.g., breakout,momentum,mean_reversion)"
              value={strategies}
              onChange={e => setStrategies(e.target.value)}
            />
            <input
              type="text"
              className="intelInput"
              placeholder="Symbols (optional, comma-separated)"
              value={symbols}
              onChange={e => setSymbols(e.target.value)}
            />
            <button className="actionBtn" onClick={handleCompare} disabled={loading || !strategies.trim()}>
              {loading ? 'Comparing...' : 'Compare Strategies'}
            </button>
          </div>

          {strategyCompare && (
            <div className="intelCards">
              {(strategyCompare.comparisons || strategyCompare.results || []).length > 0 ? (
                <div className="intelCard" style={{ gridColumn: 'span 2' }}>
                  <div className="intelCardLabel">Comparison Results</div>
                  <div className="tableCard" style={{ border: 'none', background: 'transparent' }}>
                    <table className="dataTable">
                      <thead>
                        <tr>
                          <th>Strategy</th>
                          <th>Win Rate</th>
                          <th>Profit Factor</th>
                          <th>Expectancy</th>
                          <th>Trades</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(strategyCompare.comparisons || strategyCompare.results || []).map((s, i) => (
                          <tr key={i}>
                            <td className="symbolCell">{s.strategy || s.name}</td>
                            <td className={`monoCell ${(s.win_rate || 0) >= 0.5 ? 'positive' : 'negative'}`}>
                              {((s.win_rate || 0) * 100).toFixed(1)}%
                            </td>
                            <td className="monoCell">{(s.profit_factor || 0).toFixed(2)}</td>
                            <td className={`monoCell ${(s.expectancy || 0) >= 0 ? 'positive' : 'negative'}`}>
                              {(s.expectancy || 0).toFixed(3)}
                            </td>
                            <td className="monoCell">{s.trade_count || s.count || 0}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="emptyState">No comparison results</div>
              )}

              {strategyCompare.gap_analysis && (
                <div className="intelCard">
                  <div className="intelCardLabel">Gap Analysis</div>
                  <div className="gapAnalysis">
                    {Object.entries(strategyCompare.gap_analysis).map(([key, val]) => (
                      <div key={key} className="detailRow">
                        <span className="detailKey">{key.replace(/_/g, ' ')}</span>
                        <span className="detailVal">{typeof val === 'number' ? val.toFixed(2) : String(val)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeSubTab === 'hypotheses' && (
        <div className="intelHypotheses">
          <div className="explainForm">
            <button className="actionBtn" onClick={handleGenerateHypotheses} disabled={loading}>
              {loading ? 'Generating...' : 'Generate Research Hypotheses'}
            </button>
          </div>

          {hypothesisResult && (
            <div className="intelCards">
              {(hypothesisResult.hypotheses || hypothesisResult.results || []).length > 0 ? (
                (hypothesisResult.hypotheses || hypothesisResult.results || []).map((h, i) => (
                  <div key={i} className="intelCard">
                    <div className="intelCardLabel">Hypothesis {i + 1}</div>
                    <div className="hypothesisContent">
                      {h.title && <div className="hypothesisTitle">{h.title}</div>}
                      {h.description && <p className="hypothesisDesc">{h.description}</p>}
                      {h.expected_outcome && (
                        <div className="detailRow">
                          <span className="detailKey">Expected Outcome</span>
                          <span className="detailVal">{h.expected_outcome}</span>
                        </div>
                      )}
                      {h.confidence != null && (
                        <div className="detailRow">
                          <span className="detailKey">Confidence</span>
                          <span className="detailVal">{(h.confidence * 100).toFixed(0)}%</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="intelCard">
                  <div className="intelCardLabel">Generated Hypothesis</div>
                  <div className="hypothesisContent">
                    {hypothesisResult.hypothesis && <p>{hypothesisResult.hypothesis}</p>}
                    {hypothesisResult.summary && <p>{hypothesisResult.summary}</p>}
                    {!hypothesisResult.hypothesis && !hypothesisResult.summary && (
                      <p className="hypothesisDesc">{JSON.stringify(hypothesisResult)}</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default ResearchIntelligence;
