# Contributing to LMArena Bridge

Thank you for your interest in contributing!

## Development Setup

1. **Fork and clone:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/LMArenaBridge.git
   cd LMArenaBridge
   ```

2. **Install with dev dependencies:**
   ```bash
   make install-dev
   ```

3. **Run pre-commit hooks:**
   ```bash
   make hooks
   ```

## Code Style

We use:
- **Ruff** for linting and formatting
- **MyPy** for type checking
- **Pre-commit** for automated checks

Before committing:
```bash
make format  # Auto-format
make check   # Run all checks
```

## Project Structure

```
lmarena-bridge/
├── lmarena_bridge/       # Core backend
│   ├── api/              # FastAPI routes
│   ├── services/         # Business logic
│   ├── utils/            # Utilities
│   ├── main.py           # Entry point
│   └── settings.py       # Configuration
├── lmarena_bridge_gui/   # GTK4 GUI
│   ├── ui/               # UI components
│   └── utils/            # GUI utilities
├── config/               # Default configs
├── tests/                # Test suite
└── docs/                 # Documentation
```

## Architecture Decisions

### Backend (lmarena_bridge/)

- **FastAPI** for async HTTP + WebSocket
- **Pydantic** for config validation
- **WebsocketHub** manages multiple browser tabs
- **Stream parser** handles LMArena's SSE format

### Frontend (lmarena_bridge_gui/)

- **GTK4** for native Linux UI
- **Threading** for non-blocking HTTP calls
- **GLib.idle_add** for thread-safe UI updates

### Communication Flow

```
OpenAI Client → FastAPI → WebSocket → Tampermonkey → LMArena
                  ↑                        ↓
                  └────── SSE Stream ──────┘
```

## Testing

```bash
# Run all tests
make test

# With coverage
make test-cov

# Single test
.venv/bin/pytest tests/test_settings.py -v
```

### Writing Tests

Place tests in `tests/` matching the module structure:

```python
# tests/test_settings.py
import pytest
from lmarena_bridge.settings import load_settings

def test_load_default_settings():
    s = load_settings()
    assert s.version
    assert s.server_port == 5102
```

## Adding New Features

### Backend Endpoints

1. Create route in `lmarena_bridge/api/routes_*.py`
2. Add business logic in `lmarena_bridge/services/`
3. Update tests
4. Document in README

### GUI Components

1. Create component in `lmarena_bridge_gui/ui/`
2. Extend `MainWindow` to include it
3. Add menu/toolbar items if needed
4. Test manually (no automated GUI tests yet)

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes with clear commit messages
3. Run `make check` (all checks must pass)
4. Update README.md if adding user-facing features
5. Open PR with description of changes

## Versioning

We use [Semantic Versioning](https://semver.org/):
- MAJOR: Breaking API changes
- MINOR: New features (backward-compatible)
- PATCH: Bug fixes

Update version in:
- `pyproject.toml`
- `config/config.jsonc`
- `lmarena_bridge_gui/gtk_app.py` (About dialog)

## Release Checklist

- [ ] All tests pass
- [ ] Version bumped
- [ ] CHANGELOG.md updated
- [ ] README.md reflects new features
- [ ] Git tag created: `git tag v3.0.0`
- [ ] Push tags: `git push --tags`

## Questions?

Open an issue or discussion on GitHub.