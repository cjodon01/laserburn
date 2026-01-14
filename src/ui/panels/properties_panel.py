"""
Properties Panel - Dock widget for editing shape properties.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFormLayout, QLineEdit,
    QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QGroupBox,
    QPushButton, QSlider, QHBoxLayout, QFontComboBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from typing import List, Optional

from ...core.shapes import Shape, Text, Rectangle, Ellipse, ImageShape
import math


class PropertiesPanel(QWidget):
    """Panel for editing selected shape properties."""
    
    # Signal emitted when properties change
    property_changed = pyqtSignal()
    
    # Signal emitted when user wants to open image settings dialog
    open_image_settings = pyqtSignal(object)  # Emits ImageShape
    
    def __init__(self):
        super().__init__()
        self._current_shapes: List[Shape] = []
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Title
        title = QLabel("Properties")
        title.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title)
        
        # Create scrollable form
        self._form_layout = QFormLayout()
        self._form_layout.setSpacing(8)
        
        # Transform properties group (shown for all shapes)
        self._transform_group = QGroupBox("Transform")
        self._transform_layout = QFormLayout()
        
        # Position
        self._pos_x_spin = QDoubleSpinBox()
        self._pos_x_spin.setRange(-10000, 10000)
        self._pos_x_spin.setValue(0)
        self._pos_x_spin.setSuffix(" mm")
        self._pos_x_spin.setDecimals(2)
        self._pos_x_spin.valueChanged.connect(self._on_transform_property_changed)
        self._transform_layout.addRow("X Position:", self._pos_x_spin)
        
        self._pos_y_spin = QDoubleSpinBox()
        self._pos_y_spin.setRange(-10000, 10000)
        self._pos_y_spin.setValue(0)
        self._pos_y_spin.setSuffix(" mm")
        self._pos_y_spin.setDecimals(2)
        self._pos_y_spin.valueChanged.connect(self._on_transform_property_changed)
        self._transform_layout.addRow("Y Position:", self._pos_y_spin)
        
        # Size (for shapes that have width/height)
        self._width_spin = QDoubleSpinBox()
        self._width_spin.setRange(0.01, 10000)
        self._width_spin.setValue(100)
        self._width_spin.setSuffix(" mm")
        self._width_spin.setDecimals(2)
        self._width_spin.valueChanged.connect(self._on_transform_property_changed)
        self._transform_layout.addRow("Width:", self._width_spin)
        
        self._height_spin = QDoubleSpinBox()
        self._height_spin.setRange(0.01, 10000)
        self._height_spin.setValue(100)
        self._height_spin.setSuffix(" mm")
        self._height_spin.setDecimals(2)
        self._height_spin.valueChanged.connect(self._on_transform_property_changed)
        self._transform_layout.addRow("Height:", self._height_spin)
        
        # Rotation
        self._rotation_spin = QDoubleSpinBox()
        self._rotation_spin.setRange(-360, 360)
        self._rotation_spin.setValue(0)
        self._rotation_spin.setSuffix(" °")
        self._rotation_spin.setDecimals(1)
        self._rotation_spin.valueChanged.connect(self._on_transform_property_changed)
        self._transform_layout.addRow("Rotation:", self._rotation_spin)
        
        # Scale
        self._scale_x_spin = QDoubleSpinBox()
        self._scale_x_spin.setRange(0.01, 100)
        self._scale_x_spin.setValue(1.0)
        self._scale_x_spin.setDecimals(3)
        self._scale_x_spin.valueChanged.connect(self._on_transform_property_changed)
        self._transform_layout.addRow("Scale X:", self._scale_x_spin)
        
        self._scale_y_spin = QDoubleSpinBox()
        self._scale_y_spin.setRange(0.01, 100)
        self._scale_y_spin.setValue(1.0)
        self._scale_y_spin.setDecimals(3)
        self._scale_y_spin.valueChanged.connect(self._on_transform_property_changed)
        self._transform_layout.addRow("Scale Y:", self._scale_y_spin)
        
        self._transform_group.setLayout(self._transform_layout)
        self._transform_group.setVisible(False)
        layout.addWidget(self._transform_group)
        
        # Text properties group (shown when text is selected)
        self._text_group = QGroupBox("Text Properties")
        self._text_layout = QFormLayout()
        
        # Font family - use QFontComboBox to show all available system fonts
        self._font_family_combo = QFontComboBox()
        self._font_family_combo.currentTextChanged.connect(self._on_text_property_changed)
        self._text_layout.addRow("Font Family:", self._font_family_combo)
        
        # Font size
        self._font_size_spin = QDoubleSpinBox()
        self._font_size_spin.setRange(1, 500)
        self._font_size_spin.setValue(24)
        self._font_size_spin.setSuffix(" pt")
        self._font_size_spin.valueChanged.connect(self._on_text_property_changed)
        self._text_layout.addRow("Font Size:", self._font_size_spin)
        
        # Bold
        self._bold_check = QCheckBox()
        self._bold_check.toggled.connect(self._on_text_property_changed)
        self._text_layout.addRow("Bold:", self._bold_check)
        
        # Italic
        self._italic_check = QCheckBox()
        self._italic_check.toggled.connect(self._on_text_property_changed)
        self._text_layout.addRow("Italic:", self._italic_check)
        
        self._text_group.setLayout(self._text_layout)
        self._text_group.setVisible(False)
        layout.addWidget(self._text_group)
        
        # Image properties group (shown when image is selected)
        self._image_group = QGroupBox("Image Properties")
        self._image_layout = QFormLayout()
        
        # DPI
        self._dpi_spin = QDoubleSpinBox()
        self._dpi_spin.setRange(50, 1000)
        self._dpi_spin.setValue(254)
        self._dpi_spin.setSuffix(" DPI")
        self._dpi_spin.setDecimals(0)
        self._dpi_spin.valueChanged.connect(self._on_image_property_changed)
        self._image_layout.addRow("Resolution:", self._dpi_spin)
        
        # Dithering mode
        self._dither_combo = QComboBox()
        self._dither_combo.addItems([
            "None (Threshold)",
            "Floyd-Steinberg",
            "Jarvis-Judice-Ninke",
            "Stucki",
            "Atkinson",
            "Bayer 4x4 (Ordered)"
        ])
        self._dither_combo.currentIndexChanged.connect(self._on_image_property_changed)
        self._image_layout.addRow("Dithering:", self._dither_combo)
        
        # Threshold
        self._threshold_spin = QSpinBox()
        self._threshold_spin.setRange(0, 255)
        self._threshold_spin.setValue(128)
        self._threshold_spin.valueChanged.connect(self._on_image_property_changed)
        self._image_layout.addRow("Threshold:", self._threshold_spin)
        
        # Invert
        self._invert_check = QCheckBox()
        self._invert_check.toggled.connect(self._on_image_property_changed)
        self._image_layout.addRow("Invert:", self._invert_check)
        
        # Skip white
        self._skip_white_check = QCheckBox("Skip white pixels (faster)")
        self._skip_white_check.setToolTip("Skip white pixels entirely during engraving (like LightBurn)")
        self._skip_white_check.toggled.connect(self._on_image_property_changed)
        self._image_layout.addRow("", self._skip_white_check)
        
        # Advanced settings button
        self._image_settings_btn = QPushButton("Advanced Settings...")
        self._image_settings_btn.clicked.connect(self._on_open_image_settings)
        self._image_layout.addRow("", self._image_settings_btn)
        
        self._image_group.setLayout(self._image_layout)
        self._image_group.setVisible(False)
        layout.addWidget(self._image_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def update_selection(self, shapes: List[Shape]):
        """Update panel with selected shapes."""
        self._current_shapes = shapes
        
        # Clear form
        self._transform_group.setVisible(False)
        self._text_group.setVisible(False)
        self._image_group.setVisible(False)
        
        if not shapes:
            return
        
        # Show transform properties if exactly one shape is selected
        if len(shapes) == 1:
            shape = shapes[0]
            
            # Block signals while updating values to prevent feedback loops
            self._pos_x_spin.blockSignals(True)
            self._pos_y_spin.blockSignals(True)
            self._width_spin.blockSignals(True)
            self._height_spin.blockSignals(True)
            self._rotation_spin.blockSignals(True)
            self._scale_x_spin.blockSignals(True)
            self._scale_y_spin.blockSignals(True)
            
            # Position
            self._pos_x_spin.setValue(shape.position.x)
            self._pos_y_spin.setValue(shape.position.y)
            
            # Size (for shapes with width/height)
            has_size = isinstance(shape, (Rectangle, Ellipse, ImageShape))
            self._width_spin.setVisible(has_size)
            self._transform_layout.labelForField(self._width_spin).setVisible(has_size)
            self._height_spin.setVisible(has_size)
            self._transform_layout.labelForField(self._height_spin).setVisible(has_size)
            
            # Show ACTUAL dimensions (base * scale), not base dimensions
            if isinstance(shape, Rectangle):
                self._width_spin.setValue(shape.width * abs(shape.scale_x))
                self._height_spin.setValue(shape.height * abs(shape.scale_y))
            elif isinstance(shape, Ellipse):
                self._width_spin.setValue(shape.radius_x * 2 * abs(shape.scale_x))
                self._height_spin.setValue(shape.radius_y * 2 * abs(shape.scale_y))
            elif isinstance(shape, ImageShape):
                self._width_spin.setValue(shape.width * abs(shape.scale_x))
                self._height_spin.setValue(shape.height * abs(shape.scale_y))
            
            # Rotation (convert from radians to degrees)
            self._rotation_spin.setValue(math.degrees(shape.rotation))
            
            # Scale
            self._scale_x_spin.setValue(shape.scale_x)
            self._scale_y_spin.setValue(shape.scale_y)
            
            # Unblock signals
            self._pos_x_spin.blockSignals(False)
            self._pos_y_spin.blockSignals(False)
            self._width_spin.blockSignals(False)
            self._height_spin.blockSignals(False)
            self._rotation_spin.blockSignals(False)
            self._scale_x_spin.blockSignals(False)
            self._scale_y_spin.blockSignals(False)
            
            self._transform_group.setVisible(True)
        
        # Show text properties if exactly one text shape is selected
        if len(shapes) == 1 and isinstance(shapes[0], Text):
            text_shape = shapes[0]
            
            # Block signals while updating
            self._font_family_combo.blockSignals(True)
            self._font_size_spin.blockSignals(True)
            self._bold_check.blockSignals(True)
            self._italic_check.blockSignals(True)
            
            self._font_family_combo.setCurrentText(text_shape.font_family)
            self._font_size_spin.setValue(text_shape.font_size)
            self._bold_check.setChecked(text_shape.bold)
            self._italic_check.setChecked(text_shape.italic)
            
            # Unblock signals
            self._font_family_combo.blockSignals(False)
            self._font_size_spin.blockSignals(False)
            self._bold_check.blockSignals(False)
            self._italic_check.blockSignals(False)
            
            self._text_group.setVisible(True)
        
        # Show image properties if exactly one image shape is selected
        if len(shapes) == 1 and isinstance(shapes[0], ImageShape):
            image_shape = shapes[0]
            
            # Block signals while updating
            self._dpi_spin.blockSignals(True)
            self._dither_combo.blockSignals(True)
            self._threshold_spin.blockSignals(True)
            self._invert_check.blockSignals(True)
            self._skip_white_check.blockSignals(True)
            
            # Set values from image shape
            self._dpi_spin.setValue(image_shape.dpi)
            self._threshold_spin.setValue(image_shape.threshold)
            self._invert_check.setChecked(image_shape.invert)
            self._skip_white_check.setChecked(getattr(image_shape, 'skip_white', True))
            
            # Map dither mode to combo index
            mode_map = {
                "none": 0,
                "floyd_steinberg": 1,
                "jarvis": 2,
                "stucki": 3,
                "atkinson": 4,
                "bayer": 5,
                "bayer_4x4": 5,
                "bayer_2x2": 5,
                "bayer_8x8": 5,
            }
            dither_mode = getattr(image_shape, 'dither_mode', 'floyd_steinberg')
            self._dither_combo.setCurrentIndex(mode_map.get(dither_mode, 1))
            
            # Unblock signals
            self._dpi_spin.blockSignals(False)
            self._dither_combo.blockSignals(False)
            self._threshold_spin.blockSignals(False)
            self._invert_check.blockSignals(False)
            
            self._image_group.setVisible(True)
    
    def _on_transform_property_changed(self):
        """Handle transform property changes."""
        if not self._current_shapes:
            return
        
        # Update all selected shapes
        for shape in self._current_shapes:
            # Position
            shape.position.x = self._pos_x_spin.value()
            shape.position.y = self._pos_y_spin.value()
            
            # Size - user enters ACTUAL size, we calculate what base size or scale should be
            # We adjust scale to achieve desired actual size while keeping base dimensions
            desired_width = self._width_spin.value()
            desired_height = self._height_spin.value()
            
            if isinstance(shape, Rectangle):
                # Calculate new scale to achieve desired size
                if shape.width > 0:
                    shape.scale_x = desired_width / shape.width * (1 if shape.scale_x >= 0 else -1)
                if shape.height > 0:
                    shape.scale_y = desired_height / shape.height * (1 if shape.scale_y >= 0 else -1)
            elif isinstance(shape, Ellipse):
                base_width = shape.radius_x * 2
                base_height = shape.radius_y * 2
                if base_width > 0:
                    shape.scale_x = desired_width / base_width * (1 if shape.scale_x >= 0 else -1)
                if base_height > 0:
                    shape.scale_y = desired_height / base_height * (1 if shape.scale_y >= 0 else -1)
            elif isinstance(shape, ImageShape):
                if shape.width > 0:
                    shape.scale_x = desired_width / shape.width * (1 if shape.scale_x >= 0 else -1)
                if shape.height > 0:
                    shape.scale_y = desired_height / shape.height * (1 if shape.scale_y >= 0 else -1)
            
            # Rotation (convert from degrees to radians)
            shape.rotation = math.radians(self._rotation_spin.value())
            
            # Scale - direct override (this may conflict with size changes above)
            # Only apply if scale values were explicitly changed
            # For now, let scale be computed from size changes
            # shape.scale_x = self._scale_x_spin.value()
            # shape.scale_y = self._scale_y_spin.value()
            
            # Invalidate cache for shapes that need it
            if hasattr(shape, 'invalidate_cache'):
                shape.invalidate_cache()
        
        # Emit signal to update view
        self.property_changed.emit()
    
    def _on_text_property_changed(self):
        """Handle text property changes."""
        if not self._current_shapes:
            return
        
        # Update all selected text shapes
        for shape in self._current_shapes:
            if isinstance(shape, Text):
                shape.font_family = self._font_family_combo.currentText()
                shape.font_size = self._font_size_spin.value()
                shape.bold = self._bold_check.isChecked()
                shape.italic = self._italic_check.isChecked()
                shape.invalidate_cache()
        
        # Emit signal to update view
        self.property_changed.emit()
    
    def _on_image_property_changed(self):
        """Handle image property changes."""
        if not self._current_shapes:
            return
        
        # Map combo index to dither mode string
        dither_modes = [
            "none",
            "floyd_steinberg",
            "jarvis",
            "stucki",
            "atkinson",
            "bayer_4x4",
        ]
        
        # Update all selected image shapes
        for shape in self._current_shapes:
            if isinstance(shape, ImageShape):
                shape.dpi = self._dpi_spin.value()
                shape.threshold = self._threshold_spin.value()
                shape.invert = self._invert_check.isChecked()
                shape.skip_white = self._skip_white_check.isChecked()
                
                idx = self._dither_combo.currentIndex()
                if 0 <= idx < len(dither_modes):
                    shape.dither_mode = dither_modes[idx]
        
        # Emit signal to update view
        self.property_changed.emit()
    
    def _on_open_image_settings(self):
        """Open the advanced image settings dialog."""
        if not self._current_shapes:
            return
        
        # Get the first selected image shape
        for shape in self._current_shapes:
            if isinstance(shape, ImageShape):
                self.open_image_settings.emit(shape)
                break

