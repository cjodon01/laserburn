"""
Console Widget for Laser Controller Interaction

Allows users to send commands directly to the laser controller
and view responses, similar to LightBurn's console.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton,
    QHBoxLayout, QLabel, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCharFormat, QColor, QFont, QKeyEvent
from datetime import datetime


class ConsoleWidget(QWidget):
    """Console widget for sending commands to laser controller."""
    
    # Signal emitted when user wants to send a command
    command_sent = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._command_history = []
        self._history_index = -1
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header
        header = QLabel("Controller Console")
        header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(header)
        
        # Output area (read-only)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Courier", 9))
        self.output.setMinimumHeight(200)
        # Make output area more usable
        # Use NoWrap for console (better for command output)
        self.output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.output.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.output.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        layout.addWidget(self.output, 1)  # Give it stretch factor to fill space
        
        # Input area
        input_layout = QHBoxLayout()
        
        prompt_label = QLabel(">")
        prompt_label.setStyleSheet("font-weight: bold; color: green;")
        input_layout.addWidget(prompt_label)
        
        self.input = QLineEdit()
        self.input.setPlaceholderText("Enter G-code command (e.g., G0 X10 Y10) or press Enter")
        self.input.returnPressed.connect(self._send_command)
        self.input.setFont(QFont("Courier", 9))
        # Make input field focusable and usable
        self.input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        input_layout.addWidget(self.input, 1)  # Give it stretch factor
        
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self._send_command)
        input_layout.addWidget(send_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_output)
        input_layout.addWidget(clear_btn)
        
        layout.addLayout(input_layout)
        
        # Quick commands
        quick_layout = QHBoxLayout()
        quick_label = QLabel("Quick:")
        quick_layout.addWidget(quick_label)
        
        self.quick_commands = QComboBox()
        self.quick_commands.addItems([
            "Select command...",
            "? - Status report",
            "$H - Home",
            "$X - Unlock",
            "$$ - Show all settings",
            "$30 - Check max spindle speed (IMPORTANT for power)",
            "$30=1000 - Set max spindle to 1000 (GRBL default)",
            "$21 - Check homing setting",
            "$21=1 - Enable homing",
            "$RST=* - Soft reset",
            "$I - GRBL version info",
            "G28 - Go to home",
            "G0 X0 Y0 - Go to origin",
            "M3 S1000 - Laser on full power ($30=1000)",
            "M3 S500 - Laser on 50% power ($30=1000)",
            "M5 - Laser off",
            "G0 X10 Y10 - Move to (10, 10)",
            "G0 X0 Y0 Z0 - Move to origin",
        ])
        self.quick_commands.currentIndexChanged.connect(self._on_quick_command)
        quick_layout.addWidget(self.quick_commands)
        
        layout.addLayout(quick_layout)
        
        self.setLayout(layout)
        
        # Add welcome message
        self.append_output("Console ready. Connect to laser to start sending commands.", "info")
        
        # Set focus policy so console can receive focus
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def showEvent(self, event):
        """When console is shown, focus the input field."""
        super().showEvent(event)
        # Give input field focus when console becomes visible
        self.input.setFocus()
    
    def _send_command(self):
        """Send command from input field."""
        command = self.input.text().strip()
        if not command:
            return
        
        # Add to history
        if not self._command_history or self._command_history[-1] != command:
            self._command_history.append(command)
        self._history_index = len(self._command_history)
        
        # Display command
        self.append_output(f"> {command}", "command")
        
        # Emit signal
        self.command_sent.emit(command)
        
        # Clear input
        self.input.clear()
    
    def _on_quick_command(self, index):
        """Handle quick command selection."""
        if index == 0:  # "Select command..."
            return
        
        command = self.quick_commands.currentText().split(" - ")[0]
        self.input.setText(command)
        self.quick_commands.setCurrentIndex(0)  # Reset to "Select command..."
        self.input.setFocus()
    
    def _clear_output(self):
        """Clear the output area."""
        self.output.clear()
        self.append_output("Console cleared.", "info")
    
    def append_output(self, text: str, message_type: str = "normal"):
        """
        Append text to output area.
        
        Args:
            text: Text to append
            message_type: Type of message ("command", "response", "error", "info", "normal")
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Format based on type
        if message_type == "command":
            prefix = f"[{timestamp}] > "
            color = QColor(0, 150, 255)  # Blue
        elif message_type == "response":
            prefix = f"[{timestamp}] < "
            color = QColor(0, 200, 0)  # Green
        elif message_type == "error":
            prefix = f"[{timestamp}] ERROR: "
            color = QColor(255, 0, 0)  # Red
        elif message_type == "info":
            prefix = f"[{timestamp}] INFO: "
            color = QColor(150, 150, 150)  # Gray
        else:
            prefix = f"[{timestamp}] "
            color = QColor(0, 0, 0)  # Black
        
        # Create formatted text
        cursor = self.output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        
        format = QTextCharFormat()
        format.setForeground(color)
        cursor.setCharFormat(format)
        cursor.insertText(prefix + text + "\n")
        
        # Auto-scroll to bottom
        self.output.ensureCursorVisible()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press for command history navigation."""
        # Only handle if input field has focus
        if self.input.hasFocus():
            if event.key() == Qt.Key.Key_Up:
                if self._command_history and self._history_index > 0:
                    self._history_index -= 1
                    self.input.setText(self._command_history[self._history_index])
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Down:
                if self._command_history and self._history_index < len(self._command_history) - 1:
                    self._history_index += 1
                    self.input.setText(self._command_history[self._history_index])
                elif self._history_index >= len(self._command_history) - 1:
                    self._history_index = len(self._command_history)
                    self.input.clear()
                event.accept()
                return
        
        super().keyPressEvent(event)

