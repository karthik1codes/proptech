import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API } from '../App';
import { toast } from 'sonner';

/**
 * Global Property State Context
 * Provides unified state management across all pages
 * Ensures changes in simulator reflect everywhere
 */
const PropertyStateContext = createContext(null);

export function PropertyStateProvider({ children }) {
  const [userStates, setUserStates] = useState({}); // { property_id: state }
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sessionId, setSessionId] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  // Initialize session and fetch all states
  useEffect(() => {
    initializeSession();
    fetchProperties();
    fetchAllUserStates();
    
    return () => {
      if (sessionId) {
        endSession(sessionId);
      }
    };
  }, []);

  const initializeSession = async () => {
    try {
      const response = await axios.post(
        `${API}/sessions/create`,
        { device_info: navigator.userAgent },
        { withCredentials: true }
      );
      if (response.data.success) {
        setSessionId(response.data.session_id);
      }
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  };

  const endSession = async (sid) => {
    try {
      await axios.post(`${API}/sessions/${sid}/end`, {}, { withCredentials: true });
    } catch (err) {
      console.error('Failed to end session:', err);
    }
  };

  const fetchProperties = async () => {
    try {
      const response = await axios.get(`${API}/properties`, { withCredentials: true });
      setProperties(response.data || []);
    } catch (err) {
      console.error('Failed to fetch properties:', err);
    }
  };

  const fetchAllUserStates = async () => {
    try {
      const response = await axios.get(`${API}/user-state`, { withCredentials: true });
      const states = {};
      (response.data.states || []).forEach(state => {
        states[state.property_id] = state;
      });
      setUserStates(states);
    } catch (err) {
      console.error('Failed to fetch user states:', err);
    } finally {
      setLoading(false);
    }
  };

  const getPropertyState = useCallback((propertyId) => {
    return userStates[propertyId] || { closed_floors: [], has_override: false };
  }, [userStates]);

  const getClosedFloors = useCallback((propertyId) => {
    return userStates[propertyId]?.closed_floors || [];
  }, [userStates]);

  const isFloorClosed = useCallback((propertyId, floorNumber) => {
    return getClosedFloors(propertyId).includes(floorNumber);
  }, [getClosedFloors]);

  /**
   * Close floors - persists to backend and updates global state
   */
  const closeFloors = useCallback(async (propertyId, floors) => {
    const currentClosed = getClosedFloors(propertyId);
    const newClosed = [...new Set([...currentClosed, ...floors])].sort((a, b) => a - b);
    
    // Optimistic update
    setUserStates(prev => ({
      ...prev,
      [propertyId]: {
        ...prev[propertyId],
        closed_floors: newClosed,
        has_override: true,
        property_id: propertyId
      }
    }));

    try {
      const response = await axios.post(
        `${API}/user-state/${propertyId}/close-floors`,
        { floors, session_id: sessionId },
        { withCredentials: true }
      );
      
      if (response.data.success) {
        setLastUpdate(new Date().toISOString());
        // Update with server response
        setUserStates(prev => ({
          ...prev,
          [propertyId]: {
            ...prev[propertyId],
            closed_floors: response.data.closed_floors || newClosed,
            analytics: response.data.analytics
          }
        }));
        return { success: true, analytics: response.data.analytics };
      }
    } catch (err) {
      // Rollback on error
      setUserStates(prev => ({
        ...prev,
        [propertyId]: {
          ...prev[propertyId],
          closed_floors: currentClosed
        }
      }));
      toast.error('Failed to save changes');
      return { success: false, error: err.message };
    }
  }, [sessionId, getClosedFloors]);

  /**
   * Open floors - persists to backend and updates global state
   */
  const openFloors = useCallback(async (propertyId, floors) => {
    const currentClosed = getClosedFloors(propertyId);
    const newClosed = currentClosed.filter(f => !floors.includes(f));
    
    // Optimistic update
    setUserStates(prev => ({
      ...prev,
      [propertyId]: {
        ...prev[propertyId],
        closed_floors: newClosed,
        has_override: newClosed.length > 0
      }
    }));

    try {
      const response = await axios.post(
        `${API}/user-state/${propertyId}/open-floors`,
        { floors, session_id: sessionId },
        { withCredentials: true }
      );
      
      if (response.data.success) {
        setLastUpdate(new Date().toISOString());
        setUserStates(prev => ({
          ...prev,
          [propertyId]: {
            ...prev[propertyId],
            closed_floors: response.data.closed_floors || newClosed,
            analytics: response.data.analytics
          }
        }));
        return { success: true, analytics: response.data.analytics };
      }
    } catch (err) {
      // Rollback
      setUserStates(prev => ({
        ...prev,
        [propertyId]: {
          ...prev[propertyId],
          closed_floors: currentClosed
        }
      }));
      toast.error('Failed to save changes');
      return { success: false, error: err.message };
    }
  }, [sessionId, getClosedFloors]);

  /**
   * Toggle floor state
   */
  const toggleFloor = useCallback(async (propertyId, floorNumber) => {
    if (isFloorClosed(propertyId, floorNumber)) {
      return openFloors(propertyId, [floorNumber]);
    } else {
      return closeFloors(propertyId, [floorNumber]);
    }
  }, [isFloorClosed, closeFloors, openFloors]);

  /**
   * Reset property to default state
   */
  const resetProperty = useCallback(async (propertyId) => {
    try {
      const response = await axios.post(
        `${API}/user-state/${propertyId}/reset`,
        { session_id: sessionId },
        { withCredentials: true }
      );
      
      if (response.data.success) {
        setUserStates(prev => {
          const newStates = { ...prev };
          delete newStates[propertyId];
          return newStates;
        });
        setLastUpdate(new Date().toISOString());
        toast.success('Property reset to default');
        return { success: true };
      }
    } catch (err) {
      toast.error('Failed to reset property');
      return { success: false, error: err.message };
    }
  }, [sessionId]);

  /**
   * Reset all properties
   */
  const resetAll = useCallback(async () => {
    try {
      const response = await axios.post(
        `${API}/user-state/reset-all`,
        { session_id: sessionId },
        { withCredentials: true }
      );
      
      if (response.data.success) {
        setUserStates({});
        setLastUpdate(new Date().toISOString());
        toast.success('All properties reset');
        return { success: true };
      }
    } catch (err) {
      toast.error('Failed to reset');
      return { success: false, error: err.message };
    }
  }, [sessionId]);

  /**
   * Get AI recommendations for a property considering current state
   */
  const getRecommendations = useCallback(async (propertyId) => {
    try {
      const response = await axios.get(
        `${API}/copilot/${propertyId}`,
        { withCredentials: true }
      );
      return response.data;
    } catch (err) {
      console.error('Failed to get recommendations:', err);
      return null;
    }
  }, []);

  /**
   * Get property with current state applied
   */
  const getPropertyWithState = useCallback((propertyId) => {
    const property = properties.find(p => p.property_id === propertyId);
    if (!property) return null;
    
    const state = getPropertyState(propertyId);
    
    return {
      ...property,
      userState: state,
      closedFloors: state.closed_floors || [],
      hasOptimization: state.has_override || (state.closed_floors?.length > 0),
      activeFloors: property.floors - (state.closed_floors?.length || 0)
    };
  }, [properties, getPropertyState]);

  const value = {
    // State
    userStates,
    properties,
    loading,
    sessionId,
    lastUpdate,
    
    // Getters
    getPropertyState,
    getClosedFloors,
    isFloorClosed,
    getPropertyWithState,
    
    // Actions
    closeFloors,
    openFloors,
    toggleFloor,
    resetProperty,
    resetAll,
    getRecommendations,
    
    // Refresh
    refresh: fetchAllUserStates,
    refreshProperties: fetchProperties
  };

  return (
    <PropertyStateContext.Provider value={value}>
      {children}
    </PropertyStateContext.Provider>
  );
}

export function usePropertyState() {
  const context = useContext(PropertyStateContext);
  if (!context) {
    throw new Error('usePropertyState must be used within a PropertyStateProvider');
  }
  return context;
}

export default PropertyStateContext;
