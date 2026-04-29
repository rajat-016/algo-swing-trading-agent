import React from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

const COLORS = {
  positive: '#00ff87',
  negative: '#ff3366',
  neutral: '#00d4ff',
  muted: '#505060',
  grid: 'rgba(255, 255, 255, 0.06)',
  text: '#a0a0b0',
};

const formatCurrency = (value) => {
  if (value === null || value === undefined) return '₹0';
  const sign = value >= 0 ? '₹' : '-₹';
  return `${sign}${Math.abs(value).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="chartTooltip">
        <p className="tooltipDate">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} className="tooltipValue" style={{ color: entry.color }}>
            {entry.name}: {entry.value?.toLocaleString() || entry.value}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export function EquityCurveChart({ data }) {
  if (!data || data.length === 0) {
    return <div className="chartEmpty">No data available</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} vertical={false} />
        <XAxis
          dataKey="date"
          stroke={COLORS.muted}
          tick={{ fontSize: 11, fill: COLORS.text }}
          tickFormatter={(value) => value?.slice(5) || value}
          axisLine={{ stroke: COLORS.grid }}
          tickLine={false}
        />
        <YAxis
          stroke={COLORS.muted}
          tick={{ fontSize: 11, fill: COLORS.text }}
          tickFormatter={(value) => `₹${value / 1000}k`}
          axisLine={false}
          tickLine={false}
          width={60}
        />
        <Tooltip content={<CustomTooltip />} />
        <Line
          type="monotone"
          dataKey="cumulative_pnl"
          name="Equity"
          stroke={COLORS.positive}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 5, fill: COLORS.positive, strokeWidth: 0 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function DailyPnLChart({ data }) {
  if (!data || data.length === 0) {
    return <div className="chartEmpty">No data available</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} vertical={false} />
        <XAxis
          dataKey="date"
          stroke={COLORS.muted}
          tick={{ fontSize: 11, fill: COLORS.text }}
          tickFormatter={(value) => value?.slice(5) || value}
          axisLine={{ stroke: COLORS.grid }}
          tickLine={false}
        />
        <YAxis
          stroke={COLORS.muted}
          tick={{ fontSize: 11, fill: COLORS.text }}
          tickFormatter={(value) => `₹${value / 1000}k`}
          axisLine={false}
          tickLine={false}
          width={60}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="pnl" name="P&L" radius={[4, 4, 0, 0]}>
          {data.map((entry, index) => (
            <Cell key={index} fill={entry.pnl >= 0 ? COLORS.positive : COLORS.negative} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function PositionDistributionChart({ data }) {
  if (!data || data.length === 0) {
    return <div className="chartEmpty">No positions yet</div>;
  }

  const filteredData = data.filter(d => d.value > 0);

  if (filteredData.length === 0) {
    return <div className="chartEmpty">No positions yet</div>;
  }

  const defaultColors = ['#00ff87', '#00d4ff', '#ffaa00', '#ff3366'];

  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={filteredData}
          cx="50%"
          cy="50%"
          innerRadius={55}
          outerRadius={85}
          paddingAngle={3}
          dataKey="value"
          nameKey="name"
        >
          {filteredData.map((entry, index) => (
            <Cell 
              key={index} 
              fill={entry.color || defaultColors[index % defaultColors.length]} 
              stroke="transparent"
            />
          ))}
        </Pie>
        <Tooltip 
          content={({ active, payload }) => {
            if (active && payload && payload.length) {
              return (
                <div className="chartTooltip">
                  <p className="tooltipValue" style={{ color: payload[0].payload.color }}>
                    {payload[0].name}: {payload[0].value}
                  </p>
                </div>
              );
            }
            return null;
          }}
        />
        <Legend 
          verticalAlign="bottom" 
          height={36}
          formatter={(value) => <span style={{ color: COLORS.text, fontSize: 12 }}>{value}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function MetricCard({ title, value, suffix = '', color = 'neutral', subtext }) {
  const colorMap = {
    positive: COLORS.positive,
    negative: COLORS.negative,
    neutral: '#ffffff',
  };

  return (
    <div className="metricCard">
      <div className="metricTitle">{title}</div>
      <div className="metricValue" style={{ color: colorMap[color] }}>
        {typeof value === 'number' ? value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : value}
        {suffix && <span className="metricSuffix">{suffix}</span>}
      </div>
      {subtext && <div className="metricSubtext">{subtext}</div>}
    </div>
  );
}

export function PerformanceMetrics({ metrics }) {
  if (!metrics) {
    return <div className="chartEmpty">No metrics available</div>;
  }

  return (
    <div className="metricsGrid">
      <MetricCard
        title="Total Trades"
        value={metrics.total_trades}
        color="neutral"
      />
      <MetricCard
        title="Win Rate"
        value={metrics.win_rate}
        suffix="%"
        color={metrics.win_rate >= 50 ? 'positive' : 'negative'}
      />
      <MetricCard
        title="Avg Return"
        value={metrics.avg_return}
        suffix="%"
        color={metrics.avg_return >= 0 ? 'positive' : 'negative'}
      />
      <MetricCard
        title="Max Drawdown"
        value={Math.abs(metrics.max_drawdown)}
        suffix="₹"
        color="negative"
        subtext="Peak to trough"
      />
      <MetricCard
        title="Profitable"
        value={metrics.profitable_trades}
        color="positive"
        subtext="Winning trades"
      />
      <MetricCard
        title="Losing"
        value={metrics.losing_trades}
        color="negative"
        subtext="Losing trades"
      />
    </div>
  );
}