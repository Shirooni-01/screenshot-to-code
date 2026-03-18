# 📁 Project Structure

```
screenshot-to-code/
│
├── app.py                     # Main Flask application
│   ├── Gemini AI integration  # Sends screenshot to Gemini 3 Flash
│   ├── /generate-code API     # POST endpoint for code generation  
│   ├── Error handlers         # JSON error responses (413, 500)
│   └── File handling          # Secure upload + auto-cleanup
│
├── requirements.txt           # Python package dependencies
│   ├── Flask                  # Web framework
│   ├── Pillow                 # Image processing
│   ├── Werkzeug               # File security
│   └── google-genai           # Gemini AI SDK (new)
│
├── README.md                  # Project walkthrough + documentation
│
├── STRUCTURE.md               # This file
│
├── templates/                 # Jinja2 HTML templates
│   └── index.html             # Single-page application UI
│       ├── Header             # Brand + logo (Powered by SHIROONI)
│       ├── Hero section       # Title + 3-step process visualization
│       ├── Upload panel       # Drag & drop + file browse + preview
│       ├── Output panel       # Code display + copy button
│       ├── History panel      # Past generations list (localStorage)
│       ├── Loading overlay    # Animated bouncing dots loader
│       └── Footer             # Credits (Tech Fest 2.0)
│
├── static/                    # Static assets
│   ├── style.css              # Complete stylesheet (~700 lines)
│   │   ├── Design tokens      # CSS custom properties (colors, radii, fonts)
│   │   ├── Layout styles      # Header, hero, main, footer
│   │   ├── Component styles   # Panels, drop zone, preview, buttons
│   │   ├── Code output        # Browser-chrome code box with dots
│   │   ├── History styles     # History items, thumbnails, load/delete buttons
│   │   ├── Animations         # slideUp, fadeIn, bounce, toastIn
│   │   └── Responsive         # Mobile-first media queries
│   │
│   └── script.js              # Frontend JavaScript (~270 lines)
│       ├── File handling      # Drag & drop + browse + validation
│       ├── Image preview      # FileReader + preview display
│       ├── Thumbnail gen      # Canvas resize for localStorage thumbnails
│       ├── API call           # fetch /generate-code
│       ├── Code display       # Escaped HTML output
│       ├── Clipboard          # Copy to clipboard with animated button
│       ├── History (localStorage)
│       │   ├── addToHistory   # Save generation with thumbnail + timestamp
│       │   ├── renderHistory  # Display history items dynamically
│       │   ├── loadFromHistory # Restore previously generated code
│       │   ├── deleteFromHistory # Remove individual items
│       │   └── clearHistory   # Clear all saved history
│       └── Toast notifs       # Success/error popup messages
│
├── screenshots/               # Documentation screenshots
│   ├── home-page.png          # Main UI screenshot
│   └── code-output.png        # Generated code screenshot
│
└── uploads/                   # Temporary upload directory
                               # (auto-created, files deleted after processing)
```

## Data Flow

```
User                    Frontend (JS)              Backend (Flask)           Gemini AI
 │                         │                            │                      │
 ├── Selects image ──────► │                            │                      │
 │                         ├── Validates file           │                      │
 │                         ├── Shows preview            │                      │
 │                         ├── Creates thumbnail        │                      │
 │                         │                            │                      │
 ├── Clicks Generate ────► │                            │                      │
 │                         ├── POST /generate-code ───► │                      │
 │                         │   (FormData with image)    ├── Saves image        │
 │                         │                            ├── Opens with Pillow  │
 │                         │                            ├── Sends to API ────► │
 │                         │                            │                      ├── Scans image
 │                         │                            │                      ├── Detects UI
 │                         │                            │                      ├── Generates HTML
 │                         │                            │ ◄── Returns code ────┤
 │                         │                            ├── Cleans up file     │
 │                         │ ◄── JSON response ────────┤                      │
 │                         ├── Displays code            │                      │
 │                         ├── Saves to localStorage ──►│ (browser storage)    │
 │ ◄── Shows result ──────┤                            │                      │
 │                         ├── Renders history panel    │                      │
 │                         │                            │                      │
 ├── Clicks Copy ────────► │                            │                      │
 │                         ├── Clipboard API            │                      │
 │ ◄── "Copied!" toast ───┤                            │                      │
 │                         │                            │                      │
 ├── Clicks Load ────────► │                            │                      │
 │   (from history)        ├── Reads localStorage       │                      │
 │ ◄── Shows old code ────┤                            │                      │
```

## localStorage Schema

Each history item stored in `screenshot-to-code-history`:

```json
{
  "id": "1710750000000",
  "date": "18/3/2026, 10:10:00 AM",
  "thumbnail": "data:image/jpeg;base64,/9j/4AAQ...",
  "code": "<!DOCTYPE html><html>...</html>",
  "preview": "<!DOCTYPE html> <html lang=\"en\"> <head>..."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique ID (timestamp in ms) |
| `date` | string | Human-readable date/time |
| `thumbnail` | string | Base64 JPEG, 120px max, 60% quality |
| `code` | string | Full generated HTML+CSS code |
| `preview` | string | First 120 chars of code (for list display) |

**Limits:** Max 20 items · Auto-trims on QuotaExceededError
