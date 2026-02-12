import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Building2, Plus, Search, Filter, TrendingUp, 
  Zap, Users, MapPin, ChevronRight, X
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { API } from '../App';
import { formatCurrency, formatPercent } from '../utils/formatters';
import { toast } from 'sonner';

export default function PropertyPortfolio() {
  const navigate = useNavigate();
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [newProperty, setNewProperty] = useState({
    name: '',
    type: 'Commercial Office',
    location: '',
    floors: 5,
    rooms_per_floor: 10,
    revenue_per_seat: 2500,
    energy_cost_per_unit: 8,
    maintenance_per_floor: 50000,
    baseline_energy_intensity: 150,
  });

  useEffect(() => {
    fetchProperties();
  }, []);

  const fetchProperties = async () => {
    try {
      const response = await axios.get(`${API}/properties`, { withCredentials: true });
      setProperties(response.data);
    } catch (error) {
      console.error('Error fetching properties:', error);
      toast.error('Failed to load properties');
    } finally {
      setLoading(false);
    }
  };

  const handleAddProperty = async () => {
    try {
      const response = await axios.post(`${API}/properties`, newProperty, { withCredentials: true });
      setProperties([...properties, response.data]);
      setIsAddDialogOpen(false);
      toast.success('Property added successfully');
      setNewProperty({
        name: '',
        type: 'Commercial Office',
        location: '',
        floors: 5,
        rooms_per_floor: 10,
        revenue_per_seat: 2500,
        energy_cost_per_unit: 8,
        maintenance_per_floor: 50000,
        baseline_energy_intensity: 150,
      });
    } catch (error) {
      console.error('Error adding property:', error);
      toast.error('Failed to add property');
    }
  };

  const filteredProperties = properties.filter(prop => {
    const matchesSearch = prop.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         prop.location.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = filterType === 'all' || prop.type === filterType;
    return matchesSearch && matchesType;
  });

  const getUtilizationBadge = (status) => {
    switch (status) {
      case 'Optimal': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'Underutilized': return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'Overloaded': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      default: return '';
    }
  };

  const propertyTypes = ['Commercial Office', 'Co-Working Space', 'IT Park', 'Business Center', 'Tech Hub'];

  if (loading) {
    return (
      <div className="space-y-6" data-testid="portfolio-loading">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="glass">
              <CardContent className="p-6">
                <div className="h-48 shimmer rounded"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="property-portfolio">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Building2 className="w-8 h-8 text-blue-400" />
            Property Portfolio
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage and analyze your {properties.length} properties
          </p>
        </div>
        
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-blue-600 hover:bg-blue-500 glow-blue" data-testid="add-property-btn">
              <Plus className="w-4 h-4 mr-2" />
              Add Property
            </Button>
          </DialogTrigger>
          <DialogContent className="glass max-w-lg">
            <DialogHeader>
              <DialogTitle>Add New Property</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label>Property Name</Label>
                <Input 
                  placeholder="e.g., Horizon Tech Park"
                  value={newProperty.name}
                  onChange={(e) => setNewProperty({...newProperty, name: e.target.value})}
                  data-testid="property-name-input"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Type</Label>
                  <Select 
                    value={newProperty.type}
                    onValueChange={(v) => setNewProperty({...newProperty, type: v})}
                  >
                    <SelectTrigger data-testid="property-type-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {propertyTypes.map(type => (
                        <SelectItem key={type} value={type}>{type}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="space-y-2">
                  <Label>Location</Label>
                  <Input 
                    placeholder="e.g., Mumbai, Maharashtra"
                    value={newProperty.location}
                    onChange={(e) => setNewProperty({...newProperty, location: e.target.value})}
                    data-testid="property-location-input"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Number of Floors</Label>
                  <Input 
                    type="number"
                    min={1}
                    max={50}
                    value={newProperty.floors}
                    onChange={(e) => setNewProperty({...newProperty, floors: parseInt(e.target.value) || 1})}
                    data-testid="property-floors-input"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Rooms per Floor</Label>
                  <Input 
                    type="number"
                    min={1}
                    max={50}
                    value={newProperty.rooms_per_floor}
                    onChange={(e) => setNewProperty({...newProperty, rooms_per_floor: parseInt(e.target.value) || 1})}
                    data-testid="property-rooms-input"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Revenue per Seat (₹)</Label>
                  <Input 
                    type="number"
                    min={100}
                    value={newProperty.revenue_per_seat}
                    onChange={(e) => setNewProperty({...newProperty, revenue_per_seat: parseFloat(e.target.value) || 100})}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Energy Cost/Unit (₹)</Label>
                  <Input 
                    type="number"
                    min={1}
                    value={newProperty.energy_cost_per_unit}
                    onChange={(e) => setNewProperty({...newProperty, energy_cost_per_unit: parseFloat(e.target.value) || 1})}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Maintenance/Floor (₹)</Label>
                  <Input 
                    type="number"
                    min={1000}
                    value={newProperty.maintenance_per_floor}
                    onChange={(e) => setNewProperty({...newProperty, maintenance_per_floor: parseFloat(e.target.value) || 1000})}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Energy Intensity</Label>
                  <Input 
                    type="number"
                    min={50}
                    value={newProperty.baseline_energy_intensity}
                    onChange={(e) => setNewProperty({...newProperty, baseline_energy_intensity: parseFloat(e.target.value) || 50})}
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <Button variant="ghost" onClick={() => setIsAddDialogOpen(false)}>
                  Cancel
                </Button>
                <Button 
                  onClick={handleAddProperty}
                  disabled={!newProperty.name || !newProperty.location}
                  className="bg-blue-600 hover:bg-blue-500"
                  data-testid="submit-property-btn"
                >
                  Add Property
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input 
            placeholder="Search properties..."
            className="pl-10"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            data-testid="property-search"
          />
        </div>
        <Select value={filterType} onValueChange={setFilterType}>
          <SelectTrigger className="w-full md:w-48" data-testid="property-filter">
            <Filter className="w-4 h-4 mr-2" />
            <SelectValue placeholder="Filter by type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            {propertyTypes.map(type => (
              <SelectItem key={type} value={type}>{type}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Properties Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredProperties.map((prop) => (
          <Card 
            key={prop.property_id}
            className="glass card-hover cursor-pointer group"
            onClick={() => navigate(`/property/${prop.property_id}`)}
            data-testid={`property-card-${prop.property_id}`}
          >
            <CardContent className="p-6">
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center">
                  <Building2 className="w-6 h-6 text-blue-400" />
                </div>
                <Badge className={getUtilizationBadge(prop.utilization_status)}>
                  {prop.utilization_status}
                </Badge>
              </div>

              {/* Info */}
              <h3 className="text-lg font-semibold mb-1 group-hover:text-blue-400 transition-colors">
                {prop.name}
              </h3>
              <div className="flex items-center gap-1 text-sm text-muted-foreground mb-4">
                <MapPin className="w-3 h-3" />
                {prop.location}
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border">
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">Occupancy</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Users className="w-4 h-4 text-amber-400" />
                    <span className="font-mono font-semibold">{formatPercent(prop.current_occupancy)}</span>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">Profit</p>
                  <div className="flex items-center gap-2 mt-1">
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                    <span className="font-mono font-semibold text-emerald-400">{formatCurrency(prop.current_profit)}</span>
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-border text-sm text-muted-foreground">
                <span>{prop.floors} floors • {prop.type}</span>
                <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredProperties.length === 0 && (
        <div className="text-center py-12">
          <Building2 className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-semibold">No properties found</h3>
          <p className="text-muted-foreground mt-1">
            {searchQuery || filterType !== 'all' 
              ? 'Try adjusting your search or filters'
              : 'Add your first property to get started'}
          </p>
        </div>
      )}
    </div>
  );
}
