"""
Screenshot to Code Generator
=============================
Upload screenshot → Gemini AI scans it → Generates HTML + CSS or React + Tailwind code.
Uses the google-genai SDK with Gemini 3 Flash model.
"""

import os
import uuid
import re
import time
from collections import defaultdict
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from PIL import Image
from google import genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================
# Setup
# ============================================================
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
except Exception:
    pass  # Will fail gracefully if dirs can't be created

# Gemini API Key from environment variable (never hardcode in production!)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

if not GEMINI_API_KEY:
    print("\n⚠️  WARNING: GEMINI_API_KEY not set!")
    print("   Set it in .env file or as an environment variable.\n")

# Lazy client — created on first use so the app can start even without a key
_client = None

def get_client():
    """Get or create the Gemini client (lazy initialization)."""
    global _client
    if _client is None:
        key = os.environ.get('GEMINI_API_KEY', GEMINI_API_KEY)
        if not key:
            raise ValueError("GEMINI_API_KEY is not set. Add it in Render Environment Variables.")
        _client = genai.Client(api_key=key)
    return _client

# Model
MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3-flash-preview')

# Rate Limiting — 3 requests per 2 minutes per IP
RATE_LIMIT_MAX = int(os.environ.get('RATE_LIMIT_MAX', '3'))
RATE_LIMIT_WINDOW = int(os.environ.get('RATE_LIMIT_WINDOW', '120'))  # seconds
rate_limit_store = defaultdict(list)  # {ip: [timestamp1, timestamp2, ...]}


def check_rate_limit(ip):
    """Check if the IP has exceeded the rate limit. Returns (allowed, info)."""
    now = time.time()
    # Clean old entries outside the window
    rate_limit_store[ip] = [t for t in rate_limit_store[ip] if now - t < RATE_LIMIT_WINDOW]

    if len(rate_limit_store[ip]) >= RATE_LIMIT_MAX:
        oldest = rate_limit_store[ip][0]
        wait = int(RATE_LIMIT_WINDOW - (now - oldest)) + 1
        return False, {
            'remaining': 0,
            'reset_in': wait,
            'limit': RATE_LIMIT_MAX,
            'window': RATE_LIMIT_WINDOW
        }

    return True, {
        'remaining': RATE_LIMIT_MAX - len(rate_limit_store[ip]) - 1,
        'limit': RATE_LIMIT_MAX,
        'window': RATE_LIMIT_WINDOW
    }


def record_request(ip):
    """Record a request timestamp for the given IP."""
    rate_limit_store[ip].append(time.time())


# Error handlers — always return JSON, never HTML
@app.errorhandler(413)
def handle_413(e):
    return jsonify({'error': 'File too large. Max 16 MB.'}), 413

@app.errorhandler(500)
def handle_500(e):
    return jsonify({'error': 'Server error. Try again.'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({'error': str(e)}), 500


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================
# AI Code Generation
# ============================================================

PROMPT_HTML_CSS = """Analyze this UI screenshot carefully. Scan every detail:
- Text, headings, paragraphs, labels, button text
- Images/icons → use colored placeholder divs or inline SVG
- Emojis → use actual Unicode emojis  
- Layout structure: header, nav, hero, sections, cards, grids, footer
- Colors: backgrounds, text, gradients, borders
- Spacing: padding, margins, gaps
- Buttons, links, inputs, forms

Generate a SINGLE COMPLETE HTML file that recreates this exact UI.

RULES:
1. Start with <!DOCTYPE html>, end with </html>
2. Output ONLY the HTML code — NO markdown fences, NO explanations
3. ALL CSS inside a <style> tag in <head>
4. Use Google Fonts <link> for modern typography
5. Match exact colors, layout, spacing from the screenshot
6. Use flexbox, grid, gradients, shadows, border-radius
7. Make it responsive
8. Add hover effects on buttons/links

Generate now:"""

PROMPT_REACT_TAILWIND = """Analyze this UI screenshot carefully. Scan every detail:
- Text, headings, paragraphs, labels, button text
- Images/icons → use colored placeholder divs or inline SVG icons
- Emojis → use actual Unicode emojis
- Layout structure: header, nav, hero, sections, cards, grids, footer
- Colors: backgrounds, text, gradients, borders
- Spacing: padding, margins, gaps
- Buttons, links, inputs, forms

Generate a SINGLE React functional component using Tailwind CSS that recreates this exact UI.

RULES:
1. Output ONLY the JSX code — NO markdown fences, NO explanations
2. Use a single default export: export default function Component() { return (...) }
3. Use ONLY Tailwind CSS utility classes for ALL styling (no inline styles, no CSS files)
4. Use proper Tailwind classes: flex, grid, bg-, text-, p-, m-, rounded-, shadow-, etc.
5. Match exact colors using Tailwind color palette or arbitrary values like bg-[#1a1a2e]
6. Use responsive Tailwind: sm:, md:, lg: prefixes
7. Add hover effects: hover:bg-, hover:scale-, hover:shadow-, etc.
8. Use semantic HTML elements inside JSX
9. All className attributes must use double quotes
10. Include all text content exactly as seen in the screenshot
11. For icons, use simple inline SVGs or emoji characters

Generate now:"""


def generate_code_from_screenshot(image_path, framework='html-css'):
    """Send screenshot to Gemini AI → get code back in chosen framework."""

    client = get_client()  # lazy init — won't crash on startup

    img = Image.open(image_path)

    # Choose prompt based on framework
    prompt = PROMPT_REACT_TAILWIND if framework == 'react-tailwind' else PROMPT_HTML_CSS

    # Send image + prompt to Gemini
    response = client.models.generate_content(
        model=MODEL,
        contents=[prompt, img]
    )
    code = response.text.strip()

    # Remove markdown fences if present (html, jsx, javascript, tsx)
    code = re.sub(r'^```(?:html|jsx|javascript|tsx|js)?\s*\n?', '', code, flags=re.IGNORECASE)
    code = re.sub(r'\n?```\s*$', '', code)
    code = code.strip()

    # For HTML: validate it starts with <!DOCTYPE
    if framework == 'html-css':
        if not code.lower().startswith('<!doctype'):
            match = re.search(r'(<!DOCTYPE html>.*?</html>)', code, re.DOTALL | re.IGNORECASE)
            if match:
                code = match.group(1)

    return code


# ============================================================
# Routes
# ============================================================
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/health')
def health():
    """Health check endpoint for deployment platforms."""
    return jsonify({
        'status': 'ok',
        'model': MODEL,
        'api_key_set': bool(GEMINI_API_KEY)
    })


@app.route('/generate-code', methods=['POST'])
def generate_code():
    # Rate limit check
    ip = request.remote_addr or 'unknown'
    allowed, rate_info = check_rate_limit(ip)
    if not allowed:
        return jsonify({
            'error': f'Rate limit reached. Please wait {rate_info["reset_in"]} seconds before trying again.',
            'rate_limit': rate_info
        }), 429

    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded.'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected.'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type.'}), 400

    filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        framework = request.form.get('framework', 'html-css')
        code = generate_code_from_screenshot(filepath, framework)

        # Record this successful request for rate limiting
        record_request(ip)
        _, updated_info = check_rate_limit(ip)

        return jsonify({
            'success': True,
            'generated_code': code,
            'framework': framework,
            'rate_limit': updated_info
        })
    except Exception as e:
        print(f'[Error]: {e}')
        return jsonify({'error': f'Generation failed: {str(e)}'}), 500
    finally:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass


# ============================================================
# Start
# ============================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'

    print(f"\n⚡ Screenshot to Code Generator")
    print(f"  Open:  http://127.0.0.1:{port}")
    print(f"  Model: {MODEL}")
    print(f"  API:   {'✅ Key set' if GEMINI_API_KEY else '❌ Missing'}")
    print(f"  Mode:  {'Development' if debug else 'Production'}\n")

    app.run(host='0.0.0.0', port=port, debug=debug)
