"""
Laser Panel - Dock widget for laser control and settings.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QDoubleSpinBox, QSpinBox, QCheckBox,
    QProgressBar, QListWidget, QListWidgetItem, QMessageBox,
    QTabWidget, QGridLayout, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QKeySequence

from ...laser.controller import ConnectionState, JobState
from ...laser.job_manager import JobPriority
from ..widgets.console_widget import ConsoleWidget


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
        if not self._current_job:
            self.job_status_label.setText("No job running")
            self.progress_bar.setValue(0)
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            return
        
        job = self._current_job
        
        if job.status == JobState.RUNNING:
            self.job_status_label.setText(f"Running: {job.name}")
            self.job_status_label.setStyleSheet("font-weight: bold; color: green;")
            self.progress_bar.setValue(int(job.progress))
            self.pause_btn.setEnabled(True)
            self.resume_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        elif job.status == JobState.PAUSED:
            self.job_status_label.setText(f"Paused: {job.name}")
            self.job_status_label.setStyleSheet("font-weight: bold; color: orange;")
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
            self.job_status_label.setText(f"Error: {job.name}")
            self.job_status_label.setStyleSheet("font-weight: bold; color: red;")
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
        else:
            self.job_status_label.setText(f"Queued: {job.name}")
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
