import React, { useState, useEffect } from 'react';
import { monitoringApi, stressTestApi } from '../api';
import {
  EquityCurveChart,
  DailyPnLChart,
  PositionDistributionChart,
  PerformanceMetrics,
} from './Charts';

function Monitoring() {
  const [predictions, setPredictions] = useState([]);
  const [accuracy, setAccuracy] = useState(null);
  const [drift, setDrift] = useState(null);
  const [health, setHealth] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [latency, setLatency] = useState(null);
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeSubTab, setActiveSubTab] = useState('health');
  const [stressResult, setStressResult] = useState(null);
  const [stressLoading, setStressLoading] = useState(false);

  const fetchAll = async () => {
    setLoading(true);
    try {
      await Promise.all([
        monitoringApi.getPredictions(50).then(d => setPredictions(d.predictions || [])).catch(() => {}),
        monitoringApi.getAccuracy(30).then(setAccuracy).catch(() => {}),
        monitoringApi.getDriftStatus().then(setDrift).catch(() => {}),
        monitoringApi.getHealthDashboard().then(setHealth).catch(() => {}),
        monitoringApi.getMetrics().then(setMetrics).catch(() => {}),
        monitoringApi.getLatency().then(setLatency).catch(() => {}),
        monitoringApi.getPerformance().then(setPerformance).catch(() => {}),
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const handleCreateBaseline = async () => {
    try {
      setLoading(true);
      await monitoringApi.createBaseline();
      const driftData = await monitoringApi.getDriftStatus();
      setDrift(driftData);
    } catch (err) {
      console.error('Baseline error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRunStressTest = async (scenario) => {
    try {
      setStressLoading(true);
      const result = await stressTestApi.runScenario(scenario);
      setStressResult(result);
    } catch (err) {
      console.error('Stress test error:', err);
    } finally {
      setStressLoading(false);
    }
  };

  const getConfidenceBadge = (conf) => {
    if (conf >= 0.65) return { label: 'HIGH', className: 'badge-high' };
    if (conf >= 0.50) return { label: 'MED', className: 'badge-medium' };
    return { label: 'LOW', className: 'badge-low' };
  };

  const formatPct = (val) => {
    if (val === null || val === undefined) return '-';
    return `${(val * 100).toFixed(1)}%`;
  };

  const formatMs = (ms) => {
    if (ms === null || ms === undefined) return '-';
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const getStatusBadge = (status) => {
    const cls = status === 'healthy' ? 'status-ok' : status === 'degraded' ? 'status-warn' : 'status-danger';
    return <span className={`health-badge ${cls}`}>{status.toUpperCase()}</span>;
  };

  const subTabs = [
    { id: 'health', label: 'System Health' },
    { id: 'metrics', label: 'Metrics' },
    { id: 'latency', label: 'Latency' },
    { id: 'predictions', label: 'Predictions' },
    { id: 'accuracy', label: 'Accuracy' },
    { id: 'drift', label: 'Drift' },
    { id: 'stress', label: 'Stress Test' },
  ];

  return (
    <div className="monitoring">
      <div className="section-header">
        <h2>Monitoring & Observability</h2>
        <button className="btn btn-secondary" onClick={fetchAll}>Refresh All</button>
      </div>

      <div className="sub-tabs">
        {subTabs.map(tab => (
          <button
            key={tab.id}
            className={`sub-tab ${activeSubTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveSubTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="loading">Loading monitoring data...</div>
      ) : (
        <>
          {activeSubTab === 'health' && (
            <div className="health-tab">
              <h3>System Health Dashboard</h3>
              {health && (
                <>
                  <div className="health-overall">
                    <div className={`health-status-banner ${health.status}`}>
                      Overall Status: {health.status?.toUpperCase()}
                    </div>
                    <div className="health-summary-grid">
                      <div className="metric-card-sm">
                        <div className="metric-label">Total Components</div>
                        <div className="metric-value">{health.summary?.total || 0}</div>
                      </div>
                      <div className="metric-card-sm ok">
                        <div className="metric-label">Healthy</div>
                        <div className="metric-value">{health.summary?.healthy || 0}</div>
                      </div>
                      <div className="metric-card-sm warn">
                        <div className="metric-label">Degraded</div>
                        <div className="metric-value">{health.summary?.degraded || 0}</div>
                      </div>
                      <div className="metric-card-sm danger">
                        <div className="metric-label">Unhealthy</div>
                        <div className="metric-value">{health.summary?.unhealthy || 0}</div>
                      </div>
                      <div className="metric-card-sm">
                        <div className="metric-label">Response Time</div>
                        <div className="metric-value">{formatMs(health.response_time_ms)}</div>
                      </div>
                    </div>
                  </div>

                  <div className="component-grid">
                    {Object.entries(health.components || {}).map(([name, comp]) => (
                      <div key={name} className={`component-card ${comp.status}`}>
                        <div className="component-header">
                          <span className="component-name">{name}</span>
                          {getStatusBadge(comp.status)}
                        </div>
                        <div className="component-message">{comp.message}</div>
                        <div className="component-footer">
                          <span className="component-latency">{formatMs(comp.latency_ms)}</span>
                        </div>
                        {comp.details && (
                          <div className="component-details">
                            {Object.entries(comp.details).map(([k, v]) => (
                              <div key={k} className="detail-row">
                                <span className="detail-key">{k}</span>
                                <span className="detail-value">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </>
              )}
              {!health && <div className="empty-state">Health data not available</div>}
            </div>
          )}

          {activeSubTab === 'metrics' && (
            <div className="metrics-tab">
              <h3>System Metrics</h3>
              {performance && (
                <>
                  <div className="health-status-banner" style={{background: performance.status === 'healthy' ? 'var(--accent-primary)' : 'var(--accent-warning)'}}>
                    System Performance: {performance.status?.toUpperCase()}
                  </div>
                  <div className="metrics-overview">
                    <h4>Service Metrics</h4>
                    <div className="metrics-table-container">
                      <table className="data-table metrics-table">
                        <thead>
                          <tr>
                            <th>Service</th>
                            <th>Calls</th>
                            <th>Errors</th>
                            <th>Error Rate</th>
                            <th>Avg Latency</th>
                            <th>P95 Latency</th>
                            <th>Throughput</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(performance.metrics || {}).map(([name, svc]) => (
                            <tr key={name}>
                              <td className="bold">{name}</td>
                              <td className="mono">{(svc.success_count || 0) + (svc.error_count || 0)}</td>
                              <td className="mono">{svc.error_count || 0}</td>
                              <td className="mono">
                                <span className={((svc.error_count || 0) / Math.max((svc.success_count || 0) + (svc.error_count || 0), 1) > 0.05) ? 'text-danger' : ''}>
                                  {((svc.error_count || 0) / Math.max((svc.success_count || 0) + (svc.error_count || 0), 1) * 100).toFixed(1)}%
                                </span>
                              </td>
                              <td className="mono">{formatMs(svc.latency?.avg_ms)}</td>
                              <td className="mono">{formatMs(svc.latency?.p95_ms)}</td>
                              <td className="mono">{svc.throughput_rpm || 0}/min</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div className="metrics-overview">
                    <h4>API Endpoint Metrics</h4>
                    <div className="metrics-table-container">
                      <table className="data-table metrics-table">
                        <thead>
                          <tr>
                            <th>Endpoint</th>
                            <th>Total Calls</th>
                            <th>Errors</th>
                            <th>Error Rate</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(performance.api?.endpoints || {}).map(([endpoint, data]) => (
                            <tr key={endpoint}>
                              <td className="mono" style={{fontSize: '12px'}}>{endpoint}</td>
                              <td className="mono">{data.total_calls}</td>
                              <td className="mono">{data.errors}</td>
                              <td className="mono">
                                <span className={data.error_rate > 0.05 ? 'text-danger' : ''}>
                                  {(data.error_rate * 100).toFixed(1)}%
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {Object.keys(performance.api?.endpoints || {}).length === 0 && (
                        <div className="empty-state">No API metrics yet</div>
                      )}
                    </div>
                  </div>
                </>
              )}
              {!performance && <div className="empty-state">Metrics not available</div>}
            </div>
          )}

          {activeSubTab === 'latency' && (
            <div className="latency-tab">
              <h3>Latency Breakdown</h3>
              {latency && (
                <div className="latency-grid">
                  {Object.entries(latency.breakdown || {}).map(([service, data]) => (
                    <div key={service} className="latency-card">
                      <div className="latency-header">
                        <span className="latency-service">{service}</span>
                        <span className="latency-throughput">{data.throughput_rpm || 0}/min</span>
                      </div>
                      <div className="latency-stats">
                        <div className="latency-stat">
                          <span className="latency-label">Avg</span>
                          <span className="latency-value">{formatMs(data.avg_ms)}</span>
                        </div>
                        <div className="latency-stat primary">
                          <span className="latency-label">P50</span>
                          <span className="latency-value">{formatMs(data.p50_ms)}</span>
                        </div>
                        <div className="latency-stat warning">
                          <span className="latency-label">P95</span>
                          <span className="latency-value">{formatMs(data.p95_ms)}</span>
                        </div>
                        <div className="latency-stat danger">
                          <span className="latency-label">P99</span>
                          <span className="latency-value">{formatMs(data.p99_ms)}</span>
                        </div>
                        <div className="latency-stat">
                          <span className="latency-label">Min</span>
                          <span className="latency-value">{formatMs(data.min_ms)}</span>
                        </div>
                        <div className="latency-stat">
                          <span className="latency-label">Max</span>
                          <span className="latency-value">{formatMs(data.max_ms)}</span>
                        </div>
                        <div className="latency-stat">
                          <span className="latency-label">Count</span>
                          <span className="latency-value">{data.count || 0}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                  {Object.keys(latency.breakdown || {}).length === 0 && (
                    <div className="empty-state">No latency data yet. Start making API calls to collect metrics.</div>
                  )}
                </div>
              )}
              {!latency && <div className="empty-state">Latency data not available</div>}
            </div>
          )}

          {activeSubTab === 'predictions' && (
            <div className="predictions-tab">
              <h3>Recent Predictions ({predictions.length})</h3>
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Symbol</th>
                      <th>Decision</th>
                      <th>Confidence</th>
                      <th>P(BUY)</th>
                      <th>P(HOLD)</th>
                      <th>P(SELL)</th>
                      <th>Outcome</th>
                    </tr>
                  </thead>
                  <tbody>
                    {predictions.map((p) => {
                      const confBadge = getConfidenceBadge(p.confidence);
                      return (
                        <tr key={p.id}>
                          <td className="mono">{new Date(p.timestamp).toLocaleTimeString()}</td>
                          <td className="mono bold">{p.symbol}</td>
                          <td>
                            <span className={`decision-badge decision-${p.decision.toLowerCase()}`}>{p.decision}</span>
                          </td>
                          <td>
                            <span className={`badge ${confBadge.className}`}>{confBadge.label} ({formatPct(p.confidence)})</span>
                          </td>
                          <td className="mono">{formatPct(p.p_buy)}</td>
                          <td className="mono">{formatPct(p.p_hold)}</td>
                          <td className="mono">{formatPct(p.p_sell)}</td>
                          <td>
                            {p.actual_outcome ? (
                              <span className={`outcome-${p.actual_outcome.toLowerCase()}`}>{p.actual_outcome} ({p.actual_return?.toFixed(2)}%)</span>
                            ) : (
                              <span className="pending">Pending</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeSubTab === 'accuracy' && accuracy && (
            <div className="accuracy-tab">
              <h3>Live Accuracy (Last {accuracy.lookback_days} days)</h3>
              <div className="metrics-grid">
                <div className="metric-card">
                  <div className="metric-label">Accuracy</div>
                  <div className="metric-value">{formatPct(accuracy.accuracy?.accuracy)}</div>
                  <div className="metric-detail">{accuracy.accuracy?.wins}/{accuracy.accuracy?.total} wins</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Total Predictions</div>
                  <div className="metric-value">{accuracy.accuracy?.total || 0}</div>
                </div>
              </div>

              {accuracy.calibration && (
                <>
                  <h4>Confidence Calibration</h4>
                  <div className="calibration-grid">
                    {Object.entries(accuracy.calibration).map(([bucket, data]) => (
                      <div key={bucket} className="calibration-card">
                        <div className="bucket-label">{bucket.toUpperCase()}</div>
                        <div className="bucket-winrate">{formatPct(data.win_rate)}</div>
                        <div className="bucket-count">{data.count} predictions</div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {activeSubTab === 'drift' && (
            <div className="drift-tab">
              <h3>Feature Drift Detection</h3>
              <div className="drift-status">
                <div className={`status-card ${drift?.status === 'DRIFT' ? 'status-danger' : 'status-ok'}`}>
                  <div className="status-label">Status</div>
                  <div className="status-value">{drift?.status || 'UNKNOWN'}</div>
                </div>
                {drift?.baseline_version && (
                  <div className="status-card">
                    <div className="status-label">Baseline Version</div>
                    <div className="status-value">{drift.baseline_version}</div>
                  </div>
                )}
                {drift?.baseline_created && (
                  <div className="status-card">
                    <div className="status-label">Baseline Created</div>
                    <div className="status-value">{new Date(drift.baseline_created).toLocaleDateString()}</div>
                  </div>
                )}
                <div className="status-card">
                  <div className="status-label">Features Tracked</div>
                  <div className="status-value">{drift?.features_count || 0}</div>
                </div>
              </div>
              {drift?.status === 'NO_BASELINE' && (
                <div className="no-baseline-warning">
                  <p>No drift baseline found. Create one to start monitoring.</p>
                  <button className="btn btn-primary" onClick={handleCreateBaseline}>Create Drift Baseline</button>
                </div>
              )}
            </div>
          )}

          {activeSubTab === 'stress' && (
            <div className="stress-tab">
              <h3>Stress Testing</h3>
              <div className="stress-scenarios">
                <h4>Run Scenario</h4>
                <div className="scenario-buttons">
                  {['market_drop_5pct', 'market_drop_10pct', 'market_drop_20pct', 'high_volatility', 'flash_crash'].map((scenario) => (
                    <button
                      key={scenario}
                      className="btn btn-secondary"
                      onClick={() => handleRunStressTest(scenario)}
                      disabled={stressLoading}
                    >
                      {scenario.replace(/_/g, ' ').toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>

              {stressLoading && <div className="loading">Running stress test...</div>}

              {stressResult && !stressResult.error && (
                <div className="stress-result">
                  <h4>Results: {stressResult.scenario?.toUpperCase()}</h4>
                  {stressResult.result?.signal_distribution && (
                    <div className="signal-distribution">
                      <div className="signal-stat"><span className="label">BUY</span><span className="value">{stressResult.result.signal_distribution.BUY}</span></div>
                      <div className="signal-stat"><span className="label">HOLD</span><span className="value">{stressResult.result.signal_distribution.HOLD}</span></div>
                      <div className="signal-stat"><span className="label">SELL</span><span className="value">{stressResult.result.signal_distribution.SELL}</span></div>
                    </div>
                  )}
                  {stressResult.result?.avg_confidence && (
                    <div className="avg-confidence">Avg Confidence: {formatPct(stressResult.result.avg_confidence)}</div>
                  )}
                </div>
              )}

              {stressResult?.error && <div className="error-message">Error: {stressResult.error}</div>}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default Monitoring;