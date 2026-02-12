import React from 'react';
import { Zap, TrendingDown, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { formatCurrency, formatNumber } from '../utils/formatters';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

/**
 * EnergySavingsChart - Visualizes energy savings scenarios
 * @param {Object} energyData - Energy savings data from API
 */
export default function EnergySavingsChart({ energyData }) {
  if (!energyData || !energyData.scenarios) {
    return null;
  }

  const chartData = energyData.scenarios.map(s => ({
    name: s.scenario,
    energy: s.after_energy_usage,
    cost: s.after_cost_daily,
    savings: s.monthly_savings,
  }));

  const colors = ['#64748B', '#3B82F6', '#22D3EE', '#10B981'];

  return (
    <Card className="glass" data-testid="energy-savings-chart">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Zap className="w-5 h-5 text-cyan-400" />
          Energy Usage Comparison
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="p-4 rounded-xl bg-zinc-900/50 text-center">
            <p className="text-xs text-muted-foreground uppercase mb-1">Current Usage</p>
            <p className="text-2xl font-bold font-mono">
              {formatNumber(energyData.scenarios[0]?.before_energy_usage)} kWh
            </p>
          </div>
          <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 text-center">
            <p className="text-xs text-muted-foreground uppercase mb-1">Optimized (1 Floor)</p>
            <p className="text-2xl font-bold font-mono text-blue-400">
              {formatNumber(energyData.scenarios[1]?.after_energy_usage)} kWh
            </p>
          </div>
          <div className="p-4 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-center">
            <p className="text-xs text-muted-foreground uppercase mb-1">Optimized (2 Floors)</p>
            <p className="text-2xl font-bold font-mono text-cyan-400">
              {formatNumber(energyData.scenarios[2]?.after_energy_usage)} kWh
            </p>
          </div>
          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-center">
            <p className="text-xs text-muted-foreground uppercase mb-1">Max Savings</p>
            <p className="text-2xl font-bold font-mono text-emerald-400">
              {formatCurrency(Math.max(...energyData.scenarios.map(s => s.monthly_savings || 0)))}/mo
            </p>
          </div>
        </div>

        {/* Chart */}
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={true} vertical={false} />
              <XAxis 
                type="number" 
                stroke="#64748B" 
                fontSize={12}
                tickFormatter={(v) => `${v} kWh`}
              />
              <YAxis 
                type="category" 
                dataKey="name" 
                stroke="#64748B" 
                fontSize={11}
                width={100}
              />
              <Tooltip 
                contentStyle={{ 
                  background: 'hsl(var(--card))', 
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
                formatter={(value, name) => {
                  if (name === 'energy') return [`${formatNumber(value)} kWh`, 'Energy Usage'];
                  return [value, name];
                }}
              />
              <Bar dataKey="energy" radius={[0, 4, 4, 0]}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={colors[index]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Savings Breakdown */}
        <div className="mt-6 pt-6 border-t border-border">
          <h4 className="text-sm font-semibold mb-4 flex items-center gap-2">
            <TrendingDown className="w-4 h-4 text-emerald-400" />
            Potential Savings Breakdown
          </h4>
          <div className="space-y-3">
            {energyData.scenarios.slice(1).map((scenario, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-zinc-900/50">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full`} style={{ background: colors[idx + 1] }}></div>
                  <span className="text-sm">{scenario.scenario}</span>
                </div>
                <div className="flex items-center gap-6 text-sm">
                  <div className="text-right">
                    <p className="text-muted-foreground text-xs">Weekly</p>
                    <p className="font-mono text-emerald-400">{formatCurrency(scenario.weekly_savings)}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-muted-foreground text-xs">Monthly</p>
                    <p className="font-mono text-emerald-400">{formatCurrency(scenario.monthly_savings)}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-muted-foreground text-xs">Reduction</p>
                    <p className="font-mono text-cyan-400">-{scenario.energy_reduction_percent}%</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
