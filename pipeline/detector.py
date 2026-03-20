"""
Semantic Component Detector — OpenCV-based UI element detection
================================================================
Detects UI elements and classifies them SEMANTICALLY:

  rectangle + text inside  →  button
  rectangle + empty inside →  input
  large text region        →  heading (h1 / h2)
  small text region        →  text (p)
  big rectangular area     →  image (img placeholder)
  very large grouped area  →  container (div)

Uses contour detection + pixel analysis to check for text inside shapes.
No ML models — pure OpenCV + heuristics. Fast & hackathon-friendly.

OUTPUT TAGS (only these):
  button, input, heading, text, image, container
"""

import cv2
import numpy as np


def detect_components(image_path):
    """
    Detect UI components from a screenshot using OpenCV.
    Classifies semantically by analyzing what's INSIDE each detected region.

    Args:
        image_path (str): Path to the screenshot image.

    Returns:
        list[dict]: Detected components with semantic type, position, and size.
                    Each dict has: type, text, x, y, width, height.
    """
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ── Edge Detection (Canny) + Dilate to close gaps ──
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 30, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(edges, kernel, iterations=2)

    # ── Find contours ──
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # ── Filter & classify contours SEMANTICALLY ──
    raw_components = []
    min_area = (width * height) * 0.0005   # Ignore tiny noise
    max_area = (width * height) * 0.85     # Ignore near-full-screen boxes

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h

        if area < min_area or area > max_area:
            continue
        if w < 10 or h < 8:
            continue

        # ── SEMANTIC CLASSIFICATION ──
        # Look INSIDE the rectangle to decide what it is
        component_type = _classify_semantically(gray, x, y, w, h, width, height)
        placeholder = _placeholder_for_type(component_type)

        raw_components.append({
            'type': component_type,
            'text': placeholder,
            'x': int(x),
            'y': int(y),
            'width': int(w),
            'height': int(h),
            'area': int(area)
        })

    # ── Remove overlapping detections ──
    components = _remove_overlaps(raw_components)

    # ── Sort top-to-bottom, left-to-right ──
    components.sort(key=lambda c: (c['y'], c['x']))

    # Remove internal 'area' field
    for c in components:
        c.pop('area', None)

    return components


def _classify_semantically(gray, x, y, w, h, img_w, img_h):
    """
    Classify a detected rectangle into a SEMANTIC UI type.

    Logic:
      1. Crop the region from the grayscale image.
      2. Check if it contains text (high contrast / many dark pixels).
      3. Use size + text presence to decide:
         - Small/medium rect WITH text  →  button
         - Wide rect WITHOUT text       →  input
         - Very wide, thin, has text    →  heading or text
         - Large area                   →  image or container
    """
    aspect_ratio = w / max(h, 1)
    rel_w = w / img_w         # width relative to image
    rel_h = h / img_h         # height relative to image
    rel_area = (w * h) / (img_w * img_h)

    # Crop the region and analyze its content
    has_text = _region_has_text(gray, x, y, w, h)

    # ── CONTAINER: Very large area covering a big chunk of the image ──
    if rel_area > 0.15 and rel_w > 0.4:
        return 'container'

    # ── IMAGE: Medium-large area, roughly square-ish, no obvious text ──
    if rel_area > 0.03 and 0.3 < aspect_ratio < 3.5 and rel_h > 0.08:
        if not has_text:
            return 'image'
        # If it has text inside a large area, it's a container
        return 'container'

    # ── HEADING: Wide text region, taller than typical paragraph text ──
    if has_text and rel_w > 0.25 and 15 < h < img_h * 0.08:
        return 'heading'

    # ── BUTTON: Small/medium rectangle WITH text inside ──
    if has_text and rel_w < 0.5 and rel_h < 0.1 and 1.0 < aspect_ratio < 8.0:
        return 'button'

    # ── INPUT: Wide-ish rectangle WITHOUT text inside (empty field) ──
    if not has_text and 2.0 < aspect_ratio < 25.0 and rel_w > 0.1 and rel_h < 0.08:
        return 'input'

    # ── TEXT (paragraph): Wide region with text, thin height ──
    if has_text and rel_w > 0.2 and rel_h < 0.06:
        return 'text'

    # ── INPUT fallback: Rectangle that's clearly a form field shape ──
    if not has_text and rel_h < 0.08 and aspect_ratio > 2.0:
        return 'input'

    # ── BUTTON fallback: Small clickable-looking rectangle with text ──
    if has_text and rel_area < 0.03:
        return 'button'

    # ── Defaults based on size ──
    if rel_area > 0.08:
        return 'container'
    if has_text:
        return 'text'
    return 'input'


def _region_has_text(gray, x, y, w, h):
    """
    Check if a cropped region contains text by analyzing pixel contrast.

    Text creates high contrast (dark pixels on light background or vice versa).
    An empty input field or image placeholder has uniform/low-contrast pixels.

    Returns True if the region likely contains readable text.
    """
    # Safely crop the region
    roi = gray[y:y+h, x:x+w]
    if roi.size == 0:
        return False

    # ── Method 1: Standard deviation of pixel values ──
    # Text regions have high std dev due to dark-on-light contrast
    std_dev = np.std(roi)

    # ── Method 2: Ratio of "dark" pixels ──
    # In a region with text, there are clusters of very dark pixels (the letters)
    mean_val = np.mean(roi)
    threshold = mean_val * 0.6  # pixels much darker than the region average
    dark_pixel_ratio = np.sum(roi < threshold) / roi.size

    # ── Method 3: Edge density inside the region ──
    # Text has many small edges; empty fields have very few
    roi_edges = cv2.Canny(roi, 50, 150)
    edge_density = np.sum(roi_edges > 0) / roi.size

    # Decision: region has text if it shows significant contrast patterns
    # Tuned thresholds for typical UI screenshots
    has_high_contrast = std_dev > 25
    has_dark_clusters = dark_pixel_ratio > 0.05
    has_many_edges = edge_density > 0.03

    # Need at least 2 out of 3 signals to confirm text
    signals = sum([has_high_contrast, has_dark_clusters, has_many_edges])
    return signals >= 2


def _placeholder_for_type(component_type):
    """Generate sensible placeholder text for each semantic component type."""
    placeholders = {
        'button': 'Click Me',
        'input': 'Enter text...',
        'heading': 'Page Heading',
        'text': 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
        'image': '',
        'container': ''
    }
    return placeholders.get(component_type, '')


def _remove_overlaps(components):
    """
    Remove significantly overlapping detections.
    If two boxes overlap > 60%, keep the smaller (more specific) one.
    """
    if not components:
        return []

    sorted_comps = sorted(components, key=lambda c: c['area'])
    keep = []

    for comp in sorted_comps:
        is_duplicate = False
        for kept in keep:
            if _compute_iou(comp, kept) > 0.6:
                is_duplicate = True
                break
        if not is_duplicate:
            keep.append(comp)

    return keep


def _compute_iou(a, b):
    """Compute Intersection over Union between two bounding boxes."""
    x1 = max(a['x'], b['x'])
    y1 = max(a['y'], b['y'])
    x2 = min(a['x'] + a['width'], b['x'] + b['width'])
    y2 = min(a['y'] + a['height'], b['y'] + b['height'])

    if x2 <= x1 or y2 <= y1:
        return 0.0

    intersection = (x2 - x1) * (y2 - y1)
    union = a['width'] * a['height'] + b['width'] * b['height'] - intersection
    return intersection / max(union, 1)
