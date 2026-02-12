import React, { useState, useEffect } from 'react';
import { formatPercent } from '../utils/formatters';

/**
 * FloorPlanVisualization - Interactive SVG-based floor plan
 * @param {Array} floorData - Array of floor objects with rooms
 * @param {number} floors - Total number of floors
 */
export default function FloorPlanVisualization({ floorData = [], floors = 1 }) {
  const [selectedFloor, setSelectedFloor] = useState(1);
  const [hoveredRoom, setHoveredRoom] = useState(null);

  // Debug: log props on mount and when they change
  useEffect(() => {
    console.log('FloorPlanVisualization - floorData:', floorData);
    console.log('FloorPlanVisualization - floors:', floors);
  }, [floorData, floors]);

  const getOccupancyColor = (occupancy, capacity) => {
    const rate = capacity > 0 ? occupancy / capacity : 0;
    if (rate < 0.4) return { fill: 'rgba(239, 68, 68, 0.3)', stroke: '#EF4444', status: 'Underutilized' };
    if (rate <= 0.85) return { fill: 'rgba(16, 185, 129, 0.3)', stroke: '#10B981', status: 'Optimal' };
    return { fill: 'rgba(245, 158, 11, 0.3)', stroke: '#F59E0B', status: 'Overloaded' };
  };

  // Find the current floor data
  const currentFloorData = floorData?.find(f => f.floor_number === selectedFloor);
  const rooms = currentFloorData?.rooms || [];

  // Calculate grid dimensions
  const roomsPerRow = rooms.length > 0 ? Math.ceil(Math.sqrt(rooms.length)) : 4;
  const roomWidth = 80;
  const roomHeight = 60;
  const gap = 10;
  const padding = 20;

  const svgWidth = roomsPerRow * (roomWidth + gap) + padding * 2;
  const numRows = rooms.length > 0 ? Math.ceil(rooms.length / roomsPerRow) : 3;
  const svgHeight = numRows * (roomHeight + gap) + padding * 2 + 40;

  // If no floor data, show placeholder
  if (!floorData || floorData.length === 0) {
    return (
      <div className="space-y-4 text-center py-12" data-testid="floor-plan-visualization">
        <p className="text-muted-foreground">No floor data available</p>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="floor-plan-visualization">
      {/* Floor Selector */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        <span className="text-sm text-muted-foreground mr-2">Floor:</span>
        {Array.from({ length: floors }, (_, i) => i + 1).map(floorNum => (
          <button
            key={floorNum}
            onClick={() => setSelectedFloor(floorNum)}
            className={`px-4 py-2 rounded-lg font-mono text-sm font-medium transition-all ${
              selectedFloor === floorNum
                ? 'bg-blue-500 text-white glow-blue'
                : 'bg-zinc-800 hover:bg-zinc-700 text-muted-foreground'
            }`}
            data-testid={`floor-selector-${floorNum}`}
          >
            F{floorNum}
          </button>
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-6 text-sm flex-wrap">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ background: 'rgba(239, 68, 68, 0.3)', border: '2px solid #EF4444' }}></div>
          <span className="text-muted-foreground">Underutilized (&lt;40%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ background: 'rgba(16, 185, 129, 0.3)', border: '2px solid #10B981' }}></div>
          <span className="text-muted-foreground">Optimal (40-85%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ background: 'rgba(245, 158, 11, 0.3)', border: '2px solid #F59E0B' }}></div>
          <span className="text-muted-foreground">Overloaded (&gt;85%)</span>
        </div>
      </div>

      {/* Room Grid - Using divs instead of SVG for better rendering */}
      <div className="bg-zinc-900/50 rounded-xl p-4 overflow-x-auto">
        <p className="text-sm text-muted-foreground mb-4">
          Floor {selectedFloor} - {currentFloorData?.total_capacity || 0} Total Capacity
        </p>
        
        <div 
          className="grid gap-3 mx-auto"
          style={{ 
            gridTemplateColumns: `repeat(${roomsPerRow}, minmax(80px, 1fr))`,
            maxWidth: roomsPerRow * 100 + 'px'
          }}
        >
          {rooms.map((room) => {
            const colors = getOccupancyColor(room.current_occupancy, room.capacity);
            const occupancyRate = room.capacity > 0 
              ? Math.round((room.current_occupancy / room.capacity) * 100) 
              : 0;
            const isHovered = hoveredRoom === room.room_id;

            return (
              <div
                key={room.room_id}
                className={`relative p-3 rounded-lg cursor-pointer transition-all duration-200 ${
                  isHovered ? 'transform scale-105 z-10' : ''
                }`}
                style={{
                  background: colors.fill,
                  border: `2px solid ${colors.stroke}`,
                  boxShadow: isHovered ? `0 0 20px ${colors.stroke}40` : 'none'
                }}
                onMouseEnter={() => setHoveredRoom(room.room_id)}
                onMouseLeave={() => setHoveredRoom(null)}
              >
                <p className="text-xs font-mono font-semibold text-foreground text-center">
                  {room.room_id}
                </p>
                <p className="text-[10px] text-muted-foreground text-center mt-1 truncate">
                  {room.room_type || 'Room'}
                </p>
                <p 
                  className="text-sm font-mono font-bold text-center mt-1"
                  style={{ color: colors.stroke }}
                >
                  {occupancyRate}%
                </p>
                
                {/* Tooltip on hover */}
                {isHovered && (
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 p-2 bg-zinc-900 border border-border rounded-lg shadow-lg z-50 whitespace-nowrap text-xs">
                    <p className="font-semibold">{room.room_id}</p>
                    <p className="text-muted-foreground">{room.room_type}</p>
                    <p>Capacity: {room.capacity}</p>
                    <p>Occupied: {room.current_occupancy}</p>
                    <p style={{ color: colors.stroke }}>{colors.status}</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {rooms.length === 0 && (
          <p className="text-center text-muted-foreground py-8">
            No rooms found for Floor {selectedFloor}
          </p>
        )}
      </div>

      {/* Room Stats */}
      {currentFloorData && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-3 rounded-lg bg-zinc-900/50">
            <p className="text-xs text-muted-foreground">Total Rooms</p>
            <p className="text-xl font-bold font-mono">{rooms.length}</p>
          </div>
          <div className="p-3 rounded-lg bg-zinc-900/50">
            <p className="text-xs text-muted-foreground">Total Capacity</p>
            <p className="text-xl font-bold font-mono">{currentFloorData.total_capacity}</p>
          </div>
          <div className="p-3 rounded-lg bg-zinc-900/50">
            <p className="text-xs text-muted-foreground">Current Occupancy</p>
            <p className="text-xl font-bold font-mono">
              {rooms.reduce((sum, r) => sum + r.current_occupancy, 0)}
            </p>
          </div>
          <div className="p-3 rounded-lg bg-zinc-900/50">
            <p className="text-xs text-muted-foreground">Utilization Rate</p>
            <p className="text-xl font-bold font-mono">
              {currentFloorData.total_capacity > 0 
                ? formatPercent(rooms.reduce((sum, r) => sum + r.current_occupancy, 0) / currentFloorData.total_capacity)
                : '0%'
              }
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
