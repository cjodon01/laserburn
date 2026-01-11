"""
Basic test to verify the application structure works.
"""

import sys

# Test core imports
try:
    from src.core import Document, Layer, Rectangle, Ellipse, Path, Point
    print("[OK] Core module imports OK")
except Exception as e:
    print(f"[FAIL] Core module import failed: {e}")
    sys.exit(1)

# Test creating a document
try:
    doc = Document(name="Test")
    layer = Layer(name="Layer 1")
    doc.add_layer(layer)
    
    # Add a rectangle
    rect = Rectangle(10, 10, 50, 30)
    layer.add_shape(rect)
    
    # Add an ellipse
    ellipse = Ellipse(50, 50, 20, 15)
    layer.add_shape(ellipse)
    
    print(f"[OK] Document created: {doc.name}")
    print(f"[OK] Layer created: {layer.name}")
    print(f"[OK] Shapes added: {len(layer.shapes)}")
    
    # Test getting paths
    paths = rect.get_paths()
    print(f"[OK] Rectangle paths: {len(paths)} paths, {len(paths[0])} points")
    
    paths = ellipse.get_paths()
    print(f"[OK] Ellipse paths: {len(paths)} paths, {len(paths[0])} points")
    
except Exception as e:
    print(f"[FAIL] Document creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test UI imports (if PyQt6 available)
try:
    import PyQt6.QtWidgets
    print("[OK] PyQt6 available")
    
    from src.ui.mainwindow import MainWindow
    print("[OK] UI module imports OK")
except ImportError as e:
    print(f"[WARN] PyQt6 not installed: {e}")
    print("  Install with: pip install PyQt6")
except Exception as e:
    print(f"[WARN] UI import issue: {e}")

print("\n[OK] Basic structure test passed!")

