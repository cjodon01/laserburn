"""
Layers Panel - Dock widget for managing layers.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton
from PyQt6.QtCore import pyqtSignal

from ...core.document import Document
from ...core.layer import Layer


class LayersPanel(QWidget):
    """Panel for managing document layers."""
    
    layer_selected = pyqtSignal(Layer)
    
    def __init__(self, document: Document):
        super().__init__()
        self.document = document
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout()
        
        self.layer_list = QListWidget()
        self.layer_list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.layer_list)
        
        # Buttons
        btn_add = QPushButton("Add Layer")
        btn_add.clicked.connect(self._add_layer)
        layout.addWidget(btn_add)
        
        btn_remove = QPushButton("Remove Layer")
        btn_remove.clicked.connect(self._remove_layer)
        layout.addWidget(btn_remove)
        
        self.setLayout(layout)
        self.refresh()
    
    def set_document(self, document: Document):
        """Set the document to display."""
        self.document = document
        self.refresh()
    
    def refresh(self):
        """Refresh the layer list."""
        self.layer_list.clear()
        for layer in self.document.layers:
            self.layer_list.addItem(layer.name)
    
    def _on_selection_changed(self):
        """Handle layer selection change."""
        current = self.layer_list.currentRow()
        if 0 <= current < len(self.document.layers):
            self.layer_selected.emit(self.document.layers[current])
    
    def _add_layer(self):
        """Add a new layer."""
        layer = Layer(name=f"Layer {len(self.document.layers) + 1}")
        self.document.add_layer(layer)
        self.refresh()
    
    def _remove_layer(self):
        """Remove selected layer."""
        current = self.layer_list.currentRow()
        if 0 <= current < len(self.document.layers):
            self.document.remove_layer(self.document.layers[current])
            self.refresh()

