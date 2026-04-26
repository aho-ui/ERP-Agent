import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import type { ChartArtifact } from "../lib/types";

const CHART_COLORS = ["#6366f1", "#22d3ee", "#f59e0b", "#10b981", "#f43f5e", "#a78bfa"];

export function ChartWidget({ artifact }: { artifact: ChartArtifact }) {
  const { chart_type, data, x_key, series } = artifact;
  if (chart_type === "pie") {
    return (
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="45%" outerRadius={90} label={({ percent }) => `${(percent * 100).toFixed(0)}%`} labelLine={false}>
            {data.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
          </Pie>
          <Tooltip />
          <Legend verticalAlign="bottom" height={36} />
        </PieChart>
      </ResponsiveContainer>
    );
  }
  if (chart_type === "line") {
    return (
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey={x_key} tick={{ fontSize: 10, fill: "#9ca3af" }} />
          <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} />
          <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "none", fontSize: 11 }} />
          {series && series.length > 0 && <Legend wrapperStyle={{ fontSize: 11 }} />}
          {(series ?? []).map((s, i) => <Line key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={CHART_COLORS[i % CHART_COLORS.length]} dot={false} />)}
        </LineChart>
      </ResponsiveContainer>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey={x_key} tick={{ fontSize: 10, fill: "#9ca3af" }} />
        <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} />
        <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "none", fontSize: 11 }} />
        {series && series.length > 0 && <Legend wrapperStyle={{ fontSize: 11 }} />}
        {(series ?? []).map((s, i) => <Bar key={s.key} dataKey={s.key} name={s.label} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
      </BarChart>
    </ResponsiveContainer>
  );
}
