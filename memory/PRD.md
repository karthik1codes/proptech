# Infranomic Decision Copilot - Product Requirements Document

## Latest Update: February 13, 2026

### COMPLETED: Major Feature Upgrade

#### 1. App Rebranding
- Changed app name from "PropTech" to "Infranomic" across all pages
- Updated: Login page, Header/Navigation, Footer, PDF reports

#### 2. AI-Powered Risk Analysis (OpenAI GPT Integration)
- 5-6 AI recommendations per property based on location-specific risks
- Comprehensive risk analysis with mitigation strategies
- Location-based risks for Indian cities:
  - **Bangalore**: Water scarcity, traffic congestion, IT sector dependency
  - **Mumbai**: Flooding, coastal erosion, high real estate costs
  - **Hyderabad**: Drought, rapid urbanization, water scarcity

#### 3. Location-Specific Carbon Emissions
- Regional grid emission factors:
  - Southern grid (Bangalore, Hyderabad): 0.82 kg CO₂/kWh
  - Western grid (Mumbai): 0.79 kg CO₂/kWh

#### 4. Enhanced Dashboard
- Property Risk Analysis cards with:
  - Risk score and risk level (LOW/MEDIUM/HIGH/CRITICAL)
  - Top risks with severity levels
  - Carbon emissions with grid factor
  - Efficiency metrics
- Active Optimizations banner now shows property names

#### 5. PDF Reports
- Updated branding to Infranomic
- New Risk Analysis section with:
  - Per-property risk levels
  - Top risks by location
  - Risk mitigation recommendations

---

## New API Endpoints

### AI Analysis Endpoints

```
GET /api/ai/recommendations/{property_id}
Returns: 5-6 AI-generated recommendations with:
- type, priority, title, description
- financial_impact, energy_reduction_percent
- carbon_reduction_kg, efficiency_improvement
- confidence_score, risk_factor, mitigation_strategy

GET /api/ai/risk-analysis/{property_id}
Returns:
- overall_risk_score (0-100)
- risk_level (LOW/MEDIUM/HIGH/CRITICAL)
- key_risks (array of top 5)
- mitigation_strategies
- opportunities
- climate_resilience_score
- recommendation_summary

GET /api/ai/carbon-analysis/{property_id}
Returns:
- city, region
- grid_emission_factor (kg CO₂/kWh)
- monthly_carbon_kg
- annual_carbon_tons
- carbon_reduction_potential

GET /api/ai/portfolio-risk
Returns portfolio-wide risk analysis

GET /api/analytics/dashboard-with-ai
Enhanced dashboard with per-property:
- risk_score, risk_level, top_risks
- carbon_kg, carbon_factor
- efficiency, closed_floors
```

---

## Architecture

```
/app/
├── backend/
│   ├── .env (includes EMERGENT_LLM_KEY)
│   ├── server.py (main API with AI endpoints)
│   └── services/
│       ├── ai_risk_service.py (NEW - OpenAI GPT integration)
│       ├── pdf_generator.py (updated with risk section)
│       └── ... (other services)
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── LoginPage.js (Infranomic branding)
│       │   ├── Dashboard.js (Risk Analysis cards)
│       │   ├── ExecutiveSummary.js
│       │   └── PropertyPortfolio.js
│       └── components/
│           └── Layout.js (Infranomic header)
```

---

## Location Risk Data

| Location | Climate | Top Risks | Grid Factor |
|----------|---------|-----------|-------------|
| Bangalore | Tropical Savanna | Water Scarcity (0.8), Traffic (0.85), IT Dependency (0.6) | 0.82 |
| Mumbai | Tropical Monsoon | Flooding (0.95), Coastal Erosion (0.75), RE Costs (0.9) | 0.79 |
| Hyderabad | Semi-Arid | Drought (0.75), Urbanization (0.8), Water (0.7) | 0.82 |

---

## Test Coverage

### Test Report: iteration_9.json
- **Backend**: 18/19 tests passed (95%)
- **Frontend**: 100% UI elements verified

### Verified Features:
- Infranomic branding on login, header, dashboard, footer
- Property Risk Analysis cards on Dashboard
- AI recommendations endpoint returns 5-6 items
- AI risk analysis returns comprehensive data
- Location-specific carbon factors working
- PDF report includes risk analysis section

---

## Previous Features (Still Active)

### Global State Synchronization
- PropertyStateContext for unified state management
- Changes in Simulator reflect across all pages
- Dashboard shows active optimizations with property names

### WhatsApp Integration
- Conversational bot via Twilio
- Natural language command parser
- Per-user state management
- **Webhook URL**: `{BACKEND_URL}/api/whatsapp/webhook`
- Configure this in Twilio Console → WhatsApp Sandbox → Webhook URL

### Change Logging
- Audit trail in user_change_log collection
- Session tracking

---

## Environment Variables

### Backend (`/app/backend/.env`)
```
MONGO_URL=<mongodb_url>
DB_NAME=proptech_copilot
EMERGENT_LLM_KEY=sk-emergent-xxx
TWILIO_ACCOUNT_SID=<twilio_sid>
TWILIO_AUTH_TOKEN=<twilio_token>
TWILIO_WHATSAPP_NUMBER=<number>
```

---

## Changelog

### v1.4.0 (2026-02-13) - Major Upgrade
- Rebranded app from PropTech to Infranomic
- Added AI-powered risk analysis with OpenAI GPT
- Location-specific carbon emission factors
- Property Risk Analysis cards on Dashboard
- 5-6 AI recommendations per property
- PDF reports with risk analysis section
- Active optimizations show property names

### v1.3.0 (2026-02-13) - Global State Sync
- PropertyStateContext for unified state management
- All pages consume global state

### v1.2.0 (2026-02-13) - Change Logging
- user_change_log MongoDB collection
- Session tracking

### v1.1.0 (2026-02-12) - WhatsApp Integration
- Twilio WhatsApp integration
- Natural language command parser
