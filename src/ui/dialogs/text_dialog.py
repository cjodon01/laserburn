"""
Text Input Dialog for LaserBurn

Dialog for entering text and setting font properties.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFontComboBox, QSpinBox,
    QCheckBox, QDialogButtonBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class TextDialog(QDialog):
    """Dialog for entering text and font properties."""
    
    def __init__(self, parent=None, initial_text: str = "Text",
                 font_family: str = "Arial", font_size: float = 24.0,
                 bold: bool = False, italic: bool = False):
        super().__init__(parent)
        
        self.setWindowTitle("Enter Text")
        self.setModal(True)
        
        # Layout
        layout = QVBoxLayout(self)
        
        # Text input
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("Text:"))
        self.text_input = QLineEdit(initial_text)
        self.text_input.selectAll()
        text_layout.addWidget(self.text_input)
        layout.addLayout(text_layout)
        
        # Font family
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font:"))
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(font_family))
        font_layout.addWidget(self.font_combo)
        layout.addLayout(font_layout)
        
        # Font size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Size:"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(6, 200)
        self.size_spin.setValue(int(font_size))
        size_layout.addWidget(self.size_spin)
        layout.addLayout(size_layout)
        
        # Font style
        style_layout = QHBoxLayout()
        self.bold_check = QCheckBox("Bold")
        self.bold_check.setChecked(bold)
        self.italic_check = QCheckBox("Italic")
        self.italic_check.setChecked(italic)
        style_layout.addWidget(self.bold_check)
        style_layout.addWidget(self.italic_check)
        style_layout.addStretch()
        layout.addLayout(style_layout)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Set focus to text input
        self.text_input.setFocus()
    
    def get_text(self) -> str:
        """Get entered text."""
        return self.text_input.text()
    
    def get_font_family(self) -> str:
        """Get selected font family."""
        return self.font_combo.currentFont().family()
    
    def get_font_size(self) -> float:
        """Get font size."""
        return float(self.size_spin.value())
    
    def is_bold(self) -> bool:
        """Check if bold is selected."""
        return self.bold_check.isChecked()
    
    def is_italic(self) -> bool:
        """Check if italic is selected."""
        return self.italic_check.isChecked()

