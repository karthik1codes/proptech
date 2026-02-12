import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Building2, TrendingUp, Zap, DollarSign, Users, 
  ArrowUpRight, ArrowDownRight, AlertTriangle, Leaf,
  BarChart3, ChevronRight
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { API, AuthContext } from '../App';
import { formatCurrency, formatNumber, formatPercent } from '../utils/formatters';
import AnimatedCounter from '../components/AnimatedCounter';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';

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
      <div className="space-y-6" data-testid="dashboard-loading">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="glass">
              <CardContent className="p-6">
                <div className="h-24 shimmer rounded"></div>
              </CardContent>
            </Card>
          ))}
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
      case 'Optimal': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'Underutilized': return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'Overloaded': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      default: return '';
    }
  };

  return (
    <div className="space-y-6" data-testid="dashboard">
      {/* Welcome Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Welcome back, {user?.name?.split(' ')[0] || 'User'}
          </h1>
          <p className="text-muted-foreground mt-1">
            Here's your property portfolio overview
          </p>
        </div>
        <Button 
          onClick={() => navigate('/portfolio')}
          className="bg-blue-600 hover:bg-blue-500 glow-blue"
          data-testid="view-portfolio-btn"
        >
          <Building2 className="w-4 h-4 mr-2" />
          View All Properties
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="glass card-hover metric-card" data-testid="kpi-revenue">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center">
                <DollarSign className="w-6 h-6 text-blue-400" />
              </div>
              <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                <ArrowUpRight className="w-3 h-3 mr-1" />
                12.5%
              </Badge>
            </div>
            <div className="mt-4">
              <p className="text-sm text-muted-foreground font-medium uppercase tracking-wide">Total Revenue</p>
              <p className="text-3xl font-bold font-mono mt-1">
                <AnimatedCounter value={kpis.total_revenue} formatter={formatCurrency} />
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="glass card-hover metric-card" data-testid="kpi-profit">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-emerald-400" />
              </div>
              <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                <ArrowUpRight className="w-3 h-3 mr-1" />
                8.2%
              </Badge>
            </div>
            <div className="mt-4">
              <p className="text-sm text-muted-foreground font-medium uppercase tracking-wide">Net Profit</p>
              <p className="text-3xl font-bold font-mono mt-1">
                <AnimatedCounter value={kpis.total_profit} formatter={formatCurrency} />
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="glass card-hover metric-card" data-testid="kpi-occupancy">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="w-12 h-12 rounded-xl bg-amber-500/10 flex items-center justify-center">
                <Users className="w-6 h-6 text-amber-400" />
              </div>
              <span className="text-xs text-muted-foreground">
                {formatNumber(kpis.total_occupied)} / {formatNumber(kpis.total_capacity)}
              </span>
            </div>
            <div className="mt-4">
              <p className="text-sm text-muted-foreground font-medium uppercase tracking-wide">Occupancy Rate</p>
              <p className="text-3xl font-bold font-mono mt-1">
                <AnimatedCounter value={kpis.overall_occupancy * 100} suffix="%" decimals={1} />
              </p>
            </div>
            <Progress value={kpis.overall_occupancy * 100} className="mt-3 h-2" />
          </CardContent>
        </Card>

        <Card className="glass card-hover metric-card" data-testid="kpi-energy">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="w-12 h-12 rounded-xl bg-cyan-500/10 flex items-center justify-center">
                <Zap className="w-6 h-6 text-cyan-400" />
              </div>
              <Badge variant="outline" className="bg-red-500/10 text-red-400 border-red-500/20">
                <ArrowDownRight className="w-3 h-3 mr-1" />
                -5.3%
              </Badge>
            </div>
            <div className="mt-4">
              <p className="text-sm text-muted-foreground font-medium uppercase tracking-wide">Energy Cost</p>
              <p className="text-3xl font-bold font-mono mt-1">
                <AnimatedCounter value={kpis.total_energy_cost} formatter={formatCurrency} />
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Occupancy Trend Chart */}
        <Card className="glass lg:col-span-2" data-testid="occupancy-chart">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-blue-400" />
              Weekly Occupancy Trend
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData}>
                  <defs>
                    <linearGradient id="colorOccupancy" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="day" stroke="#64748B" fontSize={12} />
                  <YAxis stroke="#64748B" fontSize={12} tickFormatter={(v) => `${v}%`} />
                  <Tooltip 
                    contentStyle={{ 
                      background: 'hsl(var(--card))', 
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px'
                    }}
                    formatter={(value) => [`${value.toFixed(1)}%`, 'Occupancy']}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="occupancy" 
                    stroke="#3B82F6" 
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
        <Card className="glass glow-blue" data-testid="optimization-potential">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Leaf className="w-5 h-5 text-emerald-400" />
              Optimization Potential
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="text-center py-4">
              <p className="text-sm text-muted-foreground uppercase tracking-wide mb-2">Potential Monthly Savings</p>
              <p className="text-4xl font-bold gradient-text font-mono">
                {formatCurrency(optimization.potential_monthly_savings)}
              </p>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Carbon Reduction</span>
                <span className="font-mono text-sm">
                  {formatNumber(optimization.potential_carbon_reduction_kg)} kg
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Confidence Score</span>
                <span className="font-mono text-sm text-emerald-400">
                  {formatPercent(optimization.optimization_confidence)}
                </span>
              </div>
            </div>

            <Button 
              onClick={() => navigate('/simulator')}
              className="w-full bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400"
              data-testid="run-simulation-btn"
            >
              Run Optimization Simulation
              <ChevronRight className="w-4 h-4 ml-2" />
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Property Overview */}
      <Card className="glass" data-testid="property-overview">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Building2 className="w-5 h-5 text-blue-400" />
              Property Overview
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={() => navigate('/portfolio')}>
              View All
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {properties.slice(0, 3).map((prop, idx) => (
              <div 
                key={prop.property_id}
                className="flex items-center justify-between p-4 rounded-xl bg-zinc-900/50 hover:bg-zinc-800/50 cursor-pointer transition-colors"
                onClick={() => navigate(`/property/${prop.property_id}`)}
                data-testid={`property-card-${prop.property_id}`}
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center text-lg font-bold text-blue-400">
                    {idx + 1}
                  </div>
                  <div>
                    <h4 className="font-semibold">{prop.name}</h4>
                    <p className="text-sm text-muted-foreground">{prop.location}</p>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <p className="text-sm text-muted-foreground">Occupancy</p>
                    <p className={`font-mono font-semibold ${getUtilizationColor(prop.utilization_status)}`}>
                      {formatPercent(prop.current_occupancy)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-muted-foreground">Profit</p>
                    <p className="font-mono font-semibold text-emerald-400">
                      {formatCurrency(prop.current_profit)}
                    </p>
                  </div>
                  <Badge className={getUtilizationBadge(prop.utilization_status)}>
                    {prop.utilization_status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
