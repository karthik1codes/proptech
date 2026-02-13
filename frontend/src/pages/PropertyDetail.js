import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Building2, ArrowLeft, Zap, Users, TrendingUp, 
  DollarSign, Leaf, BarChart3, Lightbulb, Target,
  ChevronRight, AlertTriangle, Activity, Lock
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { API } from '../App';
import { formatCurrency, formatPercent, formatNumber } from '../utils/formatters';
import FloorPlanVisualization from '../components/FloorPlanVisualization';
import EnergySavingsChart from '../components/EnergySavingsChart';
import { usePropertyState } from '../context/PropertyStateContext';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { toast } from 'sonner';

export default function PropertyDetail() {
  const { propertyId } = useParams();
  const navigate = useNavigate();
  const [property, setProperty] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [copilotInsight, setCopilotInsight] = useState(null);
  const [energySavings, setEnergySavings] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPropertyData();
  }, [propertyId]);

  const fetchPropertyData = async () => {
    try {
      const [propRes, recsRes, insightRes, energyRes] = await Promise.all([
        axios.get(`${API}/properties/${propertyId}`, { withCredentials: true }),
        axios.get(`${API}/recommendations/${propertyId}`, { withCredentials: true }),
        axios.get(`${API}/copilot/${propertyId}`, { withCredentials: true }),
        axios.get(`${API}/analytics/energy-savings/${propertyId}`, { withCredentials: true }),
      ]);
      
      setProperty(propRes.data);
      setRecommendations(recsRes.data);
      setCopilotInsight(insightRes.data);
      setEnergySavings(energyRes.data);
    } catch (error) {
      console.error('Error fetching property:', error);
      toast.error('Failed to load property details');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6" data-testid="property-detail-loading">
        <div className="h-12 shimmer rounded w-64"></div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 h-96 shimmer rounded-xl"></div>
          <div className="h-96 shimmer rounded-xl"></div>
        </div>
      </div>
    );
  }

  if (!property) {
    return (
      <div className="text-center py-12">
        <Building2 className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
        <h3 className="text-lg font-semibold">Property not found</h3>
        <Button onClick={() => navigate('/portfolio')} className="mt-4">
          Back to Portfolio
        </Button>
      </div>
    );
  }

  const getUtilizationBadge = (status) => {
    switch (status) {
      case 'Optimal': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'Underutilized': return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'Overloaded': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      default: return '';
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'High': return 'text-red-400';
      case 'Medium': return 'text-amber-400';
      case 'Low': return 'text-emerald-400';
      default: return 'text-muted-foreground';
    }
  };

  // Prepare chart data from digital twin history
  const historyData = property.digital_twin?.daily_history?.slice(-30).map(d => ({
    date: d.date.split('-').slice(1).join('/'),
    occupancy: d.occupancy_rate * 100,
    energy: d.energy_usage,
  })) || [];

  const forecastData = property.forecast?.map(f => ({
    date: f.date.split('-').slice(1).join('/'),
    forecast: f.forecasted_occupancy * 100,
    confidence: f.confidence * 100,
  })) || [];

  return (
    <div className="space-y-6" data-testid="property-detail">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button 
            variant="ghost" 
            size="icon"
            onClick={() => navigate('/portfolio')}
            data-testid="back-btn"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight">{property.name}</h1>
              <Badge className={getUtilizationBadge(property.utilization_status)}>
                {property.utilization_status}
              </Badge>
            </div>
            <p className="text-muted-foreground mt-1">{property.location} • {property.type}</p>
          </div>
        </div>
        
        <div className="flex gap-3">
          <Button 
            variant="outline"
            onClick={() => navigate(`/simulator?property=${propertyId}`)}
            data-testid="run-simulation-btn"
          >
            <Target className="w-4 h-4 mr-2" />
            Run Simulation
          </Button>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="glass" data-testid="kpi-efficiency">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <Target className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase">Efficiency Score</p>
                <p className="text-2xl font-bold font-mono">{property.efficiency_score}%</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="glass" data-testid="kpi-occupancy">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center">
                <Users className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase">Occupancy</p>
                <p className="text-2xl font-bold font-mono">{formatPercent(property.current_occupancy)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="glass" data-testid="kpi-profit">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase">Daily Profit</p>
                <p className="text-2xl font-bold font-mono text-emerald-400">{formatCurrency(property.financials?.profit)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="glass" data-testid="kpi-energy">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-cyan-500/10 flex items-center justify-center">
                <Zap className="w-5 h-5 text-cyan-400" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase">Energy Cost</p>
                <p className="text-2xl font-bold font-mono">{formatCurrency(property.financials?.energy_cost)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="glass">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="floorplan">Floor Plan</TabsTrigger>
          <TabsTrigger value="energy">Energy Analysis</TabsTrigger>
          <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Occupancy Trend */}
            <Card className="glass lg:col-span-2" data-testid="occupancy-trend">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-blue-400" />
                  30-Day Occupancy Trend
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={historyData}>
                      <defs>
                        <linearGradient id="colorOcc" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="date" stroke="#64748B" fontSize={10} interval={4} />
                      <YAxis stroke="#64748B" fontSize={10} tickFormatter={(v) => `${v}%`} />
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
                        fill="url(#colorOcc)" 
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Copilot Insight */}
            <Card className="glass glow-blue" data-testid="copilot-insight">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Lightbulb className="w-5 h-5 text-amber-400" />
                  AI Copilot Insight
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm leading-relaxed">{copilotInsight?.insight_summary}</p>
                
                <div className="space-y-3 pt-4 border-t border-border">
                  <div>
                    <p className="text-xs text-muted-foreground uppercase">Root Cause</p>
                    <p className="text-sm mt-1">{copilotInsight?.root_cause}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground uppercase">Recommended Action</p>
                    <p className="text-sm mt-1 text-blue-400">{copilotInsight?.recommended_action}</p>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Monthly Savings Potential</span>
                    <span className="font-mono text-emerald-400 font-semibold">
                      {formatCurrency(copilotInsight?.monthly_savings)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Confidence</span>
                    <span className="font-mono">
                      {formatPercent(copilotInsight?.confidence_score)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 7-Day Forecast */}
          <Card className="glass" data-testid="forecast">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-cyan-400" />
                7-Day Occupancy Forecast
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={forecastData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="date" stroke="#64748B" fontSize={12} />
                    <YAxis stroke="#64748B" fontSize={12} tickFormatter={(v) => `${v}%`} />
                    <Tooltip 
                      contentStyle={{ 
                        background: 'hsl(var(--card))', 
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                      }}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="forecast" 
                      stroke="#22D3EE" 
                      strokeWidth={2}
                      strokeDasharray="5 5"
                      dot={{ fill: '#22D3EE', strokeWidth: 2 }}
                      name="Forecast"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="floorplan">
          <Card className="glass" data-testid="floorplan-tab">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <Building2 className="w-5 h-5 text-blue-400" />
                Interactive Floor Plan
              </CardTitle>
            </CardHeader>
            <CardContent>
              <FloorPlanVisualization 
                floorData={property.digital_twin?.floor_data || []}
                floors={property.floors}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="energy">
          <div className="space-y-6">
            <EnergySavingsChart energyData={energySavings} />
            
            {/* Energy Scenarios */}
            <Card className="glass" data-testid="energy-scenarios">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Zap className="w-5 h-5 text-cyan-400" />
                  Energy Optimization Scenarios
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {energySavings?.scenarios?.map((scenario, idx) => (
                    <div 
                      key={idx}
                      className={`p-4 rounded-xl border ${idx === 0 ? 'bg-zinc-900/50 border-border' : 'bg-blue-500/5 border-blue-500/20'}`}
                    >
                      <p className="font-semibold mb-3">{scenario.scenario}</p>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Energy Usage</span>
                          <span className="font-mono">{formatNumber(scenario.after_energy_usage)} kWh</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Daily Cost</span>
                          <span className="font-mono">{formatCurrency(scenario.after_cost_daily)}</span>
                        </div>
                        {scenario.floors_closed > 0 && (
                          <>
                            <div className="flex justify-between text-emerald-400">
                              <span>Weekly Savings</span>
                              <span className="font-mono">{formatCurrency(scenario.weekly_savings)}</span>
                            </div>
                            <div className="flex justify-between text-emerald-400">
                              <span>Monthly Savings</span>
                              <span className="font-mono">{formatCurrency(scenario.monthly_savings)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Reduction</span>
                              <span className="font-mono text-cyan-400">-{scenario.energy_reduction_percent}%</span>
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="recommendations">
          <Card className="glass" data-testid="recommendations-tab">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <Lightbulb className="w-5 h-5 text-amber-400" />
                AI Recommendations
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recommendations.map((rec) => (
                  <div 
                    key={rec.id}
                    className="p-4 rounded-xl bg-zinc-900/50 border border-border hover:border-blue-500/30 transition-colors"
                    data-testid={`recommendation-${rec.id}`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant="outline">{rec.type}</Badge>
                          <span className={`text-sm font-medium ${getPriorityColor(rec.priority)}`}>
                            {rec.priority} Priority
                          </span>
                        </div>
                        <h4 className="font-semibold mb-1">{rec.title}</h4>
                        <p className="text-sm text-muted-foreground">{rec.description}</p>
                        
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 pt-4 border-t border-border">
                          <div>
                            <p className="text-xs text-muted-foreground">Monthly Impact</p>
                            <p className="font-mono text-emerald-400">{formatCurrency(rec.financial_impact)}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Weekly Energy Savings</p>
                            <p className="font-mono text-cyan-400">{formatCurrency(rec.weekly_energy_savings)}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Energy Reduction</p>
                            <p className="font-mono">{rec.energy_reduction_percent.toFixed(1)}%</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Carbon Reduction</p>
                            <p className="font-mono">{formatNumber(rec.carbon_reduction_kg)} kg</p>
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">Confidence</p>
                        <p className="font-mono text-lg">{formatPercent(rec.confidence_score)}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
