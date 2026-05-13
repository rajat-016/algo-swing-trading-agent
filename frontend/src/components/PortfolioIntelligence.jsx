import React, { useState, useEffect, useCallback } from 'react';
import { portfolioApi, correlationApi } from '../api';

function PortfolioIntelligence() {
  const [risk, setRisk] = useState(null);
  const [exposure, setExposure] = useState(null);
  const [correlation, setCorrelation] = useState(null);
  const [diversification, setDiversification] = useState(null);
  const [clusters, setClusters] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeSubTab, setActiveSubTab] = useState('overview');

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [rsk, exp, corr, div, clus] = await Promise.all([
        portfolioApi.getRisk().catch(() => null),
        portfolioApi.getExposure().catch(() => null),
        portfolioApi.getCorrelation().catch(() => null),
        correlationApi.getDiversification().catch(() => null),
        correlationApi.getClusters().catch(() => null),
      ]);
      setRisk(rsk);
      setExposure(exp);
      setCorrelation(corr);
      setDiversification(div);
      setClusters(clus);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  if (loading) return <div className="loadingBlock">Loading portfolio intelligence...</div>;
  if (error) return <div className="errorBanner">Error: {error}</div>;

  const subTabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'exposure', label: 'Exposure' },
    { id: 'correlation', label: 'Correlation' },
    { id: 'diversification', label: 'Diversification' },
  ];

  const riskData = risk?.analysis || risk;
  const exposureData = exposure?.analysis || exposure;
  const correlationData = correlation?.analysis || correlation;
  const divData = diversification?.analysis || diversification;

  const riskScore = riskData?.risk_insights?.composite_risk_score ?? riskData?.composite_risk_score;
  const riskLevel = riskScore != null
    ? (riskScore >= 70 ? 'High' : riskScore >= 40 ? 'Medium' : 'Low')
    : 'N/A';

  return (
    <section className="intelligenceDashboard">
      <div className="intelHeader">
        <h2 className="sectionTitle">Portfolio Intelligence</h2>
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
            <div className="intelCard">
              <div className="intelCardLabel">Composite Risk Score</div>
              <div className={`intelCardValue ${riskScore >= 70 ? 'negative' : riskScore >= 40 ? 'warning' : 'positive'}`}>
                {riskScore != null ? `${riskScore.toFixed(0)}/100` : 'N/A'}
              </div>
              <div className="intelCardDetails">
                <div className="detailRow">
                  <span className="detailKey">Level</span>
                  <span className={`detailVal risk-${riskLevel.toLowerCase()}`}>{riskLevel}</span>
                </div>
                {riskData?.risk_insights?.instability_flags && (
                  <div className="detailRow">
                    <span className="detailKey">Instability Flags</span>
                    <span className="detailVal">{riskData.risk_insights.instability_flags.length}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="intelCard">
              <div className="intelCardLabel">Directional Bias</div>
              <div className="intelCardValue">
                {exposureData?.directional_bias?.map(b => b.charAt(0).toUpperCase() + b.slice(1)).join(', ') || 'N/A'}
              </div>
              <div className="intelCardDetails">
                {exposureData?.directional_bias?.includes('bullish') && (
                  <div className="detailRow">
                    <span className="detailKey">Net Exposure</span>
                    <span className="detailVal">{exposureData.net_exposure != null ? `${exposureData.net_exposure.toFixed(1)}%` : 'N/A'}</span>
                  </div>
                )}
              </div>
            </div>

            {diversification && (
              <div className="intelCard">
                <div className="intelCardLabel">Diversification Score</div>
                <div className={`intelCardValue ${
                  (divData?.score ?? divData?.composite_score ?? 0) >= 70 ? 'positive' :
                  (divData?.score ?? divData?.composite_score ?? 0) >= 40 ? 'warning' : 'negative'
                }`}>
                  {divData?.score ?? divData?.composite_score ?? 0}/100
                </div>
                <div className="intelCardDetails">
                  {divData?.effective_n && (
                    <div className="detailRow">
                      <span className="detailKey">Effective N</span>
                      <span className="detailVal">{divData.effective_n.toFixed(1)}</span>
                    </div>
                  )}
                  {divData?.avg_pairwise_correlation != null && (
                    <div className="detailRow">
                      <span className="detailKey">Avg Correlation</span>
                      <span className="detailVal">{divData.avg_pairwise_correlation.toFixed(2)}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {riskData?.correlation_analysis?.clusters && (
              <div className="intelCard">
                <div className="intelCardLabel">Correlation Clusters</div>
                <div className="intelCardValue">{riskData.correlation_analysis.clusters.length}</div>
                <div className="intelCardDetails">
                  <div className="detailRow">
                    <span className="detailKey">Total Pairs</span>
                    <span className="detailVal">{riskData.correlation_analysis.total_pairs || riskData.correlation_analysis.pairs?.length || 0}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {activeSubTab === 'exposure' && (
        <div className="intelExposure">
          {exposureData?.sector_exposures && Object.keys(exposureData.sector_exposures).length > 0 ? (
            <div className="tableCard">
              <table className="dataTable">
                <thead>
                  <tr>
                    <th>Sector</th>
                    <th>Exposure</th>
                    <th>Allocation</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(exposureData.sector_exposures)
                    .sort((a, b) => (b[1]?.exposure_pct || b[1]?.exposure || 0) - (a[1]?.exposure_pct || a[1]?.exposure || 0))
                    .map(([sector, data]) => {
                      const pct = data.exposure_pct ?? data.exposure ?? 0;
                      const overexposed = pct > 30;
                      return (
                        <tr key={sector}>
                          <td className="symbolCell">{sector}</td>
                          <td className="monoCell">{data.count || 0} holdings</td>
                          <td className="monoCell">{pct.toFixed(1)}%</td>
                          <td>
                            <span className={`badge ${overexposed ? 'risk-high' : 'risk-low'}`}>
                              {overexposed ? 'OVEREXPOSED' : 'OK'}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="emptyState">No exposure data available</div>
          )}

          {exposureData?.concentration && (
            <div className="metricCards">
              <div className="metricCard">
                <div className="metricTitle">Top Holding</div>
                <div className="metricValue neutral">{exposureData.concentration.top_holding_pct?.toFixed(1) || 'N/A'}%</div>
              </div>
              <div className="metricCard">
                <div className="metricTitle">Top 3 Holdings</div>
                <div className="metricValue neutral">{exposureData.concentration.top_3_pct?.toFixed(1) || 'N/A'}%</div>
              </div>
              <div className="metricCard">
                <div className="metricTitle">Herfindahl Index</div>
                <div className="metricValue neutral">{exposureData.concentration.herfindahl_index?.toFixed(3) || 'N/A'}</div>
              </div>
            </div>
          )}
        </div>
      )}

      {activeSubTab === 'correlation' && (
        <div className="intelCorrelation">
          {correlationData?.pairs && correlationData.pairs.length > 0 ? (
            <div className="tableCard">
              <table className="dataTable">
                <thead>
                  <tr>
                    <th>Symbol 1</th>
                    <th>Symbol 2</th>
                    <th>Correlation</th>
                    <th>Strength</th>
                  </tr>
                </thead>
                <tbody>
                  {correlationData.pairs
                    .sort((a, b) => Math.abs(b.correlation || b.coefficient || 0) - Math.abs(a.correlation || a.coefficient || 0))
                    .slice(0, 50)
                    .map((pair, i) => {
                      const corr = pair.correlation ?? pair.coefficient ?? 0;
                      const strength = Math.abs(corr) >= 0.7 ? 'HIGH' : Math.abs(corr) >= 0.4 ? 'MED' : 'LOW';
                      return (
                        <tr key={i}>
                          <td className="symbolCell">{pair.symbol_1 || pair.stock_1}</td>
                          <td className="symbolCell">{pair.symbol_2 || pair.stock_2}</td>
                          <td className={`monoCell ${corr > 0 ? 'positive' : 'negative'}`}>{corr.toFixed(3)}</td>
                          <td>
                            <span className={`badge ${strength === 'HIGH' ? 'risk-high' : strength === 'MED' ? '' : 'risk-low'}`}>
                              {strength}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="emptyState">No correlation data available</div>
          )}

          {correlationData?.clusters && correlationData.clusters.length > 0 && (
            <div className="intelCards" style={{ marginTop: 24 }}>
              <div className="intelCard">
                <div className="intelCardLabel">Correlation Clusters</div>
                {correlationData.clusters.map((cluster, i) => (
                  <div key={i} className="clusterRow">
                    <span className="clusterLabel">Cluster {i + 1}</span>
                    <span className="clusterSymbols">
                      {cluster.symbols?.join(', ') || cluster.stocks?.join(', ') || cluster.members?.join(', ')}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeSubTab === 'diversification' && (
        <div className="intelDiversification">
          {divData ? (
            <div className="intelCards">
              <div className="intelCard">
                <div className="intelCardLabel">Diversification Score Breakdown</div>
                <div className="scoreBreakdown">
                  {divData.breakdown && Object.entries(divData.breakdown).map(([key, val]) => (
                    <div key={key} className="scoreRow">
                      <span className="scoreLabel">{key.replace(/_/g, ' ')}</span>
                      <span className="scoreVal">{typeof val === 'number' ? val.toFixed(1) : val}</span>
                    </div>
                  ))}
                  {!divData.breakdown && (
                    <>
                      <div className="scoreRow">
                        <span className="scoreLabel">Effective N</span>
                        <span className="scoreVal">{divData.effective_n?.toFixed(1) || 'N/A'}</span>
                      </div>
                      <div className="scoreRow">
                        <span className="scoreLabel">Avg Pairwise Correlation</span>
                        <span className="scoreVal">{divData.avg_pairwise_correlation?.toFixed(3) || 'N/A'}</span>
                      </div>
                      <div className="scoreRow">
                        <span className="scoreLabel">Sector Diversification</span>
                        <span className="scoreVal">{divData.sector_diversification_score?.toFixed(1) || 'N/A'}</span>
                      </div>
                      <div className="scoreRow">
                        <span className="scoreLabel">Concentration Penalty</span>
                        <span className="scoreVal">{divData.concentration_penalty?.toFixed(1) || 'N/A'}</span>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="emptyState">No diversification data available</div>
          )}
        </div>
      )}
    </section>
  );
}

export default PortfolioIntelligence;
