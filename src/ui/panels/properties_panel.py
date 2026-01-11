"""
Properties Panel - Dock widget for editing shape properties.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from typing import List

from ...core.shapes import Shape


class PropertiesPanel(QWidget):
    """Panel for editing selected shape properties."""
    
    def __init__(self):
        super().__init__()
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Properties"))
        layout.addStretch()
        self.setLayout(layout)
    
    def update_selection(self, shapes: List[Shape]):
        """Update panel with selected shapes."""
        # TODO: Implement property editing
        pass

