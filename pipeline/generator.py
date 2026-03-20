"""
Code Skeleton Generator — Semantic HTML only
===============================================
Converts structured layout JSON into clean skeleton code using
ONLY real semantic UI tags:

  ALLOWED: div, button, input, img, p, h1, h2, header, main, footer
  FORBIDDEN: svg, canvas, path, circle, rect, polygon, line

Supports three output frameworks:
  - HTML + CSS (default)
  - React (JSX with Tailwind)
  - Tailwind CSS (HTML with Tailwind CDN)
"""


def generate_skeleton(layout_json, framework='html-css'):
    """
    Generate skeleton code from structured layout JSON.

    Args:
        layout_json (dict): Structured layout from parser.py.
        framework (str): 'html-css', 'react-tailwind', or 'tailwind-css'.

    Returns:
        str: Generated skeleton code (semantic HTML only — no SVG/canvas).
    """
    generators = {
        'html-css': _generate_html_css,
        'react-tailwind': _generate_react_tailwind,
        'tailwind-css': _generate_tailwind_css
    }

    generator_fn = generators.get(framework, _generate_html_css)
    return generator_fn(layout_json)


# ============================================================
# HTML + CSS Generator
# ============================================================

def _generate_html_css(layout):
    """Generate a complete HTML + CSS skeleton using only semantic tags."""
    sections = layout.get('sections', [])

    css = _build_css()

    body_html = ''
    for section in sections:
        section_type = section.get('type', 'body')
        tag = _section_tag(section_type)
        elements_html = _render_elements_html(section.get('elements', []))
        body_html += f'  <{tag} class="section section-{section_type}">\n'
        body_html += f'    <div class="container">\n{elements_html}    </div>\n'
        body_html += f'  </{tag}>\n\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Generated Page</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
{css}
  </style>
</head>
<body>
{body_html}
</body>
</html>"""


def _build_css():
    """Generate base CSS for the HTML skeleton."""
    return """    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Inter', sans-serif; background: #f8f9fa; color: #1a1a2e; }
    .container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }
    .section { padding: 40px 0; }
    .section-header { background: #1a1a2e; color: #fff; padding: 20px 0; }
    .section-footer { background: #1a1a2e; color: #fff; padding: 20px 0; text-align: center; }
    h1 { font-size: 2rem; font-weight: 700; margin-bottom: 16px; }
    h2 { font-size: 1.5rem; font-weight: 600; margin-bottom: 12px; }
    p { margin-bottom: 12px; line-height: 1.6; color: #4a5568; }
    button { display: inline-block; padding: 12px 28px; background: #6366f1; color: #fff; border: none; border-radius: 8px; cursor: pointer; font-size: 15px; font-weight: 600; transition: background 0.2s; }
    button:hover { background: #4f46e5; }
    input { display: block; width: 100%; padding: 12px 16px; border: 1.5px solid #e2e8f0; border-radius: 8px; font-size: 14px; background: #fff; outline: none; transition: border-color 0.2s; }
    input:focus { border-color: #6366f1; }
    img { max-width: 100%; height: auto; border-radius: 8px; display: block; }
    .img-placeholder { background: #e2e8f0; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #94a3b8; font-size: 14px; }
    .card { background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 16px; }"""


def _render_elements_html(elements):
    """
    Render elements as SEMANTIC HTML tags.

    Mapping:
      heading   → <h1> or <h2>
      button    → <button>
      input     → <input>
      text      → <p>
      image     → <img> placeholder (div styled as image)
      container → <div class="card">
    """
    html = ''
    heading_count = 0

    for el in elements:
        el_type = el.get('type', 'text')
        text = el.get('text', '')
        w = el.get('width', 200)
        h = el.get('height', 120)

        if el_type == 'heading':
            # First heading is h1, rest are h2
            if heading_count == 0:
                html += f'      <h1>{text}</h1>\n'
            else:
                html += f'      <h2>{text}</h2>\n'
            heading_count += 1

        elif el_type == 'button':
            html += f'      <button>{text}</button>\n'

        elif el_type == 'input':
            html += f'      <input type="text" placeholder="{text}">\n'

        elif el_type == 'image':
            html += f'      <div class="img-placeholder" style="width:{w}px;height:{h}px;">Image</div>\n'

        elif el_type == 'container':
            html += f'      <div class="card" style="min-height:{h}px;">\n'
            html += f'        <h2>{text or "Section Title"}</h2>\n'
            html += f'        <p>Container content goes here.</p>\n'
            html += f'      </div>\n'

        else:  # text / fallback
            html += f'      <p>{text}</p>\n'

    return html


def _section_tag(section_type):
    """Map section types to semantic HTML5 tags."""
    return {'header': 'header', 'footer': 'footer', 'body': 'main'}.get(section_type, 'div')


# ============================================================
# React + Tailwind Generator
# ============================================================

def _generate_react_tailwind(layout):
    """Generate a React (JSX) component — semantic tags only, no SVG."""
    sections = layout.get('sections', [])

    jsx_sections = ''
    for section in sections:
        section_type = section.get('type', 'body')
        elements_jsx = _render_elements_react(section.get('elements', []))
        section_class = _tailwind_section_class(section_type)
        tag = _section_tag(section_type)

        jsx_sections += f'      <{tag} className="{section_class}">\n'
        jsx_sections += f'        <div className="max-w-7xl mx-auto px-4">\n{elements_jsx}        </div>\n'
        jsx_sections += f'      </{tag}>\n\n'

    return f"""export default function GeneratedPage() {{
  return (
    <div className="min-h-screen bg-gray-50 font-sans">
{jsx_sections}
    </div>
  );
}}"""


def _render_elements_react(elements):
    """Render elements as React/JSX — only div, button, input, img, p, h1, h2."""
    jsx = ''
    heading_count = 0

    for el in elements:
        el_type = el.get('type', 'text')
        text = el.get('text', '')

        if el_type == 'heading':
            if heading_count == 0:
                jsx += f'          <h1 className="text-3xl font-bold text-gray-900 mb-4">{text}</h1>\n'
            else:
                jsx += f'          <h2 className="text-2xl font-semibold text-gray-800 mb-3">{text}</h2>\n'
            heading_count += 1

        elif el_type == 'button':
            jsx += f'          <button className="px-7 py-3 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 font-semibold transition-colors">{text}</button>\n'

        elif el_type == 'input':
            jsx += f'          <input type="text" className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" placeholder="{text}" />\n'

        elif el_type == 'image':
            jsx += f'          <div className="bg-gray-200 rounded-lg flex items-center justify-center text-gray-400 min-h-[120px]">Image</div>\n'

        elif el_type == 'container':
            jsx += f'          <div className="bg-white rounded-xl p-6 shadow-sm mb-4">\n'
            jsx += f'            <h2 className="text-xl font-semibold mb-2">{text or "Section Title"}</h2>\n'
            jsx += f'            <p className="text-gray-600">Container content goes here.</p>\n'
            jsx += f'          </div>\n'

        else:
            jsx += f'          <p className="text-gray-700 leading-relaxed mb-3">{text}</p>\n'

    return jsx


def _tailwind_section_class(section_type):
    """Get Tailwind classes for section types."""
    return {
        'header': 'bg-gray-900 text-white py-6',
        'footer': 'bg-gray-900 text-white py-6 text-center',
        'body': 'py-12'
    }.get(section_type, 'py-12')


# ============================================================
# Tailwind CSS (HTML) Generator
# ============================================================

def _generate_tailwind_css(layout):
    """Generate HTML with Tailwind CSS — semantic tags only, no SVG."""
    sections = layout.get('sections', [])

    body_html = ''
    for section in sections:
        section_type = section.get('type', 'body')
        elements_html = _render_elements_tailwind(section.get('elements', []))
        section_class = _tailwind_section_class(section_type)
        tag = _section_tag(section_type)

        body_html += f'  <{tag} class="{section_class}">\n'
        body_html += f'    <div class="max-w-7xl mx-auto px-4">\n{elements_html}    </div>\n'
        body_html += f'  </{tag}>\n\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Generated Page</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body class="min-h-screen bg-gray-50 font-sans">
{body_html}
</body>
</html>"""


def _render_elements_tailwind(elements):
    """Render elements as HTML + Tailwind — only div, button, input, img, p, h1, h2."""
    html = ''
    heading_count = 0

    for el in elements:
        el_type = el.get('type', 'text')
        text = el.get('text', '')

        if el_type == 'heading':
            if heading_count == 0:
                html += f'      <h1 class="text-3xl font-bold text-gray-900 mb-4">{text}</h1>\n'
            else:
                html += f'      <h2 class="text-2xl font-semibold text-gray-800 mb-3">{text}</h2>\n'
            heading_count += 1

        elif el_type == 'button':
            html += f'      <button class="px-7 py-3 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 font-semibold transition-colors">{text}</button>\n'

        elif el_type == 'input':
            html += f'      <input type="text" class="w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" placeholder="{text}">\n'

        elif el_type == 'image':
            html += f'      <div class="bg-gray-200 rounded-lg flex items-center justify-center text-gray-400 min-h-[120px]">Image</div>\n'

        elif el_type == 'container':
            html += f'      <div class="bg-white rounded-xl p-6 shadow-sm mb-4">\n'
            html += f'        <h2 class="text-xl font-semibold mb-2">{text or "Section Title"}</h2>\n'
            html += f'        <p class="text-gray-600">Container content goes here.</p>\n'
            html += f'      </div>\n'

        else:
            html += f'      <p class="text-gray-700 leading-relaxed mb-3">{text}</p>\n'

    return html
