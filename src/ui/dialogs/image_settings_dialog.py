"""
Image Settings Dialog

Provides comprehensive controls for adjusting image processing settings
for laser engraving, including dithering algorithm selection, DPI,
brightness/contrast, and a live preview of the processed image.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QDoubleSpinBox, QSpinBox, QLabel, QPushButton, QGroupBox,
    QComboBox, QCheckBox, QDialogButtonBox, QSlider, QFrame,
    QScrollArea, QWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QImage, QPixmap, QPainter
from typing import Optional
import numpy as np

from ...image.dithering import DitheringMethod, ImageDitherer, adjust_brightness_contrast
from ...core.shapes import ImageShape


class ImagePreviewWidget(QLabel):
    """Widget for displaying image preview with zoom support."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        self._original_pixmap = None
        self._zoom = 1.0
    
    def set_image(self, image: np.ndarray, alpha_channel: Optional[np.ndarray] = None):
        """Set image from numpy array (grayscale or binary), with optional alpha channel."""
        if image is None:
            self.clear()
            return
        
        # Ensure image is uint8
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)
        
        height, width = image.shape[:2]
        
        # Create QImage from numpy array, handling transparency
        if alpha_channel is not None:
            # Create checkerboard pattern for transparent areas
            checkerboard = self._create_checkerboard(width, height, 8)
            
            # Composite image onto checkerboard for transparent areas
            rgb_data = np.stack([image, image, image], axis=-1)
            alpha_3d = alpha_channel[:, :, np.newaxis] / 255.0
            
            # Blend: transparent areas show checkerboard, opaque areas show image
            composite = (rgb_data * alpha_3d + checkerboard * (1 - alpha_3d)).astype(np.uint8)
            
            bytes_per_line = 3 * width
            qimage = QImage(
                composite.tobytes(),
                width, height,
                bytes_per_line,
                QImage.Format.Format_RGB888
            )
        elif len(image.shape) == 2:
            # Grayscale
            bytes_per_line = width
            qimage = QImage(image.data, width, height, bytes_per_line, 
                          QImage.Format.Format_Grayscale8)
        else:
            # RGB
            bytes_per_line = 3 * width
            qimage = QImage(image.data, width, height, bytes_per_line,
                          QImage.Format.Format_RGB888)
        
        self._original_pixmap = QPixmap.fromImage(qimage)
        self._update_display()
    
    def _create_checkerboard(self, width: int, height: int, tile_size: int = 8) -> np.ndarray:
        """Create a checkerboard pattern for transparent areas (vectorized for speed)."""
        # Create coordinate arrays
        y_coords = np.arange(height) // tile_size
        x_coords = np.arange(width) // tile_size
        
        # Create meshgrid and checkerboard mask
        yy, xx = np.meshgrid(y_coords, x_coords, indexing='ij')
        mask = (xx + yy) % 2 == 0
        
        # Create pattern using broadcasting (fast)
        pattern = np.zeros((height, width, 3), dtype=np.uint8)
        pattern[mask] = [240, 240, 240]  # Light gray
        pattern[~mask] = [200, 200, 200]  # Darker gray
        
        return pattern
    
    def _update_display(self):
        """Update the displayed pixmap with current zoom."""
        if self._original_pixmap is None:
            return
        
        # Scale to fit the widget while maintaining aspect ratio
        scaled = self._original_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled)
    
    def resizeEvent(self, event):
        """Handle resize by updating display."""
        super().resizeEvent(event)
        self._update_display()


class ImageSettingsDialog(QDialog):
    """
    Dialog for configuring image processing settings for laser engraving.
    
    Provides controls for:
    - Dithering algorithm selection (Floyd-Steinberg, Jarvis, Stucki, etc.)
    - DPI (engraving resolution)
    - Brightness and contrast adjustment
    - Threshold for binary conversion
    - Invert option
    - Live preview of processed image
    """
    
    # Signal emitted when settings change (for real-time preview)
    settings_changed = pyqtSignal()
    
    def __init__(self, image_shape: ImageShape, parent=None):
        super().__init__(parent)
        self.image_shape = image_shape
        self._original_image = image_shape.image_data.copy() if image_shape.image_data is not None else None
        
        # Create downscaled preview image for faster processing (max 512px width)
        # This makes dithering 4-5x faster while still showing good preview quality
        self._preview_image = None
        self._preview_alpha = None
        self._preview_scale = 1.0
        if self._original_image is not None:
            max_preview_width = 512
            height, width = self._original_image.shape
            if width > max_preview_width:
                self._preview_scale = max_preview_width / width
                new_width = max_preview_width
                new_height = int(height * self._preview_scale)
                # Use PIL for high-quality downscaling
                try:
                    from PIL import Image
                    pil_img = Image.fromarray(self._original_image, mode='L')
                    pil_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    self._preview_image = np.array(pil_img, dtype=np.uint8)
                except ImportError:
                    # Fallback to scipy or simple numpy downscaling
                    try:
                        from scipy.ndimage import zoom
                        self._preview_image = zoom(self._original_image, (self._preview_scale, self._preview_scale), order=1).astype(np.uint8)
                    except ImportError:
                        # Simple numpy downscaling (nearest neighbor - not ideal but works)
                        y_indices = np.linspace(0, height - 1, new_height).astype(int)
                        x_indices = np.linspace(0, width - 1, new_width).astype(int)
                        self._preview_image = self._original_image[np.ix_(y_indices, x_indices)]
                
                # Downscale alpha channel if present
                alpha_channel = getattr(image_shape, 'alpha_channel', None)
                if alpha_channel is not None:
                    try:
                        from PIL import Image
                        pil_alpha = Image.fromarray(alpha_channel, mode='L')
                        pil_alpha = pil_alpha.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        self._preview_alpha = np.array(pil_alpha, dtype=np.uint8)
                    except ImportError:
                        try:
                            from scipy.ndimage import zoom
                            self._preview_alpha = zoom(alpha_channel, (self._preview_scale, self._preview_scale), order=1).astype(np.uint8)
                        except ImportError:
                            # Simple numpy downscaling
                            y_indices = np.linspace(0, height - 1, new_height).astype(int)
                            x_indices = np.linspace(0, width - 1, new_width).astype(int)
                            self._preview_alpha = alpha_channel[np.ix_(y_indices, x_indices)]
            else:
                self._preview_image = self._original_image.copy()
                alpha_channel = getattr(image_shape, 'alpha_channel', None)
                self._preview_alpha = alpha_channel.copy() if alpha_channel is not None else None
        
        # Timer for debouncing preview updates
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._update_preview)
        
        self.setWindowTitle("Image Settings")
        self.setMinimumSize(800, 600)
        self._init_ui()
        self._load_current_settings()
        self._update_preview()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QHBoxLayout()
        
        # Left side: Settings controls
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setSpacing(10)
        
        # Dithering settings group
        dither_group = QGroupBox("Dithering")
        dither_layout = QFormLayout()
        
        # Dithering method
        self.dither_combo = QComboBox()
        self.dither_combo.addItems([
            "None (Threshold only)",
            "Floyd-Steinberg",
            "Jarvis-Judice-Ninke",
            "Stucki",
            "Atkinson",
            "Bayer 2x2 (Ordered)",
            "Bayer 4x4 (Ordered)",
            "Bayer 8x8 (Ordered)"
        ])
        self.dither_combo.currentIndexChanged.connect(self._on_setting_changed)
        dither_layout.addRow("Algorithm:", self.dither_combo)
        
        # Threshold
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 255)
        self.threshold_slider.setValue(128)
        self.threshold_slider.valueChanged.connect(self._on_setting_changed)
        
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(0, 255)
        self.threshold_spin.setValue(128)
        self.threshold_spin.valueChanged.connect(lambda v: self.threshold_slider.setValue(v))
        self.threshold_slider.valueChanged.connect(lambda v: self.threshold_spin.setValue(v))
        
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(self.threshold_spin)
        dither_layout.addRow("Threshold:", threshold_layout)
        
        dither_group.setLayout(dither_layout)
        settings_layout.addWidget(dither_group)
        
        # Resolution settings group
        resolution_group = QGroupBox("Resolution")
        resolution_layout = QFormLayout()
        
        # DPI
        self.dpi_spin = QDoubleSpinBox()
        self.dpi_spin.setRange(50, 1000)
        self.dpi_spin.setValue(254)
        self.dpi_spin.setSuffix(" DPI")
        self.dpi_spin.setDecimals(0)
        self.dpi_spin.setToolTip(
            "Engraving resolution in dots per inch.\n"
            "Higher = more detail but slower.\n"
            "254 DPI = 0.1mm line spacing (standard)\n"
            "318 DPI = 0.08mm line spacing (fine)\n"
            "508 DPI = 0.05mm line spacing (very fine)"
        )
        self.dpi_spin.valueChanged.connect(self._on_setting_changed)
        resolution_layout.addRow("DPI:", self.dpi_spin)
        
        # Line spacing info label
        self.line_spacing_label = QLabel()
        resolution_layout.addRow("Line Spacing:", self.line_spacing_label)
        
        resolution_group.setLayout(resolution_layout)
        settings_layout.addWidget(resolution_group)
        
        # Image adjustments group
        adjust_group = QGroupBox("Image Adjustments")
        adjust_layout = QFormLayout()
        
        # Brightness
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(-100, 100)
        self.brightness_slider.setValue(0)
        self.brightness_slider.valueChanged.connect(self._on_setting_changed)
        
        self.brightness_spin = QSpinBox()
        self.brightness_spin.setRange(-100, 100)
        self.brightness_spin.setValue(0)
        self.brightness_spin.valueChanged.connect(lambda v: self.brightness_slider.setValue(v))
        self.brightness_slider.valueChanged.connect(lambda v: self.brightness_spin.setValue(v))
        
        brightness_layout = QHBoxLayout()
        brightness_layout.addWidget(self.brightness_slider)
        brightness_layout.addWidget(self.brightness_spin)
        adjust_layout.addRow("Brightness:", brightness_layout)
        
        # Contrast
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(0, 300)  # 0-3.0 as percentage
        self.contrast_slider.setValue(100)  # 1.0 = 100%
        self.contrast_slider.valueChanged.connect(self._on_setting_changed)
        
        self.contrast_spin = QSpinBox()
        self.contrast_spin.setRange(0, 300)
        self.contrast_spin.setValue(100)
        self.contrast_spin.setSuffix("%")
        self.contrast_spin.valueChanged.connect(lambda v: self.contrast_slider.setValue(v))
        self.contrast_slider.valueChanged.connect(lambda v: self.contrast_spin.setValue(v))
        
        contrast_layout = QHBoxLayout()
        contrast_layout.addWidget(self.contrast_slider)
        contrast_layout.addWidget(self.contrast_spin)
        adjust_layout.addRow("Contrast:", contrast_layout)
        
        # Invert checkbox
        self.invert_check = QCheckBox("Invert image (swap black/white)")
        self.invert_check.stateChanged.connect(self._on_setting_changed)
        adjust_layout.addRow("", self.invert_check)
        
        adjust_group.setLayout(adjust_layout)
        settings_layout.addWidget(adjust_group)
        
        # Whitespace optimization group
        whitespace_group = QGroupBox("Whitespace Optimization")
        whitespace_layout = QFormLayout()
        
        # Skip white checkbox
        self.skip_white_check = QCheckBox("Skip white pixels (faster engraving, like LightBurn)")
        self.skip_white_check.setChecked(True)
        self.skip_white_check.setToolTip(
            "When enabled, white pixels are completely skipped during engraving.\n"
            "This dramatically reduces engraving time for images with large white areas.\n"
            "Disable only if you need to engrave very light gray areas."
        )
        self.skip_white_check.stateChanged.connect(self._on_setting_changed)
        whitespace_layout.addRow("", self.skip_white_check)
        
        # White threshold
        self.white_threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.white_threshold_slider.setRange(200, 255)
        self.white_threshold_slider.setValue(250)
        self.white_threshold_slider.valueChanged.connect(self._on_setting_changed)
        self.white_threshold_slider.setEnabled(False)  # Disabled when skip_white is off
        
        self.white_threshold_spin = QSpinBox()
        self.white_threshold_spin.setRange(200, 255)
        self.white_threshold_spin.setValue(250)
        self.white_threshold_spin.setToolTip(
            "Pixels with value >= this threshold are considered 'white' and skipped.\n"
            "Higher values = more aggressive white skipping (faster but may skip light grays).\n"
            "Lower values = less aggressive (slower but preserves more detail)."
        )
        self.white_threshold_spin.valueChanged.connect(lambda v: self.white_threshold_slider.setValue(v))
        self.white_threshold_slider.valueChanged.connect(lambda v: self.white_threshold_spin.setValue(v))
        self.white_threshold_spin.setEnabled(False)
        
        # Enable/disable threshold based on skip_white
        self.skip_white_check.stateChanged.connect(
            lambda checked: self.white_threshold_slider.setEnabled(checked)
        )
        self.skip_white_check.stateChanged.connect(
            lambda checked: self.white_threshold_spin.setEnabled(checked)
        )
        
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(self.white_threshold_slider)
        threshold_layout.addWidget(self.white_threshold_spin)
        whitespace_layout.addRow("White Threshold:", threshold_layout)
        
        whitespace_group.setLayout(whitespace_layout)
        settings_layout.addWidget(whitespace_group)
        
        # Reset button
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.clicked.connect(self._reset_to_defaults)
        settings_layout.addWidget(self.reset_btn)
        
        settings_layout.addStretch()
        
        # Add settings to main layout
        layout.addWidget(settings_widget, 1)
        
        # Right side: Preview
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        
        preview_label = QLabel("Preview")
        preview_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        preview_layout.addWidget(preview_label)
        
        # Preview tabs for original vs processed
        self.show_original_check = QCheckBox("Show original")
        self.show_original_check.stateChanged.connect(self._update_preview)
        preview_layout.addWidget(self.show_original_check)
        
        # Preview image
        self.preview_widget = ImagePreviewWidget()
        self.preview_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        preview_layout.addWidget(self.preview_widget)
        
        # Image info
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        preview_layout.addWidget(self.info_label)
        
        layout.addWidget(preview_widget, 2)
        
        # Dialog buttons
        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        buttons.accepted.connect(self._apply_and_accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._apply_settings)
        main_layout.addWidget(buttons)
        
        self.setLayout(main_layout)
    
    def _load_current_settings(self):
        """Load current settings from the image shape."""
        # Dithering mode
        mode_map = {
            "none": 0,
            "floyd_steinberg": 1,
            "jarvis": 2,
            "stucki": 3,
            "atkinson": 4,
            "bayer_2x2": 5,
            "bayer_4x4": 6,
            "bayer_8x8": 7,
            "bayer": 6,  # Default bayer to 4x4
        }
        dither_mode = getattr(self.image_shape, 'dither_mode', 'floyd_steinberg')
        self.dither_combo.setCurrentIndex(mode_map.get(dither_mode, 1))
        
        # Threshold
        self.threshold_slider.setValue(getattr(self.image_shape, 'threshold', 128))
        
        # DPI
        self.dpi_spin.setValue(getattr(self.image_shape, 'dpi', 254))
        
        # Brightness/Contrast
        self.brightness_slider.setValue(int(getattr(self.image_shape, 'brightness', 0)))
        self.contrast_slider.setValue(int(getattr(self.image_shape, 'contrast', 1.0) * 100))
        
        # Invert
        self.invert_check.setChecked(getattr(self.image_shape, 'invert', False))
        
        # Skip white
        self.skip_white_check.setChecked(getattr(self.image_shape, 'skip_white', True))
        self.white_threshold_slider.setValue(int(getattr(self.image_shape, 'white_threshold', 250)))
        
        self._update_line_spacing_label()
    
    def _on_setting_changed(self):
        """Handle any setting change - debounce preview update."""
        self._update_line_spacing_label()
        # Debounce preview updates to avoid lag during slider drags
        self._update_timer.start(100)  # 100ms delay
    
    def _update_line_spacing_label(self):
        """Update the line spacing info label."""
        dpi = self.dpi_spin.value()
        mm_per_inch = 25.4
        spacing = mm_per_inch / dpi
        self.line_spacing_label.setText(f"{spacing:.3f} mm")
    
    def _update_preview(self):
        """Update the preview image with current settings."""
        if self._original_image is None:
            self.preview_widget.setText("No image data")
            return
        
        # Use preview alpha channel (downscaled to match preview image)
        alpha_channel = self._preview_alpha
        
        if self.show_original_check.isChecked():
            # Show original image (use preview version for consistency)
            self.preview_widget.set_image(self._preview_image, alpha_channel)
            self._update_info_label(self._original_image, processed=False)
        else:
            # Process and show result
            processed = self._process_image()
            self.preview_widget.set_image(processed, alpha_channel)
            self._update_info_label(processed, processed=True)
    
    def _process_image(self) -> np.ndarray:
        """Process the image with current settings (uses downscaled preview for speed)."""
        if self._preview_image is None:
            return None
        
        # Use downscaled preview for fast processing (4-5x faster than full resolution)
        img = self._preview_image.copy()
        alpha_channel = self._preview_alpha
        
        # Apply brightness/contrast (transparent pixels are not adjusted)
        brightness = self.brightness_slider.value()
        contrast = self.contrast_slider.value() / 100.0
        
        if brightness != 0 or contrast != 1.0:
            img = adjust_brightness_contrast(img, brightness, contrast, alpha_channel)
        
        # Apply invert (transparent pixels are not inverted)
        if self.invert_check.isChecked():
            if alpha_channel is not None:
                # Only invert non-transparent pixels
                mask = alpha_channel >= 255
                img[mask] = 255 - img[mask]
            else:
                # No transparency - invert all pixels
                img = 255 - img
        
        # Apply dithering (transparent pixels remain white/skip)
        # Note: We always dither the preview for visual feedback, but it's fast because
        # we're using the downscaled preview image (512px max width instead of 1158px)
        dither_method = self._get_dither_method()
        threshold = self.threshold_slider.value()
        
        ditherer = ImageDitherer(dither_method)
        result = ditherer.dither(img, threshold, alpha_channel)
        
        return result
    
    def _get_dither_method(self) -> DitheringMethod:
        """Get the selected dithering method."""
        index = self.dither_combo.currentIndex()
        methods = [
            DitheringMethod.NONE,
            DitheringMethod.FLOYD_STEINBERG,
            DitheringMethod.JARVIS_JUDICE_NINKE,
            DitheringMethod.STUCKI,
            DitheringMethod.ATKINSON,
            DitheringMethod.BAYER_2x2,
            DitheringMethod.BAYER_4x4,
            DitheringMethod.BAYER_8x8,
        ]
        return methods[index] if index < len(methods) else DitheringMethod.FLOYD_STEINBERG
    
    def _get_dither_mode_string(self) -> str:
        """Get the dither mode as a string for storage."""
        index = self.dither_combo.currentIndex()
        modes = [
            "none",
            "floyd_steinberg",
            "jarvis",
            "stucki",
            "atkinson",
            "bayer_2x2",
            "bayer_4x4",
            "bayer_8x8",
        ]
        return modes[index] if index < len(modes) else "floyd_steinberg"
    
    def _update_info_label(self, image: np.ndarray, processed: bool):
        """Update the image info label."""
        if image is None:
            self.info_label.setText("")
            return
        
        height, width = image.shape[:2]
        dpi = self.dpi_spin.value()
        mm_per_inch = 25.4
        
        width_mm = (width / dpi) * mm_per_inch
        height_mm = (height / dpi) * mm_per_inch
        
        status = "Processed" if processed else "Original"
        
        # Count black pixels if processed (for estimated engraving time)
        if processed:
            black_pixels = np.sum(image == 0)
            total_pixels = image.size
            fill_percent = (black_pixels / total_pixels) * 100
            
            # Check for transparency
            alpha_channel = getattr(self.image_shape, 'alpha_channel', None)
            transparent_info = ""
            if alpha_channel is not None:
                transparent_pixels = np.sum(alpha_channel < 255)
                transparent_percent = (transparent_pixels / total_pixels) * 100
                transparent_info = f"\nTransparent: {transparent_percent:.1f}% ({transparent_pixels:,} pixels - will be skipped)"
            
            info = (
                f"{status}: {width} x {height} px\n"
                f"Output: {width_mm:.1f} x {height_mm:.1f} mm at {dpi:.0f} DPI\n"
                f"Fill: {fill_percent:.1f}% ({black_pixels:,} pixels){transparent_info}"
            )
        else:
            # Check for transparency in original
            alpha_channel = getattr(self.image_shape, 'alpha_channel', None)
            transparent_info = ""
            if alpha_channel is not None:
                transparent_pixels = np.sum(alpha_channel < 255)
                total_pixels = alpha_channel.size
                transparent_percent = (transparent_pixels / total_pixels) * 100
                transparent_info = f"\nTransparent: {transparent_percent:.1f}% ({transparent_pixels:,} pixels - will be skipped)"
            
            info = (
                f"{status}: {width} x {height} px\n"
                f"Will engrave at: {width_mm:.1f} x {height_mm:.1f} mm{transparent_info}"
            )
        
        self.info_label.setText(info)
    
    def _reset_to_defaults(self):
        """Reset all settings to defaults."""
        self.dither_combo.setCurrentIndex(1)  # Floyd-Steinberg
        self.threshold_slider.setValue(128)
        self.dpi_spin.setValue(254)
        self.brightness_slider.setValue(0)
        self.contrast_slider.setValue(100)
        self.invert_check.setChecked(False)
        self.skip_white_check.setChecked(True)
        self.white_threshold_slider.setValue(250)
    
    def _apply_settings(self):
        """Apply current settings to the image shape."""
        # Store old DPI to check if it changed
        old_dpi = self.image_shape.dpi
        new_dpi = self.dpi_spin.value()
        
        self.image_shape.dither_mode = self._get_dither_mode_string()
        self.image_shape.threshold = self.threshold_slider.value()
        self.image_shape.dpi = new_dpi
        
        # Recalculate width and height in mm when DPI changes
        if old_dpi != new_dpi and self.image_shape.image_data is not None:
            mm_per_inch = 25.4
            height_px, width_px = self.image_shape.image_data.shape
            self.image_shape.width = (width_px / new_dpi) * mm_per_inch
            self.image_shape.height = (height_px / new_dpi) * mm_per_inch
        
        self.image_shape.brightness = self.brightness_slider.value()
        self.image_shape.contrast = self.contrast_slider.value() / 100.0
        self.image_shape.invert = self.invert_check.isChecked()
        self.image_shape.skip_white = self.skip_white_check.isChecked()
        self.image_shape.white_threshold = self.white_threshold_slider.value()
        
        self.settings_changed.emit()
    
    def _apply_and_accept(self):
        """Apply settings and close dialog."""
        self._apply_settings()
        self.accept()
    
    def get_settings(self) -> dict:
        """Get the current settings as a dictionary."""
        return {
            'dither_mode': self._get_dither_mode_string(),
            'threshold': self.threshold_slider.value(),
            'dpi': self.dpi_spin.value(),
            'brightness': self.brightness_slider.value(),
            'contrast': self.contrast_slider.value() / 100.0,
            'invert': self.invert_check.isChecked(),
            'skip_white': self.skip_white_check.isChecked(),
            'white_threshold': self.white_threshold_slider.value(),
        }
