import React, { useState } from 'react';
import { formatPercent } from '../utils/formatters';

/**
 * FloorPlanVisualization - Interactive SVG-based floor plan
 * @param {Array} floorData - Array of floor objects with rooms
 * @param {number} floors - Total number of floors
 */
export default function FloorPlanVisualization({ floorData = [], floors = 1 }) {
  const [selectedFloor, setSelectedFloor] = useState(1);
  const [hoveredRoom, setHoveredRoom] = useState(null);

  const getOccupancyColor = (occupancy, capacity) => {
    const rate = capacity > 0 ? occupancy / capacity : 0;
    if (rate < 0.4) return { fill: 'rgba(239, 68, 68, 0.3)', stroke: '#EF4444', status: 'Underutilized' };
    if (rate <= 0.85) return { fill: 'rgba(16, 185, 129, 0.3)', stroke: '#10B981', status: 'Optimal' };
    return { fill: 'rgba(245, 158, 11, 0.3)', stroke: '#F59E0B', status: 'Overloaded' };
  };

  const currentFloorData = floorData.find(f => f.floor_number === selectedFloor);
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
      <div className="flex items-center gap-6 text-sm">
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

      {/* SVG Floor Plan */}
      <div className="bg-zinc-900/50 rounded-xl p-4 overflow-x-auto relative">
        <svg 
          width={Math.max(svgWidth, 600)} 
          height={Math.max(svgHeight, 280)}
          viewBox={`0 0 ${Math.max(svgWidth, 600)} ${Math.max(svgHeight, 280)}`}
          className="mx-auto"
        >
          {/* Background Grid */}
          <defs>
            <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="0.5"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* Floor Label */}
          <text x={padding} y={30} fill="#64748B" fontSize="14" fontWeight="600">
            Floor {selectedFloor} - {currentFloorData?.total_capacity || 0} Capacity
          </text>

          {/* Rooms */}
          {rooms.map((room, idx) => {
            const row = Math.floor(idx / roomsPerRow);
            const col = idx % roomsPerRow;
            const x = padding + col * (roomWidth + gap);
            const y = 50 + row * (roomHeight + gap);
            const colors = getOccupancyColor(room.current_occupancy, room.capacity);
            const occupancyRate = room.capacity > 0 ? (room.current_occupancy / room.capacity * 100).toFixed(0) : 0;
            const isHovered = hoveredRoom === room.room_id;

            return (
              <g 
                key={room.room_id}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredRoom(room.room_id)}
                onMouseLeave={() => setHoveredRoom(null)}
                style={{
                  transform: isHovered ? 'scale(1.02)' : 'scale(1)',
                  transformOrigin: `${x + roomWidth/2}px ${y + roomHeight/2}px`,
                  transition: 'transform 0.2s ease'
                }}
              >
                {/* Room Rectangle */}
                <rect
                  x={x}
                  y={y}
                  width={roomWidth}
                  height={roomHeight}
                  rx="6"
                  fill={colors.fill}
                  stroke={colors.stroke}
                  strokeWidth={isHovered ? 2.5 : 1.5}
                />
                
                {/* Room ID */}
                <text
                  x={x + roomWidth / 2}
                  y={y + 18}
                  fill="#F8FAFC"
                  fontSize="11"
                  fontWeight="600"
                  textAnchor="middle"
                  style={{ fontFamily: 'JetBrains Mono, monospace' }}
                >
                  {room.room_id}
                </text>
                
                {/* Room Type (truncated) */}
                <text
                  x={x + roomWidth / 2}
                  y={y + 32}
                  fill="#94A3B8"
                  fontSize="8"
                  textAnchor="middle"
                >
                  {room.room_type?.substring(0, 10) || 'Room'}
                </text>
                
                {/* Occupancy */}
                <text
                  x={x + roomWidth / 2}
                  y={y + 48}
                  fill={colors.stroke}
                  fontSize="12"
                  fontWeight="600"
                  textAnchor="middle"
                  style={{ fontFamily: 'JetBrains Mono, monospace' }}
                >
                  {occupancyRate}%
                </text>
              </g>
            );
          })}

          {/* Floor Summary */}
          <text 
            x={padding} 
            y={svgHeight - 10} 
            fill="#64748B" 
            fontSize="12"
          >
            {rooms.length} rooms • {rooms.filter(r => r.current_occupancy / r.capacity >= 0.4 && r.current_occupancy / r.capacity <= 0.85).length} optimal • {rooms.filter(r => r.current_occupancy / r.capacity < 0.4).length} underutilized
          </text>
        </svg>

        {/* Hover Tooltip */}
        {hoveredRoom && (
          <div 
            className="absolute z-50 p-3 rounded-lg glass border border-border shadow-xl"
            style={{
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              pointerEvents: 'none'
            }}
          >
            {rooms.filter(r => r.room_id === hoveredRoom).map(room => {
              const colors = getOccupancyColor(room.current_occupancy, room.capacity);
              return (
                <div key={room.room_id} className="space-y-1 text-sm">
                  <p className="font-semibold">{room.room_id}</p>
                  <p className="text-muted-foreground">{room.room_type}</p>
                  <div className="flex justify-between gap-4">
                    <span>Occupancy:</span>
                    <span className="font-mono" style={{ color: colors.stroke }}>
                      {room.current_occupancy} / {room.capacity}
                    </span>
                  </div>
                  <div className="flex justify-between gap-4">
                    <span>Status:</span>
                    <span style={{ color: colors.stroke }}>{colors.status}</span>
                  </div>
                </div>
              );
            })}
          </div>
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
