# Screenshot to Code Generator

Upload a UI screenshot, get working code back. HTML/CSS or React/Tailwind.

---

## The Problem

Converting UI designs into code is tedious. You're staring at a mockup, manually writing divs and buttons, eyeballing colors and spacing — it takes forever, especially when you're prototyping fast or working solo.

Most "screenshot to code" tools just throw the image at an LLM and hope for the best. That works sometimes, but the output is unpredictable — you get SVGs where you wanted buttons, random layouts, inconsistent structure.

## What We Built

A pipeline that actually **understands the screenshot first** before generating code.

Instead of sending the raw image to AI and praying, we:
1. Run OpenCV on the screenshot to detect UI components (buttons, inputs, headings, images, containers)
2. Parse those detections into a structured layout (header/body/footer sections, rows)
3. Generate clean skeleton code from that structure
4. _Then_ send the skeleton + image to Gemini to refine colors, spacing, and text

The AI only handles the last mile — visual polish. The structure comes from our own detection logic.

---

## How the Pipeline Works

```
Screenshot
    │
    ▼
┌─────────────────────────┐
│  1. Component Detection │  ← OpenCV: edges, contours, pixel analysis
│     (detector.py)       │     Finds rectangles, classifies them by
│                         │     checking what's inside (text or empty)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  2. Layout Parsing      │  ← Groups components into rows by Y-position
│     (parser.py)         │     Assigns header / body / footer sections
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  3. Skeleton Generation │  ← Turns structured JSON into real code
│     (generator.py)      │     HTML+CSS, React+Tailwind, or HTML+Tailwind
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  4. AI Refinement       │  ← Gemini looks at the original image +
│     (ai_refiner.py)     │     skeleton code, fixes colors/spacing/text
└────────────┬────────────┘
             │
             ▼
        Final Code
```

### Why not just send the image directly to AI?

We tried that first. Problems:
- AI would output SVGs and canvas elements instead of normal HTML
- Layout was often wrong — elements in the wrong sections
- No consistency between runs
- You had zero control over the output structure

With the pipeline approach, the AI gets a structured starting point. It just needs to refine styling, not figure out the entire page layout from scratch. Results are more consistent and the code is actually usable.

---

## Features

| Feature | Details |
|---------|---------|
| **Component Detection** | OpenCV-based — detects buttons, inputs, headings, text blocks, images, containers |
| **Framework Choice** | HTML/CSS (single file) or React + Tailwind (JSX component) |
| **Skeleton + Refined tabs** | See the raw skeleton code vs the AI-refined version |
| **Pipeline Visualization** | Shows each stage with timing (Detect → Parse → Generate → Refine) |
| **Rate Limiting** | 3 requests per 2 minutes per IP (configurable) |
| **History** | Past generations saved in localStorage with thumbnails |
| **Copy to clipboard** | One click |
| **No signup required** | Just upload and go |
| **Auto-cleanup** | Uploaded images are deleted after processing |

---

## Tech Stack

| Component | What we used |
|-----------|-------------|
| Backend | Python 3.11, Flask |
| Image Processing | OpenCV (contour detection, edge analysis, pixel stats) |
| AI | Google Gemini 3 Flash (refinement only) |
| Frontend | Vanilla HTML/CSS/JS |
| Fonts | Plus Jakarta Sans (Google Fonts) |
| Deployment | Render (Gunicorn) |

Key dependencies: `flask`, `opencv-python-headless`, `numpy`, `Pillow`, `google-genai`, `python-dotenv`

---

## How to Run

### Prerequisites
- Python 3.10+
- Gemini API key — [get one free here](https://aistudio.google.com/app/apikey)

### Setup

```bash
# Clone the repo
git clone <your-repo-url>
cd screenshot-to-code

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Open .env and paste your Gemini API key

# Run
python app.py
```

Open `http://127.0.0.1:5000` in your browser. Upload a screenshot, pick HTML/CSS or React/Tailwind, hit Generate.

### Environment Variables

| Variable | Required | Default | What it does |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | — | Your Gemini API key |
| `GEMINI_MODEL` | No | `gemini-3-flash-preview` | Which model to use |
| `FLASK_DEBUG` | No | `true` | Debug mode (set `false` in production) |
| `PORT` | No | `5000` | Server port |
| `RATE_LIMIT_MAX` | No | `3` | Max requests per window |
| `RATE_LIMIT_WINDOW` | No | `120` | Rate limit window in seconds |

---

## Example

**Input:** Screenshot of a landing page with a navbar, hero section with heading + CTA button, and a footer.

**What happens:**
1. OpenCV detects ~8-15 components: heading text, buttons, input fields, image areas, containers
2. Parser groups them into header (top 20%), body, footer (bottom 15%) sections
3. Generator creates semantic HTML with `<header>`, `<main>`, `<footer>`, proper `<button>`, `<input>`, `<h1>` tags
4. Gemini refines: matches actual colors from the screenshot, fixes text content, adjusts spacing

**Output:** A single .html file (or JSX component) you can open directly in a browser.

---

## Deployment

### Render (recommended)

1. Push to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect repo — it auto-detects `render.yaml`
4. Add `GEMINI_API_KEY` in environment variables
5. Deploy

The `render.yaml` and `Procfile` are already set up.

---

## Architecture — Old vs New

### Before (v1): Direct AI approach
```
Screenshot → Gemini → Code
```
Simple, but the AI had to do everything — figure out structure, pick elements, write CSS, match colors. Results were inconsistent and often included SVG/canvas tags that weren't useful.

### Now: Detection pipeline
```
Screenshot → OpenCV Detection → Structured JSON → Code Skeleton → Gemini Refinement → Code
```
We handle structure ourselves. The AI only refines styling. This gives us:
- **Consistent semantic HTML** — buttons are `<button>`, inputs are `<input>`, not random SVGs
- **Predictable layout** — sections are based on actual Y-position grouping, not AI guessing
- **Fallback support** — if Gemini fails or is slow, we still have the skeleton code
- **Transparency** — you can see exactly what was detected and how the layout was parsed

---

## Limitations

Being honest about what this can and can't do:

- **Detection accuracy is limited.** OpenCV contour detection with heuristics is not the same as a trained object detection model. It works reasonably well on clean UI screenshots with clear boundaries, but struggles with complex overlapping elements, transparent backgrounds, or very busy layouts.
- **Text content is placeholder.** The detector can tell *where* text is, but it can't read what it says (no OCR). The actual text comes from Gemini during refinement, so it depends on AI accuracy.
- **Colors come from AI.** Our skeleton uses default colors. Gemini tries to match the original, but it's not pixel-perfect.
- **Rate limited.** 3 generations per 2 minutes per IP. This is intentional to keep API costs manageable.
- **Single-page only.** Generates one page at a time, no multi-page apps.
- **No interactivity.** The generated code is static HTML/CSS. No JavaScript logic, state management, or API connections.

---

## Future Improvements

Things we'd actually work on next (not fantasy features):

- **OCR integration** — Use Tesseract or similar to read actual text from the screenshot instead of relying on AI for text content
- **Better detection** — Fine-tune thresholds or add simple ML-based component classification
- **Live preview** — Show a rendered preview of the generated code alongside the code block
- **Iterative refinement** — Let users point out what's wrong and re-generate specific sections
- **Export as zip** — Bundle the HTML + any assets into a downloadable file

---

## Project Structure

See [STRUCTURE.md](STRUCTURE.md) for a detailed breakdown of every file and the data flow.

```
screenshot-to-code/
├── app.py                    # Flask server, routes, pipeline orchestration
├── pipeline/
│   ├── __init__.py           # Package exports
│   ├── detector.py           # OpenCV component detection
│   ├── parser.py             # Layout grouping + section assignment
│   ├── generator.py          # Code skeleton generation
│   └── ai_refiner.py         # Gemini refinement
├── templates/
│   └── index.html            # Main page
├── static/
│   ├── style.css             # Dark theme styles
│   └── script.js             # Upload, API calls, history, UI logic
├── requirements.txt
├── .env.example
├── Procfile                  # Gunicorn config for deployment
├── render.yaml               # Render deployment config
└── uploads/                  # Temp storage (auto-cleaned)
```

---

## Team

Built for Tech Fest 2.0

---

## License

MIT
