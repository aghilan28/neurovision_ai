# NeuroVision AI — Frontend Integration Guide

This document describes how to integrate the production landing page into the NeuroVision FastAPI application.

## Files Modified / Added

```
neurovision_ai/
├── code.html                                          # Production landing page (NEW)
├── frontend/
│   └── application_frontend/
│       ├── docs/
│       │   └── DESIGN.md                              # Updated design system spec (MODIFIED)
│       └── pages/
│           ├── __init__.py                             # Updated exports (MODIFIED)
│           └── landing.py                              # Landing page controller (NEW)
├── backend/
│   └── application_platform/
│       └── server/
│           └── landing.py                              # FastAPI static mount (NEW)
└── static/                                            # Static assets directory (NEW)
```

## Integration Steps

### 1. Add the landing page route to FastAPI

In `backend/application_platform/server/factory.py`, add the landing page mount after the app is created:

```python
# Add this import at the top of factory.py
from .landing import mount_landing_page

# Then in build_application(), after creating the app:
def build_application(config):
    service = build_service(config)
    app = create_app(service)

    # Mount the NeuroVision landing page at root path
    mount_landing_page(app)

    return service, app
```

### 2. Verify the file structure

Ensure `code.html` exists at the project root:
```bash
ls -la code.html
# Should show the production landing page (~30KB)
```

### 3. Run the server

```bash
# Development
python scripts/serve_neurovision.py

# Or directly
uvicorn backend.application_platform.server.app:app --host 0.0.0.0 --port 8080
```

### 4. Access the landing page

Navigate to `http://localhost:8080/` to see the interactive NeuroVision landing page.

The page automatically:
- Polls `GET /health` every 5 seconds for live telemetry
- Opens upload modal routed to `POST /upload`
- Renders the WebGL neural node-link graph animation
- Transitions nav height on scroll

## API Endpoints Used by Frontend

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /health` | Polling (5s) | Returns `active_sessions` array + telemetry counters |
| `POST /upload` | File upload | Accepts EDF/EDF+ files via multipart form data |

### Expected `/health` Response Format

```json
{
  "status": "ok",
  "active_sessions": [842912, 14.2, 1200000, 99.8],
  "analyses_completed": 842912,
  "signals_processed_pb": 14.2,
  "reports_generated": 1200000,
  "avg_confidence_pct": 99.8
}
```

When the API is unavailable, the frontend gracefully degrades to `status: degraded` without freezing.

## Design Tokens

All design tokens from DESIGN.md are instantiated in the Tailwind configuration within `code.html`:

- **Colors**: Background `#141218`, Primary `#cfbcff`, Clinical Teal `#14B8A6`
- **Surfaces**: 5-level elevation hierarchy (Base → Surface-Highest)
- **Typography**: Playfair Display (headlines), Geist (body), JetBrains Mono (metrics)
- **Borders**: `1px solid outline-variant/20` — no drop shadows
- **Radius**: 4px (interactive) / 8px (panels)
