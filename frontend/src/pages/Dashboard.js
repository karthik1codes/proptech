import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Building2, TrendingUp, Zap, DollarSign, Users, 
  ArrowUpRight, ArrowDownRight, Leaf,
  BarChart3, ChevronRight, Sparkles, Lock, Activity,
  AlertTriangle, Shield, MapPin
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { API, AuthContext } from '../App';
import { formatCurrency, formatNumber, formatPercent } from '../utils/formatters';
import AnimatedCounter from '../components/AnimatedCounter';
import WhatsAppLinking from '../components/WhatsAppLinking';
import { usePropertyState } from '../context/PropertyStateContext';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function Dashboard() {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);
  
  // Use global state context
  const { 
    properties, 
    userStates, 
    getClosedFloors,
    lastUpdate,
    loading: stateLoading 
  } = usePropertyState();

  useEffect(() => {
    fetchDashboardData();
  }, [lastUpdate]); // Refetch when global state changes

  const fetchDashboardData = async () => {
    try {
      // Use the enhanced AI dashboard endpoint
      const response = await axios.get(`${API}/analytics/dashboard-with-ai`, { withCredentials: true });
      setDashboardData(response.data);
    } catch (error) {
      console.error('Error fetching dashboard:', error);
      // Fallback to regular dashboard
      try {
        const response = await axios.get(`${API}/analytics/dashboard`, { withCredentials: true });
        setDashboardData(response.data);
      } catch (fallbackError) {
        console.error('Fallback dashboard error:', fallbackError);
      }
    } finally {
      setLoading(false);
    }
  };

  // Get active optimizations from dashboard data
  const activeOptimizations = dashboardData?.active_optimizations?.details || [];
  const totalRealizedSavings = dashboardData?.active_optimizations?.realized_monthly_savings || 0;

  if (loading || stateLoading) {
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
  const propertyMetrics = dashboardData?.property_metrics || [];

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

  const getRiskBadge = (level) => {
    switch (level) {
      case 'HIGH': 
      case 'CRITICAL':
        return 'bg-red-500/10 text-red-400 border-red-500/30';
      case 'MEDIUM':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'LOW':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/30';
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

      {/* Active Optimizations Banner with Property Names */}
      {activeOptimizations.length > 0 && (
        <Card className="glass border-emerald-500/30 bg-gradient-to-r from-emerald-500/5 to-cyan-500/5 animate-fade-in" data-testid="active-optimizations-banner">
          <CardContent className="p-4">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                  <Activity className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <p className="font-semibold text-emerald-400">
                    {activeOptimizations.length} Active Optimization{activeOptimizations.length > 1 ? 's' : ''}
                  </p>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {activeOptimizations.map((opt, idx) => (
                      <Badge key={idx} className="bg-emerald-500/20 text-emerald-400 text-xs">
                        <Lock className="w-3 h-3 mr-1" />
                        {opt.property_name}: {opt.closed_floors.length} floor(s)
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-xs text-slate-500 uppercase">Est. Monthly Savings</p>
                <p className="text-xl font-bold font-mono text-emerald-400">
                  {formatCurrency(totalRealizedSavings)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

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

        {/* Carbon Card */}
        <Card className="glass card-hover metric-card border-white/5 animate-fade-in stagger-4" data-testid="kpi-carbon">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-green-500/20 to-green-600/10 flex items-center justify-center border border-green-500/20">
                <Leaf className="w-6 h-6 text-green-400" />
              </div>
              <Badge variant="outline" className="bg-red-500/10 text-red-400 border-red-500/30">
                <ArrowDownRight className="w-3 h-3 mr-1" />
                -5.3%
              </Badge>
            </div>
            <p className="text-sm text-slate-400 font-medium uppercase tracking-wider">Carbon Emissions</p>
            <p className="text-3xl font-bold text-white font-mono mt-1">
              <AnimatedCounter value={kpis.total_carbon_kg} suffix=" kg" decimals={0} />
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

        {/* WhatsApp Control */}
        <div className="animate-fade-in stagger-7">
          <WhatsAppLinking />
        </div>
      </div>

      {/* Property Risk Analysis Cards */}
      <Card className="glass border-white/5 animate-fade-in" data-testid="property-risk-analysis">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2 text-white">
              <Shield className="w-5 h-5 text-amber-400" />
              Property Risk Analysis
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={() => navigate('/portfolio')} className="text-slate-400 hover:text-white">
              View All
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {propertyMetrics.map((prop) => {
              const closedFloors = prop.closed_floors || [];
              const hasOptimization = closedFloors.length > 0;
              
              return (
                <div 
                  key={prop.property_id}
                  className="p-5 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/5 hover:border-cyan-500/20 cursor-pointer transition-all group"
                  onClick={() => navigate(`/property/${prop.property_id}`)}
                  data-testid={`property-risk-card-${prop.property_id}`}
                >
                  {/* Property Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h4 className="font-semibold text-white group-hover:text-cyan-400 transition-colors flex items-center gap-2">
                        {prop.name}
                        {hasOptimization && (
                          <span className="w-2 h-2 bg-emerald-400 rounded-full" />
                        )}
                      </h4>
                      <p className="text-xs text-slate-500 flex items-center gap-1 mt-1">
                        <MapPin className="w-3 h-3" />
                        {prop.location}
                      </p>
                    </div>
                    <Badge className={`${getRiskBadge(prop.risk_level)} border text-xs`}>
                      <AlertTriangle className="w-3 h-3 mr-1" />
                      {prop.risk_level}
                    </Badge>
                  </div>

                  {/* Risk Score & Metrics */}
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    <div className="p-2 rounded-lg bg-white/[0.02]">
                      <p className="text-xs text-slate-500">Risk Score</p>
                      <p className="text-lg font-mono font-bold text-amber-400">{prop.risk_score}</p>
                    </div>
                    <div className="p-2 rounded-lg bg-white/[0.02]">
                      <p className="text-xs text-slate-500">Efficiency</p>
                      <p className="text-lg font-mono font-bold text-cyan-400">{prop.efficiency?.toFixed(0)}%</p>
                    </div>
                  </div>

                  {/* Top Risks */}
                  <div className="space-y-2">
                    <p className="text-xs text-slate-500 uppercase">Top Risks</p>
                    {prop.top_risks?.slice(0, 2).map((risk, idx) => (
                      <div key={idx} className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">{risk.name}</span>
                        <Badge className={`${getRiskBadge(risk.level?.toUpperCase())} border text-[10px] py-0`}>
                          {risk.level}
                        </Badge>
                      </div>
                    ))}
                  </div>

                  {/* Carbon & Floor Info */}
                  <div className="mt-4 pt-4 border-t border-white/5 flex items-center justify-between text-xs">
                    <span className="text-slate-500">
                      CO₂: <span className="text-green-400 font-mono">{formatNumber(prop.carbon_kg)} kg</span>
                      <span className="text-slate-600 ml-1">({prop.carbon_factor} kg/kWh)</span>
                    </span>
                    {hasOptimization && (
                      <span className="text-emerald-400">
                        {prop.active_floors}/{prop.total_floors} floors
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Property Overview */}
      <Card className="glass border-white/5 animate-fade-in" data-testid="property-overview">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2 text-white">
              <Building2 className="w-5 h-5 text-cyan-400" />
              Property Performance
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={() => navigate('/portfolio')} className="text-slate-400 hover:text-white">
              View All
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {propertyMetrics.slice(0, 3).map((prop, idx) => {
              const closedFloors = prop.closed_floors || [];
              const hasOptimization = closedFloors.length > 0;
              
              return (
                <div 
                  key={prop.property_id}
                  className="flex items-center justify-between p-5 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/5 hover:border-cyan-500/20 cursor-pointer transition-all group"
                  onClick={() => navigate(`/property/${prop.property_id}`)}
                  data-testid={`property-card-${prop.property_id}`}
                >
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 flex items-center justify-center text-lg font-bold text-cyan-400 border border-cyan-500/20 group-hover:border-cyan-500/40 transition-colors relative">
                      {idx + 1}
                      {hasOptimization && (
                        <div className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-400 rounded-full border-2 border-zinc-900" />
                      )}
                    </div>
                    <div>
                      <h4 className="font-semibold text-white group-hover:text-cyan-400 transition-colors flex items-center gap-2">
                        {prop.name}
                        {hasOptimization && (
                          <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-xs">
                            <Lock className="w-3 h-3 mr-1" />
                            {closedFloors.length} closed
                          </Badge>
                        )}
                      </h4>
                      <p className="text-sm text-slate-500">{prop.location}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-8">
                    <div className="text-right">
                      <p className="text-xs text-slate-500 uppercase tracking-wider">Occupancy</p>
                      <p className={`font-mono font-semibold ${getUtilizationColor(prop.utilization)}`}>
                        {formatPercent(prop.occupancy)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-slate-500 uppercase tracking-wider">Profit</p>
                      <p className="font-mono font-semibold text-emerald-400">
                        {formatCurrency(prop.profit)}
                      </p>
                    </div>
                    <Badge className={`${getUtilizationBadge(prop.utilization)} border`}>
                      {prop.utilization}
                    </Badge>
                    <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-cyan-400 group-hover:translate-x-1 transition-all" />
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
