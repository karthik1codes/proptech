import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  BarChart3, TrendingUp, Leaf, Building2, 
  Crown, Medal, Award, ChevronRight, Download, Loader2, FileText
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { API } from '../App';
import { formatCurrency, formatPercent, formatNumber, formatLakhs } from '../utils/formatters';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

export default function ExecutiveSummary() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [executiveData, setExecutiveData] = useState(null);
  const [benchmarks, setBenchmarks] = useState([]);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    fetchExecutiveData();
  }, []);

  const fetchExecutiveData = async () => {
    try {
      const [execRes, benchRes] = await Promise.all([
        axios.get(`${API}/copilot/executive-summary`, { withCredentials: true }),
        axios.get(`${API}/analytics/portfolio-benchmark`, { withCredentials: true }),
      ]);
      setExecutiveData(execRes.data);
      setBenchmarks(benchRes.data);
    } catch (error) {
      console.error('Error fetching executive data:', error);
      toast.error('Failed to load executive summary');
    } finally {
      setLoading(false);
    }
  };

  const downloadPDF = async () => {
    setDownloading(true);
    try {
      const response = await axios.get(`${API}/reports/executive-summary-full/pdf`, {
        withCredentials: true,
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `PropTech_Executive_Summary_${new Date().toISOString().split('T')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Executive Summary PDF downloaded successfully!');
    } catch (error) {
      console.error('Error downloading PDF:', error);
      toast.error('Failed to download PDF');
    } finally {
      setDownloading(false);
    }
  };

  const getRankIcon = (rank) => {
    switch (rank) {
      case 1: return <Crown className="w-4 h-4 text-amber-400" />;
      case 2: return <Medal className="w-4 h-4 text-zinc-400" />;
      case 3: return <Award className="w-4 h-4 text-amber-700" />;
      default: return null;
    }
  };

  const getRankBadge = (rank) => {
    switch (rank) {
      case 1: return 'badge-rank badge-rank-1';
      case 2: return 'badge-rank badge-rank-2';
      case 3: return 'badge-rank badge-rank-3';
      default: return 'badge-rank bg-zinc-700';
    }
  };

  if (loading) {
    return (
      <div className="space-y-6" data-testid="executive-loading">
        <div className="h-12 shimmer rounded w-64"></div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-32 shimmer rounded-xl"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="executive-summary">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <BarChart3 className="w-8 h-8 text-blue-400" />
            Executive Summary
          </h1>
          <p className="text-muted-foreground mt-1">
            Strategic overview across {executiveData?.properties_analyzed || 0} properties
          </p>
        </div>
        <Button 
          onClick={() => navigate('/simulator')}
          className="bg-blue-600 hover:bg-blue-500"
        >
          Optimize Portfolio
          <ChevronRight className="w-4 h-4 ml-2" />
        </Button>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="glass glow-blue" data-testid="kpi-monthly-savings">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-emerald-400" />
              </div>
            </div>
            <p className="text-sm text-muted-foreground uppercase tracking-wide">Monthly Savings Potential</p>
            <p className="text-3xl font-bold font-mono text-emerald-400 mt-1">
              {formatLakhs(executiveData?.total_projected_monthly_savings)}
            </p>
          </CardContent>
        </Card>

        <Card className="glass" data-testid="kpi-annual-savings">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center">
                <BarChart3 className="w-6 h-6 text-blue-400" />
              </div>
            </div>
            <p className="text-sm text-muted-foreground uppercase tracking-wide">Annual Savings Potential</p>
            <p className="text-3xl font-bold font-mono gradient-text mt-1">
              {formatLakhs(executiveData?.total_projected_annual_savings)}
            </p>
          </CardContent>
        </Card>

        <Card className="glass" data-testid="kpi-carbon">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-xl bg-green-500/10 flex items-center justify-center">
                <Leaf className="w-6 h-6 text-green-400" />
              </div>
            </div>
            <p className="text-sm text-muted-foreground uppercase tracking-wide">Carbon Reduction</p>
            <p className="text-3xl font-bold font-mono text-green-400 mt-1">
              {formatNumber(executiveData?.total_carbon_reduction_kg)} kg
            </p>
          </CardContent>
        </Card>

        <Card className="glass" data-testid="kpi-efficiency">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-xl bg-cyan-500/10 flex items-center justify-center">
                <Building2 className="w-6 h-6 text-cyan-400" />
              </div>
            </div>
            <p className="text-sm text-muted-foreground uppercase tracking-wide">Avg. Efficiency Gain</p>
            <p className="text-3xl font-bold font-mono mt-1">
              +{executiveData?.avg_efficiency_improvement?.toFixed(1)}%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Executive Insight */}
      <Card className="glass border-blue-500/30" data-testid="executive-insight">
        <CardContent className="p-6">
          <p className="text-lg leading-relaxed">{executiveData?.executive_insight}</p>
        </CardContent>
      </Card>

      {/* Top Strategic Actions */}
      <Card className="glass" data-testid="strategic-actions">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-emerald-400" />
            Top Strategic Actions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {executiveData?.top_strategic_actions?.map((action, idx) => (
              <div 
                key={idx}
                className="flex items-center justify-between p-4 rounded-xl bg-zinc-900/50 hover:bg-zinc-800/50 cursor-pointer transition-colors"
                onClick={() => navigate(`/portfolio`)}
              >
                <div className="flex items-center gap-4">
                  <span className={getRankBadge(idx + 1)}>{idx + 1}</span>
                  <div>
                    <p className="font-semibold">{action.property_name}</p>
                    <p className="text-sm text-muted-foreground">{action.action}</p>
                  </div>
                </div>
                <div className="text-right">
                  <Badge variant="outline" className="mb-1">{action.type}</Badge>
                  <p className="font-mono text-emerald-400 font-semibold">
                    {formatCurrency(action.impact)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Portfolio Benchmarking */}
      <Card className="glass" data-testid="portfolio-benchmarks">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <Crown className="w-5 h-5 text-amber-400" />
            Portfolio Benchmarking
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-muted-foreground border-b border-border">
                  <th className="pb-3 pr-4">Property</th>
                  <th className="pb-3 px-4 text-center">Profit Rank</th>
                  <th className="pb-3 px-4 text-center">Energy Rank</th>
                  <th className="pb-3 px-4 text-center">Sustainability</th>
                  <th className="pb-3 px-4 text-center">Carbon Rank</th>
                  <th className="pb-3 pl-4 text-right">Occupancy</th>
                </tr>
              </thead>
              <tbody>
                {benchmarks.map((b) => (
                  <tr 
                    key={b.property_id}
                    className="border-b border-border/50 hover:bg-zinc-900/50 cursor-pointer"
                    onClick={() => navigate(`/property/${b.property_id}`)}
                  >
                    <td className="py-4 pr-4">
                      <div>
                        <p className="font-semibold">{b.name}</p>
                        <p className="text-xs text-muted-foreground">{b.location}</p>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <div className="flex items-center justify-center gap-2">
                        {getRankIcon(b.profit_rank)}
                        <span className={getRankBadge(b.profit_rank)}>{b.profit_rank}</span>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <div className="flex items-center justify-center gap-2">
                        {getRankIcon(b.energy_efficiency_rank)}
                        <span className={getRankBadge(b.energy_efficiency_rank)}>{b.energy_efficiency_rank}</span>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <div className="flex items-center justify-center gap-2">
                        {getRankIcon(b.sustainability_score_rank)}
                        <span className={getRankBadge(b.sustainability_score_rank)}>{b.sustainability_score_rank}</span>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <div className="flex items-center justify-center gap-2">
                        {getRankIcon(b.carbon_rank)}
                        <span className={getRankBadge(b.carbon_rank)}>{b.carbon_rank}</span>
                      </div>
                    </td>
                    <td className="py-4 pl-4 text-right">
                      <span className="font-mono">{formatPercent(b.occupancy_rate)}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
