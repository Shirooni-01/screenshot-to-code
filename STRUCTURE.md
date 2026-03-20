# Project Structure

How the project is organized and how data flows through it.

---

## Folder Layout

```
screenshot-to-code/
│
├── app.py                      # Main server — Flask routes + pipeline orchestration
│
├── pipeline/                   # Core processing modules
│   ├── __init__.py             # Package init, exports all 4 functions
│   ├── detector.py             # Image → component list (OpenCV)
│   ├── parser.py               # Component list → structured layout JSON
│   ├── generator.py            # Layout JSON → skeleton code (HTML/React/Tailwind)
│   └── ai_refiner.py           # Skeleton + image → refined code (Gemini)
│
├── templates/
│   └── index.html              # Single-page frontend — upload, output, history
│
├── static/
│   ├── style.css               # All styles — dark theme, responsive, animations
│   └── script.js               # Frontend logic — file handling, API calls, history
│
├── requirements.txt            # Python dependencies
├── .env                        # API keys (not committed, create from .env.example)
├── .env.example                # Template for environment variables
├── .gitignore                  # Standard ignores
│
├── Procfile                    # Gunicorn start command (for Render/Heroku)
├── render.yaml                 # Render.com deployment config
├── runtime.txt                 # Python version for deployment
│
├── uploads/                    # Temporary — images go here, get deleted after use
└── screenshots/                # README screenshots (if any)
```

---

## What Each File Does

### `app.py` — Server + Pipeline Orchestrator

This is the entry point. Handles:

- Flask setup, CORS, error handlers
- Rate limiting (in-memory, per IP, 3 requests per 2 minutes)
- File upload validation (type check, size check)
- **`generate_code_pipeline()`** — calls detector → parser → generator → ai_refiner in sequence, tracks timing for each stage
- Routes: `/` (serve frontend), `/health` (status check), `/generate-code` (POST, main endpoint)
- Temp file cleanup (uploaded images deleted after processing)

The Gemini client is lazily initialized — the app can start even without an API key set.

### `pipeline/detector.py` — Component Detection

Takes a screenshot path, returns a list of detected UI components.

How it works:
1. Loads image with OpenCV, converts to grayscale
2. Runs Canny edge detection + dilation to close gaps
3. Finds contours (external only)
4. For each contour bounding box, classifies it semantically:
   - Crops the region from the grayscale image
   - Checks if it contains text (using 3 methods: pixel std deviation, dark pixel ratio, edge density — needs 2/3 to confirm)
   - Uses size + aspect ratio + text presence to decide: button, input, heading, text, image, or container
5. Removes overlapping detections (IoU > 0.6 → keep the smaller/more specific one)
6. Sorts top-to-bottom, left-to-right

Output example:
```json
[
  {"type": "heading", "text": "Page Heading", "x": 50, "y": 20, "width": 400, "height": 30},
  {"type": "button", "text": "Click Me", "x": 50, "y": 100, "width": 120, "height": 40},
  {"type": "input", "text": "Enter text...", "x": 50, "y": 160, "width": 300, "height": 35}
]
```

No ML models. Pure OpenCV + heuristics. Runs in milliseconds.

### `pipeline/parser.py` — Layout Parsing

Takes the flat list of detected components and organizes them into a page structure.

Steps:
1. Groups components into horizontal rows based on Y-coordinate proximity (dynamic tolerance based on average element height)
2. Sorts elements within each row left-to-right
3. Assigns rows to sections based on vertical position:
   - Top 20% of image → `header`
   - Bottom 15% → `footer`
   - Everything else → `body`

Output:
```json
{
  "layout": "vertical",
  "sections": [
    {"type": "header", "elements": [...]},
    {"type": "body", "elements": [...]},
    {"type": "footer", "elements": [...]}
  ],
  "total_components": 12
}
```

### `pipeline/generator.py` — Skeleton Code Generation

Takes the structured layout JSON, outputs actual code. Supports 3 frameworks:

| Framework | Output |
|-----------|--------|
| `html-css` | Complete `.html` file with embedded `<style>` tag, Google Fonts |
| `react-tailwind` | `export default function` React component with Tailwind classes |
| `tailwind-css` | Complete HTML file with Tailwind CDN script |

Maps component types to semantic HTML:
- `heading` → `<h1>` (first) or `<h2>` (subsequent)
- `button` → `<button>`
- `input` → `<input type="text">`
- `image` → `<div>` styled as placeholder
- `container` → `<div class="card">`
- `text` → `<p>`

Uses proper semantic wrappers: `<header>`, `<main>`, `<footer>` based on section type.

**Important rule:** No SVGs, no canvas, no vector tags. Only standard HTML elements. This is enforced in the code.

### `pipeline/ai_refiner.py` — AI Refinement (Gemini)

Takes the skeleton code + original screenshot + layout JSON, sends it all to Gemini with a carefully crafted prompt.

What Gemini is asked to do:
- Match exact colors from the screenshot
- Fix spacing and padding
- Fill in actual text content (since our detector can't read text)
- Improve typography
- Add hover effects
- Make it responsive

What Gemini is told NOT to do:
- Don't change the overall structure
- Don't remove detected components
- Don't add major new sections
- **Don't use SVG, canvas, or vector tags** (this is heavily enforced in the prompt and also post-processed out as a safety net)

If Gemini fails (API error, timeout, etc.), the pipeline falls back to the skeleton code — so you always get something.

### `templates/index.html` — Frontend Page

Single HTML page with:
- Upload area (drag & drop or file browse)
- Framework selector (HTML/CSS or React/Tailwind)
- Generate button with rate limit display
- Pipeline stages visualization (Detect → Parse → Generate → Refine with timing)
- Code output with tabs (Skeleton vs AI Refined)
- Copy button
- History panel (localStorage)

### `static/script.js` — Frontend Logic

Handles:
- File selection, validation, thumbnail generation
- FormData POST to `/generate-code`
- Pipeline stage animation (visual feedback during generation)
- Code display with skeleton/refined tabs
- localStorage history (save, load, delete, clear — max 20 items)
- Rate limit UI updates
- Toast notifications

### `static/style.css` — Styles

Dark theme with:
- CSS custom properties for colors
- Panel/card components
- Pipeline stage dots with active/done states
- Code block with syntax-like styling
- Responsive breakpoints
- Animations (slide up, fade in, bounce loader, pulse)

---

## Data Flow — Step by Step

Here's exactly what happens when a user uploads a screenshot and clicks Generate:

```
1. User drops image → script.js reads file, shows preview

2. User clicks "Generate Code"
   └→ script.js creates FormData {image, framework}
   └→ POST /generate-code

3. app.py receives the request
   ├→ Rate limit check (reject if over limit)
   ├→ File validation (type, size)
   └→ Saves to /uploads/ with UUID filename

4. app.py calls generate_code_pipeline(filepath, framework)
   │
   ├→ Stage 1: detector.detect_components(image_path)
   │   Input:  image file path
   │   Output: [{type, text, x, y, width, height}, ...]
   │   Time:   ~50-200ms
   │
   ├→ Stage 2: parser.parse_layout(components, image_height)
   │   Input:  component list, image height
   │   Output: {layout, sections: [{type, elements}], total_components}
   │   Time:   <5ms
   │
   ├→ Stage 3: generator.generate_skeleton(layout, framework)
   │   Input:  layout JSON, framework string
   │   Output: complete HTML/JSX code string
   │   Time:   <5ms
   │
   └→ Stage 4: ai_refiner.refine_with_ai(client, model, image, skeleton, layout, framework)
       Input:  Gemini client, image path, skeleton code, layout JSON
       Output: refined code string
       Time:   ~5-15 seconds (API call)

5. app.py returns JSON response:
   {
     success: true,
     generated_code: "...",
     skeleton_code: "...",
     framework: "html-css",
     detection: {
       components: [...],
       layout: {...},
       stages: [{name, duration_ms, result}, ...],
       total_time_ms: 8500
     },
     rate_limit: {remaining: 2, limit: 3, window: 120}
   }

6. script.js receives response
   ├→ Completes pipeline stage animation
   ├→ Shows detection stats (component counts, timing)
   ├→ Displays code with skeleton/refined tabs
   ├→ Saves to localStorage history
   └→ Updates rate limit counter

7. app.py deletes the uploaded image from /uploads/
```

---

## Rate Limiting

Simple in-memory rate limiter. Per-IP tracking with a sliding window.

- Default: 3 requests per 120 seconds
- Configurable via `RATE_LIMIT_MAX` and `RATE_LIMIT_WINDOW` env vars
- Not persistent across restarts (resets when server restarts)
- Returns remaining count and reset time in every response

This is intentional — keeps Gemini API costs under control during demos and public deployment.

---

## Deployment Files

| File | Purpose |
|------|---------|
| `Procfile` | Gunicorn command for Heroku/Render: single worker, 120s timeout |
| `render.yaml` | Render.com service definition with env vars |
| `runtime.txt` | Specifies Python 3.11 |
| `.env.example` | Template for local `.env` file |

The timeout is set to 120 seconds because the Gemini API call can take 10-15 seconds, and we want some breathing room.
