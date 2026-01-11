"""
Test script to verify LaserBurn application functionality.
"""

import sys
import os

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from src.core import Document, Layer, Rectangle, Ellipse, Point
        print("  [OK] Core module")
    except Exception as e:
        print(f"  [FAIL] Core module: {e}")
        return False
    
    try:
        from src.io import SVGParser, export_svg
        print("  [OK] I/O module")
    except Exception as e:
        print(f"  [FAIL] I/O module: {e}")
        return False
    
    try:
        from src.laser import GCodeGenerator, GCodeSettings
        print("  [OK] Laser module")
    except Exception as e:
        print(f"  [FAIL] Laser module: {e}")
        return False
    
    try:
        import PyQt6.QtWidgets
        from src.ui.mainwindow import MainWindow
        print("  [OK] UI module")
    except Exception as e:
        print(f"  [WARN] UI module: {e}")
        print("         (PyQt6 may not be installed)")
    
    return True


def test_core_functionality():
    """Test core shape functionality."""
    print("\nTesting core functionality...")
    
    try:
        from src.core import Document, Layer, Rectangle, Ellipse
        
        # Create document
        doc = Document(name="Test")
        layer = Layer(name="Layer 1")
        doc.add_layer(layer)
        
        # Add shapes
        rect = Rectangle(10, 10, 50, 30)
        layer.add_shape(rect)
        
        ellipse = Ellipse(50, 50, 20, 15)
        layer.add_shape(ellipse)
        
        # Test paths
        rect_paths = rect.get_paths()
        ellipse_paths = ellipse.get_paths()
        
        assert len(rect_paths) > 0, "Rectangle should have paths"
        assert len(ellipse_paths) > 0, "Ellipse should have paths"
        
        print("  [OK] Document creation")
        print("  [OK] Shape creation")
        print("  [OK] Path generation")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Core functionality: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gcode_generation():
    """Test G-code generation."""
    print("\nTesting G-code generation...")
    
    try:
        from src.core import Document, Layer, Rectangle
        from src.laser import GCodeGenerator, GCodeSettings
        
        doc = Document(name="Test", width=100, height=100)
        layer = Layer(name="Cut")
        doc.add_layer(layer)
        
        rect = Rectangle(10, 10, 50, 50)
        layer.add_shape(rect)
        
        generator = GCodeGenerator(GCodeSettings())
        gcode = generator.generate(doc)
        
        assert "G21" in gcode, "Should set units to mm"
        assert "G90" in gcode, "Should use absolute positioning"
        assert "M5" in gcode, "Should turn laser off"
        assert "G0" in gcode or "G1" in gcode, "Should have movement commands"
        
        print("  [OK] G-code generation")
        print(f"  [OK] Generated {len(gcode.splitlines())} lines")
        
        return True
    except Exception as e:
        print(f"  [FAIL] G-code generation: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("LaserBurn Application Test Suite")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Core Functionality", test_core_functionality()))
    results.append(("G-code Generation", test_gcode_generation()))
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print("\n[FAILURE] Some tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

