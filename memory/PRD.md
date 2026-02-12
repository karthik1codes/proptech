# PropTech Decision Copilot - Product Requirements Document

## Latest Update: February 12, 2026

### Backlog Implementation Complete: WhatsApp Enhanced Features

**Features Implemented:**

1. **WhatsApp Message Templates** (`backend/services/whatsapp_service.py`)
   - `MessageTemplates` class with pre-defined templates
   - Templates: welcome, help_menu, property_list, property_details, alert_notification, active_alerts, no_alerts, error_message
   - Consistent formatting with emojis and separators

2. **Conversation History Persistence** (`backend/services/conversation_history.py`)
   - MongoDB collection: `whatsapp_conversations`
   - Saves all inbound/outbound messages with metadata
   - APIs: GET `/api/whatsapp/conversations/{phone_number}`, GET `/api/whatsapp/conversations?query=`
   - Features: search, user stats, context retrieval

3. **Scheduled Alert Checks** (`backend/services/alert_scheduler.py`)
   - Background task runs every 30 minutes (configurable via `ALERT_CHECK_INTERVAL`)
   - Checks all properties against thresholds
   - Sends alerts to subscribed phone numbers
   - MongoDB collections: `alert_subscriptions`, `alert_logs`
   - APIs: 
     - POST `/api/whatsapp/alerts/subscribe`
     - POST `/api/whatsapp/alerts/unsubscribe`
     - GET `/api/whatsapp/alerts/subscriptions`
     - GET `/api/whatsapp/alerts/history`
     - POST `/api/whatsapp/alerts/check-now`

4. **New WhatsApp Commands**
   - `alerts` - View active alerts across all properties
   - `status` - System status (scheduler, subscribers, properties)
   - `subscribe` - Subscribe to automated alerts
   - `unsubscribe` - Unsubscribe from alerts

---

### Previous Upgrade: Clean MCP Implementation & WhatsApp Integration

**Changes Made:**
1. **MCP Endpoint Cleanup**
   - Moved MCP to root-level `/mcp` (also accessible at `/api/mcp` for external access)
   - Updated response format with `annotations: []` and `isError` fields
   - Removed OpenAI-exclusive MCP server and related endpoints
   - MCP reuses existing analytics engine functions
   - MCP does NOT require authentication

2. **Twilio WhatsApp Integration Added**
   - New service module: `backend/services/whatsapp_service.py`
   - Webhook endpoint: `POST /whatsapp/webhook` and `/api/whatsapp/webhook`
   - Authenticated send endpoint: `POST /api/whatsapp/send`
   - Property alert system: `POST /api/whatsapp/alert`
   - Status check: `GET /api/whatsapp/status`
   
   **Alert Thresholds:**
   - High Occupancy: > 90%
   - Low Utilization: < 40%
   - Energy Spike: > 15%

   **Environment Variables Required:**
   - `TWILIO_ACCOUNT_SID`
   - `TWILIO_AUTH_TOKEN`
   - `TWILIO_WHATSAPP_NUMBER`
   - `ALERT_CHECK_INTERVAL` (optional, default: 1800 seconds)

---

## Overview
**Product Name:** PropTech Decision Copilot  
**Version:** 1.0.0  
**Last Updated:** 2026-02-12  

## Problem Statement
Build a production-ready full-stack AI PropTech Decision Copilot with Google OAuth authentication, dynamic property portfolio management, advanced visualization, quantified optimization engine, and enterprise-grade UI.

## User Personas
1. **Real Estate Managers** - Need occupancy tracking and portfolio oversight
2. **Facility Managers** - Focus on energy optimization and maintenance
3. **Operations Teams** - Day-to-day property management decisions
4. **C-Suite Executives** - Strategic overview and ROI insights

## Core Requirements

### Authentication
- [x] Google OAuth via Emergent Auth
- [x] Session management with secure cookies
- [x] Protected API routes

### Property Portfolio System
- [x] In-memory property store with 3 preloaded properties
- [x] Digital twin generation (90-day occupancy, energy, bookings)
- [x] Add new property feature
- [x] Property search and filtering

### Intelligence Engine
- [x] 7-day occupancy forecasting with moving average
- [x] Utilization classification (Underutilized/Optimal/Overloaded)
- [x] Financial model (Revenue, Energy, Maintenance, Profit)
- [x] Energy savings calculator
- [x] What-if floor closure simulator
- [x] Utilization efficiency score

### Visualization
- [x] Interactive floor plan with room-level metrics
- [x] Occupancy trend charts (30-day history, 7-day forecast)
- [x] Energy comparison charts
- [x] Portfolio benchmarking with rankings

### Currency Localization
- [x] Indian Rupee (₹) formatting
- [x] Lakhs & Crores notation

## What's Been Implemented (2026-02-12)

### Backend (FastAPI)
- `/api/auth/session` - Exchange session_id for token
- `/api/auth/me` - Get current user
- `/api/auth/logout` - Clear session
- `/api/properties` - List all properties
- `/api/properties/{id}` - Get property details with digital twin
- `/api/properties` (POST) - Add new property
- `/api/analytics/dashboard` - Dashboard KPIs
- `/api/analytics/portfolio-benchmark` - Property rankings
- `/api/analytics/simulate-floor-closure` - What-if simulator
- `/api/analytics/energy-savings/{id}` - Energy optimization scenarios
- `/api/recommendations/{id}` - AI recommendations
- `/api/copilot/{id}` - Copilot insight per property
- `/api/copilot/executive-summary` - Portfolio-wide executive summary

### Frontend (React)
- Login page with Google OAuth
- Dashboard with KPI cards and charts
- Property Portfolio page with search/filter
- Property Detail page with tabs (Overview, Floor Plan, Energy, Recommendations)
- Scenario Simulator with floor selection and hybrid intensity
- Executive Summary with benchmarking table

### Design System
- Dark mode default with light mode toggle
- Glassmorphism effects
- Animated counters
- Color-coded utilization indicators
- Responsive bento grid layout

## Prioritized Backlog

### P0 (Critical) - Done
- [x] Authentication flow
- [x] Property CRUD
- [x] Dashboard with KPIs
- [x] Floor closure simulation

### P1 (High) - Future
- [ ] Real-time data updates (WebSocket)
- [ ] Export reports to PDF
- [ ] Email alerts for utilization thresholds
- [ ] Multi-user property sharing

### P2 (Medium) - Future
- [ ] Historical comparison reports
- [ ] Custom date range analytics
- [ ] Booking system integration
- [ ] Mobile app version

## Next Tasks
1. Add unit tests for backend APIs
2. Implement real-time occupancy updates
3. Add PDF export for executive reports
4. Integrate with building management systems

---

## Update: v1.1.0 (2026-02-12) - MCP Integration & Premium UI

### New Features

#### MCP (Model Context Protocol) Integration
- Added `/api/mcp` endpoint for AI assistant integration (ChatGPT, Claude)
- JSON-RPC style protocol with 5 tools:
  - `list_properties` - Portfolio overview with all properties
  - `get_property_overview` - Detailed property metrics
  - `simulate_floor_closure` - What-if scenario analysis
  - `energy_savings_report` - Energy optimization scenarios
  - `get_recommendations` - AI recommendations with impact analysis
- All responses formatted in markdown for better AI consumption
- See README.md for ngrok/Cloudflare tunnel instructions

#### Dark Mode Only - Premium UI
- Removed light mode toggle (dark mode permanent)
- Deep dark gradient backgrounds
- Glassmorphism cards with blur effects
- Cyan/blue glow accents
- Animated gradient borders on hover
- Premium loading spinner
- Polished navigation with active state indicators
- Enhanced login page with stats and features showcase

### Technical Changes
- Backend: Added MCPHandler class with tool implementations
- Frontend: Removed ThemeContext, updated all components for dark-only
- CSS: New premium variables, glassmorphism utilities, glow effects
- README: Added MCP documentation section

### Breaking Changes
- None - OAuth and all existing APIs work unchanged
