"""
Array Dialog for LaserBurn

Allows users to create arrays of selected shapes with configurable
rows, columns, and spacing.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QDoubleSpinBox, QPushButton, QDialogButtonBox, QGroupBox
)
from PyQt6.QtCore import Qt


class ArrayDialog(QDialog):
    """Dialog for configuring array parameters."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Array")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        
        # Array dimensions group
        dimensions_group = QGroupBox("Array Dimensions")
        dimensions_layout = QVBoxLayout()
        
        # Rows
        rows_layout = QHBoxLayout()
        rows_layout.addWidget(QLabel("Rows:"))
        self.rows_spin = QSpinBox()
        self.rows_spin.setMinimum(1)
        self.rows_spin.setMaximum(100)
        self.rows_spin.setValue(2)
        rows_layout.addWidget(self.rows_spin)
        rows_layout.addStretch()
        dimensions_layout.addLayout(rows_layout)
        
        # Columns
        cols_layout = QHBoxLayout()
        cols_layout.addWidget(QLabel("Columns:"))
        self.columns_spin = QSpinBox()
        self.columns_spin.setMinimum(1)
        self.columns_spin.setMaximum(100)
        self.columns_spin.setValue(2)
        cols_layout.addWidget(self.columns_spin)
        cols_layout.addStretch()
        dimensions_layout.addLayout(cols_layout)
        
        dimensions_group.setLayout(dimensions_layout)
        layout.addWidget(dimensions_group)
        
        # Spacing group
        spacing_group = QGroupBox("Spacing (mm)")
        spacing_layout = QVBoxLayout()
        
        # X spacing
        x_spacing_layout = QHBoxLayout()
        x_spacing_layout.addWidget(QLabel("X Spacing:"))
        self.x_spacing_spin = QDoubleSpinBox()
        self.x_spacing_spin.setMinimum(0.0)
        self.x_spacing_spin.setMaximum(10000.0)
        self.x_spacing_spin.setValue(10.0)
        self.x_spacing_spin.setDecimals(2)
        self.x_spacing_spin.setSuffix(" mm")
        x_spacing_layout.addWidget(self.x_spacing_spin)
        x_spacing_layout.addStretch()
        spacing_layout.addLayout(x_spacing_layout)
        
        # Y spacing
        y_spacing_layout = QHBoxLayout()
        y_spacing_layout.addWidget(QLabel("Y Spacing:"))
        self.y_spacing_spin = QDoubleSpinBox()
        self.y_spacing_spin.setMinimum(0.0)
        self.y_spacing_spin.setMaximum(10000.0)
        self.y_spacing_spin.setValue(10.0)
        self.y_spacing_spin.setDecimals(2)
        self.y_spacing_spin.setSuffix(" mm")
        y_spacing_layout.addWidget(self.y_spacing_spin)
        y_spacing_layout.addStretch()
        spacing_layout.addLayout(y_spacing_layout)
        
        spacing_group.setLayout(spacing_layout)
        layout.addWidget(spacing_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_rows(self) -> int:
        """Get number of rows."""
        return self.rows_spin.value()
    
    def get_columns(self) -> int:
        """Get number of columns."""
        return self.columns_spin.value()
    
    def get_x_spacing(self) -> float:
        """Get X spacing in mm."""
        return self.x_spacing_spin.value()
    
    def get_y_spacing(self) -> float:
        """Get Y spacing in mm."""
        return self.y_spacing_spin.value()
