"""
Connection Dialog for Laser Controller

Allows user to select serial port and connection settings.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QDialogButtonBox, QFormLayout, QSpinBox
)
from PyQt6.QtCore import Qt

from ...laser.controller import LaserController


class ConnectionDialog(QDialog):
    """Dialog for connecting to laser controller."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to Laser")
        self.setModal(True)
        
        self.port = None
        self.baudrate = 115200
        
        self._init_ui()
        self._refresh_ports()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout()
        
        # Form layout
        form = QFormLayout()
        
        # Port selection
        self.port_combo = QComboBox()
        self.port_combo.setEditable(False)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_ports)
        
        port_layout = QHBoxLayout()
        port_layout.addWidget(self.port_combo)
        port_layout.addWidget(refresh_btn)
        
        form.addRow("Port:", port_layout)
        
        # Baudrate
        self.baudrate_spin = QSpinBox()
        self.baudrate_spin.setRange(9600, 1152000)
        self.baudrate_spin.setValue(115200)
        self.baudrate_spin.setSingleStep(9600)
        form.addRow("Baudrate:", self.baudrate_spin)
        
        layout.addLayout(form)
        
        # Status label
        self.status_label = QLabel("Select a port and click Connect")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Connect")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        self.resize(400, 150)
    
    def _refresh_ports(self):
        """Refresh the list of available serial ports."""
        self.port_combo.clear()
        
        try:
            ports = LaserController.list_ports()
            
            if not ports:
                self.port_combo.addItem("No ports available")
                self.status_label.setText(
                    "No serial ports found.\n\n"
                    "Make sure your laser is:\n"
                    "- Connected via USB\n"
                    "- Powered on\n"
                    "- Driver installed\n\n"
                    "Check Device Manager for COM ports."
                )
                return
            
            for port_info in ports:
                display = f"{port_info['port']} - {port_info['description']}"
                self.port_combo.addItem(display, port_info['port'])
            
            self.status_label.setText(f"Found {len(ports)} port(s). Select one to connect.")
        except Exception as e:
            self.port_combo.addItem("Error listing ports")
            self.status_label.setText(f"Error listing ports: {str(e)}")
    
    def accept(self):
        """Handle accept button."""
        if self.port_combo.currentData():
            self.port = self.port_combo.currentData()
            self.baudrate = self.baudrate_spin.value()
            super().accept()
        else:
            self.status_label.setText("Please select a port")
    
    def get_connection_info(self):
        """Get connection information."""
        return self.port, self.baudrate

