# LMArena Bridge - Complete User Manual

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [First-Time Setup](#first-time-setup)
4. [Using the GUI](#using-the-gui)
5. [Using the API](#using-the-api)
6. [Advanced Configuration](#advanced-configuration)
7. [Troubleshooting](#troubleshooting)
8. [FAQ](#faq)

---

## Introduction

LMArena Bridge allows you to use LMArena models through an OpenAI-compatible API. This means you can:

- Use LMArena models with existing tools (SillyTavern, LibreChat, etc.)
- Write scripts using the OpenAI SDK
- Manage everything through a user-friendly GUI

### How It Works

```
Your App → OpenAI API → LMArena Bridge → Browser (Tampermonkey) → LMArena
```

The bridge acts as a middleman, translating OpenAI-style requests into LMArena actions.

---

## Installation

### Step 1: Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3-gi gir1.2-gtk-4.0 libgtk-4-dev git python3-venv
```

**Fedora:**
```bash
sudo dnf install python3-gobject gtk4 git python3-virtualenv
```

**Arch Linux:**
```bash
sudo pacman -S python-gobject gtk4 git python-virtualenv
```

### Step 2: Clone and Install

```bash
git clone https://github.com/Lianues/LMArenaBridge.git
cd LMArenaBridge
make install-gui
```

This will:
- Create a virtual environment
- Install all Python dependencies
- Set up the application

### Step 3: Install Tampermonkey Script

1. Install [Tampermonkey](https://www.tampermonkey.net/) browser extension
2. Open `public/userscripts/LMArenaApiBridge.user.js` in a text editor
3. Copy the entire contents
4. Open Tampermonkey dashboard → "Create new script"
5. Paste and save

---

## First-Time Setup

### Launch the GUI

```bash
make gui
```

You'll see the **Setup Wizard** on first run.

### Setup Wizard Steps

#### Step 1: Start Server

Click "Start Server" in the GUI toolbar.

Wait until the status indicator turns **green** (✅).

#### Step 2: Connect Browser

1. Click "Open LMArena in Browser" in the wizard
2. Log in to LMArena if needed
3. The wizard will detect the connection automatically

**Verification:** Status changes to "✅ Connected"

#### Step 3: Capture Session IDs

LMArena uses session IDs to track conversations. We need to capture one:

1. In the wizard, click "Start ID Capture"
2. Go to LMArena in your browser
3. Start any conversation (or open an existing one)
4. Click the **"Retry"** button (⟳) next to any message

**Verification:** Wizard shows "✅ IDs Captured!"

#### Step 4: Refresh Models (Optional)

Click "Request Model Update" to get the latest model list from LMArena.

This creates `config/available_models.json` with all current models.

#### Step 5: Complete

Click "Close" in the wizard. You're ready to go!

---

## Using the GUI

### Main Window Overview

```
┌─────────────────────────────────────────┐
│ [●] LMArena Bridge          [≡]         │  ← Header bar
├─────────────────────────────────────────┤
│ [Start] [Stop] │ [Open] [IDs] [Models]  │  ← Toolbar
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │ Chat │ Config │ Models │ Map │ Logs │ │  ← Tabs
│ └─────────────────────────────────────┘ │
│                                         │
│         (Tab content here)              │
│                                         │
├─────────────────────────────────────────┤
│ Status: Connected │ Clients: client-123 │  ← Status bar
└─────────────────────────────────────────┘
```

### Tab 1: Chat Playground

**Purpose:** Test models interactively

**How to use:**
1. Select a model from dropdown
2. (Optional) Enter a system prompt
3. Type your message
4. Click "Send" or press Enter
5. See streaming response in real-time

**Features:**
- Chat history is preserved during session
- "Clear History" starts fresh
- "↻" button refreshes model list

**Example:**
```
System Prompt: You are a pirate
Your Message: Tell me about the ocean
[Response streams here]
```

### Tab 2: Configuration

**Purpose:** Edit all settings in one place

**Sections:**

1. **Session Settings**
   - Session ID / Message ID (captured via wizard)
   
2. **Operation Mode**
   - Direct Chat: Normal 1-on-1 conversation
   - Battle: Use battle arena mode
   - Battle Target: Which assistant (A or B)

3. **Features**
   - Bypass Mode: Inject empty message (helps with filters)
   - Tavern Mode: Merge system prompts (for character cards)
   - Auto-update: Check for new versions on start
   - Auto-open browser: Launch LMArena on start

4. **File Bed** (Advanced)
   - Upload images to external server before sending
   - Useful if LMArena rejects large base64 data

5. **Advanced**
   - Server port (default: 5102)
   - Stream timeout (default: 360s)
   - API Key (optional security)

**Actions:**
- "Save Configuration" → Write to disk
- "Reload" → Revert to saved values

### Tab 3: Models

**Purpose:** Manage available models

**Actions:**

- **Add Model:**
  1. Click "Add Model"
  2. Enter name (e.g., "gpt-4")
  3. Enter LMArena model ID (UUID)
  4. Choose type (text or image)
  5. Click "Save"

- **Edit Model:**
  1. Select model in list
  2. Click "Edit"
  3. Modify and save

- **Delete Model:**
  1. Select model
  2. Click "Delete"
  3. Confirm

- **Refresh from Server:**
  - Requests page source from browser
  - Extracts all available models
  - Saves to `available_models.json`

**Model ID format:**
- UUID only: `e2d9d353-6dbe-4414-bf87-bd289d523726`
- With type: `e2d9d353-6dbe-4414-bf87-bd289d523726:text`
- No ID (for templates): `null:image`

### Tab 4: Endpoint Mapping

**Purpose:** Map specific models to different sessions/modes

**Use case:** You want different models to use different LMArena sessions or modes.

**Example:**
```json
{
  "gpt-5-analysis": {
    "session_id": "abc-123",
    "message_id": "def-456",
    "mode": "direct_chat"
  },
  "gpt-5-creative": {
    "session_id": "xyz-789",
    "message_id": "uvw-012",
    "mode": "battle",
    "battle_target": "A"
  }
}
```

Now `gpt-5-analysis` and `gpt-5-creative` use different sessions.

**Actions:**
- **Add Mapping:** Define model → session relationship
- **Edit Mapping:** Modify existing
- **Delete Mapping:** Remove (falls back to global config)

### Tab 5: Logs

**Purpose:** View server output in real-time

**Features:**
- **Search:** Filter logs by keyword
- **Clear:** Wipe current logs
- **Save:** Export to file

**What to look for:**
- `✅ Oil monkey script connected` → Browser connected
- `API CALL [ID: abc12345]` → New request received
- `STREAMER [ID: abc12345]` → Streaming response
- `❌` or `ERROR` → Problems

---

## Using the API

### Starting the Server

**GUI:** Click "Start Server"

**CLI:**
```bash
make run
```

**Systemd (background):**
```bash
systemctl --user enable --now lmarena-bridge.service
```

### Endpoints

Base URL: `http://127.0.0.1:5102`

#### GET /v1/models

List available models.

**Request:**
```bash
curl http://127.0.0.1:5102/v1/models
```

**Response:**
```json
{
  "object": "list",
  "data": [
    {"id": "gemini-2.5-pro", "object": "model", "created": 1234567890, "owned_by": "LMArenaBridge"},
    {"id": "gpt-5", "object": "model", "created": 1234567890, "owned_by": "LMArenaBridge"}
  ]
}
```

#### POST /v1/chat/completions

Send a chat request.

**Request (streaming):**
```bash
curl -X POST http://127.0.0.1:5102/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-pro",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

**Response (SSE):**
```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1234567890,"model":"gemini-2.5-pro","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1234567890,"model":"gemini-2.5-pro","choices":[{"index":0,"delta":{"content":"!"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1234567890,"model":"gemini-2.5-pro","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

**Request (non-streaming):**
```json
{
  "model": "gemini-2.5-pro",
  "messages": [{"role": "user", "content": "Hello!"}],
  "stream": false
}
```

**Response:**
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "gemini-2.5-pro",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "Hello! How can I help?"},
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 0, "completion_tokens": 5, "total_tokens": 5}
}
```

### Using with OpenAI SDK

**Python:**
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:5102/v1",
    api_key="dummy"  # Required by SDK, not used unless you set one in config
)

# Streaming
stream = client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[{"role": "user", "content": "Count to 5"}],
    stream=True
)

for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")

# Non-streaming
response = client.chat.completions.create(
    model="gpt-5",
    messages=[{"role": "user", "content": "What is 2+2?"}],
    stream=False
)

print(response.choices[0].message.content)
```

**Node.js:**
```javascript
import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'http://127.0.0.1:5102/v1',
  apiKey: 'dummy'
});

const response = await client.chat.completions.create({
  model: 'gemini-2.5-pro',
  messages: [{role: 'user', content: 'Hello!'}],
  stream: true
});

for await (const chunk of response) {
  process.stdout.write(chunk.choices[0]?.delta?.content || '');
}
```

### Using with Third-Party Tools

#### SillyTavern

1. Go to **Settings → API Connections**
2. Select **"Chat Completion (OpenAI-compatible)"**
3. Set **API URL:** `http://127.0.0.1:5102/v1`
4. Set **API Key:** (whatever you set in config, or leave blank)
5. Click **"Connect"**

#### LibreChat

In `.env`:
```bash
OPENAI_API_KEY=dummy
OPENAI_REVERSE_PROXY=http://127.0.0.1:5102/v1
```

#### Continue.dev (VSCode)

In `~/.continue/config.json`:
```json
{
  "models": [{
    "title": "LMArena Gemini",
    "provider": "openai",
    "model": "gemini-2.5-pro",
    "apiBase": "http://127.0.0.1:5102/v1"
  }]
}
```

---

## Advanced Configuration

### Config File Locations

**Priority:**
1. `LMABRIDGE_CONFIG_DIR` environment variable
2. `./config/` (if exists, for development)
3. `~/.config/lmarena-bridge/` (default for production)

**Override example:**
```bash
export LMABRIDGE_CONFIG_DIR=/custom/path
make run
```

### config.jsonc Explained

```jsonc
{
  // Version (don't modify manually)
  "version": "3.0.0",

  // Captured via GUI wizard or id_updater.py
  "session_id": "uuid-here",
  "message_id": "uuid-here",

  // Operation mode: "direct_chat" or "battle"
  "id_updater_last_mode": "direct_chat",
  
  // Battle target: "A" or "B"
  "id_updater_battle_target": "A",

  // Check GitHub for updates on start
  "enable_auto_update": true,

  // Inject empty user message (bypass some filters)
  "bypass_enabled": true,

  // Merge all system messages into one (for character cards)
  "tavern_mode_enabled": false,

  // Use external file bed for images
  "file_bed_enabled": false,
  "file_bed_upload_url": "http://127.0.0.1:5180/upload",
  "file_bed_api_key": "secret",

  // Fallback to default IDs if model not in endpoint map
  "use_default_ids_if_mapping_not_found": true,

  // How long to wait for response chunks (seconds)
  "stream_response_timeout_seconds": 360,

  // Auto-restart if idle (disabled by default)
  "enable_idle_restart": false,
  "idle_restart_timeout_seconds": -1,

  // Require API key in Authorization header
  "api_key": "",

  // Auto-open browser on start
  "auto_open_browser": false,

  // Server settings
  "server_host": "0.0.0.0",
  "server_port": 5102
}
```

### models.json Explained

Maps friendly names to LMArena model IDs.

**Format:**
```json
{
  "model-name": "lmarena-uuid:type"
}
```

**Examples:**
```json
{
  "gpt-4": "e2d9d353-6dbe-4414-bf87-bd289d523726",
  "gpt-4-turbo": "983bc566-b783-4d28-b24c-3c8b08eb1086:text",
  "dall-e-3": "null:image",
  "gemini-2.5-pro": "abc-def-ghi:text"
}
```

**Special values:**
- `null` → No specific model ID (uses whatever's in session)
- `:text` → Text generation model (default)
- `:image` → Image generation model

### model_endpoint_map.json Explained

Maps models to specific sessions.

**Single mapping:**
```json
{
  "research-gpt": {
    "session_id": "session-uuid",
    "message_id": "message-uuid",
    "mode": "direct_chat"
  }
}
```

**Multiple mappings (random selection):**
```json
{
  "gpt-5": [
    {
      "session_id": "session-1",
      "message_id": "message-1",
      "mode": "direct_chat"
    },
    {
      "session_id": "session-2",
      "message_id": "message-2",
      "mode": "battle",
      "battle_target": "A"
    }
  ]
}
```

When you request `gpt-5`, it randomly picks one of these sessions.

---

## Troubleshooting

### Server Issues

**Problem:** Server won't start

**Solutions:**
1. Check port is free: `lsof -i :5102`
2. Try different port: `make run PORT=5103`
3. Check logs in GUI → Logs tab

---

**Problem:** "Connection refused" when calling API

**Solutions:**
1. Ensure server is running (green status in GUI)
2. Check firewall: `sudo ufw allow 5102`
3. Verify URL: `curl http://127.0.0.1:5102/internal/healthz`

### Browser Connection Issues

**Problem:** Browser won't connect

**Solutions:**
1. Verify Tampermonkey script is enabled
2. Refresh LMArena page
3. Check browser console (F12) for errors
4. Try different browser

---

**Problem:** "No browser connected" error

**Solutions:**
1. Open https://lmarena.ai in browser
2. Ensure script shows ✅ in page title
3. Check WebSocket connection in browser DevTools → Network → WS

### ID Capture Issues

**Problem:** IDs not captured after clicking Retry

**Solutions:**
1. Must click **"Retry" (⟳)**, not "Regenerate"
2. Ensure ID capture was activated first (GUI button)
3. Check Logs tab for capture confirmation
4. Try refreshing LMArena page and re-activating capture

---

**Problem:** "Invalid session/message ID" error

**Solutions:**
1. IDs may have expired; capture new ones
2. Check `config.jsonc` doesn't contain `YOUR_SESSION_ID`
3. Run setup wizard again

### Model Issues

**Problem:** "Model not found" error

**Solutions:**
1. Check model exists in `models.json`
2. Refresh model list (GUI → Models → "Refresh from Server")
3. Verify model name spelling

---

**Problem:** Image model not generating images

**Solutions:**
1. Ensure model type is `:image` in `models.json`
2. Check LMArena actually supports that model for images
3. Try in LMArena web UI first to verify

### Response Issues

**Problem:** Response times out

**Solutions:**
1. Increase timeout in config: `"stream_response_timeout_seconds": 600`
2. Check browser didn't close/sleep
3. Verify LMArena isn't rate-limiting you

---

**Problem:** Response stops mid-stream

**Solutions:**
1. Check for content filter trigger (finishReason: "content-filter")
2. Try bypass mode: `"bypass_enabled": true`
3. Rephrase prompt

---

**Problem:** Cloudflare verification detected

**Solutions:**
1. Complete verification in browser manually
2. Refresh LMArena page
3. Wait 30 seconds and retry request

### GUI Issues

**Problem:** GUI won't launch

**Solutions:**
1. Verify GTK4: `pkg-config --modversion gtk4` (should output version)
2. Check Python GObject: `python -c "import gi"`
3. Reinstall: `make clean && make install-gui`

---

**Problem:** GUI crashes on start

**Solutions:**
1. Check error in terminal
2. Remove config: `rm -rf ~/.config/lmarena-bridge/`
3. Re-run setup wizard

---

## FAQ

**Q: Do I need an LMArena account?**
A: Yes, you must be logged in to LMArena in your browser.

**Q: Does this use official APIs?**
A: No, it automates browser interactions via Tampermonkey. Use responsibly.

**Q: Can I run multiple instances?**
A: Yes, use different ports: `make run PORT=5103`

**Q: Is my API key sent to LMArena?**
A: No, the `api_key` in config is only for protecting your local server.

**Q: Can I use this on Windows/Mac?**
A: The backend works, but GUI requires Linux (GTK4). Use CLI mode.

**Q: How do I update?**
A: `git pull && make clean && make install-gui`

**Q: Can I package this as a Flatpak/Snap?**
A: Yes, see `packaging/` folder (coming soon).

**Q: How do I report bugs?**
A: Open an issue on GitHub with logs from GUI → Logs tab.

**Q: Can I use this commercially?**
A: Check LMArena's Terms of Service. This tool is MIT licensed.

**Q: Why GTK4 and not Qt/Electron?**
A: GTK4 is native to Linux, lightweight, and integrates well with GNOME.

---

## Glossary

- **Session ID**: LMArena's conversation identifier
- **Message ID**: Last message in a conversation thread
- **Battle Mode**: LMArena's A/B comparison mode
- **Direct Chat**: Normal 1-on-1 conversation mode
- **Bypass Mode**: Injects empty message to work around filters
- **Tavern Mode**: Merges system prompts (for character AI)
- **File Bed**: External image hosting server
- **Endpoint Mapping**: Model-specific session configuration
- **Tampermonkey**: Browser extension for running userscripts
- **SSE**: Server-Sent Events (streaming protocol)

---

**Last Updated:** 2024-01-XX
**Version:** 3.0.0