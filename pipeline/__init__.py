"""
Pipeline Package — Component Detection + Structured Code Generation
====================================================================
Transforms screenshots into structured code through:
  1. detector  → OpenCV-based UI component detection
  2. parser    → Layout grouping & section assignment
  3. generator → Skeleton code generation (HTML/React/Tailwind)
  4. ai_refiner → Gemini-powered styling refinement
"""

from .detector import detect_components
from .parser import parse_layout
from .generator import generate_skeleton
from .ai_refiner import refine_with_ai

__all__ = ['detect_components', 'parse_layout', 'generate_skeleton', 'refine_with_ai']
