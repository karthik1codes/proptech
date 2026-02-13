# PropTech Decision Copilot - Product Requirements Document

## Latest Update: February 13, 2026

### COMPLETED: Global State Synchronization System

Implemented unified state management across all pages. Changes made in the Scenario Simulator now reflect globally:
- **Dashboard**: Shows "Active Optimizations" banner with floor count and estimated savings
- **Executive Summary**: Displays realized savings from active optimizations
- **Property Portfolio**: Property cards show optimization badges (e.g., "2 closed")
- **Property Detail**: Floor plan visualization shows closed floors in red with lock icon
- **Scenario Simulator**: Syncs with global state, shows "Apply Changes Globally" button

---

## Global State Architecture

### Frontend Context (`/app/frontend/src/context/PropertyStateContext.js`)

```javascript
// Key exports:
PropertyStateProvider  // Wrap at App level
usePropertyState()     // Hook for all pages

// State:
userStates             // { property_id: { closed_floors: [], ... } }
properties             // Array of property objects
lastUpdate             // Timestamp for re-render triggers

// Actions:
closeFloors(propertyId, floors)   // Close floors with optimistic update
openFloors(propertyId, floors)    // Open floors
toggleFloor(propertyId, floor)    // Toggle single floor
resetProperty(propertyId)         // Reset to default
resetAll()                        // Reset all properties
getClosedFloors(propertyId)       // Get closed floors for a property
```

### Backend API Endpoints

- `GET /api/user-state` - Get all user property states
- `GET /api/user-state/{property_id}` - Get state for specific property
- `POST /api/user-state/{property_id}/close-floors` - Close floors (body: `{floors: [1,2,3]}`)
- `POST /api/user-state/{property_id}/open-floors` - Open floors
- `POST /api/user-state/{property_id}/reset` - Reset property state
- `POST /api/user-state/reset-all` - Reset all property states

### MongoDB Collection: `user_property_states`

```json
{
  "user_id": "google-oauth-id",
  "property_id": "prop_001",
  "closed_floors": [6, 7, 8],
  "hybrid_intensity": 1.0,
  "target_occupancy": null,
  "last_simulation_result": {...},
  "updated_at": "2026-02-13T01:30:00Z"
}
```

---

## Previous Features (Still Active)

### Change Logging System (`backend/services/change_log_service.py`)

**MongoDB Collections:**
- `user_change_log` - Full audit trail
- `user_sessions` - Session tracking

**Schema - user_change_log:**
```json
{
  "change_id": "uuid",
  "user_id": "string",
  "entity_type": "property_state|simulation|alert",
  "entity_id": "prop_001",
  "field": "closed_floors",
  "old_value": [1, 2],
  "new_value": [1, 2, 3],
  "timestamp": "datetime",
  "session_id": "session_abc123",
  "metadata": {"source": "api", "property_name": "Horizon"}
}
```

**API Endpoints:**
- `POST /api/sessions/create` - Create tracking session
- `GET /api/sessions` - List user sessions
- `GET /api/sessions/{session_id}` - Session details with changes
- `POST /api/sessions/{session_id}/end` - End session
- `GET /api/change-log` - Get user changes (filters: entity_type, entity_id, session_id)
- `GET /api/change-log/entity/{type}/{id}` - Entity history
- `GET /api/change-log/stats` - Change statistics

**Frontend Auto-Save Hook (`frontend/src/hooks/useAutoSave.js`):**
- 500ms debounce on changes
- Optimistic updates
- Session creation on mount
- Session cleanup on unmount
- Methods: `closeFloor`, `openFloor`, `toggleFloor`, `reset`, `saveNow`

---

### Fully Conversational Multi-User PropTech Copilot (WhatsApp)

Every website action is now executable via WhatsApp with strict multi-user isolation.

---

## Services Implemented

### 1. Per-User Optimization State (`backend/services/user_state_service.py`)
- MongoDB collection: `user_property_states`
- Schema: `{user_id, property_id, closed_floors[], hybrid_intensity, target_occupancy, last_simulation_result, updated_at}`
- User A closes F7 → Only User A sees it (complete isolation)
- Runtime overrides only, no digital twin duplication

### 2. WhatsApp ↔ Google Account Linking (`backend/services/whatsapp_linking_service.py`)
- MongoDB collections: `whatsapp_user_mapping`, `whatsapp_otp_codes`
- OTP verification via Twilio (6-digit code, 10-min expiry)
- APIs:
  - POST `/api/whatsapp/link/initiate` - Send OTP
  - POST `/api/whatsapp/link/verify` - Verify OTP
  - GET `/api/whatsapp/link/status` - Check linking status
  - POST `/api/whatsapp/link/unlink` - Remove link

### 3. Natural Language Command Parser (`backend/services/command_parser.py`)
- Intent detection for 20+ command types
- Extracts: property name, floor numbers, parameters
- Patterns: "Close F7 in Horizon", "What if we shut floor 2?", "Simulate closing F3"

### 4. PDF Report Generator (`backend/services/pdf_generator.py`)
- Property reports with user override state
- Executive summary across portfolio
- Energy savings reports
- APIs:
  - GET `/api/reports/property/{property_id}/pdf`
  - GET `/api/reports/executive-summary/pdf`
  - GET `/api/reports/energy/{property_id}/pdf`

---

## WhatsApp Commands

### Floor Control (Requires Account Linking)
- `Close F7 in Horizon` - Close floor 7
- `Open floor 3` - Reopen floor 3
- `Close floors 2,4,5` - Close multiple floors

### Simulation (Requires Account Linking)
- `Simulate closing F3` - Run what-if analysis
- `What if we shut floor 2?` - What-if scenario
- `Run optimization` - Get optimization insights

### Analytics (Requires Account Linking)
- `Show dashboard` - Portfolio overview
- `Executive summary` - Full summary
- `Horizon details` - Property analytics
- `Energy report Horizon` - Energy analysis

### Reports (Requires Account Linking)
- `Download PDF` - Get summary report
- `Energy report` - Energy savings PDF

### Reset (Requires Account Linking)
- `Reset Horizon` - Reset property state
- `Reset all` - Reset all overrides
- `Undo` - Revert last change

### Alerts
- `Alerts` - View active alerts
- `Subscribe` - Enable auto-alerts
- `Unsubscribe` - Disable alerts

### General (No Auth Required)
- `List` - Show all properties
- `Status` - System status
- `Help` - Show all commands

---

## Response Format (WhatsApp)

Every WhatsApp response includes:
- Monthly savings (₹ formatted)
- Efficiency change
- Energy reduction %
- Carbon reduction
- Risk assessment
- Confidence score

---

## Architecture

```
MongoDB Collections:
├── user_property_states (per-user floor closures)
├── whatsapp_user_mapping (phone-to-user links)
├── whatsapp_otp_codes (verification codes, auto-expire)
├── whatsapp_conversations (chat history)
├── alert_subscriptions (alert subscribers)
├── alert_logs (sent alerts)
├── user_change_log (audit trail)
└── user_sessions (session tracking)

Frontend Context:
└── PropertyStateContext (global state management)
    ├── userStates
    ├── properties
    ├── closeFloors()
    ├── openFloors()
    ├── toggleFloor()
    ├── resetProperty()
    └── getClosedFloors()

Services:
├── UserPropertyStateService
├── WhatsAppLinkingService
├── CommandParser
├── PDFReportGenerator
├── AlertScheduler
├── ConversationHistory
└── ChangeLogService
```

---

## Test Coverage

### Test Report: iteration_8.json
- **Backend**: 17/17 tests passed (100%)
- **Frontend**: All UI elements verified (100%)
- **Test File**: `/app/backend/tests/test_global_state_sync.py`

### Verified Features:
- Global state context initialization
- Floor closure persistence to backend
- State reflection on Dashboard, Executive, Portfolio, PropertyDetail pages
- FloorPlanVisualization shows closed floors with visual indicators
- Reset functionality works correctly
- All API endpoints working

---

## Prioritized Backlog

### P0 (Critical) - Completed
- [x] Global State Synchronization
- [x] Authentication flow
- [x] Property CRUD
- [x] Dashboard with KPIs
- [x] Floor closure simulation
- [x] WhatsApp integration
- [x] Change logging
- [x] PDF reports

### P1 (High) - Future
- [ ] Real-time data updates (WebSocket)
- [ ] Enhanced AI recommendation engine with user context
- [ ] Mobile app version

### P2 (Medium) - Future
- [ ] Historical comparison reports
- [ ] Custom date range analytics
- [ ] Booking system integration
- [ ] Multi-language support

---

## Environment Variables

### Backend (`/app/backend/.env`)
```
MONGO_URL=<mongodb_url>
DB_NAME=proptech_copilot
TWILIO_ACCOUNT_SID=<twilio_sid>
TWILIO_AUTH_TOKEN=<twilio_token>
TWILIO_WHATSAPP_NUMBER=<whatsapp_number>
```

### Frontend (`/app/frontend/.env`)
```
REACT_APP_BACKEND_URL=<preview_url>
```

---

## Technical Stack

- **Backend**: FastAPI, MongoDB (Motor async), Twilio, ReportLab, APScheduler
- **Frontend**: React 18, Tailwind CSS, Chart.js, Recharts, Shadcn/UI
- **State Management**: React Context (PropertyStateContext)
- **Authentication**: Emergent-managed Google OAuth
- **Database**: MongoDB Atlas

---

## Changelog

### v1.3.0 (2026-02-13) - Global State Sync
- Implemented PropertyStateContext for unified state management
- Updated all pages to consume global state
- Added "Active Optimizations" indicators across Dashboard, Executive, Portfolio
- FloorPlanVisualization now shows closed floors with visual indicators
- Tested with 100% pass rate

### v1.2.0 (2026-02-13) - Change Logging
- Added user_change_log MongoDB collection
- Session tracking with change history
- Frontend useAutoSave hook

### v1.1.0 (2026-02-12) - WhatsApp & Multi-User
- Twilio WhatsApp integration
- Natural language command parser
- Per-user property state isolation
- PDF report generation

### v1.0.0 (2026-02-12) - Initial Release
- Google OAuth authentication
- Property portfolio management
- Digital twin visualization
- Floor closure simulation
- AI recommendations
