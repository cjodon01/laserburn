"""
Layers Panel - Dock widget for managing layers.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QFormLayout, QGroupBox, QDoubleSpinBox, QSpinBox,
    QCheckBox, QComboBox, QLabel, QSplitter, QMenu, QInputDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QAction

from ...core.document import Document
from ...core.layer import Layer
from ...core.shapes import Shape


class LayersPanel(QWidget):
    """Panel for managing document layers."""
    
    layer_selected = pyqtSignal(Layer)
    layer_settings_changed = pyqtSignal(Layer)
    layer_reordered = pyqtSignal()
    shapes_moved_between_layers = pyqtSignal()
    shape_selected = pyqtSignal(object)  # Emits Shape when selected in panel
    shape_deleted = pyqtSignal(object, object)  # Emits (shape, layer) when deleted
    
    def __init__(self, document: Document):
        super().__init__()
        self.document = document
        self._selected_layer: Layer = None
        self._updating_ui = False
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Create splitter for layers list and settings
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Layers list section
        layers_group = QGroupBox("Layers")
        layers_layout = QVBoxLayout()
        
        self.layer_tree = QTreeWidget()
        self.layer_tree.setHeaderLabels(["Layer / Object", "Type"])
        self.layer_tree.setRootIsDecorated(True)
        self.layer_tree.setDragEnabled(True)
        self.layer_tree.setAcceptDrops(True)
        self.layer_tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.layer_tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.layer_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.layer_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.layer_tree.customContextMenuRequested.connect(self._show_context_menu)
        layers_layout.addWidget(self.layer_tree)
        
        # Layer buttons
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Add Layer")
        btn_add.clicked.connect(self._add_layer)
        btn_remove = QPushButton("Remove Layer")
        btn_remove.clicked.connect(self._remove_layer)
        btn_up = QPushButton("↑")
        btn_up.setToolTip("Move layer up")
        btn_up.clicked.connect(self._move_layer_up)
        btn_down = QPushButton("↓")
        btn_down.setToolTip("Move layer down")
        btn_down.clicked.connect(self._move_layer_down)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_remove)
        btn_layout.addWidget(btn_up)
        btn_layout.addWidget(btn_down)
        layers_layout.addLayout(btn_layout)
        
        layers_group.setLayout(layers_layout)
        splitter.addWidget(layers_group)
        
        # Layer settings section
        settings_group = QGroupBox("Layer Settings")
        settings_layout = QVBoxLayout()
        
        # Settings form
        self.settings_form = QFormLayout()
        
        # Power
        self.power_spin = QDoubleSpinBox()
        self.power_spin.setRange(0, 100)
        self.power_spin.setValue(50)
        self.power_spin.setSuffix(" %")
        self.power_spin.setDecimals(1)
        self.power_spin.valueChanged.connect(self._on_settings_changed)
        self.settings_form.addRow("Power:", self.power_spin)
        
        # Speed
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.1, 1000)
        self.speed_spin.setValue(100)
        self.speed_spin.setSuffix(" mm/s")
        self.speed_spin.setDecimals(1)
        self.speed_spin.valueChanged.connect(self._on_settings_changed)
        self.settings_form.addRow("Speed:", self.speed_spin)
        
        # Passes
        self.passes_spin = QSpinBox()
        self.passes_spin.setRange(1, 10)
        self.passes_spin.setValue(1)
        self.passes_spin.valueChanged.connect(self._on_settings_changed)
        self.settings_form.addRow("Passes:", self.passes_spin)
        
        # Fill enabled
        self.fill_enabled_check = QCheckBox()
        self.fill_enabled_check.setChecked(False)
        self.fill_enabled_check.stateChanged.connect(self._on_fill_enabled_changed)
        self.settings_form.addRow("Fill Enabled:", self.fill_enabled_check)
        
        # Fill pattern
        self.fill_pattern_combo = QComboBox()
        self.fill_pattern_combo.addItems(["horizontal", "vertical", "crosshatch", "diagonal"])
        self.fill_pattern_combo.currentTextChanged.connect(self._on_settings_changed)
        self.settings_form.addRow("Fill Pattern:", self.fill_pattern_combo)
        
        # Fill line interval
        self.fill_interval_spin = QDoubleSpinBox()
        self.fill_interval_spin.setRange(0.01, 10.0)
        self.fill_interval_spin.setValue(0.1)
        self.fill_interval_spin.setSuffix(" mm")
        self.fill_interval_spin.setDecimals(2)
        self.fill_interval_spin.valueChanged.connect(self._on_settings_changed)
        self.settings_form.addRow("Fill Spacing:", self.fill_interval_spin)
        
        # Fill angle (for diagonal)
        self.fill_angle_spin = QDoubleSpinBox()
        self.fill_angle_spin.setRange(-180, 180)
        self.fill_angle_spin.setValue(0.0)
        self.fill_angle_spin.setSuffix(" °")
        self.fill_angle_spin.setDecimals(1)
        self.fill_angle_spin.valueChanged.connect(self._on_settings_changed)
        self.settings_form.addRow("Fill Angle:", self.fill_angle_spin)
        
        # Air assist
        self.air_assist_check = QCheckBox()
        self.air_assist_check.setChecked(True)
        self.air_assist_check.stateChanged.connect(self._on_settings_changed)
        self.settings_form.addRow("Air Assist:", self.air_assist_check)
        
        settings_layout.addLayout(self.settings_form)
        settings_layout.addStretch()
        
        settings_group.setLayout(settings_layout)
        splitter.addWidget(settings_group)
        
        # Set splitter proportions (70% layers, 30% settings)
        splitter.setSizes([300, 200])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
        # Initially disable settings
        self._set_settings_enabled(False)
        
        self.refresh()
    
    def _set_settings_enabled(self, enabled: bool):
        """Enable or disable settings controls."""
        self.power_spin.setEnabled(enabled)
        self.speed_spin.setEnabled(enabled)
        self.passes_spin.setEnabled(enabled)
        self.fill_enabled_check.setEnabled(enabled)
        self.fill_pattern_combo.setEnabled(enabled)
        self.fill_interval_spin.setEnabled(enabled)
        self.fill_angle_spin.setEnabled(enabled)
        self.air_assist_check.setEnabled(enabled)
    
    def set_document(self, document: Document):
        """Set the document to display."""
        self.document = document
        self._selected_layer = None
        self.refresh()
    
    def refresh(self):
        """Refresh the layer list."""
        self._updating_ui = True
        self.layer_tree.clear()
        
        for layer in self.document.layers:
            # Create layer item
            layer_item = QTreeWidgetItem(self.layer_tree)
            layer_item.setText(0, layer.name)
            layer_item.setText(1, f"{len(layer.shapes)} objects")
            layer_item.setData(0, Qt.ItemDataRole.UserRole, layer)
            
            # Set layer color indicator
            if layer.color:
                try:
                    color = QColor(layer.color)
                    layer_item.setForeground(0, color)
                except:
                    pass
            
            # Add shapes as children
            for shape in layer.shapes:
                shape_item = QTreeWidgetItem(layer_item)
                shape_name = getattr(shape, 'name', 'Unnamed')
                if not shape_name or shape_name == "":
                    shape_name = type(shape).__name__
                shape_item.setText(0, shape_name)
                shape_item.setText(1, type(shape).__name__)
                shape_item.setData(0, Qt.ItemDataRole.UserRole, shape)
                
                # Show visibility state
                if not shape.visible:
                    shape_item.setForeground(0, QColor(128, 128, 128))
                    shape_item.setText(0, f"{shape_name} (hidden)")
            
            # Expand layer by default
            layer_item.setExpanded(True)
        
        self._updating_ui = False
    
    def _on_selection_changed(self):
        """Handle layer/object selection change."""
        if self._updating_ui:
            return
        
        current = self.layer_tree.currentItem()
        if not current:
            self._selected_layer = None
            self._set_settings_enabled(False)
            return
        
        # Get layer from item
        data = current.data(0, Qt.ItemDataRole.UserRole)
        
        if isinstance(data, Layer):
            # Selected a layer
            self._selected_layer = data
            self._update_settings_ui()
            self._set_settings_enabled(True)
            self.layer_selected.emit(data)
        elif isinstance(data, Shape):
            # Selected a shape - find its layer and emit shape selection
            self.shape_selected.emit(data)
            for doc_layer in self.document.layers:
                if data in doc_layer.shapes:
                    self._selected_layer = doc_layer
                    self._update_settings_ui()
                    self._set_settings_enabled(True)
                    self.layer_selected.emit(doc_layer)
                    break
    
    def _on_item_double_clicked(self, item, column):
        """Handle double-click on item."""
        layer = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(layer, Layer):
            # Rename layer
            # TODO: Implement rename dialog
            pass
    
    def _update_settings_ui(self):
        """Update settings UI from selected layer."""
        if not self._selected_layer:
            return
        
        self._updating_ui = True
        
        settings = self._selected_layer.laser_settings
        
        self.power_spin.setValue(settings.power)
        self.speed_spin.setValue(settings.speed)
        self.passes_spin.setValue(settings.passes)
        self.fill_enabled_check.setChecked(settings.fill_enabled)
        self.fill_pattern_combo.setCurrentText(settings.fill_pattern)
        self.fill_interval_spin.setValue(settings.line_interval)
        self.fill_angle_spin.setValue(settings.fill_angle)
        self.air_assist_check.setChecked(settings.air_assist)
        
        self._updating_ui = False
    
    def _on_fill_enabled_changed(self, state):
        """Handle fill enabled checkbox change."""
        if self._updating_ui:
            return
        
        enabled = state == Qt.CheckState.Checked.value
        self.fill_pattern_combo.setEnabled(enabled)
        self.fill_interval_spin.setEnabled(enabled)
        self.fill_angle_spin.setEnabled(enabled)
        
        self._on_settings_changed()
    
    def _on_settings_changed(self):
        """Handle settings change."""
        if self._updating_ui or not self._selected_layer:
            return
        
        # Update layer settings
        settings = self._selected_layer.laser_settings
        settings.power = self.power_spin.value()
        settings.speed = self.speed_spin.value()
        settings.passes = self.passes_spin.value()
        settings.fill_enabled = self.fill_enabled_check.isChecked()
        settings.fill_pattern = self.fill_pattern_combo.currentText()
        settings.line_interval = self.fill_interval_spin.value()
        settings.fill_angle = self.fill_angle_spin.value()
        settings.air_assist = self.air_assist_check.isChecked()
        
        # Emit signal
        self.layer_settings_changed.emit(self._selected_layer)
    
    def _add_layer(self):
        """Add a new layer."""
        layer = Layer(name=f"Layer {len(self.document.layers) + 1}")
        self.document.add_layer(layer)
        self.refresh()
        
        # Select the new layer
        for i in range(self.layer_tree.topLevelItemCount()):
            item = self.layer_tree.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == layer:
                self.layer_tree.setCurrentItem(item)
                break
    
    def _remove_layer(self):
        """Remove selected layer."""
        current = self.layer_tree.currentItem()
        if not current:
            return
        
        layer = current.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(layer, Layer):
            if layer in self.document.layers:
                self.document.remove_layer(layer)
                self._selected_layer = None
                self._set_settings_enabled(False)
                self.refresh()
    
    def _move_layer_up(self):
        """Move selected layer up in the list."""
        current = self.layer_tree.currentItem()
        if not current:
            return
        
        layer = current.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(layer, Layer):
            idx = self.document.layers.index(layer)
            if idx > 0:
                # Swap with layer above
                self.document.layers[idx], self.document.layers[idx - 1] = \
                    self.document.layers[idx - 1], self.document.layers[idx]
                self.refresh()
                # Reselect the moved layer
                for i in range(self.layer_tree.topLevelItemCount()):
                    item = self.layer_tree.topLevelItem(i)
                    if item.data(0, Qt.ItemDataRole.UserRole) == layer:
                        self.layer_tree.setCurrentItem(item)
                        break
    
    def _move_layer_down(self):
        """Move selected layer down in the list."""
        current = self.layer_tree.currentItem()
        if not current:
            return
        
        layer = current.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(layer, Layer):
            idx = self.document.layers.index(layer)
            if idx < len(self.document.layers) - 1:
                # Swap with layer below
                self.document.layers[idx], self.document.layers[idx + 1] = \
                    self.document.layers[idx + 1], self.document.layers[idx]
                self.refresh()
                # Reselect the moved layer
                for i in range(self.layer_tree.topLevelItemCount()):
                    item = self.layer_tree.topLevelItem(i)
                    if item.data(0, Qt.ItemDataRole.UserRole) == layer:
                        self.layer_tree.setCurrentItem(item)
                        break
                self.layer_reordered.emit()
    
    def _show_context_menu(self, position):
        """Show context menu for layers/shapes."""
        item = self.layer_tree.itemAt(position)
        if not item:
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        
        if isinstance(data, Shape):
            # Context menu for shapes
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self._delete_shape(data))
            menu.addAction(delete_action)
            
            # Add "Move to Layer" submenu
            move_menu = menu.addMenu("Move to Layer")
            for layer in self.document.layers:
                # Find the layer this shape is currently in
                current_layer = None
                for l in self.document.layers:
                    if data in l.shapes:
                        current_layer = l
                        break
                
                if layer != current_layer:
                    action = QAction(layer.name, self)
                    action.triggered.connect(
                        lambda checked, target_layer=layer, shape=data: 
                        self._move_shape_to_layer(shape, target_layer)
                    )
                    move_menu.addAction(action)
            
            # Rename action
            rename_action = QAction("Rename", self)
            rename_action.triggered.connect(lambda: self._rename_shape(data))
            menu.addAction(rename_action)
            
        elif isinstance(data, Layer):
            # Context menu for layers
            rename_action = QAction("Rename Layer", self)
            rename_action.triggered.connect(lambda: self._rename_layer(data))
            menu.addAction(rename_action)
            
            delete_action = QAction("Delete Layer", self)
            delete_action.triggered.connect(self._remove_layer)
            menu.addAction(delete_action)
        
        menu.exec(self.layer_tree.viewport().mapToGlobal(position))
    
    def _delete_shape(self, shape: Shape):
        """Delete a shape from its layer."""
        for layer in self.document.layers:
            if shape in layer.shapes:
                layer.remove_shape(shape)
                self.shape_deleted.emit(shape, layer)
                self.refresh()
                break
    
    def _move_shape_to_layer(self, shape: Shape, target_layer: Layer):
        """Move a shape from its current layer to target layer."""
        # Find and remove from current layer
        for layer in self.document.layers:
            if shape in layer.shapes:
                layer.remove_shape(shape)
                break
        
        # Add to target layer
        target_layer.add_shape(shape)
        self.shapes_moved_between_layers.emit()
        self.refresh()
    
    def _rename_shape(self, shape: Shape):
        """Rename a shape."""
        current_name = getattr(shape, 'name', '') or type(shape).__name__
        new_name, ok = QInputDialog.getText(
            self, "Rename Shape", "New name:", text=current_name
        )
        if ok and new_name:
            shape.name = new_name
            self.refresh()
    
    def _rename_layer(self, layer: Layer):
        """Rename a layer."""
        new_name, ok = QInputDialog.getText(
            self, "Rename Layer", "New name:", text=layer.name
        )
        if ok and new_name:
            layer.name = new_name
            self.refresh()
    
    def delete_selected(self):
        """Delete currently selected item (shape or layer)."""
        current = self.layer_tree.currentItem()
        if not current:
            return
        
        data = current.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, Shape):
            self._delete_shape(data)
        elif isinstance(data, Layer):
            # Confirm before deleting layer with shapes
            if data.shapes:
                reply = QMessageBox.question(
                    self, "Delete Layer",
                    f"Layer '{data.name}' contains {len(data.shapes)} objects. Delete anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            self._remove_layer()
    
    def keyPressEvent(self, event):
        """Handle key presses."""
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected()
        else:
            super().keyPressEvent(event)
    
    def select_shape_by_object(self, shape: Shape):
        """Select a shape in the tree by its object reference."""
        self._updating_ui = True
        
        # Find and select the tree item for this shape
        for i in range(self.layer_tree.topLevelItemCount()):
            layer_item = self.layer_tree.topLevelItem(i)
            for j in range(layer_item.childCount()):
                shape_item = layer_item.child(j)
                item_data = shape_item.data(0, Qt.ItemDataRole.UserRole)
                if item_data == shape:
                    self.layer_tree.setCurrentItem(shape_item)
                    self.layer_tree.scrollToItem(shape_item)
                    self._updating_ui = False
                    return True
        
        self._updating_ui = False
        return False
    
    def get_selected_shapes(self):
        """Get list of currently selected shapes."""
        selected = []
        for item in self.layer_tree.selectedItems():
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, Shape):
                selected.append(data)
        return selected