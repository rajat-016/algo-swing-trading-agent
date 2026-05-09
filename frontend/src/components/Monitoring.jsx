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
  const [loading, setLoading] = useState(true);
  const [activeSubTab, setActiveSubTab] = useState('predictions');
  const [stressResult, setStressResult] = useState(null);
  const [stressLoading, setStressLoading] = useState(false);

  const fetchPredictions = async () => {
    try {
      const data = await monitoringApi.getPredictions(50);
      setPredictions(data.predictions || []);
    } catch (err) {
      console.error('Predictions error:', err);
    }
  };

  const fetchAccuracy = async () => {
    try {
      const data = await monitoringApi.getAccuracy(30);
      setAccuracy(data);
    } catch (err) {
      console.error('Accuracy error:', err);
    }
  };

  const fetchDrift = async () => {
    try {
      const data = await monitoringApi.getDriftStatus();
      setDrift(data);
    } catch (err) {
      console.error('Drift error:', err);
    }
  };

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      await Promise.all([fetchPredictions(), fetchAccuracy(), fetchDrift()]);
      setLoading(false);
    };
    fetchAll();
  }, []);

  const handleCreateBaseline = async () => {
    try {
      setLoading(true);
      await monitoringApi.createBaseline();
      await fetchDrift();
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

  return (
    <div className="monitoring">
      <div className="section-header">
        <h2>ML Monitoring Dashboard</h2>
        <button
          className="btn btn-secondary"
          onClick={() => { fetchPredictions(); fetchAccuracy(); fetchDrift(); }}
        >
          Refresh
        </button>
      </div>

      <div className="sub-tabs">
        <button
          className={`sub-tab ${activeSubTab === 'predictions' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('predictions')}
        >
          Predictions
        </button>
        <button
          className={`sub-tab ${activeSubTab === 'accuracy' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('accuracy')}
        >
          Accuracy
        </button>
        <button
          className={`sub-tab ${activeSubTab === 'drift' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('drift')}
        >
          Drift Detection
        </button>
        <button
          className={`sub-tab ${activeSubTab === 'stress' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('stress')}
        >
          Stress Test
        </button>
      </div>

      {loading ? (
        <div className="loading">Loading monitoring data...</div>
      ) : (
        <>
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
                          <td className="mono">
                            {new Date(p.timestamp).toLocaleTimeString()}
                          </td>
                          <td className="mono bold">{p.symbol}</td>
                          <td>
                            <span className={`decision-badge decision-${p.decision.toLowerCase()}`}>
                              {p.decision}
                            </span>
                          </td>
                          <td>
                            <span className={`badge ${confBadge.className}`}>
                              {confBadge.label} ({formatPct(p.confidence)})
                            </span>
                          </td>
                          <td className="mono">{formatPct(p.p_buy)}</td>
                          <td className="mono">{formatPct(p.p_hold)}</td>
                          <td className="mono">{formatPct(p.p_sell)}</td>
                          <td>
                            {p.actual_outcome ? (
                              <span className={`outcome-${p.actual_outcome.toLowerCase()}`}>
                                {p.actual_outcome} ({p.actual_return?.toFixed(2)}%)
                              </span>
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
                  <div className="metric-value">
                    {formatPct(accuracy.accuracy?.accuracy)}
                  </div>
                  <div className="metric-detail">
                    {accuracy.accuracy?.wins}/{accuracy.accuracy?.total} wins
                  </div>
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
                        <div className="bucket-winrate">
                          {formatPct(data.win_rate)}
                        </div>
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
                    <div className="status-value">
                      {new Date(drift.baseline_created).toLocaleDateString()}
                    </div>
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
                  <button className="btn btn-primary" onClick={handleCreateBaseline}>
                    Create Drift Baseline
                  </button>
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
                      <div className="signal-stat">
                        <span className="label">BUY</span>
                        <span className="value">{stressResult.result.signal_distribution.BUY}</span>
                      </div>
                      <div className="signal-stat">
                        <span className="label">HOLD</span>
                        <span className="value">{stressResult.result.signal_distribution.HOLD}</span>
                      </div>
                      <div className="signal-stat">
                        <span className="label">SELL</span>
                        <span className="value">{stressResult.result.signal_distribution.SELL}</span>
                      </div>
                    </div>
                  )}
                  {stressResult.result?.avg_confidence && (
                    <div className="avg-confidence">
                      Avg Confidence: {formatPct(stressResult.result.avg_confidence)}
                    </div>
                  )}
                </div>
              )}

              {stressResult?.error && (
                <div className="error-message">
                  Error: {stressResult.error}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default Monitoring;
