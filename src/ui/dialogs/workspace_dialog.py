"""
Workspace Size Dialog

Allows user to set the workspace dimensions based on laser bed size.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QDoubleSpinBox, QPushButton, QFormLayout, QComboBox
)
from PyQt6.QtCore import Qt
from typing import Tuple


class WorkspaceDialog(QDialog):
    """Dialog for setting workspace dimensions."""
    
    # Common laser bed sizes (width x height in mm)
    PRESET_SIZES = {
        "Small (100x100mm)": (100, 100),
        "Medium (200x200mm)": (200, 200),
        "Large (300x300mm)": (300, 300),
        "XLarge (400x400mm)": (400, 400),
        "K40 (300x200mm)": (300, 200),
        "Glowforge Basic (279x152mm)": (279, 152),
        "Glowforge Plus (279x406mm)": (279, 406),
        "Epilog Mini (305x203mm)": (305, 203),
        "Epilog Zing (406x305mm)": (406, 305),
        "Custom": None
    }
    
    def __init__(self, current_width: float, current_height: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Workspace Size")
        self.setModal(True)
        self.setMinimumWidth(300)
        
        self.width = current_width
        self.height = current_height
        
        layout = QVBoxLayout(self)
        
        # Preset selection
        form_layout = QFormLayout()
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(self.PRESET_SIZES.keys()))
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        form_layout.addRow("Preset:", self.preset_combo)
        
        # Width input
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(10, 2000)
        self.width_spin.setValue(current_width)
        self.width_spin.setSuffix(" mm")
        self.width_spin.setDecimals(1)
        self.width_spin.valueChanged.connect(self._on_custom_changed)
        form_layout.addRow("Width:", self.width_spin)
        
        # Height input
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(10, 2000)
        self.height_spin.setValue(current_height)
        self.height_spin.setSuffix(" mm")
        self.height_spin.setDecimals(1)
        self.height_spin.valueChanged.connect(self._on_custom_changed)
        form_layout.addRow("Height:", self.height_spin)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        # Find matching preset
        self._find_matching_preset()
    
    def _find_matching_preset(self):
        """Find preset that matches current dimensions."""
        for preset_name, size in self.PRESET_SIZES.items():
            if size and abs(size[0] - self.width) < 1 and abs(size[1] - self.height) < 1:
                index = self.preset_combo.findText(preset_name)
                if index >= 0:
                    self.preset_combo.setCurrentIndex(index)
                    return
        # No match found, select Custom
        index = self.preset_combo.findText("Custom")
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)
    
    def _on_preset_changed(self, preset_name: str):
        """Handle preset selection change."""
        size = self.PRESET_SIZES.get(preset_name)
        if size:
            self.width_spin.blockSignals(True)
            self.height_spin.blockSignals(True)
            self.width_spin.setValue(size[0])
            self.height_spin.setValue(size[1])
            self.width_spin.blockSignals(False)
            self.height_spin.blockSignals(False)
        # If Custom, don't change values
    
    def _on_custom_changed(self):
        """Handle custom size change."""
        # Switch to Custom preset if user manually changes values
        if self.preset_combo.currentText() != "Custom":
            index = self.preset_combo.findText("Custom")
            if index >= 0:
                self.preset_combo.blockSignals(True)
                self.preset_combo.setCurrentIndex(index)
                self.preset_combo.blockSignals(False)
    
    def get_size(self) -> Tuple[float, float]:
        """Get the selected workspace size."""
        return (self.width_spin.value(), self.height_spin.value())

