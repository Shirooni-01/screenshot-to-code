"""
Screenshot to Code Generator
====================================
Upload screenshot → Component Detection → Structured JSON → Code Skeleton → Gemini Refinement → Final Output

Pipeline:
  Image → detector.py → parser.py → generator.py → ai_refiner.py → Final Code

Uses OpenCV for component detection + Gemini for refinement only.
"""

import os
import uuid
import time
import cv2
from collections import defaultdict
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from google import genai
from dotenv import load_dotenv

# Import pipeline modules
from pipeline.detector import detect_components
from pipeline.parser import parse_layout
from pipeline.generator import generate_skeleton
from pipeline.ai_refiner import refine_with_ai

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
    print(f'[Unhandled Error]: {e}')
    return jsonify({'error': 'Something went wrong. Please try again.'}), 500


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================
# Pipeline — Component Detection + Structured Generation
# ============================================================

def generate_code_pipeline(image_path, framework='html-css'):
    """
    Pipeline: Image → Detection → Parsing → Skeleton → AI Refinement.

    Returns a dict with:
      - components: list of detected components
      - layout: structured layout JSON
      - skeleton_code: code before AI refinement
      - final_code: AI-refined code
      - pipeline_stages: timing info for each stage
    """
    stages = []
    start_total = time.time()

    # ── Stage 1: Component Detection (OpenCV) ──
    t0 = time.time()
    components = detect_components(image_path)
    stages.append({
        'name': 'Component Detection',
        'duration_ms': int((time.time() - t0) * 1000),
        'result': f'{len(components)} components found'
    })

    # ── Stage 2: Layout Parsing ──
    t0 = time.time()
    # Get image dimensions for section assignment
    img_cv = cv2.imread(image_path)
    img_height = img_cv.shape[0] if img_cv is not None else 1000
    layout = parse_layout(components, img_height)
    stages.append({
        'name': 'Layout Parsing',
        'duration_ms': int((time.time() - t0) * 1000),
        'result': f'{len(layout.get("sections", []))} sections identified'
    })

    # ── Stage 3: Skeleton Code Generation ──
    t0 = time.time()
    skeleton_code = generate_skeleton(layout, framework)
    stages.append({
        'name': 'Skeleton Generation',
        'duration_ms': int((time.time() - t0) * 1000),
        'result': f'{len(skeleton_code)} chars of {framework} code'
    })

    # ── Stage 4: AI Refinement (Gemini) ──
    t0 = time.time()
    try:
        client = get_client()
        final_code = refine_with_ai(client, MODEL, image_path, skeleton_code, layout, framework)
        stages.append({
            'name': 'AI Refinement',
            'duration_ms': int((time.time() - t0) * 1000),
            'result': 'Gemini refined successfully'
        })
    except Exception as e:
        # If Gemini fails, fall back to skeleton code
        final_code = skeleton_code
        stages.append({
            'name': 'AI Refinement',
            'duration_ms': int((time.time() - t0) * 1000),
            'result': f'Fallback to skeleton (AI error: {str(e)[:80]})'
        })

    total_ms = int((time.time() - start_total) * 1000)

    return {
        'components': components,
        'layout': layout,
        'skeleton_code': skeleton_code,
        'final_code': final_code,
        'pipeline_stages': stages,
        'total_time_ms': total_ms
    }


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
    """Pipeline endpoint — Component Detection → Structured Generation → AI Refinement."""
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

        # Always use the detection pipeline
        pipeline_result = generate_code_pipeline(filepath, framework)
        result = {
            'success': True,
            'generated_code': pipeline_result['final_code'],
            'skeleton_code': pipeline_result['skeleton_code'],
            'framework': framework,
            'detection': {
                'components': pipeline_result['components'],
                'layout': pipeline_result['layout'],
                'stages': pipeline_result['pipeline_stages'],
                'total_time_ms': pipeline_result['total_time_ms']
            }
        }

        # Record this successful request for rate limiting
        record_request(ip)
        _, updated_info = check_rate_limit(ip)
        result['rate_limit'] = updated_info

        return jsonify(result)

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
    print(f"  Pipeline: Image → Detection → Parsing → Skeleton → AI Refinement")
    print(f"  Open:  http://127.0.0.1:{port}")
    print(f"  Model: {MODEL}")
    print(f"  API:   {'✅ Key set' if GEMINI_API_KEY else '❌ Missing'}")
    print(f"  Mode:  {'Development' if debug else 'Production'}\n")

    app.run(host='0.0.0.0', port=port, debug=debug)
