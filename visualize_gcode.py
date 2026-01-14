#!/usr/bin/env python3
"""
Visualize G-code as ASCII art to preview what will be engraved.
"""

import sys
import re
from pathlib import Path

def parse_gcode(filepath):
    """Parse G-code and extract engraving moves."""
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # State tracking
    x = 0.0
    y = 0.0
    relative_mode = False
    engraving_points = []  # List of (x, y) tuples where laser is on
    
    # Track bounds
    min_x = float('inf')
    max_x = float('-inf')
    min_y = float('inf')
    max_y = float('-inf')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith(';'):
            continue
        
        # Check for mode changes
        if 'G90' in line:
            relative_mode = False
        elif 'G91' in line:
            relative_mode = True
        
        # Parse G0/G1 moves
        if line.startswith('G0') or line.startswith('G1'):
            # Extract X, Y, S values
            x_match = re.search(r'X([-\d.]+)', line)
            y_match = re.search(r'Y([-\d.]+)', line)
            s_match = re.search(r'S(\d+)', line)
            
            # Update position
            if x_match:
                x_val = float(x_match.group(1))
                if relative_mode:
                    x += x_val
                else:
                    x = x_val
            
            if y_match:
                y_val = float(y_match.group(1))
                if relative_mode:
                    y += y_val
                else:
                    y = y_val
            
            # Check if laser is on (S > 0)
            laser_on = False
            if s_match:
                s_val = int(s_match.group(1))
                laser_on = (s_val > 0)
            
            # Record engraving point if laser is on
            if laser_on:
                engraving_points.append((x, y))
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
    
    return engraving_points, (min_x, max_x, min_y, max_y)


def render_ascii(engraving_points, bounds, width=120, height=40):
    """Render engraving points as ASCII art."""
    if not engraving_points:
        return "No engraving points found"
    
    min_x, max_x, min_y, max_y = bounds
    
    # Handle edge case
    if max_x == min_x:
        max_x = min_x + 1
    if max_y == min_y:
        max_y = min_y + 1
    
    # Calculate scale
    x_range = max_x - min_x
    y_range = max_y - min_y
    
    # Use aspect ratio to determine dimensions
    aspect = x_range / y_range if y_range > 0 else 1.0
    if aspect > 1:
        # Wider than tall
        display_width = width
        display_height = int(width / aspect)
    else:
        # Taller than wide
        display_height = height
        display_width = int(height * aspect)
    
    # Create grid
    grid = [[' ' for _ in range(display_width)] for _ in range(display_height)]
    
    # Map points to grid
    for px, py in engraving_points:
        # Normalize to 0-1 range
        nx = (px - min_x) / x_range
        ny = (py - min_y) / y_range
        
        # Map to grid coordinates (flip Y because screen Y increases downward)
        gx = int(nx * (display_width - 1))
        gy = int((1 - ny) * (display_height - 1))
        
        # Clamp to grid bounds
        gx = max(0, min(display_width - 1, gx))
        gy = max(0, min(display_height - 1, gy))
        
        # Mark as engraved (use different chars for density)
        if grid[gy][gx] == ' ':
            grid[gy][gx] = '.'
        elif grid[gy][gx] == '.':
            grid[gy][gx] = ':'
        elif grid[gy][gx] == ':':
            grid[gy][gx] = '*'
        elif grid[gy][gx] == '*':
            grid[gy][gx] = '#'
    
    # Convert to string
    result = []
    result.append(f"G-code Visualization ({len(engraving_points)} engraving points)")
    result.append(f"Bounds: X[{min_x:.2f}, {max_x:.2f}] Y[{min_y:.2f}, {max_y:.2f}]")
    result.append(f"Size: {x_range:.2f}mm x {y_range:.2f}mm")
    result.append("")
    result.append("Legend: . = light, : = medium, * = heavy, # = very heavy engraving")
    result.append("")
    
    for row in grid:
        result.append(''.join(row))
    
    return '\n'.join(result)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 visualize_gcode.py <gcode_file>")
        print("Example: python3 visualize_gcode.py gcode/ichigotest.gcode")
        sys.exit(1)
    
    gcode_file = Path(sys.argv[1])
    if not gcode_file.exists():
        print(f"Error: File not found: {gcode_file}")
        sys.exit(1)
    
    print(f"Parsing G-code: {gcode_file}")
    print("This may take a moment for large files...")
    
    try:
        engraving_points, bounds = parse_gcode(gcode_file)
        
        if not engraving_points:
            print("No engraving points found in G-code.")
            sys.exit(1)
        
        print(f"\nFound {len(engraving_points)} engraving points")
        print("Rendering ASCII visualization...\n")
        
        # Render with different sizes
        print("=" * 120)
        print("PREVIEW (80x30):")
        print("=" * 120)
        print(render_ascii(engraving_points, bounds, width=80, height=30))
        
        print("\n" + "=" * 120)
        print("DETAILED VIEW (120x40):")
        print("=" * 120)
        print(render_ascii(engraving_points, bounds, width=120, height=40))
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
