"""
Tests for cylinder warping functionality.

Tests the mathematical transformations and image warping
for cylinder engraving without a rotary attachment.
"""

import unittest
import math
from src.image.cylinder_warp import (
    CylinderParams, CylinderWarper,
    apply_cylinder_compensation_to_gcode
)
from src.core.shapes import Point

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None


class TestCylinderParams(unittest.TestCase):
    """Test CylinderParams class."""
    
    def test_basic_creation(self):
        """Test creating basic cylinder parameters."""
        params = CylinderParams(diameter=50.0, max_angle=45.0)
        self.assertEqual(params.diameter, 50.0)
        self.assertEqual(params.max_angle, 45.0)
        self.assertEqual(params.radius, 25.0)
    
    def test_radius_property(self):
        """Test radius calculation."""
        params = CylinderParams(diameter=100.0, max_angle=45.0)
        self.assertEqual(params.radius, 50.0)
    
    def test_auto_engrave_width(self):
        """Test automatic engrave width calculation."""
        params = CylinderParams(diameter=50.0, max_angle=45.0)
        # Should be set automatically based on max_angle
        self.assertGreater(params.engrave_width, 0)
        
        # Check it's approximately correct
        max_theta = math.radians(45.0)
        expected_flat = 2 * 25.0 * math.sin(max_theta)
        self.assertAlmostEqual(params.engrave_width, expected_flat, places=1)
    
    def test_validation_valid(self):
        """Test parameter validation with valid values."""
        params = CylinderParams(diameter=50.0, max_angle=45.0)
        is_valid, error = params.validate()
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
    
    def test_validation_invalid_diameter(self):
        """Test validation with invalid diameter."""
        params = CylinderParams(diameter=0.0, max_angle=45.0)
        is_valid, error = params.validate()
        self.assertFalse(is_valid)
        self.assertIn("positive", error.lower())
    
    def test_validation_invalid_angle(self):
        """Test validation with invalid angle."""
        params = CylinderParams(diameter=50.0, max_angle=95.0)
        is_valid, error = params.validate()
        self.assertFalse(is_valid)
    
    def test_get_usable_flat_width(self):
        """Test usable flat width calculation."""
        params = CylinderParams(diameter=50.0, max_angle=45.0)
        width = params.get_usable_flat_width()
        
        # Should be 2 * R * sin(theta)
        expected = 2 * 25.0 * math.sin(math.radians(45.0))
        self.assertAlmostEqual(width, expected, places=2)
    
    def test_get_power_at_edge(self):
        """Test power multiplier at edge calculation."""
        params = CylinderParams(diameter=50.0, max_angle=45.0)
        power_mult = params.get_power_at_edge()
        
        # Should be 1 / cos(45°) = sqrt(2) ≈ 1.414
        expected = 1.0 / math.cos(math.radians(45.0))
        self.assertAlmostEqual(power_mult, expected, places=3)
    
    def test_get_z_drop_at_edge(self):
        """Test Z drop at edge calculation."""
        params = CylinderParams(diameter=50.0, max_angle=45.0)
        z_drop = params.get_z_drop_at_edge()
        
        # Should be R * (1 - cos(45°))
        expected = 25.0 * (1 - math.cos(math.radians(45.0)))
        self.assertAlmostEqual(z_drop, expected, places=3)


class TestCylinderWarper(unittest.TestCase):
    """Test CylinderWarper class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.params = CylinderParams(diameter=50.0, max_angle=45.0)
        self.warper = CylinderWarper(self.params)
    
    def test_arc_to_flat_center(self):
        """Test arc to flat conversion at center."""
        # At center, arc length 0 should map to flat position 0
        flat = self.warper.arc_to_flat(0.0)
        self.assertAlmostEqual(flat, 0.0, places=5)
    
    def test_arc_to_flat_small(self):
        """Test arc to flat conversion for small arc."""
        # Small arc: arc ≈ flat (for small angles)
        arc = 1.0  # 1mm arc
        flat = self.warper.arc_to_flat(arc)
        # Should be approximately equal for small values
        self.assertAlmostEqual(flat, arc, places=1)
    
    def test_arc_to_flat_large(self):
        """Test arc to flat conversion for larger arc."""
        # For 45° angle, arc = R * θ, flat = R * sin(θ)
        theta = math.radians(30.0)
        arc = self.params.radius * theta
        flat = self.warper.arc_to_flat(arc)
        expected = self.params.radius * math.sin(theta)
        self.assertAlmostEqual(flat, expected, places=3)
    
    def test_flat_to_arc_inverse(self):
        """Test that flat_to_arc is inverse of arc_to_flat."""
        # Test round-trip conversion
        test_arcs = [0.0, 5.0, 10.0, 20.0]
        for arc in test_arcs:
            flat = self.warper.arc_to_flat(arc)
            arc_back = self.warper.flat_to_arc(flat)
            self.assertAlmostEqual(arc, arc_back, places=2)
    
    def test_get_power_compensation_center(self):
        """Test power compensation at center."""
        # At center, power multiplier should be 1.0
        power_mult = self.warper.get_power_compensation(0.0)
        self.assertAlmostEqual(power_mult, 1.0, places=5)
    
    def test_get_power_compensation_edge(self):
        """Test power compensation at edge."""
        # At max angle, should match params.get_power_at_edge()
        max_flat = self.params.get_usable_flat_width() / 2
        power_mult = self.warper.get_power_compensation(max_flat)
        expected = self.params.get_power_at_edge()
        self.assertAlmostEqual(power_mult, expected, places=2)
    
    def test_get_z_offset_center(self):
        """Test Z offset at center."""
        # At center, Z offset should be 0
        z_offset = self.warper.get_z_offset(0.0)
        self.assertAlmostEqual(z_offset, 0.0, places=5)
    
    def test_get_z_offset_edge(self):
        """Test Z offset at edge."""
        # At max angle, should match params.get_z_drop_at_edge()
        max_flat = self.params.get_usable_flat_width() / 2
        z_offset = self.warper.get_z_offset(max_flat)
        expected = self.params.get_z_drop_at_edge()
        self.assertAlmostEqual(z_offset, expected, places=2)
    
    def test_get_angle_at_position(self):
        """Test angle calculation at position."""
        # At center, angle should be 0
        angle = self.warper.get_angle_at_position(0.0)
        self.assertAlmostEqual(angle, 0.0, places=3)
        
        # At edge, should match max_angle
        max_flat = self.params.get_usable_flat_width() / 2
        angle = self.warper.get_angle_at_position(max_flat)
        self.assertAlmostEqual(abs(angle), self.params.max_angle, places=1)
    
    def test_warp_point(self):
        """Test warping a single point."""
        # Point at center should stay at center
        x, y = self.warper.warp_point(0.0, 10.0)
        self.assertAlmostEqual(x, 0.0, places=5)
        self.assertAlmostEqual(y, 10.0, places=5)
        
        # Point offset in X should be warped
        x, y = self.warper.warp_point(10.0, 10.0)
        # X should be less than 10 (compressed)
        self.assertLess(abs(x), 10.0)
        self.assertAlmostEqual(y, 10.0, places=5)
    
    def test_warp_path(self):
        """Test warping a path."""
        # Create a simple horizontal line
        path = [
            Point(-10.0, 0.0),
            Point(0.0, 0.0),
            Point(10.0, 0.0)
        ]
        
        warped = self.warper.warp_path(path, center_x=0.0)
        
        self.assertEqual(len(warped), 3)
        # Center point should stay at center
        self.assertAlmostEqual(warped[1].x, 0.0, places=3)
        # Edge points should be compressed
        self.assertLess(abs(warped[0].x), 10.0)
        self.assertLess(abs(warped[2].x), 10.0)
        # Y should not change
        for pt in warped:
            self.assertAlmostEqual(pt.y, 0.0, places=5)
    
    def test_generate_power_profile(self):
        """Test power profile generation."""
        # Use max_power > base to allow compensation to show
        profile = self.warper.generate_power_profile(num_steps=10, base_power=100.0, max_power=200.0)
        
        self.assertEqual(len(profile), 10)
        # First and last should be at edges (negative and positive x)
        # Both edges should have higher power than center
        edge_power_neg = profile[0][1]
        edge_power_pos = profile[-1][1]
        # Find the point closest to center (x closest to 0)
        center_idx = min(range(len(profile)), key=lambda i: abs(profile[i][0]))
        center_power = profile[center_idx][1]
        # Center should be close to base (within 1% tolerance)
        self.assertAlmostEqual(center_power, 100.0, delta=1.0)
        # Edges should be >= base (may be clamped to max_power)
        self.assertGreaterEqual(edge_power_neg, 100.0)
        self.assertGreaterEqual(edge_power_pos, 100.0)
        # For 45° angle, edges should definitely be higher (unless clamped)
        # At 45°, power_mult = 1/cos(45°) ≈ 1.414, so power should be ~141
        self.assertGreater(edge_power_neg, 100.0)
        self.assertGreater(edge_power_pos, 100.0)
    
    @unittest.skipIf(not HAS_NUMPY, "NumPy not available")
    def test_warp_image_grayscale(self):
        """Test warping a grayscale image."""
        # Create a simple test image (horizontal gradient)
        width, height = 100, 50
        image = np.zeros((height, width), dtype=np.uint8)
        for x in range(width):
            image[:, x] = int(255 * x / width)
        
        warped = self.warper.warp_image(image)
        
        self.assertEqual(warped.shape, image.shape)
        self.assertEqual(warped.dtype, image.dtype)
        # Center should be similar
        self.assertAlmostEqual(int(warped[height//2, width//2]), 
                              int(image[height//2, width//2]), 
                              delta=10)
    
    @unittest.skipIf(not HAS_NUMPY, "NumPy not available")
    def test_warp_image_rgb(self):
        """Test warping an RGB image."""
        # Create a simple test image
        width, height = 100, 50
        image = np.zeros((height, width, 3), dtype=np.uint8)
        image[:, :, 0] = 255  # Red channel
        
        warped = self.warper.warp_image(image)
        
        self.assertEqual(warped.shape, image.shape)
        self.assertEqual(warped.dtype, image.dtype)
    
    @unittest.skipIf(not HAS_NUMPY, "NumPy not available")
    def test_generate_power_map(self):
        """Test power map generation."""
        width, height = 100, 50
        power_map = self.warper.generate_power_map(width, height, 
                                                   base_power=100.0, 
                                                   max_power=200.0)
        
        self.assertEqual(power_map.shape, (height, width))
        # Center should be base power
        self.assertAlmostEqual(power_map[height//2, width//2], 100.0, places=1)
        # Edges should be higher
        self.assertGreater(power_map[height//2, 0], 100.0)
        self.assertGreater(power_map[height//2, width-1], 100.0)


class TestGCodeCompensation(unittest.TestCase):
    """Test G-code compensation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.params = CylinderParams(diameter=50.0, max_angle=45.0)
    
    def test_apply_compensation_basic(self):
        """Test basic G-code compensation."""
        gcode = [
            "G0 X0 Y0",
            "G1 X10 Y0 S100",
            "G1 X20 Y0 S100",
            "M5"
        ]
        
        modified = apply_cylinder_compensation_to_gcode(
            gcode, self.params, design_center_x=10.0, base_power=100.0
        )
        
        # Should have header comments
        self.assertTrue(any("Cylinder Compensation" in line for line in modified))
        
        # Power values should be modified
        power_lines = [line for line in modified if "S" in line and "G1" in line]
        self.assertGreater(len(power_lines), 0)
    
    def test_apply_compensation_center(self):
        """Test compensation at center (should be minimal)."""
        gcode = [
            "G1 X10 Y0 S100"
        ]
        
        modified = apply_cylinder_compensation_to_gcode(
            gcode, self.params, design_center_x=10.0, base_power=100.0
        )
        
        # Find the line with S value
        for line in modified:
            if "S" in line and "G1" in line:
                # Extract S value
                import re
                match = re.search(r'S(\d+)', line)
                if match:
                    power = int(match.group(1))
                    # At center, should be close to base
                    self.assertAlmostEqual(power, 100.0, delta=5)
    
    def test_apply_compensation_with_z(self):
        """Test compensation with Z offset."""
        gcode = [
            "G1 X10 Y0 S100"
        ]
        
        modified = apply_cylinder_compensation_to_gcode(
            gcode, self.params, design_center_x=10.0, 
            base_power=100.0, include_z=True
        )
        
        # Should have Z values
        z_lines = [line for line in modified if "Z" in line]
        self.assertGreater(len(z_lines), 0)
    
    def test_apply_compensation_skips_comments(self):
        """Test that comments are preserved."""
        gcode = [
            "; This is a comment",
            "G1 X10 Y0 S100",
            "; Another comment"
        ]
        
        modified = apply_cylinder_compensation_to_gcode(
            gcode, self.params, design_center_x=10.0, base_power=100.0
        )
        
        # Comments should be preserved
        comments = [line for line in modified if line.strip().startswith(';')]
        self.assertGreaterEqual(len(comments), 2)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def test_invalid_params_in_warper(self):
        """Test that invalid params raise error in warper."""
        invalid_params = CylinderParams(diameter=0.0, max_angle=45.0)
        
        with self.assertRaises(ValueError):
            CylinderWarper(invalid_params)
    
    def test_very_small_diameter(self):
        """Test with very small diameter."""
        params = CylinderParams(diameter=1.0, max_angle=30.0)
        warper = CylinderWarper(params)
        
        # Should still work
        flat = warper.arc_to_flat(0.1)
        self.assertIsInstance(flat, float)
    
    def test_very_large_diameter(self):
        """Test with very large diameter."""
        params = CylinderParams(diameter=1000.0, max_angle=45.0)
        warper = CylinderWarper(params)
        
        # Should still work
        flat = warper.arc_to_flat(100.0)
        self.assertIsInstance(flat, float)
    
    def test_small_angle(self):
        """Test with small max angle."""
        params = CylinderParams(diameter=50.0, max_angle=10.0)
        warper = CylinderWarper(params)
        
        # Should work, but usable width will be small
        width = params.get_usable_flat_width()
        self.assertGreater(width, 0)
        self.assertLess(width, 10.0)  # Should be small


if __name__ == '__main__':
    unittest.main()
