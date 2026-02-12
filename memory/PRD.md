# PropTech Decision Copilot - Product Requirements Document

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
