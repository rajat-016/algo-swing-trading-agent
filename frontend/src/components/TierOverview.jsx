import React, { useState, useEffect, useCallback } from 'react';
import { stocksApi, tradingApi } from '../api';

const defaultTierConfig = [
  { tier: 1, trigger_pct: 5.0, qty_pct: 25.0, trailing_sl_offset: 0.0 },
  { tier: 2, trigger_pct: 10.0, qty_pct: 25.0, trailing_sl_offset: 3.0 },
  { tier: 3, trigger_pct: 15.0, qty_pct: 25.0, trailing_sl_offset: 7.0 },
  { tier: 4, trigger_pct: 20.0, qty_pct: 25.0, trailing_sl_offset: null },
];

const formatCurrency = (value) => {
  if (value === null || value === undefined) return '-';
  return `\u20B9${value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const formatPercent = (value) => {
  if (value === null || value === undefined) return '-';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
};

export default function TierOverview({ stocks }) {
  const [tierConfig, setTierConfig] = useState(defaultTierConfig);
  const [exitLogs, setExitLogs] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState('');

  const activeStocks = stocks.filter(s => s.status === 'ENTERED' || s.status === 'EXITED');

  useEffect(() => {
    tradingApi.getTierConfig()
      .then(data => { if (data?.tiers) setTierConfig(data.tiers); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (activeStocks.length > 0 && !selectedSymbol) {
      setSelectedSymbol(activeStocks[0].symbol);
    }
  }, [activeStocks, selectedSymbol]);

  const fetchExitLogs = useCallback(async (symbol) => {
    if (!symbol) return;
    try {
      const data = await stocksApi.getExitLogs(symbol);
      setExitLogs(data?.exit_logs || []);
    } catch {
      setExitLogs([]);
    }
  }, []);

  useEffect(() => {
    fetchExitLogs(selectedSymbol);
  }, [selectedSymbol, fetchExitLogs]);

  const stock = stocks.find(s => s.symbol === selectedSymbol);
  if (!stock) {
    return (
      <section className="tierSection">
        <div className="emptyState">No stocks available. Add positions to view tier progression.</div>
      </section>
    );
  }

  const originalQty = stock.original_quantity || stock.entry_quantity || 0;
  const remainingQty = stock.remaining_quantity ?? originalQty;
  const currentTier = stock.current_tier || 1;
  const entryPrice = stock.entry_price || stock.average_price || 0;
  const currentPrice = stock.current_price || 0;
  const realizedPnl = stock.realized_pnl || 0;
  const trailingSl = stock.trailing_sl;
  const unrelPnl = currentPrice ? (currentPrice - entryPrice) * remainingQty : 0;
  const totalPnl = realizedPnl + unrelPnl;
  const totalPnlPct = entryPrice ? ((totalPnl) / (entryPrice * originalQty)) * 100 : 0;

  const tierRows = tierConfig.map(tc => {
    const exitLog = exitLogs.find(e => e.tier === tc.tier);
    const isDone = !!exitLog;
    const isCurrent = tc.tier === currentTier && !isDone;
    const isPending = tc.tier > currentTier && !isDone;
    const triggerPrice = entryPrice * (1 + tc.trigger_pct / 100);
    const qtyToSell = Math.min(
      Math.max(1, Math.round(originalQty * tc.qty_pct / 100)),
      originalQty
    );

    let statusLabel, statusClass;
    if (isDone) {
      statusLabel = 'DONE';
      statusClass = 'done';
    } else if (isCurrent) {
      statusLabel = 'LIVE';
      statusClass = 'live';
    } else {
      statusLabel = 'PENDING';
      statusClass = 'pending';
    }

    return {
      ...tc,
      exitLog,
      isDone,
      isCurrent,
      isPending,
      triggerPrice,
      qtyToSell,
      statusLabel,
      statusClass,
    };
  });

  const completedCount = tierRows.filter(r => r.isDone).length;

  return (
    <section className="tierSection">
      <div className="tierHeader">
        <div className="sectionHeader">
          <h2 className="sectionTitle">Tier Exit Overview</h2>
          <span className="sectionSubtitle">Realized P&L: {formatCurrency(realizedPnl)} &middot; Total P&L: <span className={totalPnl >= 0 ? 'positive' : 'negative'}>{formatCurrency(totalPnl)} ({formatPercent(totalPnlPct)})</span></span>
        </div>
      </div>

      <div className="tierStockSelector">
        <label className="tierSelectorLabel">Stock:</label>
        <select
          className="tierSelector"
          value={selectedSymbol}
          onChange={e => setSelectedSymbol(e.target.value)}
        >
          {activeStocks.map(s => (
            <option key={s.symbol} value={s.symbol}>
              {s.symbol} &mdash; T{Math.min(s.current_tier || 1, 4)}/4 &middot; {s.remaining_quantity ?? s.entry_quantity}/{s.original_quantity || s.entry_quantity} qty
            </option>
          ))}
        </select>
      </div>

      <div className="tierSummaryCards">
        <div className="tierSummaryCard">
          <span className="tierSummaryLabel">Original Qty</span>
          <span className="tierSummaryValue">{originalQty}</span>
        </div>
        <div className="tierSummaryCard">
          <span className="tierSummaryLabel">Remaining</span>
          <span className="tierSummaryValue">{remainingQty} <span className="tierSummarySub">({Math.round(remainingQty/originalQty*100)}%)</span></span>
        </div>
        <div className="tierSummaryCard">
          <span className="tierSummaryLabel">Entry Price</span>
          <span className="tierSummaryValue">{formatCurrency(entryPrice)}</span>
        </div>
        <div className="tierSummaryCard">
          <span className="tierSummaryLabel">Current Price</span>
          <span className={`tierSummaryValue ${currentPrice >= entryPrice ? 'positive' : 'negative'}`}>
            {formatCurrency(currentPrice)}
          </span>
        </div>
        {trailingSl && (
          <div className="tierSummaryCard">
            <span className="tierSummaryLabel">Trailing SL</span>
            <span className="tierSummaryValue warning">{formatCurrency(trailingSl)}</span>
          </div>
        )}
        <div className="tierSummaryCard">
          <span className="tierSummaryLabel">Realized P&L</span>
          <span className={`tierSummaryValue ${realizedPnl >= 0 ? 'positive' : 'negative'}`}>
            {formatCurrency(realizedPnl)}
          </span>
        </div>
        <div className="tierSummaryCard">
          <span className="tierSummaryLabel">Tiers Completed</span>
          <span className="tierSummaryValue">{completedCount}/4</span>
        </div>
      </div>

      <div className="tierTableCard">
        <table className="dataTable">
          <thead>
            <tr>
              <th>Tier</th>
              <th>Trigger %</th>
              <th>Sell %</th>
              <th>Trailing SL</th>
              <th>Qty to Sell</th>
              <th>Exit Price</th>
              <th>Exit Date</th>
              <th>Qty Sold</th>
              <th>Tier P&L</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {tierRows.map(row => (
              <tr key={row.tier} className={`tierRow ${row.statusClass}`}>
                <td className="tierNumCell">T{row.tier}</td>
                <td className="monoCell">{formatPercent(row.trigger_pct)}</td>
                <td className="monoCell">{row.qty_pct}%</td>
                <td className="monoCell">
                  {row.trailing_sl_offset !== null && row.trailing_sl_offset !== undefined
                    ? `Entry ${row.trailing_sl_offset > 0 ? '+' : ''}${row.trailing_sl_offset}%`
                    : '-'}
                </td>
                <td className="monoCell">{row.isDone ? '-' : row.qtyToSell}</td>
                <td className="priceCell">
                  {row.isDone
                    ? formatCurrency(row.exitLog.exit_price)
                    : <span className="triggerForecast">{formatCurrency(row.triggerPrice)}</span>
                  }
                </td>
                <td className="dateCell">
                  {row.isDone ? new Date(row.exitLog.exit_date).toLocaleString() : '-'}
                </td>
                <td className="monoCell">
                  {row.isDone ? row.exitLog.quantity : '-'}
                </td>
                <td className={`pnlCell ${row.isDone && (row.exitLog.pnl || 0) >= 0 ? 'positive' : row.isDone ? 'negative' : ''}`}>
                  {row.isDone ? formatCurrency(row.exitLog.pnl) : '-'}
                </td>
                <td>
                  <span className={`tierStatusPill ${row.statusClass}`}>
                    {row.statusLabel}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="tierProgressSection">
        <h3 className="sectionTitle">Exit Progress</h3>
        <div className="tierProgressBar">
          {tierRows.map(row => {
            const pct = originalQty > 0 ? (row.qtyToSell / originalQty) * 100 : 0;
            return (
              <div
                key={row.tier}
                className={`tierProgressSegment ${row.statusClass}`}
                style={{ width: `${pct}%` }}
                title={`Tier ${row.tier}: ${row.isDone ? 'Sold ' + row.exitLog.quantity : 'Pending ' + row.qtyToSell} shares`}
              >
                {row.isDone ? '\u2713' : row.tier}
              </div>
            );
          })}
        </div>
        <div className="tierProgressLegend">
          {tierRows.map(row => (
            <span key={row.tier} className="tierLegendItem">
              <span className={`legendDot ${row.statusClass}`}></span>
              T{row.tier}: {row.isDone ? `${row.exitLog.quantity} sold @ ${formatCurrency(row.exitLog.exit_price)}` : `${row.qtyToSell} qty @ ${formatCurrency(row.triggerPrice)}`}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}