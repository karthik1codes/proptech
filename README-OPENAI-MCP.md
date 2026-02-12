# OpenAI-Exclusive MCP Server Configuration

## Overview

This MCP (Model Context Protocol) server routes **ALL** model inference requests **exclusively to OpenAI's ChatGPT API (GPT-5.2)**. 

**Architecture:** Single-provider design - No multi-model routing, no fallbacks.

---

## Server URL

```
Production HTTPS Endpoint:
https://ai-real-estate-4.preview.emergentagent.com/api/mcp/openai
```

### Available Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/mcp/openai` | MCP JSON-RPC endpoint (tools/call, initialize, etc.) |
| `POST /api/mcp/openai/chat/completions` | Direct chat completions (OpenAI-style response) |

---

## Configuration JSON

```json
{
  "mcpServers": {
    "openai-proptech": {
      "url": "https://ai-real-estate-4.preview.emergentagent.com/api/mcp/openai",
      "transport": "http",
      "headers": {
        "Content-Type": "application/json"
      },
      "provider": "openai",
      "model": "gpt-5.2",
      "protocolVersion": "1.0.0",
      "capabilities": {
        "tools": true,
        "chat_completion": true,
        "multi_turn_conversation": true,
        "system_messages": true
      }
    }
  }
}
```

---

## Required Headers

```
Content-Type: application/json
```

**Note:** Authentication is handled server-side via the `OPENAI_API_KEY` environment variable. No client-side API key required.

---

## Available Tools

### 1. `chat_completion`
Send a message to OpenAI GPT-5.2 and get a response.

**Input Schema:**
```json
{
  "messages": [
    {"role": "user", "content": "Your message here"}
  ],
  "session_id": "optional-session-id",
  "system_message": "Optional custom system prompt",
  "temperature": 0.7
}
```

### 2. `get_model_info`
Get information about the configured OpenAI model.

### 3. `health_check`
Check if the OpenAI MCP server is operational.

---

## Example API Calls

### 1. Initialize Connection (MCP Standard)

```bash
curl -X POST "https://ai-real-estate-4.preview.emergentagent.com/api/mcp/openai" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "initialize"
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "protocolVersion": "1.0.0",
    "serverInfo": {
      "name": "openai-mcp-server",
      "version": "1.0.0",
      "description": "OpenAI-Exclusive MCP Server - Routes ALL requests to OpenAI GPT-5.2 ONLY"
    },
    "capabilities": {
      "tools": {"listChanged": false},
      "provider": "openai",
      "model": "gpt-5.2",
      "features": ["chat_completion", "multi_turn_conversation", "system_messages"]
    }
  }
}
```

### 2. List Available Tools

```bash
curl -X POST "https://ai-real-estate-4.preview.emergentagent.com/api/mcp/openai" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "tools/list"
  }'
```

### 3. Chat Completion via MCP Tool Call

```bash
curl -X POST "https://ai-real-estate-4.preview.emergentagent.com/api/mcp/openai" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "3",
    "method": "tools/call",
    "params": {
      "name": "chat_completion",
      "arguments": {
        "messages": [
          {"role": "user", "content": "What is the capital of France?"}
        ],
        "session_id": "my-conversation",
        "system_message": "You are a helpful geography assistant."
      }
    }
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "The capital of France is Paris."
      }
    ],
    "isError": false
  }
}
```

### 4. Direct Chat Completions (OpenAI-Style)

```bash
curl -X POST "https://ai-real-estate-4.preview.emergentagent.com/api/mcp/openai/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Explain quantum computing in one sentence."}
    ],
    "session_id": "science-chat",
    "system_message": "You are a physics professor.",
    "temperature": 0.5
  }'
```

**Response:**
```json
{
  "id": "chatcmpl-abc123def456",
  "object": "chat.completion",
  "created": 1770915099,
  "model": "gpt-5.2",
  "provider": "openai",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Quantum computing harnesses quantum mechanical phenomena like superposition and entanglement to perform computations exponentially faster than classical computers for certain problems."
      },
      "finish_reason": "stop"
    }
  ],
  "session_id": "science-chat"
}
```

### 5. Health Check

```bash
curl -X POST "https://ai-real-estate-4.preview.emergentagent.com/api/mcp/openai" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "4",
    "method": "tools/call",
    "params": {
      "name": "health_check",
      "arguments": {}
    }
  }'
```

---

## Multi-Turn Conversation Example

```bash
# First message
curl -X POST "https://ai-real-estate-4.preview.emergentagent.com/api/mcp/openai/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "My name is Alex."}],
    "session_id": "conversation-123"
  }'

# Follow-up (same session)
curl -X POST "https://ai-real-estate-4.preview.emergentagent.com/api/mcp/openai/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is my name?"}],
    "session_id": "conversation-123"
  }'
# Response will remember: "Your name is Alex."
```

---

## Security Notes

1. **API Key Storage:** The OpenAI API key is stored securely as an environment variable (`OPENAI_API_KEY`) on the server. It is never exposed to clients.

2. **No Client-Side Keys Required:** Clients do not need to provide any API keys - authentication is handled server-side.

3. **HTTPS Only:** All endpoints use HTTPS encryption in transit.

4. **Single Provider Architecture:** No multi-model routing logic eliminates complexity and potential security vectors.

5. **Session Isolation:** Each `session_id` maintains its own conversation context, isolated from other sessions.

6. **Rate Limiting:** Subject to OpenAI API rate limits for the configured account tier.

---

## Error Handling

All errors follow JSON-RPC 2.0 error format:

```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "error": {
    "code": -32603,
    "message": "Error description"
  }
}
```

| Error Code | Description |
|------------|-------------|
| -32600 | Invalid Request |
| -32601 | Method not found |
| -32602 | Invalid params |
| -32603 | Internal error |

---

## Technical Specifications

| Property | Value |
|----------|-------|
| Protocol | MCP 1.0.0 |
| Transport | HTTP/HTTPS |
| Provider | OpenAI (exclusive) |
| Model | gpt-5.2 |
| Supported Features | Chat completions, multi-turn, system messages |
| Response Format | JSON-RPC 2.0 |
