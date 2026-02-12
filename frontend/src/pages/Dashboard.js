import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Building2, TrendingUp, Zap, DollarSign, Users, 
  ArrowUpRight, ArrowDownRight, Leaf,
  BarChart3, ChevronRight, Sparkles
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { API, AuthContext } from '../App';
import { formatCurrency, formatNumber, formatPercent } from '../utils/formatters';
import AnimatedCounter from '../components/AnimatedCounter';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function Dashboard() {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);
  const [properties, setProperties] = useState([]);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [dashboardRes, propertiesRes] = await Promise.all([
        axios.get(`${API}/analytics/dashboard`, { withCredentials: true }),
        axios.get(`${API}/properties`, { withCredentials: true })
      ]);
      setDashboardData(dashboardRes.data);
      setProperties(propertiesRes.data);
    } catch (error) {
      console.error('Error fetching dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-8" data-testid="dashboard-loading">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-36 skeleton rounded-2xl"></div>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 h-80 skeleton rounded-2xl"></div>
          <div className="h-80 skeleton rounded-2xl"></div>
        </div>
      </div>
    );
  }

  const kpis = dashboardData?.kpis || {};
  const optimization = dashboardData?.optimization_potential || {};

  // Mock trend data for chart
  const trendData = Array.from({ length: 7 }, (_, i) => ({
    day: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i],
    occupancy: 60 + Math.random() * 25,
    revenue: kpis.total_revenue / 7 * (0.8 + Math.random() * 0.4),
  }));

  const getUtilizationColor = (status) => {
    switch (status) {
      case 'Optimal': return 'text-emerald-400';
      case 'Underutilized': return 'text-red-400';
      case 'Overloaded': return 'text-amber-400';
      default: return 'text-muted-foreground';
    }
  };

  const getUtilizationBadge = (status) => {
    switch (status) {
      case 'Optimal': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'Underutilized': return 'bg-red-500/10 text-red-400 border-red-500/30';
      case 'Overloaded': return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      default: return '';
    }
  };

  return (
    <div className="space-y-8" data-testid="dashboard">
      {/* Welcome Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
        <div className="animate-fade-in">
          <h1 className="text-4xl font-bold tracking-tight text-white">
            Welcome back, <span className="gradient-text">{user?.name?.split(' ')[0] || 'User'}</span>
          </h1>
          <p className="text-slate-400 mt-2 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            Here's your property portfolio overview
          </p>
        </div>
        <Button 
          onClick={() => navigate('/portfolio')}
          className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 transition-all btn-glow"
          data-testid="view-portfolio-btn"
        >
          <Building2 className="w-4 h-4 mr-2" />
          View All Properties
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Revenue Card */}
        <Card className="glass card-hover metric-card border-white/5 animate-fade-in stagger-1" data-testid="kpi-revenue">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500/20 to-blue-600/10 flex items-center justify-center border border-blue-500/20">
                <DollarSign className="w-6 h-6 text-blue-400" />
              </div>
              <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/30">
                <ArrowUpRight className="w-3 h-3 mr-1" />
                12.5%
              </Badge>
            </div>
            <p className="text-sm text-slate-400 font-medium uppercase tracking-wider">Total Revenue</p>
            <p className="text-3xl font-bold text-white font-mono mt-1">
              <AnimatedCounter value={kpis.total_revenue} formatter={formatCurrency} />
            </p>
          </CardContent>
        </Card>

        {/* Profit Card */}
        <Card className="glass card-hover metric-card border-white/5 animate-fade-in stagger-2" data-testid="kpi-profit">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500/20 to-emerald-600/10 flex items-center justify-center border border-emerald-500/20">
                <TrendingUp className="w-6 h-6 text-emerald-400" />
              </div>
              <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/30">
                <ArrowUpRight className="w-3 h-3 mr-1" />
                8.2%
              </Badge>
            </div>
            <p className="text-sm text-slate-400 font-medium uppercase tracking-wider">Net Profit</p>
            <p className="text-3xl font-bold text-emerald-400 font-mono mt-1">
              <AnimatedCounter value={kpis.total_profit} formatter={formatCurrency} />
            </p>
          </CardContent>
        </Card>

        {/* Occupancy Card */}
        <Card className="glass card-hover metric-card border-white/5 animate-fade-in stagger-3" data-testid="kpi-occupancy">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500/20 to-amber-600/10 flex items-center justify-center border border-amber-500/20">
                <Users className="w-6 h-6 text-amber-400" />
              </div>
              <span className="text-xs text-slate-500 font-mono">
                {formatNumber(kpis.total_occupied)} / {formatNumber(kpis.total_capacity)}
              </span>
            </div>
            <p className="text-sm text-slate-400 font-medium uppercase tracking-wider">Occupancy Rate</p>
            <p className="text-3xl font-bold text-white font-mono mt-1">
              <AnimatedCounter value={kpis.overall_occupancy * 100} suffix="%" decimals={1} />
            </p>
            <Progress value={kpis.overall_occupancy * 100} className="mt-3 h-1.5 bg-slate-800" />
          </CardContent>
        </Card>

        {/* Energy Card */}
        <Card className="glass card-hover metric-card border-white/5 animate-fade-in stagger-4" data-testid="kpi-energy">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500/20 to-cyan-600/10 flex items-center justify-center border border-cyan-500/20">
                <Zap className="w-6 h-6 text-cyan-400" />
              </div>
              <Badge variant="outline" className="bg-red-500/10 text-red-400 border-red-500/30">
                <ArrowDownRight className="w-3 h-3 mr-1" />
                -5.3%
              </Badge>
            </div>
            <p className="text-sm text-slate-400 font-medium uppercase tracking-wider">Energy Cost</p>
            <p className="text-3xl font-bold text-white font-mono mt-1">
              <AnimatedCounter value={kpis.total_energy_cost} formatter={formatCurrency} />
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Occupancy Trend Chart */}
        <Card className="glass lg:col-span-2 border-white/5 animate-fade-in stagger-5" data-testid="occupancy-chart">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2 text-white">
              <BarChart3 className="w-5 h-5 text-cyan-400" />
              Weekly Occupancy Trend
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData}>
                  <defs>
                    <linearGradient id="colorOccupancy" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#06B6D4" stopOpacity={0.4}/>
                      <stop offset="100%" stopColor="#06B6D4" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                  <XAxis dataKey="day" stroke="#64748B" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#64748B" fontSize={12} tickFormatter={(v) => `${v}%`} tickLine={false} axisLine={false} />
                  <Tooltip 
                    contentStyle={{ 
                      background: 'rgba(15, 23, 42, 0.9)', 
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '12px',
                      boxShadow: '0 20px 40px rgba(0,0,0,0.4)'
                    }}
                    formatter={(value) => [`${value.toFixed(1)}%`, 'Occupancy']}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="occupancy" 
                    stroke="#06B6D4" 
                    strokeWidth={2}
                    fillOpacity={1} 
                    fill="url(#colorOccupancy)" 
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Optimization Potential */}
        <Card className="glass glow-primary border-white/5 animate-fade-in stagger-6" data-testid="optimization-potential">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2 text-white">
              <Leaf className="w-5 h-5 text-emerald-400" />
              Optimization Potential
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="text-center py-6 rounded-xl bg-gradient-to-br from-emerald-500/10 to-cyan-500/10 border border-emerald-500/20">
              <p className="text-sm text-slate-400 uppercase tracking-wider mb-2">Monthly Savings</p>
              <p className="text-4xl font-bold gradient-text font-mono">
                {formatCurrency(optimization.potential_monthly_savings)}
              </p>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02]">
                <span className="text-sm text-slate-400">Carbon Reduction</span>
                <span className="font-mono text-emerald-400 font-semibold">
                  {formatNumber(optimization.potential_carbon_reduction_kg)} kg
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02]">
                <span className="text-sm text-slate-400">Confidence Score</span>
                <span className="font-mono text-cyan-400 font-semibold">
                  {formatPercent(optimization.optimization_confidence)}
                </span>
              </div>
            </div>

            <Button 
              onClick={() => navigate('/simulator')}
              className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/20 btn-glow"
              data-testid="run-simulation-btn"
            >
              Run Optimization Simulation
              <ChevronRight className="w-4 h-4 ml-2" />
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Property Overview */}
      <Card className="glass border-white/5 animate-fade-in" data-testid="property-overview">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2 text-white">
              <Building2 className="w-5 h-5 text-cyan-400" />
              Property Overview
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={() => navigate('/portfolio')} className="text-slate-400 hover:text-white">
              View All
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {properties.slice(0, 3).map((prop, idx) => (
              <div 
                key={prop.property_id}
                className="flex items-center justify-between p-5 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/5 hover:border-cyan-500/20 cursor-pointer transition-all group"
                onClick={() => navigate(`/property/${prop.property_id}`)}
                data-testid={`property-card-${prop.property_id}`}
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 flex items-center justify-center text-lg font-bold text-cyan-400 border border-cyan-500/20 group-hover:border-cyan-500/40 transition-colors">
                    {idx + 1}
                  </div>
                  <div>
                    <h4 className="font-semibold text-white group-hover:text-cyan-400 transition-colors">{prop.name}</h4>
                    <p className="text-sm text-slate-500">{prop.location}</p>
                  </div>
                </div>
                <div className="flex items-center gap-8">
                  <div className="text-right">
                    <p className="text-xs text-slate-500 uppercase tracking-wider">Occupancy</p>
                    <p className={`font-mono font-semibold ${getUtilizationColor(prop.utilization_status)}`}>
                      {formatPercent(prop.current_occupancy)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-500 uppercase tracking-wider">Profit</p>
                    <p className="font-mono font-semibold text-emerald-400">
                      {formatCurrency(prop.current_profit)}
                    </p>
                  </div>
                  <Badge className={`${getUtilizationBadge(prop.utilization_status)} border`}>
                    {prop.utilization_status}
                  </Badge>
                  <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-cyan-400 group-hover:translate-x-1 transition-all" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
