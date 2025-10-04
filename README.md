# LMArena Bridge

A robust, OpenAI-compatible API bridge for [LMArena](https://lmarena.ai) with an optional GTK4 graphical interface.

## Features

- ✅ **OpenAI-Compatible API** - Drop-in replacement for OpenAI SDK
- 🎨 **Native Linux GUI** - Built with GTK4 for seamless desktop integration
- 🔄 **Multi-Model Support** - Manage multiple models with custom endpoint mapping
- 🎯 **Direct Chat & Battle Modes** - Full support for LMArena's features
- 🔐 **Optional API Key Protection** - Secure your local instance
- 📦 **File Bed Integration** - Upload images to external storage
- 🛠️ **Setup Wizard** - Get started in minutes

## Installation

### Prerequisites

**System Dependencies (GTK4):**

```bash
# Ubuntu/Debian
sudo apt install python3-gi gir1.2-gtk-4.0 libgtk-4-dev

# Fedora
sudo dnf install python3-gobject gtk4

# Arch Linux
sudo pacman -S python-gobject gtk4
```

**Python 3.10+** is required.

### Quick Install

```bash
git clone https://github.com/Lianues/LMArenaBridge.git
cd LMArenaBridge
make install-gui
```

## Usage

### Option 1: GUI (Recommended for Desktop)

```bash
make gui
```

The GUI provides:
- **Setup Wizard** - First-run configuration assistant
- **Chat Playground** - Test models interactively
- **Configuration Editor** - Manage all settings with validation
- **Model Manager** - Add/edit/delete models
- **Endpoint Mapper** - Map models to specific sessions
- **Log Viewer** - Real-time server logs with search

### Option 2: Command Line

```bash
# Start the server
make run

# In another terminal, test it
curl http://127.0.0.1:5102/v1/models
```

### Option 3: Headless Server (systemd)

```bash
# Install as user service
mkdir -p ~/.config/systemd/user
cp packaging/systemd/lmarena-bridge.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now lmarena-bridge.service
```

## Quick Start

1. **Launch the GUI:**
   ```bash
   make gui
   ```

2. **Follow the Setup Wizard:**
   - Click "Start Server"
   - Open LMArena in browser (wizard has a button)
   - Install the Tampermonkey userscript from `public/userscripts/`
   - Complete ID capture by clicking "Retry" in LMArena
   - (Optional) Refresh model list

3. **Test in Chat Playground:**
   - Select a model
   - Type a message
   - See streaming responses

## Configuration

Config files are stored in:
- **Development:** `./config/`
- **Production:** `~/.config/lmarena-bridge/`
- **Override:** Set `LMABRIDGE_CONFIG_DIR` environment variable

### Key Files

- `config.jsonc` - Main configuration (session IDs, features, etc.)
- `models.json` - Available models with their IDs and types
- `model_endpoint_map.json` - Model-specific session mappings

### Example: Using with OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:5102/v1",
    api_key="your-key-if-set"  # Optional
)

response = client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True
)

for chunk in response:
    print(chunk.choices[0].delta.content or "", end="")
```

## Advanced Features

### Battle Mode

Map a model to operate in Battle mode:

```json
// In model_endpoint_map.json
{
  "my-model": {
    "session_id": "uuid-here",
    "message_id": "uuid-here",
    "mode": "battle",
    "battle_target": "A"
  }
}
```

### Image Models

Mark a model as image-generating:

```json
// In models.json
{
  "dall-e-3": "some-uuid:image"
}
```

### File Bed (for large attachments)

Enable in `config.jsonc`:

```jsonc
{
  "file_bed_enabled": true,
  "file_bed_upload_url": "http://127.0.0.1:5180/upload",
  "file_bed_api_key": "your-secret"
}
```

## Troubleshooting

### Server won't start
- Check port 5102 is not in use: `lsof -i :5102`
- Verify installation: `pip show lmarena-bridge`

### Browser not connecting
- Ensure Tampermonkey script is installed and enabled
- Check browser console for errors
- Verify you're on `https://lmarena.ai`

### IDs not captured
- Click "Retry" in LMArena (not "Regenerate")
- Check server logs in GUI's "Logs" tab
- Ensure browser is connected (green indicator)

### GUI won't launch
- Verify GTK4 is installed: `pkg-config --modversion gtk4`
- Check Python GObject: `python -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk"`

## Development

```bash
# Install with dev tools
make install-dev

# Run tests
make test

# Lint and format
make format lint

# Type check
make type-check

# Run all checks
make check
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- LMArena team for the amazing platform
- FastAPI & GTK teams for excellent frameworks