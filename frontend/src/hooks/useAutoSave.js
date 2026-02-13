import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { API } from '../App';
import { toast } from 'sonner';

/**
 * Hook for managing user property state with auto-save and debounce
 * Automatically persists changes to the backend without explicit save clicks
 */
export function useAutoSaveState(propertyId, initialState = null) {
  const [state, setState] = useState(initialState);
  const [closedFloors, setClosedFloors] = useState([]);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  
  const saveTimeoutRef = useRef(null);
  const pendingChangesRef = useRef(null);
  
  // Create session on mount
  useEffect(() => {
    createSession();
    
    return () => {
      // End session on unmount
      if (sessionId) {
        endSession(sessionId);
      }
    };
  }, []);
  
  // Fetch current state on mount
  useEffect(() => {
    if (propertyId) {
      fetchState();
    }
  }, [propertyId]);
  
  const createSession = async () => {
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
      await axios.post(
        `${API}/sessions/${sid}/end`,
        {},
        { withCredentials: true }
      );
    } catch (err) {
      console.error('Failed to end session:', err);
    }
  };
  
  const fetchState = async () => {
    try {
      const response = await axios.get(
        `${API}/user-state/${propertyId}`,
        { withCredentials: true }
      );
      
      setState(response.data);
      setClosedFloors(response.data.closed_floors || []);
    } catch (err) {
      console.error('Failed to fetch state:', err);
      setError(err.message);
    }
  };
  
  /**
   * Debounced save function - waits for user to stop making changes
   */
  const debouncedSave = useCallback(async (floors, action = 'update') => {
    // Clear any pending save
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    
    // Store pending changes
    pendingChangesRef.current = { floors, action };
    
    // Debounce: wait 500ms before saving
    saveTimeoutRef.current = setTimeout(async () => {
      await performSave(floors, action);
    }, 500);
  }, [propertyId, sessionId]);
  
  /**
   * Actually perform the save to backend
   */
  const performSave = async (floors, action) => {
    if (!propertyId) return;
    
    setSaving(true);
    setError(null);
    
    try {
      const endpoint = action === 'close' 
        ? `${API}/user-state/${propertyId}/close-floors`
        : `${API}/user-state/${propertyId}/open-floors`;
      
      const response = await axios.post(
        endpoint,
        { floors, session_id: sessionId },
        { withCredentials: true }
      );
      
      if (response.data.success) {
        setLastSaved(new Date().toISOString());
        setState(prev => ({
          ...prev,
          closed_floors: response.data.closed_floors || closedFloors,
          has_override: true
        }));
        
        // Silent save - no toast for auto-save
        console.log('Auto-saved:', { floors, action, propertyId });
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message;
      setError(errorMsg);
      toast.error(`Failed to save: ${errorMsg}`);
    } finally {
      setSaving(false);
      pendingChangesRef.current = null;
    }
  };
  
  /**
   * Close a floor - optimistic update with debounced save
   */
  const closeFloor = useCallback((floorNumber) => {
    if (closedFloors.includes(floorNumber)) return;
    
    const newClosedFloors = [...closedFloors, floorNumber].sort((a, b) => a - b);
    setClosedFloors(newClosedFloors);
    
    // Debounced save
    debouncedSave([floorNumber], 'close');
  }, [closedFloors, debouncedSave]);
  
  /**
   * Open a floor - optimistic update with debounced save
   */
  const openFloor = useCallback((floorNumber) => {
    if (!closedFloors.includes(floorNumber)) return;
    
    const newClosedFloors = closedFloors.filter(f => f !== floorNumber);
    setClosedFloors(newClosedFloors);
    
    // Debounced save
    debouncedSave([floorNumber], 'open');
  }, [closedFloors, debouncedSave]);
  
  /**
   * Toggle floor state
   */
  const toggleFloor = useCallback((floorNumber) => {
    if (closedFloors.includes(floorNumber)) {
      openFloor(floorNumber);
    } else {
      closeFloor(floorNumber);
    }
  }, [closedFloors, closeFloor, openFloor]);
  
  /**
   * Close multiple floors at once
   */
  const closeFloors = useCallback((floors) => {
    const newClosedFloors = [...new Set([...closedFloors, ...floors])].sort((a, b) => a - b);
    setClosedFloors(newClosedFloors);
    debouncedSave(floors, 'close');
  }, [closedFloors, debouncedSave]);
  
  /**
   * Open multiple floors at once
   */
  const openFloors = useCallback((floors) => {
    const newClosedFloors = closedFloors.filter(f => !floors.includes(f));
    setClosedFloors(newClosedFloors);
    debouncedSave(floors, 'open');
  }, [closedFloors, debouncedSave]);
  
  /**
   * Reset to default state
   */
  const reset = useCallback(async () => {
    try {
      setSaving(true);
      
      await axios.post(
        `${API}/user-state/${propertyId}/reset`,
        { session_id: sessionId },
        { withCredentials: true }
      );
      
      setClosedFloors([]);
      setState(prev => ({ ...prev, has_override: false, closed_floors: [] }));
      setLastSaved(new Date().toISOString());
      
      toast.success('Property state reset to default');
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message;
      setError(errorMsg);
      toast.error(`Failed to reset: ${errorMsg}`);
    } finally {
      setSaving(false);
    }
  }, [propertyId, sessionId]);
  
  /**
   * Force immediate save (bypasses debounce)
   */
  const saveNow = useCallback(async () => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    
    if (pendingChangesRef.current) {
      const { floors, action } = pendingChangesRef.current;
      await performSave(floors, action);
    }
  }, [performSave]);
  
  return {
    // State
    state,
    closedFloors,
    saving,
    lastSaved,
    error,
    sessionId,
    
    // Actions
    closeFloor,
    openFloor,
    toggleFloor,
    closeFloors,
    openFloors,
    reset,
    saveNow,
    refetch: fetchState
  };
}

/**
 * Hook for fetching user change history
 */
export function useChangeHistory(entityType = null, entityId = null) {
  const [changes, setChanges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const fetchChanges = useCallback(async () => {
    setLoading(true);
    try {
      let url = `${API}/change-log`;
      const params = new URLSearchParams();
      
      if (entityType) params.append('entity_type', entityType);
      if (entityId) params.append('entity_id', entityId);
      params.append('limit', '50');
      
      const queryString = params.toString();
      if (queryString) url += `?${queryString}`;
      
      const response = await axios.get(url, { withCredentials: true });
      setChanges(response.data.changes || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [entityType, entityId]);
  
  useEffect(() => {
    fetchChanges();
  }, [fetchChanges]);
  
  return { changes, loading, error, refetch: fetchChanges };
}

/**
 * Hook for fetching user sessions
 */
export function useSessions() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const fetchSessions = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/sessions`, { withCredentials: true });
      setSessions(response.data.sessions || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);
  
  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);
  
  const getSessionDetails = useCallback(async (sessionId) => {
    try {
      const response = await axios.get(`${API}/sessions/${sessionId}`, { withCredentials: true });
      return response.data;
    } catch (err) {
      throw new Error(err.response?.data?.detail || err.message);
    }
  }, []);
  
  return { sessions, loading, error, refetch: fetchSessions, getSessionDetails };
}

export default useAutoSaveState;
