"""
Laser Panel - Dock widget for laser control and settings.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QDoubleSpinBox, QSpinBox, QCheckBox,
    QProgressBar, QListWidget, QListWidgetItem, QMessageBox,
    QTabWidget, QGridLayout, QScrollArea, QComboBox, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QKeySequence

from ...laser.controller import ConnectionState, JobState
from ...laser.job_manager import JobPriority
from ...laser.gcode_generator import StartFrom, JobOrigin
from ..widgets.console_widget import ConsoleWidget
from ..widgets.gcode_preview_widget import GCodePreviewWidget


class LaserPanel(QWidget):
    """Panel for laser control and settings."""
    
    # Signals
    connect_requested = pyqtSignal()
    disconnect_requested = pyqtSignal()
    home_requested = pyqtSignal()
    set_home_requested = pyqtSignal()
    abort_home_requested = pyqtSignal()
    frame_requested = pyqtSignal()
    start_job_requested = pyqtSignal()
    pause_job_requested = pyqtSignal()
    resume_job_requested = pyqtSignal()
    stop_job_requested = pyqtSignal()
    jog_requested = pyqtSignal(float, float, float)  # x, y, z movement
    console_command = pyqtSignal(str)  # Command from console
    
    def __init__(self):
        super().__init__()
        self._controller = None
        self._job_manager = None
        self._current_job = None
        self._jog_speed = 1000.0  # mm/min
        self._jog_distance = 1.0  # mm per step
        # Cache for generated G-code to avoid regenerating
        self._cached_gcode = None
        self._cached_settings = None
        self._cached_document_id = None  # Track document version to invalidate cache
        self._cached_warnings = []
        self._init_ui()
    
    def set_controller(self, controller):
        """Set the laser controller."""
        self._controller = controller
        self._update_connection_status()
        
        # Connect console to controller
        if controller:
            controller.add_status_callback(self._on_controller_response)
    
    def set_job_manager(self, job_manager):
        """Set the job manager."""
        self._job_manager = job_manager
        if job_manager:
            job_manager.add_job_callback(self._on_job_update)
            self._update_job_queue()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # Create tab widget
        tabs = QTabWidget()
        
        # Control tab
        control_tab = self._create_control_tab()
        tabs.addTab(control_tab, "Control")
        
        # Console tab
        console_tab = self._create_console_tab()
        tabs.addTab(console_tab, "Console")
        
        # Preview tab
        preview_tab = self._create_preview_tab()
        tabs.addTab(preview_tab, "Preview")
        
        layout.addWidget(tabs)
        self.setLayout(layout)
    
    def _create_control_tab(self):
        """Create the control tab."""
        # Create scroll area for the control tab
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Create the content widget
        content_widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Connection group
        conn_group = QGroupBox("Connection")
        conn_layout = QVBoxLayout()
        
        self.connection_status = QLabel("Disconnected")
        self.connection_status.setStyleSheet("font-weight: bold; color: red;")
        conn_layout.addWidget(self.connection_status)
        
        self.position_label = QLabel("Position: X: 0.00 Y: 0.00 Z: 0.00")
        conn_layout.addWidget(self.position_label)
        
        btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_requested.emit)
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.disconnect_requested.emit)
        self.disconnect_btn.setEnabled(False)
        self.home_btn = QPushButton("Home")
        self.home_btn.clicked.connect(self.home_requested.emit)
        self.home_btn.setEnabled(False)
        self.set_home_btn = QPushButton("Set Home")
        self.set_home_btn.clicked.connect(self.set_home_requested.emit)
        self.set_home_btn.setEnabled(False)
        self.set_home_btn.setToolTip("Set current position as home (0,0,0) without homing sequence")
        self.abort_home_btn = QPushButton("Stop Home")
        self.abort_home_btn.clicked.connect(self.abort_home_requested.emit)
        self.abort_home_btn.setEnabled(False)
        self.abort_home_btn.setToolTip("Abort/stop the current homing sequence")
        self.abort_home_btn.setStyleSheet("background-color: #ff6b6b; color: white;")
        self.frame_btn = QPushButton("Frame")
        self.frame_btn.clicked.connect(self.frame_requested.emit)
        self.frame_btn.setEnabled(False)
        self.frame_btn.setToolTip("Trace the outline of the design (laser will NOT be enabled)")
        
        btn_layout.addWidget(self.connect_btn)
        btn_layout.addWidget(self.disconnect_btn)
        btn_layout.addWidget(self.home_btn)
        btn_layout.addWidget(self.set_home_btn)
        btn_layout.addWidget(self.abort_home_btn)
        btn_layout.addWidget(self.frame_btn)
        conn_layout.addLayout(btn_layout)
        
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)
        
        # Jog control group
        jog_group = QGroupBox("Manual Movement (Jog)")
        jog_layout = QVBoxLayout()
        
        # Jog settings
        jog_settings = QHBoxLayout()
        jog_settings.addWidget(QLabel("Speed:"))
        self.jog_speed_spin = QDoubleSpinBox()
        self.jog_speed_spin.setRange(100, 10000)
        self.jog_speed_spin.setValue(1000)
        self.jog_speed_spin.setSuffix(" mm/min")
        self.jog_speed_spin.valueChanged.connect(lambda v: setattr(self, '_jog_speed', v))
        jog_settings.addWidget(self.jog_speed_spin)
        
        jog_settings.addWidget(QLabel("Step:"))
        self.jog_step_spin = QDoubleSpinBox()
        self.jog_step_spin.setRange(0.1, 100)
        self.jog_step_spin.setValue(1.0)
        self.jog_step_spin.setSuffix(" mm")
        self.jog_step_spin.setDecimals(1)
        self.jog_step_spin.valueChanged.connect(lambda v: setattr(self, '_jog_distance', v))
        jog_settings.addWidget(self.jog_step_spin)
        
        jog_layout.addLayout(jog_settings)
        
        # Jog buttons (arrow key layout)
        jog_buttons = QGridLayout()
        
        # Create arrow buttons
        self.jog_up_btn = QPushButton("↑")
        self.jog_up_btn.setMaximumWidth(50)
        self.jog_up_btn.clicked.connect(lambda: self._jog(0, self._jog_distance, 0))
        self.jog_up_btn.setEnabled(False)
        self.jog_up_btn.setToolTip("Move Y+ (Up Arrow)")
        
        self.jog_down_btn = QPushButton("↓")
        self.jog_down_btn.setMaximumWidth(50)
        self.jog_down_btn.clicked.connect(lambda: self._jog(0, -self._jog_distance, 0))
        self.jog_down_btn.setEnabled(False)
        self.jog_down_btn.setToolTip("Move Y- (Down Arrow)")
        
        self.jog_left_btn = QPushButton("←")
        self.jog_left_btn.setMaximumWidth(50)
        self.jog_left_btn.clicked.connect(lambda: self._jog(-self._jog_distance, 0, 0))
        self.jog_left_btn.setEnabled(False)
        self.jog_left_btn.setToolTip("Move X- (Left Arrow)")
        
        self.jog_right_btn = QPushButton("→")
        self.jog_right_btn.setMaximumWidth(50)
        self.jog_right_btn.clicked.connect(lambda: self._jog(self._jog_distance, 0, 0))
        self.jog_right_btn.setEnabled(False)
        self.jog_right_btn.setToolTip("Move X+ (Right Arrow)")
        
        self.jog_z_up_btn = QPushButton("Z+")
        self.jog_z_up_btn.setMaximumWidth(50)
        self.jog_z_up_btn.clicked.connect(lambda: self._jog(0, 0, self._jog_distance))
        self.jog_z_up_btn.setEnabled(False)
        self.jog_z_up_btn.setToolTip("Move Z+ (Page Up)")
        
        self.jog_z_down_btn = QPushButton("Z-")
        self.jog_z_down_btn.setMaximumWidth(50)
        self.jog_z_down_btn.clicked.connect(lambda: self._jog(0, 0, -self._jog_distance))
        self.jog_z_down_btn.setEnabled(False)
        self.jog_z_down_btn.setToolTip("Move Z- (Page Down)")
        
        # Arrange in grid (arrow key layout)
        #     ↑
        # ←  ○  →
        #     ↓
        jog_buttons.addWidget(self.jog_up_btn, 0, 1)
        jog_buttons.addWidget(self.jog_left_btn, 1, 0)
        jog_buttons.addWidget(QLabel(""), 1, 1)  # Center placeholder
        jog_buttons.addWidget(self.jog_right_btn, 1, 2)
        jog_buttons.addWidget(self.jog_down_btn, 2, 1)
        
        # Z axis buttons
        z_layout = QHBoxLayout()
        z_layout.addWidget(QLabel("Z:"))
        z_layout.addWidget(self.jog_z_up_btn)
        z_layout.addWidget(self.jog_z_down_btn)
        z_layout.addStretch()
        
        jog_layout.addLayout(jog_buttons)
        jog_layout.addLayout(z_layout)
        
        jog_group.setLayout(jog_layout)
        layout.addWidget(jog_group)
        
        # Job control group
        job_group = QGroupBox("Job Control")
        job_layout = QVBoxLayout()
        
        self.job_status_label = QLabel("No job running")
        self.job_status_label.setStyleSheet("font-weight: bold;")
        job_layout.addWidget(self.job_status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        job_layout.addWidget(self.progress_bar)
        
        job_btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_job_requested.emit)
        self.start_btn.setEnabled(False)
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.pause_job_requested.emit)
        self.pause_btn.setEnabled(False)
        self.resume_btn = QPushButton("Resume")
        self.resume_btn.clicked.connect(self.resume_job_requested.emit)
        self.resume_btn.setEnabled(False)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_job_requested.emit)
        self.stop_btn.setEnabled(False)
        
        job_btn_layout.addWidget(self.start_btn)
        job_btn_layout.addWidget(self.pause_btn)
        job_btn_layout.addWidget(self.resume_btn)
        job_btn_layout.addWidget(self.stop_btn)
        job_layout.addLayout(job_btn_layout)
        
        job_group.setLayout(job_layout)
        layout.addWidget(job_group)
        
        # Job Start Settings
        start_group = QGroupBox("Job Start Settings")
        start_layout = QVBoxLayout()
        
        # Start From dropdown
        start_from_layout = QFormLayout()
        self.start_from_combo = QComboBox()
        self.start_from_combo.addItem("Home", StartFrom.HOME)
        self.start_from_combo.addItem("Current Position", StartFrom.CURRENT_POSITION)
        self.start_from_combo.setCurrentIndex(0)  # Default to Home
        self.start_from_combo.setToolTip(
            "Home: Start from machine home (0,0,0) - uses absolute coordinates\n"
            "Current Position: Start from wherever laser currently is - uses relative coordinates"
        )
        start_from_layout.addRow("Start From:", self.start_from_combo)
        start_layout.addLayout(start_from_layout)
        
        # Job Origin grid (3x3)
        origin_label = QLabel("Job Origin:")
        start_layout.addWidget(origin_label)
        
        # Create 3x3 grid of radio buttons
        origin_grid = QGridLayout()
        origin_grid.setSpacing(3)
        self.job_origin_group = QButtonGroup()
        
        # Job origin positions (top to bottom, left to right)
        origins = [
            (JobOrigin.TOP_LEFT, 0, 0), (JobOrigin.TOP_CENTER, 0, 1), (JobOrigin.TOP_RIGHT, 0, 2),
            (JobOrigin.MIDDLE_LEFT, 1, 0), (JobOrigin.CENTER, 1, 1), (JobOrigin.MIDDLE_RIGHT, 1, 2),
            (JobOrigin.BOTTOM_LEFT, 2, 0), (JobOrigin.BOTTOM_CENTER, 2, 1), (JobOrigin.BOTTOM_RIGHT, 2, 2)
        ]
        
        for job_origin, row, col in origins:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setFixedSize(35, 35)
            # Set style to show checked state
            btn.setStyleSheet("""
                QPushButton {
                    border: 2px solid #666;
                    border-radius: 3px;
                    background-color: #444;
                }
                QPushButton:checked {
                    background-color: #0066cc;
                    border: 2px solid #0088ff;
                }
                QPushButton:hover {
                    border: 2px solid #888;
                }
            """)
            tooltip_text = job_origin.value.replace("-", " ").title()
            btn.setToolTip(tooltip_text)
            self.job_origin_group.addButton(btn, list(JobOrigin).index(job_origin))
            origin_grid.addWidget(btn, row, col)
            
            # Set center as default
            if job_origin == JobOrigin.CENTER:
                btn.setChecked(True)
        
        start_layout.addLayout(origin_grid)
        start_layout.addWidget(QLabel("Select which point of the design\ncorresponds to the start position"))
        
        start_group.setLayout(start_layout)
        layout.addWidget(start_group)
        
        # Job queue
        queue_group = QGroupBox("Job Queue")
        queue_layout = QVBoxLayout()
        
        self.queue_list = QListWidget()
        self.queue_list.setMaximumHeight(80)
        queue_layout.addWidget(self.queue_list)
        
        queue_group.setLayout(queue_layout)
        layout.addWidget(queue_group)
        
        # Machine work area group
        workarea_group = QGroupBox("Machine Work Area")
        workarea_layout = QFormLayout()
        
        self.workarea_x_spin = QDoubleSpinBox()
        self.workarea_x_spin.setRange(10, 2000)
        self.workarea_x_spin.setValue(400)
        self.workarea_x_spin.setSuffix(" mm")
        self.workarea_x_spin.setDecimals(1)
        workarea_layout.addRow("X (Width):", self.workarea_x_spin)
        
        self.workarea_y_spin = QDoubleSpinBox()
        self.workarea_y_spin.setRange(10, 2000)
        self.workarea_y_spin.setValue(400)
        self.workarea_y_spin.setSuffix(" mm")
        self.workarea_y_spin.setDecimals(1)
        workarea_layout.addRow("Y (Height):", self.workarea_y_spin)
        
        self.workarea_z_spin = QDoubleSpinBox()
        self.workarea_z_spin.setRange(1, 500)
        self.workarea_z_spin.setValue(50)
        self.workarea_z_spin.setSuffix(" mm")
        self.workarea_z_spin.setDecimals(1)
        workarea_layout.addRow("Z (Depth):", self.workarea_z_spin)
        
        workarea_btn_layout = QHBoxLayout()
        self.detect_workarea_btn = QPushButton("Auto-Detect")
        self.detect_workarea_btn.setToolTip("Query GRBL settings to auto-detect work area")
        self.detect_workarea_btn.clicked.connect(self._on_detect_workarea)
        self.detect_workarea_btn.setEnabled(False)
        workarea_btn_layout.addWidget(self.detect_workarea_btn)
        
        self.apply_workarea_btn = QPushButton("Apply")
        self.apply_workarea_btn.setToolTip("Apply work area settings")
        self.apply_workarea_btn.clicked.connect(self._on_apply_workarea)
        self.apply_workarea_btn.setEnabled(False)
        workarea_btn_layout.addWidget(self.apply_workarea_btn)
        
        workarea_layout.addRow("", workarea_btn_layout)
        workarea_group.setLayout(workarea_layout)
        layout.addWidget(workarea_group)
        
        # Max Spindle Speed ($30) - CRITICAL for correct power output
        spindle_group = QGroupBox("Power Settings")
        spindle_layout = QFormLayout()
        
        self.max_spindle_spin = QSpinBox()
        self.max_spindle_spin.setRange(1, 65535)
        self.max_spindle_spin.setValue(1000)  # GRBL default
        self.max_spindle_spin.setToolTip(
            "Max spindle speed ($30 setting in GRBL)\n"
            "CRITICAL: Must match your laser controller's $30 setting!\n"
            "Common values:\n"
            "  - 255: Some 8-bit PWM controllers\n"
            "  - 1000: GRBL default (most common)\n"
            "  - 10000: Some high-resolution controllers\n"
            "If power seems weak, check this value matches your $30 setting."
        )
        spindle_layout.addRow("Max Spindle ($30):", self.max_spindle_spin)
        
        spindle_info_label = QLabel("50% power at $30=1000 sends S500")
        spindle_info_label.setStyleSheet("color: #888; font-size: 10px;")
        spindle_layout.addRow("", spindle_info_label)
        self._spindle_info_label = spindle_info_label
        
        # Update info label when spindle value changes
        self.max_spindle_spin.valueChanged.connect(self._update_spindle_info)
        
        spindle_group.setLayout(spindle_layout)
        layout.addWidget(spindle_group)
        
        content_widget.setLayout(layout)
        scroll.setWidget(content_widget)
        return scroll
    
    def _create_console_tab(self):
        """Create the console tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.console = ConsoleWidget()
        self.console.command_sent.connect(self._on_console_command)
        # Make console fill the tab
        layout.addWidget(self.console)
        
        widget.setLayout(layout)
        return widget
    
    def _create_preview_tab(self):
        """Create the G-code preview tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Controls
        controls = QHBoxLayout()
        self.generate_preview_btn = QPushButton("Generate Preview")
        self.generate_preview_btn.setToolTip("Generate burn preview from current document")
        controls.addWidget(self.generate_preview_btn)
        
        # Connect button if document is already set
        if hasattr(self, '_preview_document') and self._preview_document:
            self.generate_preview_btn.clicked.connect(
                lambda: self.generate_preview_from_document(self._preview_document)
            )
        
        load_preview_btn = QPushButton("Load G-Code File...")
        load_preview_btn.setToolTip("Load G-code file to preview")
        load_preview_btn.clicked.connect(self._load_gcode_preview)
        controls.addWidget(load_preview_btn)
        
        controls.addStretch()
        layout.addLayout(controls)
        
        # Create preview widget
        self.preview_widget = GCodePreviewWidget()
        layout.addWidget(self.preview_widget)
        
        widget.setLayout(layout)
        return widget
    
    def _load_gcode_preview(self):
        """Load G-code file for preview."""
        from PyQt6.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Load G-Code File",
            "",
            "G-Code Files (*.gcode *.nc *.ngc);;All Files (*)"
        )
        if filepath and hasattr(self, 'preview_widget'):
            self.preview_widget.load_gcode(filepath)
    
    def set_document_for_preview(self, document):
        """Set document for preview generation."""
        self._preview_document = document
        if hasattr(self, 'generate_preview_btn'):
            # Disconnect any existing connections to avoid duplicates
            try:
                self.generate_preview_btn.clicked.disconnect()
            except TypeError:
                # No connections to disconnect
                pass
            # Connect to use the stored document reference
            self.generate_preview_btn.clicked.connect(
                lambda: self.generate_preview_from_document(self._preview_document)
            )
    
    def _jog(self, x: float, y: float, z: float):
        """Execute a jog movement."""
        if not self._controller:
            return
        
        self.jog_requested.emit(x, y, z)
    
    def _on_console_command(self, command: str):
        """Handle command from console."""
        self.console_command.emit(command)
    
    def _on_controller_response(self, status):
        """Handle controller status updates (for console display)."""
        # This will be called for status updates
        # We can parse and display in console if needed
        pass
    
    def append_console_response(self, text: str, message_type: str = "response"):
        """Append response to console."""
        if hasattr(self, 'console'):
            self.console.append_output(text, message_type)
    
    def _update_connection_status(self):
        """Update connection status display."""
        # Ensure this runs on the main thread
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._do_update_connection_status)
    
    def _do_update_connection_status(self):
        """Actually update connection status display (called on main thread)."""
        if not self._controller:
            self.connection_status.setText("Disconnected")
            self.connection_status.setStyleSheet("font-weight: bold; color: red;")
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self.home_btn.setEnabled(False)
            self.frame_btn.setEnabled(False)
            self._enable_jog_buttons(False)
            return
        
        status = self._controller.status
        
        if status.state == ConnectionState.CONNECTED:
            self.connection_status.setText("Connected")
            self.connection_status.setStyleSheet("font-weight: bold; color: green;")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.home_btn.setEnabled(True)
            self.set_home_btn.setEnabled(True)
            self.abort_home_btn.setEnabled(False)  # Only enable when homing
            self.frame_btn.setEnabled(True)
            self.start_btn.setEnabled(True)
            self._enable_jog_buttons(True)
            self.detect_workarea_btn.setEnabled(True)
            self.apply_workarea_btn.setEnabled(True)
            
            # Update work area display from controller
            if self._controller and hasattr(self._controller, 'get_work_area'):
                x, y, z = self._controller.get_work_area()
                self.workarea_x_spin.setValue(x)
                self.workarea_y_spin.setValue(y)
                self.workarea_z_spin.setValue(z)
        elif status.state == ConnectionState.BUSY:
            # Check if it's homing
            if hasattr(self._controller, '_homing_in_progress') and self._controller._homing_in_progress:
                self.connection_status.setText("Homing in progress...")
                self.connection_status.setStyleSheet("font-weight: bold; color: orange;")
                self.home_btn.setEnabled(False)
                self.abort_home_btn.setEnabled(True)
            else:
                self.connection_status.setText("Busy")
                self.connection_status.setStyleSheet("font-weight: bold; color: orange;")
                self.abort_home_btn.setEnabled(False)
        elif status.state == ConnectionState.CONNECTING:
            self.connection_status.setText("Connecting...")
            self.connection_status.setStyleSheet("font-weight: bold; color: orange;")
            self.connect_btn.setEnabled(False)
            self.set_home_btn.setEnabled(False)
            self.abort_home_btn.setEnabled(False)
            self._enable_jog_buttons(False)
        elif status.state == ConnectionState.ERROR or status.state == ConnectionState.ALARM:
            self.connection_status.setText(f"Error: {status.error_message}")
            self.connection_status.setStyleSheet("font-weight: bold; color: red;")
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self._enable_jog_buttons(False)
        else:
            self.connection_status.setText("Disconnected")
            self.connection_status.setStyleSheet("font-weight: bold; color: red;")
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self._enable_jog_buttons(False)
        
        # Update position
        self.position_label.setText(
            f"Position: X: {status.position_x:.2f} Y: {status.position_y:.2f} Z: {status.position_z:.2f}"
        )
    
    def _enable_jog_buttons(self, enabled: bool):
        """Enable or disable jog buttons."""
        self.jog_up_btn.setEnabled(enabled)
        self.jog_down_btn.setEnabled(enabled)
        self.jog_left_btn.setEnabled(enabled)
        self.jog_right_btn.setEnabled(enabled)
        self.jog_z_up_btn.setEnabled(enabled)
        self.jog_z_down_btn.setEnabled(enabled)
    
    def _update_job_status(self):
        """Update job status display."""
        # Get current job from job manager if available
        if self._job_manager:
            current_job = self._job_manager.get_current_job()
            if current_job:
                self._current_job = current_job
        
        if not self._current_job:
            self.job_status_label.setText("No job running")
            self.progress_bar.setValue(0)
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            return
        
        job = self._current_job
        
        if job.status == JobState.RUNNING:
            self.job_status_label.setText(f"Running: {job.name} ({job.progress:.1f}%)")
            self.job_status_label.setStyleSheet("font-weight: bold; color: green;")
            self.progress_bar.setValue(int(job.progress))
            self.pause_btn.setEnabled(True)
            self.resume_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        elif job.status == JobState.PAUSED:
            self.job_status_label.setText(f"Paused: {job.name} ({job.progress:.1f}%)")
            self.job_status_label.setStyleSheet("font-weight: bold; color: orange;")
            self.progress_bar.setValue(int(job.progress))
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
        elif job.status == JobState.COMPLETED:
            self.job_status_label.setText(f"Completed: {job.name}")
            self.job_status_label.setStyleSheet("font-weight: bold; color: blue;")
            self.progress_bar.setValue(100)
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
        elif job.status == JobState.ERROR:
            error_msg = job.error_message if job.error_message else "Unknown error"
            self.job_status_label.setText(f"Error: {job.name} - {error_msg}")
            self.job_status_label.setStyleSheet("font-weight: bold; color: red;")
            self.progress_bar.setValue(int(job.progress))
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
        elif job.status == JobState.CANCELLED:
            self.job_status_label.setText(f"Cancelled: {job.name}")
            self.job_status_label.setStyleSheet("font-weight: bold; color: gray;")
            self.progress_bar.setValue(int(job.progress))
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
        else:
            self.job_status_label.setText(f"Queued: {job.name}")
            self.progress_bar.setValue(0)
            self.job_status_label.setStyleSheet("font-weight: bold; color: gray;")
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
    
    def _update_job_queue(self):
        """Update job queue display."""
        self.queue_list.clear()
        
        if not self._job_manager:
            return
        
        queue = self._job_manager.get_queue()
        current = self._job_manager.get_current_job()
        
        if current:
            item = QListWidgetItem(f"▶ {current.name} (Running)")
            item.setForeground(QColor("green"))
            self.queue_list.addItem(item)
        
        for job in queue:
            priority_str = job.priority.name if job.priority else "NORMAL"
            item = QListWidgetItem(f"○ {job.name} ({priority_str})")
            self.queue_list.addItem(item)
    
    def _on_job_update(self, job):
        """Handle job status update. Thread-safe version using QTimer."""
        # Use QTimer.singleShot to ensure UI updates happen on the main thread
        # This avoids "QBasicTimer can only be used with threads started with QThread" errors
        from PyQt6.QtCore import QTimer
        
        def update_ui():
            if job == self._current_job or (not self._current_job and job.status == JobState.RUNNING):
                self._current_job = job
            elif job.status in (JobState.COMPLETED, JobState.CANCELLED, JobState.ERROR):
                if job == self._current_job:
                    self._current_job = None
            
            self._update_job_status()
            self._update_job_queue()
        
        # Schedule the update on the main thread
        QTimer.singleShot(0, update_ui)
    
    def update_controller_status(self):
        """Update controller status (called from main window)."""
        self._update_connection_status()
    
    def get_laser_settings(self):
        """Get default laser settings (settings are now managed per-layer)."""
        from ...core.shapes import LaserSettings
        
        # Return default settings - actual settings are managed in layers panel
        return LaserSettings()
    
    def _update_spindle_info(self, value):
        """Update the spindle info label when value changes."""
        # Use default 50% power for example calculation
        power_percent = 50
        s_value = int(round((power_percent / 100.0) * value))
        if hasattr(self, '_spindle_info_label'):
            self._spindle_info_label.setText(f"{power_percent:.0f}% power at $30={value} sends S{s_value}")
    
    def get_max_spindle_speed(self):
        """Get the configured max spindle speed."""
        return self.max_spindle_spin.value()
    
    def set_max_spindle_speed(self, value: int):
        """Set the max spindle speed in the UI."""
        self.max_spindle_spin.setValue(value)
        self._update_spindle_info(value)
    
    def get_start_from(self) -> StartFrom:
        """Get the selected start from option."""
        return self.start_from_combo.currentData()
    
    def get_job_origin(self) -> JobOrigin:
        """Get the selected job origin."""
        checked_id = self.job_origin_group.checkedId()
        if checked_id >= 0:
            return list(JobOrigin)[checked_id]
        return JobOrigin.CENTER  # Default
    
    def _on_detect_workarea(self):
        """Auto-detect work area from GRBL settings."""
        if not self._controller:
            return
        
        if hasattr(self._controller, '_detect_work_area'):
            self._controller._detect_work_area()
            # Update spin boxes with detected values
            if hasattr(self._controller, 'get_work_area'):
                x, y, z = self._controller.get_work_area()
                self.workarea_x_spin.setValue(x)
                self.workarea_y_spin.setValue(y)
                self.workarea_z_spin.setValue(z)
        
        # Also detect and update max spindle speed
        if hasattr(self._controller, '_detect_max_spindle_speed'):
            self._controller._detect_max_spindle_speed()
            if hasattr(self._controller, 'get_max_spindle_speed'):
                spindle = self._controller.get_max_spindle_speed()
                self.max_spindle_spin.setValue(spindle)
        
        QMessageBox.information(
            self,
            "Settings Detected",
            f"GRBL settings detected:\n"
            f"Work Area: {self.workarea_x_spin.value():.1f} x {self.workarea_y_spin.value():.1f} x {self.workarea_z_spin.value():.1f} mm\n"
            f"Max Spindle ($30): {self.max_spindle_spin.value()}"
        )
    
    def _on_apply_workarea(self):
        """Apply work area settings to controller."""
        if not self._controller:
            return
        
        x = self.workarea_x_spin.value()
        y = self.workarea_y_spin.value()
        z = self.workarea_z_spin.value()
        
        if hasattr(self._controller, 'set_work_area'):
            self._controller.set_work_area(x, y, z)
            QMessageBox.information(
                self,
                "Work Area Updated",
                f"Work area set to:\n"
                f"X: {x:.1f}mm\n"
                f"Y: {y:.1f}mm\n"
                f"Z: {z:.1f}mm"
            )
    
    def apply_material(self, material):
        """Apply material settings (no-op - settings are now managed per-layer)."""
        # Material settings are now applied directly to layers via the layers panel
        # This method is kept for compatibility but does nothing
        pass
    
    def update_preview_from_gcode(self, gcode_content: str):
        """Update preview from G-code content."""
        if hasattr(self, 'preview_widget'):
            # Save to temp file and load it
            import tempfile
            import os
            
            # On Windows, we need to close the file before reading it
            # Use a regular file write instead of NamedTemporaryFile
            temp_path = None
            try:
                # Create temp file with explicit encoding
                fd, temp_path = tempfile.mkstemp(suffix='.gcode', text=True)
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(gcode_content)
                
                # File is now closed, safe to read on Windows
                self.preview_widget.load_gcode(temp_path)
            finally:
                # Clean up temp file
                if temp_path:
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
    
    def update_preview_from_file(self, filepath: str):
        """Update preview widget from G-code file."""
        if hasattr(self, 'preview_widget'):
            self.preview_widget.load_gcode(filepath)
    
    def get_cached_gcode(self, document, settings):
        """
        Get cached G-code if available and settings match.
        
        Args:
            document: The document to check cache for
            settings: GCodeSettings to match against cache
        
        Returns:
            (gcode, warnings) tuple if cache is valid, None otherwise
        """
        document_fingerprint = self._get_document_fingerprint(document)
        if (self._cached_gcode and 
            self._cached_document_id == document_fingerprint and
            self._cached_settings and
            self._cached_settings.start_from == settings.start_from and
            self._cached_settings.job_origin == settings.job_origin):
            return self._cached_gcode, self._cached_warnings
        return None
    
    def invalidate_gcode_cache(self):
        """Invalidate the G-code cache (call when document changes)."""
        self._cached_gcode = None
        self._cached_settings = None
        self._cached_document_id = None
        self._cached_warnings = []
    
    def _get_document_fingerprint(self, document):
        """
        Generate a fingerprint/hash of document content that affects G-code generation.
        
        This changes when the document is modified, allowing cache invalidation.
        """
        import hashlib
        
        # Collect all relevant document state that affects G-code
        fingerprint_data = []
        
        # Document dimensions
        fingerprint_data.append(f"size:{document.width:.2f}x{document.height:.2f}")
        
        # Layer information (visibility, cut_order, shape count)
        for layer in document.layers:
            layer_info = f"layer:{layer.name}:v{layer.visible}:o{layer.cut_order}:s{len(layer.shapes)}"
            fingerprint_data.append(layer_info)
            
            # Shape information (visibility, type, basic properties)
            for shape in layer.shapes:
                shape_type = type(shape).__name__
                shape_visible = shape.visible
                # Get bounding box for shape position/size
                try:
                    bbox = shape.get_bounding_box()
                    shape_info = f"shape:{shape_type}:v{shape_visible}:{bbox.min_x:.2f},{bbox.min_y:.2f},{bbox.max_x:.2f},{bbox.max_y:.2f}"
                except:
                    shape_info = f"shape:{shape_type}:v{shape_visible}"
                fingerprint_data.append(shape_info)
        
        # Cylinder settings
        if document.cylinder_params:
            fingerprint_data.append(f"cylinder:{document.cylinder_params.diameter:.2f}:{document.cylinder_params.max_angle:.2f}")
        fingerprint_data.append(f"cylinder_power:{document.cylinder_compensate_power}")
        fingerprint_data.append(f"cylinder_z:{document.cylinder_compensate_z}")
        
        # Create hash
        fingerprint_str = "|".join(fingerprint_data)
        return hashlib.md5(fingerprint_str.encode()).hexdigest()
    
    def generate_preview_from_document(self, document):
        """Generate preview from document without saving G-code file."""
        print(f"DEBUG: generate_preview_from_document called with document: {document}")
        
        if not hasattr(self, 'preview_widget'):
            QMessageBox.warning(
                self,
                "Preview Error",
                "Preview widget not initialized."
            )
            return
        
        if not document:
            QMessageBox.warning(
                self,
                "Preview Error",
                "No document available to generate preview."
            )
            return
        
        # Check if document has any visible shapes using get_design_bounds()
        # This is more robust than manually checking paths
        design_bounds = document.get_design_bounds()
        if design_bounds is None:
            # Provide more helpful error message
            total_layers = len(document.layers)
            total_shapes = sum(len(layer.shapes) for layer in document.layers)
            visible_layers = sum(1 for layer in document.layers if layer.visible)
            total_shapes_in_visible_layers = sum(len(layer.shapes) for layer in document.layers if layer.visible)
            
            QMessageBox.information(
                self,
                "No Content",
                f"Document has no visible shapes to preview.\n\n"
                f"Layers: {total_layers} total, {visible_layers} visible\n"
                f"Shapes: {total_shapes} total, {total_shapes_in_visible_layers} in visible layers\n\n"
                f"Make sure you have shapes in visible layers that can generate G-code."
            )
            return
        
        try:
            from ...laser.gcode_generator import GCodeGenerator, GCodeSettings
            
            # Use UI settings (same as export would use)
            settings = GCodeSettings()
            if hasattr(self, 'get_start_from'):
                settings.start_from = self.get_start_from()
            if hasattr(self, 'get_job_origin'):
                settings.job_origin = self.get_job_origin()
            
            # Check cache first using document fingerprint
            document_fingerprint = self._get_document_fingerprint(document)
            if (self._cached_gcode and 
                self._cached_document_id == document_fingerprint and
                self._cached_settings and
                self._cached_settings.start_from == settings.start_from and
                self._cached_settings.job_origin == settings.job_origin):
                print("Using cached G-code for preview")
                gcode = self._cached_gcode
                warnings = self._cached_warnings
            else:
                # Generate G-code in memory
                generator = GCodeGenerator(settings)
                gcode, warnings = generator.generate(document)
                
                # Cache the result
                self._cached_gcode = gcode
                self._cached_settings = settings
                self._cached_document_id = document_fingerprint
                self._cached_warnings = warnings
                print("Generated and cached new G-code")
            
            # Check if G-code was generated
            if not gcode or not gcode.strip():
                QMessageBox.warning(
                    self,
                    "Preview Error",
                    "G-code generation produced no output.\n\n"
                    "Check that your shapes are valid and visible."
                )
                return
            
            # Show warnings if any
            if warnings:
                warning_text = "\n".join(warnings[:5])  # Show first 5 warnings
                if len(warnings) > 5:
                    warning_text += f"\n... and {len(warnings) - 5} more"
                QMessageBox.warning(
                    self,
                    "G-code Generation Warnings",
                    f"The following warnings occurred:\n\n{warning_text}"
                )
            
            # Update preview from G-code content
            self.update_preview_from_gcode(gcode)
            
        except Exception as e:
            error_msg = str(e)
            import traceback
            traceback_str = traceback.format_exc()
            print(f"Error generating preview: {error_msg}")
            print(traceback_str)
            
            QMessageBox.critical(
                self,
                "Preview Generation Failed",
                f"Failed to generate preview:\n\n{error_msg}\n\n"
                "Check the console for detailed error information."
            )
