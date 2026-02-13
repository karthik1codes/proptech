import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Building2, Zap, TrendingUp, TrendingDown, Leaf, 
  AlertTriangle, Target, RefreshCw, ChevronRight, Save, RotateCcw, Clock
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Slider } from '../components/ui/slider';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { API } from '../App';
import { formatCurrency, formatPercent, formatNumber } from '../utils/formatters';
import { toast } from 'sonner';
import { usePropertyState } from '../context/PropertyStateContext';

export default function ScenarioSimulator() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  // Use global state context
  const { 
    properties, 
    getClosedFloors, 
    closeFloors, 
    openFloors, 
    resetProperty,
    lastUpdate 
  } = usePropertyState();
  
  const [selectedProperty, setSelectedProperty] = useState(null);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [simulation, setSimulation] = useState(null);

  // Simulation parameters - these track the UI state
  const [floorsToClose, setFloorsToClose] = useState([]);
  const [hybridIntensity, setHybridIntensity] = useState(1.0);
  const [targetOccupancy, setTargetOccupancy] = useState(null);
  const [useCustomOccupancy, setUseCustomOccupancy] = useState(false);
  
  // Track if we have unsaved changes
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  useEffect(() => {
    if (properties.length > 0) {
      setLoading(false);
      const propId = searchParams.get('property');
      if (propId) {
        const prop = properties.find(p => p.property_id === propId);
        if (prop) {
          selectProperty(prop);
        }
      } else if (!selectedProperty) {
        selectProperty(properties[0]);
      }
    }
  }, [properties, searchParams]);

  // When property changes, sync with global state
  useEffect(() => {
    if (selectedProperty) {
      const savedClosedFloors = getClosedFloors(selectedProperty.property_id);
      setFloorsToClose(savedClosedFloors);
      // Auto-run simulation if there are closed floors
      if (savedClosedFloors.length > 0) {
        runSimulationWithFloors(savedClosedFloors);
      }
    }
  }, [selectedProperty?.property_id, lastUpdate]);

  const selectProperty = (prop) => {
    setSelectedProperty(prop);
    const savedClosedFloors = getClosedFloors(prop.property_id);
    setFloorsToClose(savedClosedFloors);
    setSimulation(null);
    setHasUnsavedChanges(false);
    
    // Auto-run simulation if floors were previously closed
    if (savedClosedFloors.length > 0) {
      runSimulationWithFloors(savedClosedFloors, prop);
    }
  };

  const runSimulationWithFloors = async (floors, prop = selectedProperty) => {
    if (!prop) return;
    
    setSimulating(true);
    try {
      const response = await axios.post(`${API}/analytics/simulate-floor-closure`, {
        property_id: prop.property_id,
        floors_to_close: floors,
        hybrid_intensity: hybridIntensity,
        target_occupancy: useCustomOccupancy ? targetOccupancy : null,
      }, { withCredentials: true });
      
      setSimulation(response.data);
    } catch (error) {
      console.error('Error running simulation:', error);
    } finally {
      setSimulating(false);
    }
  };

  const runSimulation = async () => {
    if (!selectedProperty) return;
    
    setSimulating(true);
    try {
      const response = await axios.post(`${API}/analytics/simulate-floor-closure`, {
        property_id: selectedProperty.property_id,
        floors_to_close: floorsToClose,
        hybrid_intensity: hybridIntensity,
        target_occupancy: useCustomOccupancy ? targetOccupancy : null,
      }, { withCredentials: true });
      
      setSimulation(response.data);
      
      // Check if current selection differs from saved state
      const savedFloors = getClosedFloors(selectedProperty.property_id);
      const currentSet = new Set(floorsToClose);
      const savedSet = new Set(savedFloors);
      const isDifferent = floorsToClose.length !== savedFloors.length || 
                         !floorsToClose.every(f => savedSet.has(f));
      
      setHasUnsavedChanges(isDifferent);
      
      if (isDifferent) {
        toast.success('Simulation complete! Click "Apply Changes Globally" to save.');
      } else {
        toast.success('Simulation complete - matches current saved state.');
      }
    } catch (error) {
      console.error('Error running simulation:', error);
      toast.error('Failed to run simulation');
    } finally {
      setSimulating(false);
    }
  };

  const toggleFloor = (floorNum) => {
    const newFloors = floorsToClose.includes(floorNum)
      ? floorsToClose.filter(f => f !== floorNum)
      : [...floorsToClose, floorNum];
    
    setFloorsToClose(newFloors);
    setHasUnsavedChanges(true);
  };

  // Apply changes - saves to global state and backend
  const applyChanges = async () => {
    if (!selectedProperty) return;
    
    setSaving(true);
    try {
      const currentSavedFloors = getClosedFloors(selectedProperty.property_id);
      
      // Check if anything actually changed
      const currentSet = new Set(currentSavedFloors);
      const newSet = new Set(floorsToClose);
      const hasChanges = currentSavedFloors.length !== floorsToClose.length || 
                        !currentSavedFloors.every(f => newSet.has(f));
      
      if (!hasChanges) {
        toast.info('No changes to apply');
        setSaving(false);
        return;
      }
      
      // Determine floors to close and open
      const floorsToCloseNew = floorsToClose.filter(f => !currentSet.has(f));
      const floorsToOpenList = currentSavedFloors.filter(f => !newSet.has(f));
      
      let success = true;
      
      // Close new floors
      if (floorsToCloseNew.length > 0) {
        const result = await closeFloors(selectedProperty.property_id, floorsToCloseNew);
        if (!result?.success) success = false;
      }
      
      // Open removed floors
      if (floorsToOpenList.length > 0) {
        const result = await openFloors(selectedProperty.property_id, floorsToOpenList);
        if (!result?.success) success = false;
      }
      
      if (success) {
        setHasUnsavedChanges(false);
        toast.success('Changes applied! Dashboard and other pages will now reflect these optimizations.');
      } else {
        toast.error('Some changes may not have been applied. Please refresh and try again.');
      }
    } catch (error) {
      console.error('Error applying changes:', error);
      toast.error('Failed to apply changes');
    } finally {
      setSaving(false);
    }
  };

  // Reset to default
  const handleReset = async () => {
    if (!selectedProperty) return;
    
    setSaving(true);
    try {
      await resetProperty(selectedProperty.property_id);
      setFloorsToClose([]);
      setSimulation(null);
      setHasUnsavedChanges(false);
    } catch (error) {
      console.error('Error resetting:', error);
      toast.error('Failed to reset');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6" data-testid="simulator-loading">
        <div className="h-12 shimmer rounded w-64"></div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="h-96 shimmer rounded-xl"></div>
          <div className="lg:col-span-2 h-96 shimmer rounded-xl"></div>
        </div>
      </div>
    );
  }

  const savedClosedFloors = selectedProperty ? getClosedFloors(selectedProperty.property_id) : [];
  const hasActiveOptimizations = savedClosedFloors.length > 0;

  return (
    <div className="space-y-6" data-testid="scenario-simulator">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Target className="w-8 h-8 text-blue-400" />
            What-If Scenario Simulator
          </h1>
          <p className="text-muted-foreground mt-1">
            Simulate floor closures and optimize your property operations
          </p>
        </div>
        
        {/* Active Optimizations Indicator */}
        {hasActiveOptimizations && (
          <div className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
            <span className="text-sm text-emerald-400">
              <strong>{savedClosedFloors.length}</strong> floor(s) actively closed
            </span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Controls Panel */}
        <Card className="glass" data-testid="simulator-controls">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg">Simulation Parameters</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Property Selection */}
            <div className="space-y-2">
              <Label>Select Property</Label>
              <Select 
                value={selectedProperty?.property_id || ''}
                onValueChange={(v) => {
                  const prop = properties.find(p => p.property_id === v);
                  selectProperty(prop);
                }}
              >
                <SelectTrigger data-testid="property-select">
                  <SelectValue placeholder="Select a property" />
                </SelectTrigger>
                <SelectContent>
                  {properties.map(prop => (
                    <SelectItem key={prop.property_id} value={prop.property_id}>
                      {prop.name}
                      {getClosedFloors(prop.property_id).length > 0 && (
                        <Badge className="ml-2 bg-emerald-500/20 text-emerald-400 text-xs">
                          {getClosedFloors(prop.property_id).length} optimized
                        </Badge>
                      )}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {selectedProperty && (
              <>
                {/* Floor Selection */}
                <div className="space-y-3">
                  <Label>Select Floors to Close</Label>
                  <div className="grid grid-cols-4 gap-2">
                    {Array.from({ length: selectedProperty.floors }, (_, i) => i + 1).map(floorNum => {
                      const isSelected = floorsToClose.includes(floorNum);
                      const wasSaved = savedClosedFloors.includes(floorNum);
                      
                      return (
                        <button
                          key={floorNum}
                          onClick={() => toggleFloor(floorNum)}
                          className={`h-10 rounded-lg font-mono text-sm font-medium transition-all relative ${
                            isSelected
                              ? 'bg-red-500/20 border-2 border-red-500 text-red-400'
                              : 'bg-zinc-800 border border-border hover:border-blue-500/50'
                          }`}
                          data-testid={`floor-toggle-${floorNum}`}
                        >
                          F{floorNum}
                          {wasSaved && !isSelected && (
                            <span className="absolute -top-1 -right-1 w-2 h-2 bg-amber-400 rounded-full" title="Previously closed" />
                          )}
                        </button>
                      );
                    })}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {floorsToClose.length} floor(s) selected for closure
                    {hasUnsavedChanges && (
                      <span className="text-amber-400 ml-2">(unsaved changes)</span>
                    )}
                  </p>
                </div>

                {/* Hybrid Intensity */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label>Hybrid Work Intensity</Label>
                    <span className="text-sm font-mono">{(hybridIntensity * 100).toFixed(0)}%</span>
                  </div>
                  <Slider
                    value={[hybridIntensity * 100]}
                    onValueChange={([v]) => setHybridIntensity(v / 100)}
                    min={10}
                    max={150}
                    step={5}
                    data-testid="hybrid-slider"
                  />
                  <p className="text-xs text-muted-foreground">
                    Adjust to simulate different hybrid work adoption levels
                  </p>
                </div>

                {/* Custom Occupancy */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label>Custom Target Occupancy</Label>
                    <Switch 
                      checked={useCustomOccupancy}
                      onCheckedChange={setUseCustomOccupancy}
                      data-testid="custom-occupancy-toggle"
                    />
                  </div>
                  {useCustomOccupancy && (
                    <>
                      <Slider
                        value={[targetOccupancy ? targetOccupancy * 100 : 60]}
                        onValueChange={([v]) => setTargetOccupancy(v / 100)}
                        min={10}
                        max={100}
                        step={5}
                        data-testid="occupancy-slider"
                      />
                      <p className="text-sm font-mono text-center">
                        {(targetOccupancy ? targetOccupancy * 100 : 60).toFixed(0)}% Target
                      </p>
                    </>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="space-y-3">
                  {/* Run Simulation */}
                  <Button 
                    onClick={runSimulation}
                    disabled={simulating}
                    className="w-full bg-blue-600 hover:bg-blue-500 glow-blue"
                    data-testid="run-simulation-btn"
                  >
                    {simulating ? (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                        Simulating...
                      </>
                    ) : (
                      <>
                        <Target className="w-4 h-4 mr-2" />
                        Run Simulation
                      </>
                    )}
                  </Button>
                  
                  {/* Apply Changes - Save to Global State */}
                  {simulation && (
                    <Button 
                      onClick={applyChanges}
                      disabled={saving || !hasUnsavedChanges}
                      className="w-full bg-emerald-600 hover:bg-emerald-500"
                      data-testid="apply-changes-btn"
                    >
                      {saving ? (
                        <>
                          <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        <>
                          <Save className="w-4 h-4 mr-2" />
                          Apply Changes Globally
                        </>
                      )}
                    </Button>
                  )}
                  
                  {/* Reset */}
                  {hasActiveOptimizations && (
                    <Button 
                      onClick={handleReset}
                      disabled={saving}
                      variant="outline"
                      className="w-full border-red-500/30 text-red-400 hover:bg-red-500/10"
                      data-testid="reset-btn"
                    >
                      <RotateCcw className="w-4 h-4 mr-2" />
                      Reset to Default
                    </Button>
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Results Panel */}
        <div className="lg:col-span-2 space-y-6">
          {simulation ? (
            <>
              {/* Savings Summary */}
              <Card className="glass glow-blue" data-testid="savings-summary">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <TrendingUp className="w-5 h-5 text-emerald-400" />
                      Projected Savings
                    </CardTitle>
                    {hasActiveOptimizations && (
                      <Badge className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                        <Clock className="w-3 h-3 mr-1" />
                        Active
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                      <p className="text-xs text-muted-foreground uppercase mb-1">Weekly Savings</p>
                      <p className="text-2xl font-bold font-mono text-emerald-400">
                        {formatCurrency(simulation.savings.total_weekly_savings)}
                      </p>
                    </div>
                    <div className="text-center p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                      <p className="text-xs text-muted-foreground uppercase mb-1">Monthly Savings</p>
                      <p className="text-2xl font-bold font-mono text-emerald-400">
                        {formatCurrency(simulation.savings.total_monthly_savings)}
                      </p>
                    </div>
                    <div className="text-center p-4 rounded-xl bg-cyan-500/10 border border-cyan-500/20">
                      <p className="text-xs text-muted-foreground uppercase mb-1">Energy Reduction</p>
                      <p className="text-2xl font-bold font-mono text-cyan-400">
                        {simulation.energy_impact.energy_reduction_percent}%
                      </p>
                    </div>
                    <div className="text-center p-4 rounded-xl bg-green-500/10 border border-green-500/20">
                      <p className="text-xs text-muted-foreground uppercase mb-1">Carbon Reduction</p>
                      <p className="text-2xl font-bold font-mono text-green-400">
                        {formatNumber(simulation.carbon_impact.monthly_carbon_reduction_kg)} kg
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Before vs After Comparison */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Current State */}
                <Card className="glass" data-testid="current-state">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Building2 className="w-5 h-5 text-muted-foreground" />
                      Current State
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">Occupancy</span>
                      <span className="font-mono font-semibold">{formatPercent(simulation.current_state.occupancy_rate)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">Efficiency Score</span>
                      <span className="font-mono font-semibold">{simulation.current_state.efficiency_score}%</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">Daily Revenue</span>
                      <span className="font-mono font-semibold">{formatCurrency(simulation.current_state.revenue)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">Energy Cost</span>
                      <span className="font-mono text-amber-400">{formatCurrency(simulation.energy_impact.before_cost_daily)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">Daily Profit</span>
                      <span className="font-mono">{formatCurrency(simulation.current_state.profit)}</span>
                    </div>
                  </CardContent>
                </Card>

                {/* Projected State */}
                <Card className="glass border-blue-500/30" data-testid="projected-state">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <TrendingUp className="w-5 h-5 text-blue-400" />
                      After Optimization
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">Occupancy</span>
                      <span className="font-mono font-semibold">{formatPercent(simulation.projected_state.occupancy_rate)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">Efficiency Score</span>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-emerald-400">{simulation.projected_state.efficiency_score}%</span>
                        {simulation.efficiency_score_change.improvement > 0 && (
                          <Badge className="bg-emerald-500/10 text-emerald-400 text-xs">
                            +{simulation.efficiency_score_change.improvement}%
                          </Badge>
                        )}
                      </div>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">Daily Revenue</span>
                      <span className="font-mono font-semibold">{formatCurrency(simulation.projected_state.revenue)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">Energy Cost</span>
                      <span className="font-mono text-emerald-400">{formatCurrency(simulation.energy_impact.after_cost_daily)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">Daily Profit</span>
                      <span className="font-mono text-emerald-400">{formatCurrency(simulation.projected_state.profit)}</span>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Risk Assessment */}
              <Card className="glass" data-testid="risk-assessment">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-amber-400" />
                    Risk Assessment
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-4 rounded-xl bg-zinc-900/50">
                      <p className="text-sm text-muted-foreground mb-1">Overload Risk</p>
                      <Badge className={
                        simulation.risk_assessment.overload_risk === 'Low' 
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : simulation.risk_assessment.overload_risk === 'Medium'
                          ? 'bg-amber-500/10 text-amber-400'
                          : 'bg-red-500/10 text-red-400'
                      }>
                        {simulation.risk_assessment.overload_risk}
                      </Badge>
                    </div>
                    <div className="p-4 rounded-xl bg-zinc-900/50">
                      <p className="text-sm text-muted-foreground mb-1">Redistribution Efficiency</p>
                      <Badge className={
                        simulation.risk_assessment.redistribution_efficiency === 'Good'
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : 'bg-amber-500/10 text-amber-400'
                      }>
                        {simulation.risk_assessment.redistribution_efficiency}
                      </Badge>
                    </div>
                    <div className="p-4 rounded-xl bg-zinc-900/50">
                      <p className="text-sm text-muted-foreground mb-1">Active Floors</p>
                      <span className="font-mono text-lg font-semibold">
                        {simulation.scenario_summary.active_floors} / {selectedProperty?.floors}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card className="glass h-full flex items-center justify-center" data-testid="no-simulation">
              <CardContent className="text-center py-12">
                <Target className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">Configure Your Scenario</h3>
                <p className="text-muted-foreground max-w-md">
                  Select floors to close, adjust hybrid work intensity, and run the simulation to see projected savings.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
