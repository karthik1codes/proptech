# PropTech Decision Copilot

AI-powered property portfolio management platform with MCP (Model Context Protocol) support.

## Features

- **Google OAuth Authentication** via Emergent Auth
- **Real-time Dashboard** with KPIs and occupancy tracking  
- **Property Portfolio Management** with digital twin data
- **What-If Scenario Simulator** for floor closure analysis
- **Energy Savings Calculator** with weekly/monthly projections
- **AI Recommendations Engine** with confidence scores
- **Executive Summary** with portfolio benchmarking
- **MCP Integration** for AI assistant connectivity

## Tech Stack

- **Frontend**: React + Tailwind CSS
- **Backend**: FastAPI (Python)
- **Database**: MongoDB (sessions only), In-memory property store
- **Auth**: Emergent Google OAuth

## MCP (Model Context Protocol) Integration

The PropTech Decision Copilot exposes an MCP endpoint that allows AI assistants (like ChatGPT, Claude) to interact with your property data.

### Endpoint

```
POST /api/mcp
Content-Type: application/json
```

### Available Tools

| Tool | Description |
|------|-------------|
| `list_properties` | Returns all properties with name, location, occupancy, profit (₹), efficiency score |
| `get_property_overview` | Get detailed overview including revenue, profit, sustainability, efficiency, carbon estimate |
| `simulate_floor_closure` | Simulate closing floors and get weekly/monthly savings, energy reduction, carbon impact |
| `energy_savings_report` | Get energy savings analysis with scenarios |
| `get_recommendations` | Get AI recommendations with financial impact and confidence scores |

### Example Request

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "list_properties",
    "arguments": {}
  },
  "id": 1
}
```

### Example Response

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "# Property Portfolio Overview\n\n## Horizon Tech Park\n- **Location**: Bangalore, Karnataka\n- **Occupancy**: 63.1%\n- **Profit**: ₹11.46 L\n- **Efficiency Score**: 100%\n..."
      }
    ]
  }
}
```

### Exposing MCP via ngrok (for ChatGPT/Claude integration)

To make your MCP endpoint accessible to external AI assistants:

#### Option 1: ngrok

1. Install ngrok: https://ngrok.com/download

2. Start ngrok tunnel:
```bash
ngrok http 8001
```

3. Use the generated URL (e.g., `https://abc123.ngrok.io/api/mcp`) as your MCP server URL

#### Option 2: Cloudflare Tunnel

1. Install cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/

2. Create tunnel:
```bash
cloudflared tunnel --url http://localhost:8001
```

3. Use the generated URL with `/api/mcp` path

### Testing MCP Locally

```bash
curl -X POST http://localhost:8001/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

## Environment Variables

### Backend (.env)
```
MONGO_URL=<your-mongodb-url>
DB_NAME=<database-name>
```

### Frontend (.env)
```
REACT_APP_BACKEND_URL=<backend-url>
```

## Running Locally

The application runs on:
- Frontend: http://localhost:3000
- Backend: http://localhost:8001

## API Endpoints

### Authentication
- `POST /api/auth/session` - Exchange session_id for token
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - Logout

### Properties
- `GET /api/properties` - List all properties
- `GET /api/properties/{id}` - Get property details
- `POST /api/properties` - Add new property

### Analytics
- `GET /api/analytics/dashboard` - Dashboard KPIs
- `GET /api/analytics/portfolio-benchmark` - Property rankings
- `POST /api/analytics/simulate-floor-closure` - What-if simulation
- `GET /api/analytics/energy-savings/{id}` - Energy scenarios

### Recommendations
- `GET /api/recommendations/{id}` - AI recommendations
- `GET /api/copilot/{id}` - Copilot insights
- `GET /api/copilot/executive-summary` - Executive summary

### MCP
- `POST /api/mcp` - MCP endpoint for AI assistant integration

## Currency Format

All financial metrics are displayed in Indian Rupees (₹) with Lakhs/Crores notation:
- ₹14,00,000 → ₹14 L
- ₹1,05,00,000 → ₹1.05 Cr

## License

MIT
