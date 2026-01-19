"""
SVG Parser for LaserBurn

Supports basic shapes and paths. Simplified version for initial release.
"""

import re
import math
from xml.etree import ElementTree as ET
from typing import List, Optional, Tuple

from ..core.shapes import (
    Shape, Path, Rectangle, Ellipse, Point,
    MoveToSegment, LineToSegment, CubicBezierSegment, QuadraticBezierSegment
)
from ..core.document import Document
from ..core.layer import Layer


class SVGParser:
    """Parse SVG files into LaserBurn documents."""
    
    SVG_NS = '{http://www.w3.org/2000/svg}'
    
    def __init__(self):
        self.document: Optional[Document] = None
        # Transform matrix: [a, b, c, d, e, f] representing [[a, c, e], [b, d, f], [0, 0, 1]]
        self.current_transform: List[float] = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]  # Identity matrix
    
    def parse_file(self, filepath: str) -> Document:
        """Parse an SVG file and return a Document."""
        tree = ET.parse(filepath)
        root = tree.getroot()
        return self.parse_svg(root)
    
    def parse_string(self, svg_string: str) -> Document:
        """Parse an SVG string and return a Document."""
        root = ET.fromstring(svg_string)
        return self.parse_svg(root)
    
    def parse_svg(self, root: ET.Element) -> Document:
        """Parse the SVG root element."""
        # Reset transform to identity for each parse
        self.current_transform = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
        
        # Get document dimensions
        width = self._parse_length(root.get('width', '300'))
        height = self._parse_length(root.get('height', '200'))
        
        # Handle viewBox
        viewbox = root.get('viewBox')
        if viewbox:
            vb_parts = viewbox.split()
            if len(vb_parts) == 4:
                # viewBox format: "x y width height"
                # Use viewBox dimensions if width/height not specified
                if not root.get('width') or not root.get('height'):
                    width = float(vb_parts[2])
                    height = float(vb_parts[3])
        
        self.document = Document(width=width, height=height)
        
        # Create default layer
        default_layer = Layer(name="SVG Import")
        self.document.add_layer(default_layer)
        
        # Parse all elements
        self._parse_element(root, default_layer)
        
        return self.document
    
    def _get_style_value(self, element: ET.Element, attr: str, default: str = 'none') -> str:
        """Get style attribute value, checking both style attribute and direct attribute."""
        # Check direct attribute first
        value = element.get(attr)
        if value:
            return value
        
        # Check style attribute
        style = element.get('style', '')
        if style:
            # Parse style="fill:black;stroke:none"
            for part in style.split(';'):
                if ':' in part:
                    key, val = part.split(':', 1)
                    if key.strip() == attr:
                        return val.strip()
        
        return default
    
    def _parse_element(self, element: ET.Element, layer: Layer) -> None:
        """Recursively parse SVG elements."""
        tag = element.tag.replace(self.SVG_NS, '')
        
        # Save current transform
        saved_transform = self.current_transform.copy()
        
        # Apply element's transform
        transform_str = element.get('transform')
        if transform_str:
            self._apply_transform(transform_str)
        
        shape = None
        if tag == 'rect':
            shape = self._parse_rect(element)
        elif tag == 'circle':
            shape = self._parse_circle(element)
        elif tag == 'ellipse':
            shape = self._parse_ellipse(element)
        elif tag == 'line':
            shape = self._parse_line(element)
        elif tag == 'polyline':
            shape = self._parse_polyline(element, closed=False)
        elif tag == 'polygon':
            shape = self._parse_polyline(element, closed=True)
        elif tag == 'path':
            shape = self._parse_path(element)
        elif tag in ('g', 'svg'):
            # Group - recurse into children
            for child in element:
                self._parse_element(child, layer)
        
        if shape:
            # Apply current transform to shape
            self._apply_transform_to_shape(shape)
            layer.add_shape(shape)
        
        # Restore transform
        self.current_transform = saved_transform
    
    def _parse_rect(self, element: ET.Element) -> Rectangle:
        """Parse a rect element."""
        x = float(element.get('x', 0))
        y = float(element.get('y', 0))
        width = float(element.get('width', 0))
        height = float(element.get('height', 0))
        rx = float(element.get('rx', 0))
        
        return Rectangle(x, y, width, height, corner_radius=rx)
    
    def _parse_circle(self, element: ET.Element) -> Ellipse:
        """Parse a circle element."""
        cx = float(element.get('cx', 0))
        cy = float(element.get('cy', 0))
        r = float(element.get('r', 0))
        
        return Ellipse(cx, cy, r, r)
    
    def _parse_ellipse(self, element: ET.Element) -> Ellipse:
        """Parse an ellipse element."""
        cx = float(element.get('cx', 0))
        cy = float(element.get('cy', 0))
        rx = float(element.get('rx', 0))
        ry = float(element.get('ry', 0))
        
        return Ellipse(cx, cy, rx, ry)
    
    def _parse_line(self, element: ET.Element) -> Path:
        """Parse a line element."""
        x1 = float(element.get('x1', 0))
        y1 = float(element.get('y1', 0))
        x2 = float(element.get('x2', 0))
        y2 = float(element.get('y2', 0))
        
        path = Path()
        path.move_to(x1, y1)
        path.line_to(x2, y2)
        return path
    
    def _parse_polyline(self, element: ET.Element, closed: bool) -> Path:
        """Parse a polyline or polygon element."""
        points_str = element.get('points', '')
        points = self._parse_points(points_str)
        
        if not points:
            return Path()
        
        path = Path()
        path.move_to(points[0][0], points[0][1])
        for x, y in points[1:]:
            path.line_to(x, y)
        
        if closed:
            path.close()
        
        return path
    
    def _parse_path(self, element: ET.Element) -> Path:
        """Parse a path element's d attribute."""
        d = element.get('d', '')
        if not d or not d.strip():
            return Path()
            
        path = self._parse_path_d(d)
        
        # Check if path should be closed based on fill attribute
        # For laser cutting, we typically want closed paths for filled shapes
        # BUT: Only close if the path isn't already closed (has Z command)
        fill = self._get_style_value(element, 'fill', 'none')
        
        # Check if path already ends with Z (closed command)
        d_stripped = d.strip()
        is_already_closed = d_stripped.upper().endswith('Z')
        
        # If fill is not 'none', ensure path is closed (for outline cutting)
        # But don't close if it's already closed
        if fill and fill.lower() not in ('none', 'transparent', ''):
            if not path.closed and not is_already_closed and path.segments:
                # Close the path to create a proper outline
                path.close()
        
        return path
    
    def _parse_path_d(self, d: str) -> Path:
        """Parse SVG path data string - simplified version."""
        path = Path()
        
        # Tokenize
        tokens = self._tokenize_path(d)
        if not tokens:
            return path
        
        current_x, current_y = 0.0, 0.0
        start_x, start_y = 0.0, 0.0
        i = 0
        last_command = None
        last_control = None  # For smooth curves (S, T)
        has_initial_moveto = False  # Track if path started with moveTo
        
        def is_numeric(s: str) -> bool:
            """Check if string can be converted to float."""
            try:
                float(s)
                return True
            except ValueError:
                return False
        
        def get_float_token(idx: int) -> Optional[float]:
            """Safely get a float token, return None if invalid."""
            if idx >= len(tokens):
                return None
            token = tokens[idx]
            if is_numeric(token):
                return float(token)
            return None
        
        while i < len(tokens):
            token = tokens[i]
            
            if token.isalpha():
                command = token
                i += 1
                last_command = command
            else:
                # Repeat last command (except M becomes L, preserving case)
                if last_command:
                    command = last_command
                    if command.upper() == 'M':
                        # M becomes L, m becomes l (preserve relative/absolute)
                        command = 'L' if command.isupper() else 'l'
                else:
                    command = 'L'  # Default to line
            
            is_relative = command.islower()
            cmd_upper = command.upper()
            
            try:
                if cmd_upper == 'M':
                    if i + 1 >= len(tokens):
                        break
                    x = get_float_token(i)
                    y = get_float_token(i + 1)
                    if x is None or y is None:
                        # Skip invalid move command
                        break
                    i += 2
                    if is_relative:
                        x += current_x
                        y += current_y
                    path.move_to(x, y)
                    current_x, current_y = x, y
                    start_x, start_y = x, y
                    last_control = None  # Reset control point on move
                    has_initial_moveto = True
                    
                elif cmd_upper == 'L':
                    if i + 1 >= len(tokens):
                        break
                    x = get_float_token(i)
                    y = get_float_token(i + 1)
                    if x is None or y is None:
                        # Skip invalid line command
                        break
                    i += 2
                    if is_relative:
                        x += current_x
                        y += current_y
                    # Ensure we have an initial moveTo before lineTo
                    if not has_initial_moveto:
                        path.move_to(current_x, current_y)
                        has_initial_moveto = True
                    path.line_to(x, y)
                    current_x, current_y = x, y
                    last_control = None  # Reset control point on line
                    
                elif cmd_upper == 'H':  # Horizontal line
                    if i >= len(tokens):
                        break
                    x = get_float_token(i)
                    if x is None:
                        break
                    i += 1
                    if is_relative:
                        x += current_x
                    if not has_initial_moveto:
                        path.move_to(current_x, current_y)
                        has_initial_moveto = True
                    path.line_to(x, current_y)
                    current_x = x
                    last_control = None  # Reset control point on line
                    
                elif cmd_upper == 'V':  # Vertical line
                    if i >= len(tokens):
                        break
                    y = get_float_token(i)
                    if y is None:
                        break
                    i += 1
                    if is_relative:
                        y += current_y
                    if not has_initial_moveto:
                        path.move_to(current_x, current_y)
                        has_initial_moveto = True
                    path.line_to(current_x, y)
                    current_y = y
                    last_control = None  # Reset control point on line
                    
                elif cmd_upper == 'C':  # Cubic bezier curve
                    if i + 5 >= len(tokens):
                        break
                    cp1x = get_float_token(i)
                    cp1y = get_float_token(i + 1)
                    cp2x = get_float_token(i + 2)
                    cp2y = get_float_token(i + 3)
                    x = get_float_token(i + 4)
                    y = get_float_token(i + 5)
                    if any(v is None for v in [cp1x, cp1y, cp2x, cp2y, x, y]):
                        break
                    i += 6
                    if is_relative:
                        cp1x += current_x
                        cp1y += current_y
                        cp2x += current_x
                        cp2y += current_y
                        x += current_x
                        y += current_y
                    if not has_initial_moveto:
                        path.move_to(current_x, current_y)
                        has_initial_moveto = True
                    path.cubic_to(cp1x, cp1y, cp2x, cp2y, x, y)
                    current_x, current_y = x, y
                    last_control = Point(cp2x, cp2y)  # Store second control point
                    
                elif cmd_upper == 'S':  # Smooth cubic bezier (reflects previous control point)
                    if i + 3 >= len(tokens):
                        break
                    cp2x = get_float_token(i)
                    cp2y = get_float_token(i + 1)
                    x = get_float_token(i + 2)
                    y = get_float_token(i + 3)
                    if any(v is None for v in [cp2x, cp2y, x, y]):
                        break
                    i += 4
                    if is_relative:
                        cp2x += current_x
                        cp2y += current_y
                        x += current_x
                        y += current_y
                    if not has_initial_moveto:
                        path.move_to(current_x, current_y)
                        has_initial_moveto = True
                    # Reflect last control point for smooth curve
                    if last_control and last_command and last_command.upper() in ('C', 'S'):
                        cp1x = 2 * current_x - last_control.x
                        cp1y = 2 * current_y - last_control.y
                    else:
                        cp1x, cp1y = current_x, current_y
                    path.cubic_to(cp1x, cp1y, cp2x, cp2y, x, y)
                    current_x, current_y = x, y
                    last_control = Point(cp2x, cp2y)
                    
                elif cmd_upper == 'Q':  # Quadratic bezier curve
                    if i + 3 >= len(tokens):
                        break
                    cpx = get_float_token(i)
                    cpy = get_float_token(i + 1)
                    x = get_float_token(i + 2)
                    y = get_float_token(i + 3)
                    if any(v is None for v in [cpx, cpy, x, y]):
                        break
                    i += 4
                    if is_relative:
                        cpx += current_x
                        cpy += current_y
                        x += current_x
                        y += current_y
                    if not has_initial_moveto:
                        path.move_to(current_x, current_y)
                        has_initial_moveto = True
                    path.quadratic_to(cpx, cpy, x, y)
                    current_x, current_y = x, y
                    last_control = Point(cpx, cpy)
                    
                elif cmd_upper == 'T':  # Smooth quadratic bezier
                    if i + 1 >= len(tokens):
                        break
                    x = get_float_token(i)
                    y = get_float_token(i + 1)
                    if x is None or y is None:
                        break
                    i += 2
                    if is_relative:
                        x += current_x
                        y += current_y
                    if not has_initial_moveto:
                        path.move_to(current_x, current_y)
                        has_initial_moveto = True
                    # Reflect last control point for smooth curve
                    if last_control and last_command and last_command.upper() in ('Q', 'T'):
                        cpx = 2 * current_x - last_control.x
                        cpy = 2 * current_y - last_control.y
                    else:
                        cpx, cpy = current_x, current_y
                    path.quadratic_to(cpx, cpy, x, y)
                    current_x, current_y = x, y
                    last_control = Point(cpx, cpy)
                    
                elif cmd_upper == 'A':  # Arc command - convert to bezier curves
                    if i + 6 >= len(tokens):
                        break
                    rx = abs(get_float_token(i) or 0)
                    ry = abs(get_float_token(i + 1) or 0)
                    x_rot = get_float_token(i + 2) or 0
                    large_arc = int(get_float_token(i + 3) or 0)
                    sweep = int(get_float_token(i + 4) or 0)
                    x = get_float_token(i + 5)
                    y = get_float_token(i + 6)
                    if x is None or y is None:
                        break
                    i += 7
                    if is_relative:
                        x += current_x
                        y += current_y
                    
                    # Skip degenerate arcs (start == end)
                    if abs(x - current_x) < 0.0001 and abs(y - current_y) < 0.0001:
                        # No arc needed, already at destination
                        last_control = None
                        continue
                    
                    if not has_initial_moveto:
                        path.move_to(current_x, current_y)
                        has_initial_moveto = True
                    
                    # Convert arc to cubic beziers
                    arc_paths = self._arc_to_bezier(
                        current_x, current_y, rx, ry, x_rot,
                        large_arc, sweep, x, y
                    )
                    for cp1, cp2, end in arc_paths:
                        path.cubic_to(cp1.x, cp1.y, cp2.x, cp2.y, end.x, end.y)
                    
                    current_x, current_y = x, y
                    last_control = None
                    
                elif cmd_upper == 'Z':
                    path.close()
                    current_x, current_y = start_x, start_y
                    last_control = None
                    # Don't increment i here since Z has no parameters
                    
                else:
                    # Skip unsupported commands - try to find next command
                    # Look ahead for next alphabetic token
                    found_next = False
                    for j in range(i, len(tokens)):
                        if tokens[j].isalpha():
                            i = j
                            found_next = True
                            break
                    if not found_next:
                        break  # No more commands
            except (ValueError, IndexError) as e:
                # Skip invalid tokens and try to continue
                print(f"Warning: Error parsing path token at position {i}: {e}")
                i += 1
                if i >= len(tokens):
                    break
            
            # Update last_command for next iteration
            if token.isalpha():
                last_command = command
        
        return path
    
    def _arc_to_bezier(self, x1: float, y1: float, rx: float, ry: float,
                       phi: float, large_arc: int, sweep: int,
                       x2: float, y2: float) -> List[Tuple[Point, Point, Point]]:
        """Convert SVG arc to cubic bezier curves."""
        # Implementation based on W3C SVG arc specification
        
        if rx == 0 or ry == 0:
            # Degenerate case - straight line
            return [(Point(x1, y1), Point(x2, y2), Point(x2, y2))]
        
        phi_rad = math.radians(phi)
        cos_phi = math.cos(phi_rad)
        sin_phi = math.sin(phi_rad)
        
        # Step 1: Compute (x1', y1')
        dx = (x1 - x2) / 2
        dy = (y1 - y2) / 2
        x1p = cos_phi * dx + sin_phi * dy
        y1p = -sin_phi * dx + cos_phi * dy
        
        # Ensure radii are large enough
        lambda_ = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
        if lambda_ > 1:
            rx *= math.sqrt(lambda_)
            ry *= math.sqrt(lambda_)
        
        # Step 2: Compute (cx', cy')
        sq = max(0, ((rx*rx * ry*ry) - (rx*rx * y1p*y1p) - (ry*ry * x1p*x1p)) /
                    ((rx*rx * y1p*y1p) + (ry*ry * x1p*x1p)))
        coef = math.sqrt(sq)
        if large_arc == sweep:
            coef = -coef
        cxp = coef * rx * y1p / ry
        cyp = -coef * ry * x1p / rx
        
        # Step 3: Compute (cx, cy) from (cx', cy')
        cx = cos_phi * cxp - sin_phi * cyp + (x1 + x2) / 2
        cy = sin_phi * cxp + cos_phi * cyp + (y1 + y2) / 2
        
        # Step 4: Compute theta1 and dtheta
        def angle(ux, uy, vx, vy):
            n = math.sqrt(ux*ux + uy*uy) * math.sqrt(vx*vx + vy*vy)
            if n == 0:
                return 0
            c = (ux*vx + uy*vy) / n
            s = ux*vy - uy*vx
            return math.atan2(s, max(-1, min(1, c)))
        
        theta1 = angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
        dtheta = angle((x1p - cxp) / rx, (y1p - cyp) / ry,
                       (-x1p - cxp) / rx, (-y1p - cyp) / ry)
        
        if sweep == 0 and dtheta > 0:
            dtheta -= 2 * math.pi
        elif sweep == 1 and dtheta < 0:
            dtheta += 2 * math.pi
        
        # Split arc into segments of max 90 degrees
        segments = max(1, int(math.ceil(abs(dtheta) / (math.pi / 2))))
        delta = dtheta / segments
        
        curves = []
        for i in range(segments):
            t1 = theta1 + i * delta
            t2 = theta1 + (i + 1) * delta
            
            # Bezier control points for arc segment
            alpha = math.sin(delta) * (math.sqrt(4 + 3 * math.tan(delta/2)**2) - 1) / 3
            
            x1_i = math.cos(t1)
            y1_i = math.sin(t1)
            x2_i = math.cos(t2)
            y2_i = math.sin(t2)
            
            cp1x = x1_i - alpha * y1_i
            cp1y = y1_i + alpha * x1_i
            cp2x = x2_i + alpha * y2_i
            cp2y = y2_i - alpha * x2_i
            
            # Transform back
            def transform_point(px, py):
                x = px * rx
                y = py * ry
                return Point(
                    cos_phi * x - sin_phi * y + cx,
                    sin_phi * x + cos_phi * y + cy
                )
            
            p1 = transform_point(x1_i, y1_i)
            c1 = transform_point(cp1x, cp1y)
            c2 = transform_point(cp2x, cp2y)
            p2 = transform_point(x2_i, y2_i)
            
            curves.append((c1, c2, p2))
        
        return curves
    
    def _tokenize_path(self, d: str) -> List[str]:
        """Tokenize SVG path data."""
        # Improved pattern that handles:
        # - Commands: M, L, H, V, C, S, Q, T, A, Z (case insensitive)
        # - Numbers: integers, decimals, scientific notation
        # - Negative numbers (including after commands)
        pattern = r'([MmZzLlHhVvCcSsQqTtAa])|(-?[0-9]+\.?[0-9]*(?:[eE][-+]?[0-9]+)?)|(-?\.[0-9]+(?:[eE][-+]?[0-9]+)?)'
        tokens = []
        for match in re.finditer(pattern, d):
            # Get the matched group (command or number)
            token = match.group(0)  # Get the full match
            if token and token.strip():
                tokens.append(token.strip())
        return tokens
    
    def _parse_length(self, length_str: str) -> float:
        """Parse SVG length value."""
        if not length_str:
            return 0.0
        
        # Remove units
        for unit in ['px', 'pt', 'pc', 'mm', 'cm', 'in', 'em']:
            if length_str.endswith(unit):
                return float(length_str[:-len(unit)])
        
        return float(length_str)
    
    def _parse_points(self, points_str: str) -> List[Tuple[float, float]]:
        """Parse SVG points attribute."""
        points = []
        numbers = re.findall(r'-?[0-9]*\.?[0-9]+', points_str)
        for i in range(0, len(numbers) - 1, 2):
            points.append((float(numbers[i]), float(numbers[i+1])))
        return points
    
    def _apply_transform(self, transform_str: str) -> None:
        """Apply SVG transform to current matrix."""
        # Parse transforms like "translate(10, 20) rotate(45) scale(2)"
        transform_pattern = r'(translate|rotate|scale|matrix|skewX|skewY)\s*\(([^)]+)\)'
        
        for match in re.finditer(transform_pattern, transform_str):
            func = match.group(1)
            args = [float(x) for x in re.findall(r'-?[0-9]*\.?[0-9]+', match.group(2))]
            
            if func == 'translate':
                tx = args[0] if len(args) > 0 else 0
                ty = args[1] if len(args) > 1 else 0
                # Translation matrix: [[1, 0, tx], [0, 1, ty], [0, 0, 1]]
                self._multiply_matrix([1.0, 0.0, 0.0, 1.0, tx, ty])
                
            elif func == 'rotate':
                angle = math.radians(args[0])
                cx = args[1] if len(args) > 1 else 0
                cy = args[2] if len(args) > 2 else 0
                cos_a = math.cos(angle)
                sin_a = math.sin(angle)
                # Rotation matrix: [[cos, -sin, 0], [sin, cos, 0], [0, 0, 1]]
                # If center point, translate, rotate, translate back
                if cx != 0 or cy != 0:
                    self._multiply_matrix([1.0, 0.0, 0.0, 1.0, -cx, -cy])
                self._multiply_matrix([cos_a, sin_a, -sin_a, cos_a, 0.0, 0.0])
                if cx != 0 or cy != 0:
                    self._multiply_matrix([1.0, 0.0, 0.0, 1.0, cx, cy])
                    
            elif func == 'scale':
                sx = args[0] if len(args) > 0 else 1
                sy = args[1] if len(args) > 1 else sx
                # Scale matrix: [[sx, 0, 0], [0, sy, 0], [0, 0, 1]]
                self._multiply_matrix([sx, 0.0, 0.0, sy, 0.0, 0.0])
                
            elif func == 'matrix':
                if len(args) >= 6:
                    # Direct matrix: [[a, c, e], [b, d, f], [0, 0, 1]]
                    self._multiply_matrix([args[0], args[1], args[2], args[3], args[4], args[5]])
                    
            elif func == 'skewX':
                angle = math.radians(args[0] if len(args) > 0 else 0)
                tan_a = math.tan(angle)
                # SkewX matrix: [[1, 0, 0], [tan, 1, 0], [0, 0, 1]]
                self._multiply_matrix([1.0, tan_a, 0.0, 1.0, 0.0, 0.0])
                
            elif func == 'skewY':
                angle = math.radians(args[0] if len(args) > 0 else 0)
                tan_a = math.tan(angle)
                # SkewY matrix: [[1, tan, 0], [0, 1, 0], [0, 0, 1]]
                self._multiply_matrix([1.0, 0.0, tan_a, 1.0, 0.0, 0.0])
    
    def _multiply_matrix(self, other: List[float]) -> None:
        """Multiply current transform matrix by another matrix."""
        # Current: [a1, b1, c1, d1, e1, f1]
        # Other: [a2, b2, c2, d2, e2, f2]
        # Result: other * current
        a1, b1, c1, d1, e1, f1 = self.current_transform
        a2, b2, c2, d2, e2, f2 = other
        
        # Matrix multiplication
        # [[a2, c2, e2], [b2, d2, f2], [0, 0, 1]] * [[a1, c1, e1], [b1, d1, f1], [0, 0, 1]]
        self.current_transform = [
            a2 * a1 + c2 * b1,      # a
            b2 * a1 + d2 * b1,      # b
            a2 * c1 + c2 * d1,      # c
            b2 * c1 + d2 * d1,      # d
            a2 * e1 + c2 * f1 + e2, # e
            b2 * e1 + d2 * f1 + f2  # f
        ]
    
    def _apply_transform_to_shape(self, shape: Shape) -> None:
        """Apply current transform matrix to a shape."""
        # Transform all points in the shape
        # For shapes with position (Rectangle, Ellipse), transform the position
        # For Path shapes, we'll transform points when getting paths
        
        if isinstance(shape, (Rectangle, Ellipse)):
            # Transform the position point
            p = self._transform_point(Point(shape.position.x, shape.position.y))
            shape.position = p
            
            # Apply scale to dimensions
            a, b, c, d, e, f = self.current_transform
            scale_x = math.sqrt(a * a + b * b)
            scale_y = math.sqrt(c * c + d * d)
            
            if isinstance(shape, Rectangle):
                shape.width *= scale_x
                shape.height *= scale_y
            elif isinstance(shape, Ellipse):
                shape.radius_x *= scale_x
                shape.radius_y *= scale_y
                
        elif isinstance(shape, Path):
            # Transform all path segments to world coordinates
            for seg in shape.segments:
                if isinstance(seg, MoveToSegment):
                    seg.point = self._transform_point(seg.point)
                elif isinstance(seg, LineToSegment):
                    seg.point = self._transform_point(seg.point)
                elif isinstance(seg, CubicBezierSegment):
                    seg.cp1 = self._transform_point(seg.cp1)
                    seg.cp2 = self._transform_point(seg.cp2)
                    seg.end_point = self._transform_point(seg.end_point)
                elif isinstance(seg, QuadraticBezierSegment):
                    seg.control_point = self._transform_point(seg.control_point)
                    seg.end_point = self._transform_point(seg.end_point)
            
            # Normalize path: calculate bounding box and offset segments to local coordinates
            # This ensures position is applied correctly in get_paths()
            if shape.segments:
                # Calculate bounding box from transformed segments
                all_points = []
                for seg in shape.segments:
                    if isinstance(seg, MoveToSegment):
                        all_points.append(seg.point)
                    elif isinstance(seg, LineToSegment):
                        all_points.append(seg.point)
                    elif isinstance(seg, CubicBezierSegment):
                        all_points.extend([seg.cp1, seg.cp2, seg.end_point])
                    elif isinstance(seg, QuadraticBezierSegment):
                        all_points.extend([seg.control_point, seg.end_point])
                
                if all_points:
                    min_x = min(p.x for p in all_points)
                    min_y = min(p.y for p in all_points)
                    
                    # Set position to minimum point
                    shape.position = Point(min_x, min_y)
                    
                    # Offset all segments by -position to put them in local coordinates
                    offset = Point(-min_x, -min_y)
                    for seg in shape.segments:
                        if isinstance(seg, MoveToSegment):
                            seg.point = Point(seg.point.x + offset.x, seg.point.y + offset.y)
                        elif isinstance(seg, LineToSegment):
                            seg.point = Point(seg.point.x + offset.x, seg.point.y + offset.y)
                        elif isinstance(seg, CubicBezierSegment):
                            seg.cp1 = Point(seg.cp1.x + offset.x, seg.cp1.y + offset.y)
                            seg.cp2 = Point(seg.cp2.x + offset.x, seg.cp2.y + offset.y)
                            seg.end_point = Point(seg.end_point.x + offset.x, seg.end_point.y + offset.y)
                        elif isinstance(seg, QuadraticBezierSegment):
                            seg.control_point = Point(seg.control_point.x + offset.x, seg.control_point.y + offset.y)
                            seg.end_point = Point(seg.end_point.x + offset.x, seg.end_point.y + offset.y)
    
    def _transform_point(self, point: Point) -> Point:
        """Transform a point using the current transform matrix."""
        a, b, c, d, e, f = self.current_transform
        # Matrix multiplication: [[a, c, e], [b, d, f], [0, 0, 1]] * [x, y, 1]
        x = a * point.x + c * point.y + e
        y = b * point.x + d * point.y + f
        return Point(x, y)


def export_svg(document: Document, filepath: str) -> None:
    """Export a Document to SVG format."""
    svg = ET.Element('svg')
    svg.set('xmlns', 'http://www.w3.org/2000/svg')
    svg.set('width', f'{document.width}mm')
    svg.set('height', f'{document.height}mm')
    svg.set('viewBox', f'0 0 {document.width} {document.height}')
    
    for layer in document.layers:
        g = ET.SubElement(svg, 'g')
        g.set('id', layer.name)
        g.set('stroke', layer.color)
        g.set('fill', 'none')
        
        for shape in layer.shapes:
            paths = shape.get_paths()
            for path_points in paths:
                if not path_points:
                    continue
                
                d = f'M {path_points[0].x},{path_points[0].y}'
                for point in path_points[1:]:
                    d += f' L {point.x},{point.y}'
                
                path_elem = ET.SubElement(g, 'path')
                path_elem.set('d', d)
    
    tree = ET.ElementTree(svg)
    ET.indent(tree, space="  ")
    tree.write(filepath, encoding='unicode', xml_declaration=True)

