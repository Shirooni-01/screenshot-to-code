"""
Layout Parser — Structure components into a page layout
=========================================================
Takes raw detected components and organizes them into:
  1. Rows (Y-axis alignment grouping)
  2. Sections (header / body / footer)
  3. Structured JSON output

Simple heuristic approach — no ML needed.
"""


def parse_layout(components, image_height):
    """
    Parse detected components into a structured layout.

    Args:
        components (list[dict]): Detected components from detector.py.
        image_height (int): Height of the original image (for section splitting).

    Returns:
        dict: Structured layout with sections and rows.
    """
    if not components:
        return {
            'layout': 'vertical',
            'sections': [],
            'total_components': 0
        }

    # ── Step 1: Group components into rows by Y-alignment ──
    rows = _group_into_rows(components)

    # ── Step 2: Sort elements within each row left-to-right ──
    for row in rows:
        row['elements'].sort(key=lambda e: e['x'])

    # ── Step 3: Assign sections (header / body / footer) ──
    sections = _assign_sections(rows, image_height)

    return {
        'layout': 'vertical',
        'sections': sections,
        'total_components': len(components)
    }


def _group_into_rows(components):
    """
    Group components into horizontal rows based on Y-coordinate proximity.
    Components within a tolerance band are considered the same row.
    """
    if not components:
        return []

    # Sort by Y position
    sorted_comps = sorted(components, key=lambda c: c['y'])

    rows = []
    current_row = {
        'y': sorted_comps[0]['y'],
        'elements': [sorted_comps[0]]
    }

    # Tolerance: elements within this Y-distance are in the same row
    # Use the average height of elements as a dynamic tolerance
    avg_height = sum(c['height'] for c in sorted_comps) / len(sorted_comps)
    tolerance = max(avg_height * 0.6, 15)  # At least 15px tolerance

    for comp in sorted_comps[1:]:
        # Check if this component is on the same row
        row_center_y = current_row['y'] + avg_height / 2
        comp_center_y = comp['y'] + comp['height'] / 2

        if abs(comp_center_y - row_center_y) <= tolerance:
            # Same row
            current_row['elements'].append(comp)
        else:
            # New row
            rows.append(current_row)
            current_row = {
                'y': comp['y'],
                'elements': [comp]
            }

    rows.append(current_row)
    return rows


def _assign_sections(rows, image_height):
    """
    Assign rows to header / body / footer sections based on vertical position.

    Heuristic:
      - Top 20% of image → header
      - Bottom 15% of image → footer
      - Everything else → body
    """
    if not rows:
        return []

    header_cutoff = image_height * 0.20
    footer_cutoff = image_height * 0.85

    header_elements = []
    body_elements = []
    footer_elements = []

    for row in rows:
        row_y = row['y']
        elements = row['elements']

        if row_y < header_cutoff:
            header_elements.extend(elements)
        elif row_y >= footer_cutoff:
            footer_elements.extend(elements)
        else:
            body_elements.extend(elements)

    sections = []

    if header_elements:
        sections.append({
            'type': 'header',
            'elements': _clean_elements(header_elements)
        })

    if body_elements:
        sections.append({
            'type': 'body',
            'elements': _clean_elements(body_elements)
        })

    if footer_elements:
        sections.append({
            'type': 'footer',
            'elements': _clean_elements(footer_elements)
        })

    # If no sections were created (unlikely), put everything in body
    if not sections:
        all_elements = []
        for row in rows:
            all_elements.extend(row['elements'])
        sections.append({
            'type': 'body',
            'elements': _clean_elements(all_elements)
        })

    return sections


def _clean_elements(elements):
    """
    Clean element data for output — keep only the fields we need.
    """
    cleaned = []
    for el in elements:
        cleaned.append({
            'type': el.get('type', 'text'),
            'text': el.get('text', ''),
            'x': el.get('x', 0),
            'y': el.get('y', 0),
            'width': el.get('width', 0),
            'height': el.get('height', 0)
        })
    return cleaned
