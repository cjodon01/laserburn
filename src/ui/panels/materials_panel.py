"""
Materials Panel - Dock widget for material library.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal


class MaterialsPanel(QWidget):
    """Panel for material library."""
    
    material_selected = pyqtSignal(object)  # MaterialPreset
    
    def __init__(self):
        super().__init__()
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Materials"))
        layout.addStretch()
        self.setLayout(layout)

