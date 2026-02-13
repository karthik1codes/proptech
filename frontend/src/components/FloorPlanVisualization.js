import React, { useState, useEffect } from 'react';
import { formatPercent } from '../utils/formatters';
import { Lock, Unlock } from 'lucide-react';

/**
 * FloorPlanVisualization - Interactive SVG-based floor plan
 * Shows closed floors with visual indicators
 * @param {Array} floorData - Array of floor objects with rooms
 * @param {number} floors - Total number of floors
 * @param {Array} closedFloors - Array of closed floor numbers
 * @param {Function} onFloorToggle - Callback when floor is toggled
 * @param {boolean} interactive - Whether floors can be toggled
 */
export default function FloorPlanVisualization({ 
  floorData = [], 
  floors = 1, 
  closedFloors = [],
  onFloorToggle,
  interactive = false
}) {
  const [selectedFloor, setSelectedFloor] = useState(1);
  const [hoveredRoom, setHoveredRoom] = useState(null);

  // Auto-select first non-closed floor if current is closed
  useEffect(() => {
    if (closedFloors.includes(selectedFloor)) {
      const openFloor = Array.from({ length: floors }, (_, i) => i + 1)
        .find(f => !closedFloors.includes(f));
      if (openFloor) setSelectedFloor(openFloor);
    }
  }, [closedFloors, selectedFloor, floors]);

  const getOccupancyColor = (occupancy, capacity, isClosed) => {
    if (isClosed) {
      return { fill: 'rgba(100, 100, 100, 0.2)', stroke: '#6b7280', status: 'Closed' };
    }
    const rate = capacity > 0 ? occupancy / capacity : 0;
    if (rate < 0.4) return { fill: 'rgba(239, 68, 68, 0.3)', stroke: '#EF4444', status: 'Underutilized' };
    if (rate <= 0.85) return { fill: 'rgba(16, 185, 129, 0.3)', stroke: '#10B981', status: 'Optimal' };
    return { fill: 'rgba(245, 158, 11, 0.3)', stroke: '#F59E0B', status: 'Overloaded' };
  };

  const isFloorClosed = (floorNum) => closedFloors.includes(floorNum);

  // Find the current floor data
  const currentFloorData = floorData?.find(f => f.floor_number === selectedFloor);
  const rooms = currentFloorData?.rooms || [];
  const currentFloorClosed = isFloorClosed(selectedFloor);

  // Calculate grid dimensions
  const roomsPerRow = rooms.length > 0 ? Math.ceil(Math.sqrt(rooms.length)) : 4;

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
      {/* Floor Selector with Closed Indicators */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        <span className="text-sm text-muted-foreground mr-2">Floor:</span>
        {Array.from({ length: floors }, (_, i) => i + 1).map(floorNum => {
          const isClosed = isFloorClosed(floorNum);
          return (
            <button
              key={floorNum}
              onClick={() => {
                if (interactive && onFloorToggle) {
                  onFloorToggle(floorNum);
                } else {
                  setSelectedFloor(floorNum);
                }
              }}
              className={`relative px-4 py-2 rounded-lg font-mono text-sm font-medium transition-all ${
                isClosed
                  ? 'bg-red-500/20 border-2 border-red-500/50 text-red-400'
                  : selectedFloor === floorNum
                    ? 'bg-blue-500 text-white glow-blue'
                    : 'bg-zinc-800 hover:bg-zinc-700 text-muted-foreground'
              }`}
              data-testid={`floor-selector-${floorNum}`}
            >
              {isClosed && <Lock className="w-3 h-3 absolute -top-1 -right-1 text-red-400" />}
              F{floorNum}
            </button>
          );
        })}
      </div>

      {/* Closed Floors Summary */}
      {closedFloors.length > 0 && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
          <Lock className="w-4 h-4 text-red-400" />
          <span className="text-sm text-red-300">
            <strong>{closedFloors.length}</strong> floor(s) closed: {closedFloors.map(f => `F${f}`).join(', ')}
          </span>
          {interactive && (
            <span className="text-xs text-red-400 ml-auto">Click floor to toggle</span>
          )}
        </div>
      )}

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
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ background: 'rgba(100, 100, 100, 0.2)', border: '2px solid #6b7280' }}></div>
          <span className="text-muted-foreground">Closed</span>
        </div>
      </div>

      {/* Room Grid */}
      <div className={`bg-zinc-900/50 rounded-xl p-4 overflow-x-auto ${currentFloorClosed ? 'opacity-50' : ''}`}>
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-muted-foreground">
            Floor {selectedFloor} - {currentFloorData?.total_capacity || 0} Total Capacity
          </p>
          {currentFloorClosed && (
            <span className="flex items-center gap-1 text-sm text-red-400 bg-red-500/10 px-2 py-1 rounded">
              <Lock className="w-3 h-3" /> CLOSED
            </span>
          )}
        </div>
        
        <div 
          className="grid gap-3 mx-auto"
          style={{ 
            gridTemplateColumns: `repeat(${roomsPerRow}, minmax(80px, 1fr))`,
            maxWidth: roomsPerRow * 100 + 'px'
          }}
        >
          {rooms.map((room) => {
            const colors = getOccupancyColor(room.current_occupancy, room.capacity, currentFloorClosed);
            const occupancyRate = room.capacity > 0 
              ? Math.round((room.current_occupancy / room.capacity) * 100) 
              : 0;
            const isHovered = hoveredRoom === room.room_id;

            return (
              <div
                key={room.room_id}
                className={`relative p-3 rounded-lg cursor-pointer transition-all duration-200 ${
                  isHovered ? 'transform scale-105 z-10' : ''
                } ${currentFloorClosed ? 'grayscale' : ''}`}
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
                  {currentFloorClosed ? '—' : `${occupancyRate}%`}
                </p>
                
                {/* Tooltip on hover */}
                {isHovered && (
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 p-2 bg-zinc-900 border border-border rounded-lg shadow-lg z-50 whitespace-nowrap text-xs">
                    <p className="font-semibold">{room.room_id}</p>
                    <p className="text-muted-foreground">{room.room_type}</p>
                    {currentFloorClosed ? (
                      <p className="text-red-400">Floor Closed</p>
                    ) : (
                      <>
                        <p>Capacity: {room.capacity}</p>
                        <p>Occupied: {room.current_occupancy}</p>
                        <p style={{ color: colors.stroke }}>{colors.status}</p>
                      </>
                    )}
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
            <p className="text-xs text-muted-foreground">Active Floors</p>
            <p className="text-xl font-bold font-mono text-green-400">
              {floors - closedFloors.length}/{floors}
            </p>
          </div>
          <div className="p-3 rounded-lg bg-zinc-900/50">
            <p className="text-xs text-muted-foreground">Total Capacity</p>
            <p className="text-xl font-bold font-mono">{currentFloorData.total_capacity}</p>
          </div>
          <div className="p-3 rounded-lg bg-zinc-900/50">
            <p className="text-xs text-muted-foreground">Current Occupancy</p>
            <p className="text-xl font-bold font-mono">
              {currentFloorClosed ? '—' : rooms.reduce((sum, r) => sum + r.current_occupancy, 0)}
            </p>
          </div>
          <div className="p-3 rounded-lg bg-zinc-900/50">
            <p className="text-xs text-muted-foreground">Utilization Rate</p>
            <p className="text-xl font-bold font-mono">
              {currentFloorClosed 
                ? '—' 
                : currentFloorData.total_capacity > 0 
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
