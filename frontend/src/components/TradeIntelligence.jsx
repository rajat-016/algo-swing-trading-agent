import React, { useState, useEffect, useCallback } from 'react';
import { stocksApi, tradeApi, journalApi, memoryApi, regimeApi } from '../api';

function ConfidenceBar({ value, label, color }) {
  const pct = Math.min(Math.max((value || 0) * 100, 0), 100);
  const barColor = color || (value >= 0.65 ? 'var(--accent-primary)' : value >= 0.5 ? 'var(--accent-warning)' : 'var(--accent-danger)');
  return (
    <div className="cbRow">
      {label && <span className="cbLabel">{label}</span>}
      <div className="cbBar">
        <div className="cbFill" style={{ width: `${pct}%`, background: barColor }}></div>
      </div>
      <span className="cbVal">{pct.toFixed(0)}%</span>
    </div>
  );
}

function RegimeBadgeSmall({ regime, riskLevel }) {
  const isBull = regime?.includes('bull') || regime?.includes('breakout');
  const isBear = regime?.includes('bear') || regime?.includes('high_vol') || regime?.includes('event');
  const color = isBull ? 'var(--accent-primary)' : isBear ? 'var(--accent-danger)' : 'var(--accent-warning)';
  return (
    <span className="regimeBadgeSm" style={{ color, borderColor: `${color}30`, background: `${color}15` }}>
      {regime?.replace(/_/g, ' ') || 'unknown'}
    </span>
  );
}

function TradeIntelligence() {
  const [activeSubTab, setActiveSubTab] = useState('explain');
  const [stocks, setStocks] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [selectedPmSymbol, setSelectedPmSymbol] = useState('');
  const [tradeResult, setTradeResult] = useState(null);
  const [postMortemResult, setPostMortemResult] = useState(null);
  const [journalTrades, setJournalTrades] = useState([]);
  const [journalStats, setJournalStats] = useState(null);
  const [memorySearchQuery, setMemorySearchQuery] = useState('');
  const [memoryResults, setMemoryResults] = useState([]);
  const [currentRegime, setCurrentRegime] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pmLoading, setPmLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pmError, setPmError] = useState(null);

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
      setTradeResult(null);
      let result = null;
      try {
        result = await tradeApi.getIntelligence({ symbol: selectedSymbol });
      } catch (_) {
        result = await tradeApi.explain({ symbol: selectedSymbol });
      }
      setTradeResult(result);
    } catch (err) {
      setError(err.message || 'Failed to explain trade');
    } finally {
      setLoading(false);
    }
  }, [selectedSymbol]);

  const handlePostMortem = useCallback(async () => {
    if (!selectedPmSymbol) return;
    try {
      setPmLoading(true);
      setPmError(null);
      setPostMortemResult(null);
      const result = await tradeApi.getPostMortem({ symbol: selectedPmSymbol });
      setPostMortemResult(result);
    } catch (err) {
      setPmError(err.message || 'Failed to analyze post-mortem');
    } finally {
      setPmLoading(false);
    }
  }, [selectedPmSymbol]);

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

  const explain = tradeResult?.explanation || tradeResult;
  const reasoning = tradeResult?.reasoning;
  const failureAnalysis = tradeResult?.failure_analysis;
  const similarTrades = tradeResult?.similar_trades;
  const prediction = explain?.prediction;
  const posFeatures = explain?.top_positive_features || [];
  const negFeatures = explain?.top_negative_features || [];
  const regimeCtx = explain?.regime_context;

  const subTabs = [
    { id: 'explain', label: 'Explain Trade' },
    { id: 'postmortem', label: 'Post-Mortem & Reflection' },
    { id: 'journal', label: 'Trade Journal' },
    { id: 'memory', label: 'Memory Search' },
    { id: 'regime', label: 'Regime Context' },
  ];

  const renderFeatureAttribution = () => {
    const hasFeatures = posFeatures.length > 0 || negFeatures.length > 0;
    if (!hasFeatures) return null;
    return (
      <div className="intelCards" style={{ marginTop: 16 }}>
        <div className="intelCard">
          <div className="intelCardLabel">Feature Attribution</div>
          <div className="featureAttribution">
            {posFeatures.length > 0 && (
              <div className="faGroup">
                <div className="faGroupLabel positive">Top Positive Features</div>
                {posFeatures.map((f, i) => (
                  <div key={i} className="featureRow">
                    <span className="featureName">{f.feature || f.name}</span>
                    <div className="featureBar">
                      <div className="featureBarFill" style={{
                        width: `${Math.min(Math.abs((f.contribution_pct || f.shap_value || 0)) * 5, 100)}%`,
                        background: 'var(--accent-primary)'
                      }}></div>
                    </div>
                    <span className="featureVal positive">
                      {f.shap_value != null ? f.shap_value.toFixed(3) : f.contribution_pct != null ? `${f.contribution_pct.toFixed(1)}%` : ''}
                    </span>
                  </div>
                ))}
              </div>
            )}
            {negFeatures.length > 0 && (
              <div className="faGroup" style={{ marginTop: 12 }}>
                <div className="faGroupLabel negative">Top Negative Features</div>
                {negFeatures.map((f, i) => (
                  <div key={i} className="featureRow">
                    <span className="featureName">{f.feature || f.name}</span>
                    <div className="featureBar">
                      <div className="featureBarFill" style={{
                        width: `${Math.min(Math.abs((f.contribution_pct || f.shap_value || 0)) * 5, 100)}%`,
                        background: 'var(--accent-danger)'
                      }}></div>
                    </div>
                    <span className="featureVal negative">
                      {f.shap_value != null ? f.shap_value.toFixed(3) : f.contribution_pct != null ? `${f.contribution_pct.toFixed(1)}%` : ''}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderConfidenceMetrics = () => {
    if (!prediction) return null;
    const probs = prediction.probabilities || {};
    return (
      <div className="intelCards" style={{ marginTop: 16 }}>
        <div className="intelCard">
          <div className="intelCardLabel">Confidence Metrics</div>
          <div className="cmBody">
            <div className="cmHeader">
              <div>
                <span className={`decisionBadge ${prediction.decision === 'BUY' ? 'buy' : prediction.decision === 'SELL' ? 'sell' : 'hold'}`}>
                  {prediction.decision || 'N/A'}
                </span>
                <span className={`cmLevel ${prediction.confidence_level}`}>{prediction.confidence_level?.toUpperCase()}</span>
              </div>
              <span className="cmConfidence">{(prediction.confidence * 100).toFixed(1)}%</span>
            </div>
            <div className="cmProbs">
              <span className="cmProbLabel">Probability Distribution</span>
              <ConfidenceBar value={probs.buy} label="BUY" color="var(--accent-primary)" />
              <ConfidenceBar value={probs.hold} label="HOLD" color="var(--accent-warning)" />
              <ConfidenceBar value={probs.sell} label="SELL" color="var(--accent-danger)" />
            </div>
            <div className="cmDetails">
              {prediction.margin_over_second != null && (
                <div className="detailRow">
                  <span className="detailKey">Margin over 2nd</span>
                  <span className="detailVal">{prediction.margin_over_second.toFixed(3)}</span>
                </div>
              )}
              {prediction.entropy != null && (
                <div className="detailRow">
                  <span className="detailKey">Prediction Entropy</span>
                  <span className="detailVal">{prediction.entropy.toFixed(3)}</span>
                </div>
              )}
              {prediction.model_version && (
                <div className="detailRow">
                  <span className="detailKey">Model Version</span>
                  <span className="detailVal mono">{prediction.model_version}</span>
                </div>
              )}
              {prediction.feature_version && (
                <div className="detailRow">
                  <span className="detailKey">Feature Version</span>
                  <span className="detailVal mono">{prediction.feature_version}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderRegimeContext = () => {
    if (!regimeCtx) return null;
    return (
      <div className="intelCards" style={{ marginTop: 16 }}>
        <div className="intelCard">
          <div className="intelCardLabel">Regime Context</div>
          <div className="intelCardDetails">
            <div className="detailRow">
              <span className="detailKey">Regime</span>
              <span className="detailVal"><RegimeBadgeSmall regime={regimeCtx.regime} riskLevel={regimeCtx.risk_level} /></span>
            </div>
            <div className="detailRow">
              <span className="detailKey">Confidence</span>
              <span className="detailVal">{(regimeCtx.confidence * 100).toFixed(1)}%</span>
            </div>
            <div className="detailRow">
              <span className="detailKey">Risk Level</span>
              <span className={`detailVal risk-${regimeCtx.risk_level || 'unknown'}`}>{(regimeCtx.risk_level || 'unknown').toUpperCase()}</span>
            </div>
            {regimeCtx.stability && (
              <div className="detailRow">
                <span className="detailKey">Stability</span>
                <span className="detailVal" style={{ textTransform: 'capitalize' }}>{regimeCtx.stability}</span>
              </div>
            )}
            {regimeCtx.suggested_behavior?.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <span className="faGroupLabel" style={{ fontSize: 12, marginBottom: 4, display: 'block' }}>Suggested Behavior</span>
                <ul className="recList">
                  {regimeCtx.suggested_behavior.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderReasoning = () => {
    if (!reasoning) return null;
    return (
      <div className="intelCards" style={{ marginTop: 16 }}>
        <div className="intelCard">
          <div className="intelCardLabel">Trade Reasoning</div>
          <div className="reasoningBody">
            {reasoning.entry_rationale && (
              <div className="reasoningSection">
                <div className="rsTitle">Entry Rationale</div>
                <div className="rsText">{reasoning.entry_rationale.primary_reason || 'N/A'}</div>
                {reasoning.entry_rationale.supporting_factors?.length > 0 && (
                  <div className="rsFactors">
                    {reasoning.entry_rationale.supporting_factors.map((f, i) => (
                      <span key={i} className="rsFactor">{f}</span>
                    ))}
                  </div>
                )}
                {reasoning.entry_rationale.regime_alignment && (
                  <div className="rsDetail">{reasoning.entry_rationale.regime_alignment}</div>
                )}
              </div>
            )}
            {reasoning.outcome_analysis && (
              <div className="reasoningSection">
                <div className="rsTitle">Outcome Analysis</div>
                <div className="rsOutcome">
                  <span className={`badge ${reasoning.outcome_analysis.outcome === 'WIN' ? 'risk-low' : 'risk-high'}`}>
                    {reasoning.outcome_analysis.outcome || 'UNKNOWN'}
                  </span>
                  {reasoning.outcome_analysis.exit_reason && (
                    <span className="rsDetail" style={{ marginLeft: 8 }}>{reasoning.outcome_analysis.exit_reason}</span>
                  )}
                </div>
                {reasoning.outcome_analysis.pnl_analysis && <div className="rsText">{reasoning.outcome_analysis.pnl_analysis}</div>}
                {reasoning.outcome_analysis.regime_impact && <div className="rsDetail">{reasoning.outcome_analysis.regime_impact}</div>}
              </div>
            )}
            {reasoning.risk_factors?.length > 0 && (
              <div className="reasoningSection">
                <div className="rsTitle">Risk Factors</div>
                <ul className="rsList">
                  {reasoning.risk_factors.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </div>
            )}
            {reasoning.confidence_assessment && (
              <div className="reasoningSection">
                <div className="rsTitle">Confidence Assessment</div>
                <div className="rsHeader">
                  <span className={`cmLevel ${reasoning.confidence_assessment.verdict}`}>
                    {reasoning.confidence_assessment.verdict?.toUpperCase()}
                  </span>
                  <span className="rsValue">{reasoning.confidence_assessment.strength != null ? (reasoning.confidence_assessment.strength * 100).toFixed(0) + '%' : ''}</span>
                </div>
                {reasoning.confidence_assessment.details?.length > 0 && (
                  <ul className="rsList">{reasoning.confidence_assessment.details.map((d, i) => <li key={i}>{d}</li>)}</ul>
                )}
              </div>
            )}
            {reasoning.summary && (
              <div className="reasoningSection summary">
                <div className="rsText">{reasoning.summary}</div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderSimilarTrades = () => {
    const trades = similarTrades?.similar_trades || explain?.historical_trade_similarity?.similar_trades || [];
    if (trades.length === 0) return null;
    const isEnhanced = similarTrades?.factor_weights != null;
    return (
      <div className="intelCards" style={{ marginTop: 16 }}>
        <div className="intelCard">
          <div className="intelCardLabel">Similar Historical Trades</div>
          <div className="simTrades">
            {trades.map((t, i) => (
              <div key={i} className="simTradeCard">
                <div className="simTradeMain">
                  <span className="simTradeSymbol">{t.ticker || t.symbol}</span>
                  <span className="simTradeOutcome">
                    <span className={`badge ${t.outcome === 'WIN' || t.outcome === 'win' ? 'risk-low' : 'risk-high'}`}>
                      {t.outcome || 'UNKNOWN'}
                    </span>
                  </span>
                  {t.confidence != null && (
                    <span className="simTradeConf">{(t.confidence * 100).toFixed(0)}% conf</span>
                  )}
                  {t.relevance_score != null && (
                    <span className="simTradeRelevance">{(t.relevance_score * 100).toFixed(0)}% match</span>
                  )}
                  {t.regime && (
                    <span className="simTradeRegime"><RegimeBadgeSmall regime={t.regime} /></span>
                  )}
                </div>
                {isEnhanced && t.match_factors && (
                  <div className="simTradeFactors">
                    {Object.entries(t.match_factors).filter(([k]) => k !== 'composite_score').map(([k, v]) => (
                      <span key={k} className="stFactor">
                        {k.replace(/_/g, ' ')}: <strong>{(v * 100).toFixed(0)}%</strong>
                      </span>
                    ))}
                    {t.match_factors.composite_score != null && (
                      <span className="stFactor composite">
                        Composite: <strong>{(t.match_factors.composite_score * 100).toFixed(0)}%</strong>
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
            {isEnhanced && similarTrades.factor_weights && (
              <div className="simTradeWeights">
                <span className="faGroupLabel" style={{ fontSize: 11 }}>Factor Weights</span>
                <div className="stWeightsRow">
                  {Object.entries(similarTrades.factor_weights).map(([k, v]) => (
                    <span key={k} className="stWeight">{k.replace(/_/g, ' ')}: {(v * 100).toFixed(0)}%</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderFailureAnalysis = () => {
    if (!failureAnalysis || !failureAnalysis.failure_detected) return null;
    return (
      <div className="intelCards" style={{ marginTop: 16 }}>
        <div className="intelCard">
          <div className="intelCardLabel" style={{ color: 'var(--accent-danger)' }}>Failure Analysis</div>
          <div className="faBody">
            <div className="faSeverity">
              Severity: <span className={`faSevLabel ${failureAnalysis.severity}`}>{failureAnalysis.severity?.toUpperCase()}</span>
            </div>
            {failureAnalysis.failure_reasons?.length > 0 && (
              <ul className="rsList" style={{ marginTop: 8 }}>
                {failureAnalysis.failure_reasons.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            )}
            {failureAnalysis.primary_cause && (
              <div className="faPrimary">
                <span className="faGroupLabel">Primary Cause</span>
                <div className="rsText">{failureAnalysis.primary_cause}</div>
              </div>
            )}
            <div className="faDetectors">
              {[
                { key: 'regime_mismatch', label: 'Regime Mismatch', data: failureAnalysis.regime_mismatch },
                { key: 'volatility_expansion', label: 'Volatility Expansion', data: failureAnalysis.volatility_expansion },
                { key: 'weak_confirmations', label: 'Weak Confirmations', data: failureAnalysis.weak_confirmations },
                { key: 'stop_loss_analysis', label: 'Stop-Loss Analysis', data: failureAnalysis.stop_loss_analysis },
                { key: 'weak_momentum', label: 'Weak Momentum', data: failureAnalysis.weak_momentum },
                { key: 'regime_instability', label: 'Regime Instability', data: failureAnalysis.regime_instability },
                { key: 'feature_alignment', label: 'Feature Alignment', data: failureAnalysis.feature_alignment },
              ].map(({ key, label, data }) => {
                if (!data) return null;
                const detected = data.mismatch_detected || data.expansion_detected || data.weak_detected || data.is_detected
                  || data.weak_momentum_detected || data.instability_detected || data.poor_alignment_detected
                  || data.sl_hit || Object.keys(data).length === 0;
                return (
                  <div key={key} className={`faDetector ${detected ? 'active' : ''}`}>
                    <div className="faDetectorHeader">
                      <span className="faDetectorLabel">{label}</span>
                      <span className={`badge ${detected ? 'risk-high' : 'risk-low'}`}>{detected ? 'DETECTED' : 'NORMAL'}</span>
                    </div>
                    {data.description && <div className="faDetectorDesc">{data.description}</div>}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderPostMortem = () => {
    if (!postMortemResult) return null;
    const pm = postMortemResult;
    const tradeSummary = pm.trade_summary;
    const failurePatterns = pm.failure_patterns;
    const pmReasoning = pm.reasoning;
    const pmFailure = pm.failure_analysis;
    const pmSimilar = pm.similar_trades;

    return (
      <div className="explainResult">
        {tradeSummary && (
          <div className="intelCards">
            <div className="intelCard">
              <div className="intelCardLabel">Trade Summary</div>
              <div className="intelCardDetails">
                <div className="detailRow">
                  <span className="detailKey">Symbol</span>
                  <span className="detailVal mono">{tradeSummary.symbol}</span>
                </div>
                <div className="detailRow">
                  <span className="detailKey">Decision</span>
                  <span className={`detailVal ${tradeSummary.decision === 'BUY' ? 'positive' : tradeSummary.decision === 'SELL' ? 'negative' : ''}`}>
                    {tradeSummary.decision || 'N/A'}
                  </span>
                </div>
                <div className="detailRow">
                  <span className="detailKey">Outcome</span>
                  <span className={`badge ${tradeSummary.outcome === 'WIN' ? 'risk-low' : 'risk-high'}`}>
                    {tradeSummary.outcome || 'UNKNOWN'}
                  </span>
                </div>
                {tradeSummary.trade_id && (
                  <div className="detailRow">
                    <span className="detailKey">Trade ID</span>
                    <span className="detailVal mono">{tradeSummary.trade_id}</span>
                  </div>
                )}
                {tradeSummary.timestamp && (
                  <div className="detailRow">
                    <span className="detailKey">Timestamp</span>
                    <span className="detailVal">{new Date(tradeSummary.timestamp).toLocaleString()}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {pmReasoning && (
          <div className="intelCards" style={{ marginTop: 16 }}>
            <div className="intelCard">
              <div className="intelCardLabel">Post-Trade Reasoning</div>
              <div className="reasoningBody">
                {pmReasoning.entry_rationale?.primary_reason && <div className="reasoningSection">
                  <div className="rsTitle">Entry Rationale</div>
                  <div className="rsText">{pmReasoning.entry_rationale.primary_reason}</div>
                </div>}
                {pmReasoning.outcome_analysis?.pnl_analysis && <div className="reasoningSection">
                  <div className="rsTitle">Outcome</div>
                  <div className="rsText">{pmReasoning.outcome_analysis.pnl_analysis}</div>
                </div>}
                {pmReasoning.summary && <div className="reasoningSection summary">
                  <div className="rsText">{pmReasoning.summary}</div>
                </div>}
              </div>
            </div>
          </div>
        )}

        {pmFailure && pmFailure.failure_detected && (
          <div className="intelCards" style={{ marginTop: 16 }}>
            <div className="intelCard">
              <div className="intelCardLabel" style={{ color: 'var(--accent-danger)' }}>Failure Analysis</div>
              <div className="faBody">
                <div className="faSeverity">
                  Severity: <span className={`faSevLabel ${pmFailure.severity}`}>{pmFailure.severity?.toUpperCase()}</span>
                </div>
                {pmFailure.failure_reasons?.length > 0 && (
                  <ul className="rsList" style={{ marginTop: 8 }}>
                    {pmFailure.failure_reasons.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                )}
                {pmFailure.primary_cause && (
                  <div className="faPrimary"><div className="rsText">{pmFailure.primary_cause}</div></div>
                )}
              </div>
            </div>
          </div>
        )}

        {failurePatterns && (
          <div className="intelCards" style={{ marginTop: 16 }}>
            <div className="intelCard">
              <div className="intelCardLabel">Reflection: Failure Pattern Analysis</div>
              <div className="reflectionBody">
                <div className="detailRow">
                  <span className="detailKey">Total Analyzed</span>
                  <span className="detailVal">{failurePatterns.total_trades_analyzed || 0} trades</span>
                </div>
                <div className="detailRow">
                  <span className="detailKey">Patterns Found</span>
                  <span className="detailVal">{failurePatterns.patterns_found || 0}</span>
                </div>
                {failurePatterns.most_common_regime && (
                  <div className="detailRow">
                    <span className="detailKey">Most Common Regime</span>
                    <span className="detailVal"><RegimeBadgeSmall regime={failurePatterns.most_common_regime} /></span>
                  </div>
                )}
                {failurePatterns.patterns?.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <span className="faGroupLabel" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>Pattern Categories</span>
                    {failurePatterns.patterns.map((p, i) => (
                      <div key={i} className="patternRow">
                        <span className="patternCat">{p.category?.replace(/_/g, ' ')}</span>
                        <div className="patternBarWrap">
                          <div className="patternBar" style={{ width: `${(p.frequency || 0) * 100}%` }}></div>
                        </div>
                        <span className="patternFreq">{(p.frequency * 100).toFixed(0)}% ({p.count})</span>
                      </div>
                    ))}
                  </div>
                )}
                {failurePatterns.recurring_patterns?.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <span className="faGroupLabel" style={{ color: 'var(--accent-warning)', fontSize: 12, marginBottom: 8, display: 'block' }}>
                      Recurring Patterns ({failurePatterns.recurring_patterns.length})
                    </span>
                    {failurePatterns.recurring_patterns.map((rp, i) => (
                      <div key={i} className="recurringRow">{rp}</div>
                    ))}
                  </div>
                )}
                {failurePatterns.regime_breakdown && Object.keys(failurePatterns.regime_breakdown).length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <span className="faGroupLabel" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>Regime Breakdown</span>
                    <div className="breakdownGrid">
                      {Object.entries(failurePatterns.regime_breakdown).map(([r, c]) => (
                        <div key={r} className="breakdownItem">
                          <RegimeBadgeSmall regime={r} />
                          <span className="breakdownCount">{c}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {failurePatterns.outcome_breakdown && Object.keys(failurePatterns.outcome_breakdown).length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <span className="faGroupLabel" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>Outcome Breakdown</span>
                    <div className="breakdownGrid">
                      {Object.entries(failurePatterns.outcome_breakdown).map(([o, c]) => (
                        <div key={o} className="breakdownItem">
                          <span className={`badge ${o === 'WIN' ? 'risk-low' : 'risk-high'}`}>{o}</span>
                          <span className="breakdownCount">{c}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {pmSimilar?.similar_trades?.length > 0 && (
          <div className="intelCards" style={{ marginTop: 16 }}>
            <div className="intelCard">
              <div className="intelCardLabel">Similar Trades</div>
              <div className="simTrades">
                {pmSimilar.similar_trades.map((t, i) => (
                  <div key={i} className="simTradeCard">
                    <span className="simTradeSymbol">{t.ticker || t.symbol}</span>
                    <span className={`badge ${t.outcome === 'WIN' || t.outcome === 'win' ? 'risk-low' : 'risk-high'}`}>{t.outcome || 'UNKNOWN'}</span>
                    {t.relevance_score != null && <span className="simTradeRelevance">{(t.relevance_score * 100).toFixed(0)}% match</span>}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {pm.latency_ms != null && (
          <div className="latencyFooter">Analysis completed in {pm.latency_ms.toFixed(0)}ms</div>
        )}
      </div>
    );
  };

  return (
    <section className="intelligenceDashboard">
      <div className="intelHeader">
        <h2 className="sectionTitle">Trade Explanation Dashboard</h2>
      </div>

      <div className="sub-tabs">
        {subTabs.map(t => (
          <button key={t.id} className={`sub-tab ${activeSubTab === t.id ? 'active' : ''}`} onClick={() => setActiveSubTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {error && <div className="errorBanner">{error}</div>}
      {pmError && activeSubTab === 'postmortem' && <div className="errorBanner">{pmError}</div>}

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

          {loading && <div className="loadingBlock" style={{ marginTop: 16 }}>Running trade intelligence analysis...</div>}

          {tradeResult && (
            <div className="explainResult">
              <div className="intelCards">
                <div className="intelCard">
                  <div className="intelCardLabel">Trade Summary</div>
                  <div className="intelCardDetails">
                    <div className="detailRow">
                      <span className="detailKey">Symbol</span>
                      <span className="detailVal mono">{explain?.symbol || selectedSymbol}</span>
                    </div>
                    {explain?.trade_id && (
                      <div className="detailRow">
                        <span className="detailKey">Trade ID</span>
                        <span className="detailVal mono">{explain.trade_id}</span>
                      </div>
                    )}
                    {explain?.timestamp && (
                      <div className="detailRow">
                        <span className="detailKey">Timestamp</span>
                        <span className="detailVal">{new Date(explain.timestamp).toLocaleString()}</span>
                      </div>
                    )}
                    {tradeResult.status && (
                      <div className="detailRow">
                        <span className="detailKey">Status</span>
                        <span className="detailVal" style={{ textTransform: 'capitalize' }}>{tradeResult.status}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {renderConfidenceMetrics()}
              {renderReasoning()}
              {renderFeatureAttribution()}
              {renderRegimeContext()}
              {renderFailureAnalysis()}
              {renderSimilarTrades()}

              {tradeResult.latency_ms != null && (
                <div className="latencyFooter">Analysis completed in {tradeResult.latency_ms.toFixed(0)}ms</div>
              )}
            </div>
          )}

          {!tradeResult && !loading && (
            <div className="emptyState">Select a symbol and click "Explain Trade" to view analysis</div>
          )}
        </div>
      )}

      {activeSubTab === 'postmortem' && (
        <div className="intelExplain">
          <div className="explainForm">
            <select className="intelSelect" value={selectedPmSymbol} onChange={e => setSelectedPmSymbol(e.target.value)}>
              <option value="">Select a symbol...</option>
              {stocks.map(s => (
                <option key={s.symbol} value={s.symbol}>{s.symbol}</option>
              ))}
            </select>
            <button className="actionBtn" onClick={handlePostMortem} disabled={pmLoading || !selectedPmSymbol}>
              {pmLoading ? 'Analyzing...' : 'Run Post-Mortem'}
            </button>
          </div>

          {pmLoading && <div className="loadingBlock" style={{ marginTop: 16 }}>Running post-mortem analysis with reflection...</div>}
          {renderPostMortem()}
          {!postMortemResult && !pmLoading && (
            <div className="emptyState">Select a symbol and click "Run Post-Mortem" for full post-trade analysis with reflection</div>
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
