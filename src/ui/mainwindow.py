"""
Main Application Window for LaserBurn
"""

from PyQt6.QtWidgets import (
    QMainWindow, QToolBar, QDockWidget, QStatusBar,
    QMenuBar, QMenu, QFileDialog, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt, QSettings, QSize
from PyQt6.QtGui import QAction, QKeySequence, QActionGroup

from ..core.document import Document
from ..core.layer import Layer
from ..graphics import ToolType
from .canvas import LaserCanvas
import math
from .panels.layers_panel import LayersPanel
from .panels.properties_panel import PropertiesPanel
from .panels.laser_panel import LaserPanel
from .panels.materials_panel import MaterialsPanel
from .dialogs.connection_dialog import ConnectionDialog
from ..laser.grbl import GRBLController
from ..laser.job_manager import JobManager, JobPriority
from ..laser.gcode_generator import GCodeGenerator, GCodeSettings
from ..laser.controller import ConnectionState
import traceback
import time


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        self.document = Document(name="Untitled")
        self.document.add_layer(Layer(name="Layer 1"))
        
        self.setWindowTitle("LaserBurn - Laser Engraving Software")
        self.setMinimumSize(1200, 800)
        
        # Initialize laser components
        self._controller = None
        self._job_manager = None
        
        # Setup UI components
        self._create_actions()
        self._create_menus()
        self._create_toolbars()
        self._create_central_widget()
        self._create_dock_panels()
        self._create_status_bar()
        
        # Initialize laser system
        self._init_laser_system()
        
        # Load settings
        self._load_settings()
        
        # Connect signals
        self._connect_signals()
    
    def _create_actions(self):
        """Create all menu/toolbar actions."""
        
        # File actions
        self.action_new = QAction("&New", self)
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        self.action_new.setStatusTip("Create a new document")
        self.action_new.triggered.connect(self._on_new)
        
        self.action_open = QAction("&Open...", self)
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open.setStatusTip("Open an existing file")
        self.action_open.triggered.connect(self._on_open)
        
        self.action_save = QAction("&Save", self)
        self.action_save.setShortcut(QKeySequence.StandardKey.Save)
        self.action_save.setStatusTip("Save the current document")
        self.action_save.triggered.connect(self._on_save)
        
        self.action_save_as = QAction("Save &As...", self)
        self.action_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.action_save_as.triggered.connect(self._on_save_as)
        
        self.action_import = QAction("&Import...", self)
        self.action_import.setShortcut("Ctrl+I")
        self.action_import.setStatusTip("Import SVG, DXF, or image files")
        self.action_import.triggered.connect(self._on_import)
        
        self.action_export = QAction("&Export G-Code...", self)
        self.action_export.setShortcut("Ctrl+E")
        self.action_export.triggered.connect(self._on_export_gcode)
        
        self.action_exit = QAction("E&xit", self)
        self.action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_exit.triggered.connect(self.close)
        
        # Edit actions
        self.action_undo = QAction("&Undo", self)
        self.action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.action_undo.triggered.connect(self._on_undo)
        
        self.action_redo = QAction("&Redo", self)
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.action_redo.triggered.connect(self._on_redo)
        
        self.action_delete = QAction("&Delete", self)
        self.action_delete.setShortcut(QKeySequence.StandardKey.Delete)
        self.action_delete.triggered.connect(self._on_delete)
        
        self.action_select_all = QAction("Select &All", self)
        self.action_select_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        self.action_select_all.triggered.connect(self._on_select_all)
        
        # View actions
        self.action_zoom_in = QAction("Zoom &In", self)
        self.action_zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self.action_zoom_in.triggered.connect(self._on_zoom_in)
        
        self.action_zoom_out = QAction("Zoom &Out", self)
        self.action_zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self.action_zoom_out.triggered.connect(self._on_zoom_out)
        
        self.action_zoom_fit = QAction("Zoom to &Fit", self)
        self.action_zoom_fit.setShortcut("Ctrl+0")
        self.action_zoom_fit.triggered.connect(self._on_zoom_fit)
        
        self.action_workspace_size = QAction("&Workspace Size...", self)
        self.action_workspace_size.setStatusTip("Set workspace dimensions")
        self.action_workspace_size.triggered.connect(self._on_workspace_size)
        
        # Panel visibility actions
        self.action_show_layers = QAction("&Layers Panel", self)
        self.action_show_layers.setCheckable(True)
        self.action_show_layers.setChecked(True)
        self.action_show_layers.triggered.connect(self._toggle_layers_panel)
        
        self.action_show_properties = QAction("&Properties Panel", self)
        self.action_show_properties.setCheckable(True)
        self.action_show_properties.setChecked(True)
        self.action_show_properties.triggered.connect(self._toggle_properties_panel)
        
        self.action_show_laser = QAction("&Laser Panel", self)
        self.action_show_laser.setCheckable(True)
        self.action_show_laser.setChecked(True)
        self.action_show_laser.triggered.connect(self._toggle_laser_panel)
        
        self.action_show_materials = QAction("&Materials Panel", self)
        self.action_show_materials.setCheckable(True)
        self.action_show_materials.setChecked(True)
        self.action_show_materials.triggered.connect(self._toggle_materials_panel)
        
        # Transform actions
        self.action_mirror_horizontal = QAction("Mirror &Horizontal", self)
        self.action_mirror_horizontal.setShortcut("Ctrl+Shift+H")
        self.action_mirror_horizontal.setStatusTip("Mirror selected shapes horizontally")
        self.action_mirror_horizontal.triggered.connect(self._on_mirror_horizontal)
        
        self.action_mirror_vertical = QAction("Mirror &Vertical", self)
        self.action_mirror_vertical.setShortcut("Ctrl+Shift+V")
        self.action_mirror_vertical.setStatusTip("Mirror selected shapes vertically")
        self.action_mirror_vertical.triggered.connect(self._on_mirror_vertical)
        
        self.action_rotate_90 = QAction("Rotate &90°", self)
        self.action_rotate_90.setShortcut("Ctrl+R")
        self.action_rotate_90.setStatusTip("Rotate selected shapes 90 degrees")
        self.action_rotate_90.triggered.connect(lambda: self._on_rotate(math.pi / 2))
        
        self.action_rotate_180 = QAction("Rotate &180°", self)
        self.action_rotate_180.setStatusTip("Rotate selected shapes 180 degrees")
        self.action_rotate_180.triggered.connect(lambda: self._on_rotate(math.pi))
        
        # Cylinder engraving action
        self.action_cylinder_engraving = QAction("Cylinder &Engraving...", self)
        self.action_cylinder_engraving.setStatusTip("Configure cylinder engraving settings")
        self.action_cylinder_engraving.triggered.connect(self._on_cylinder_engraving)
        
        # Tool actions
        self.action_tool_select = QAction("&Select", self)
        self.action_tool_select.setShortcut("V")
        self.action_tool_select.setCheckable(True)
        self.action_tool_select.setChecked(True)
        self.action_tool_select.triggered.connect(
            lambda: self.canvas.set_tool(ToolType.SELECT)
        )
        
        self.action_tool_line = QAction("&Line", self)
        self.action_tool_line.setShortcut("L")
        self.action_tool_line.setCheckable(True)
        self.action_tool_line.triggered.connect(
            lambda: self.canvas.set_tool(ToolType.LINE)
        )
        
        self.action_tool_rect = QAction("&Rectangle", self)
        self.action_tool_rect.setShortcut("R")
        self.action_tool_rect.setCheckable(True)
        self.action_tool_rect.triggered.connect(
            lambda: self.canvas.set_tool(ToolType.RECTANGLE)
        )
        
        self.action_tool_ellipse = QAction("&Ellipse", self)
        self.action_tool_ellipse.setShortcut("E")
        self.action_tool_ellipse.setCheckable(True)
        self.action_tool_ellipse.triggered.connect(
            lambda: self.canvas.set_tool(ToolType.ELLIPSE)
        )
        
        self.action_tool_polygon = QAction("&Polygon", self)
        self.action_tool_polygon.setShortcut("P")
        self.action_tool_polygon.setCheckable(True)
        self.action_tool_polygon.triggered.connect(
            lambda: self.canvas.set_tool(ToolType.POLYGON)
        )
        
        self.action_tool_pen = QAction("&Pen", self)
        self.action_tool_pen.setShortcut("N")
        self.action_tool_pen.setCheckable(True)
        self.action_tool_pen.triggered.connect(
            lambda: self.canvas.set_tool(ToolType.PEN)
        )
        
        self.action_tool_text = QAction("&Text", self)
        self.action_tool_text.setShortcut("T")
        self.action_tool_text.setCheckable(True)
        self.action_tool_text.triggered.connect(
            lambda: self.canvas.set_tool(ToolType.TEXT)
        )
        
        # Create tool action group for mutual exclusivity
        self.tool_action_group = QActionGroup(self)
        self.tool_action_group.addAction(self.action_tool_select)
        self.tool_action_group.addAction(self.action_tool_line)
        self.tool_action_group.addAction(self.action_tool_rect)
        self.tool_action_group.addAction(self.action_tool_ellipse)
        self.tool_action_group.addAction(self.action_tool_polygon)
        self.tool_action_group.addAction(self.action_tool_pen)
        self.tool_action_group.addAction(self.action_tool_text)
        
        # Laser actions
        self.action_connect = QAction("&Connect Laser...", self)
        self.action_connect.setStatusTip("Connect to laser controller")
        self.action_connect.triggered.connect(self._on_connect_laser)
        
        self.action_disconnect = QAction("&Disconnect Laser", self)
        self.action_disconnect.setStatusTip("Disconnect from laser controller")
        self.action_disconnect.triggered.connect(self._on_disconnect_laser)
        self.action_disconnect.setEnabled(False)
        
        self.action_home = QAction("&Home", self)
        self.action_home.setShortcut("Ctrl+H")
        self.action_home.setStatusTip("Home the laser")
        self.action_home.triggered.connect(self._on_home)
        self.action_home.setEnabled(False)
        
        self.action_frame = QAction("&Frame", self)
        self.action_frame.setStatusTip("Trace the outline of the job")
        self.action_frame.triggered.connect(self._on_frame)
        self.action_frame.setEnabled(False)
        
        self.action_start_job = QAction("&Start Job", self)
        self.action_start_job.setShortcut("F5")
        self.action_start_job.setStatusTip("Start the laser job")
        self.action_start_job.triggered.connect(self._on_start_job)
        self.action_start_job.setEnabled(False)
        
        self.action_pause_job = QAction("&Pause Job", self)
        self.action_pause_job.setShortcut("F6")
        self.action_pause_job.setStatusTip("Pause the laser job")
        self.action_pause_job.triggered.connect(self._on_pause_job)
        self.action_pause_job.setEnabled(False)
        
        self.action_resume_job = QAction("&Resume Job", self)
        self.action_resume_job.setShortcut("F7")
        self.action_resume_job.setStatusTip("Resume the laser job")
        self.action_resume_job.triggered.connect(self._on_resume_job)
        self.action_resume_job.setEnabled(False)
        
        self.action_stop_job = QAction("&Stop Job", self)
        self.action_stop_job.setShortcut("F8")
        self.action_stop_job.setStatusTip("Stop the laser job")
        self.action_stop_job.triggered.connect(self._on_stop_job)
        self.action_stop_job.setEnabled(False)
    
    def _create_menus(self):
        """Create menu bar and menus."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.action_new)
        file_menu.addAction(self.action_open)
        file_menu.addSeparator()
        file_menu.addAction(self.action_save)
        file_menu.addAction(self.action_save_as)
        file_menu.addSeparator()
        file_menu.addAction(self.action_import)
        file_menu.addAction(self.action_export)
        file_menu.addSeparator()
        file_menu.addAction(self.action_exit)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction(self.action_undo)
        edit_menu.addAction(self.action_redo)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_delete)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_select_all)
        edit_menu.addSeparator()
        
        # Transform submenu
        transform_menu = edit_menu.addMenu("&Transform")
        transform_menu.addAction(self.action_mirror_horizontal)
        transform_menu.addAction(self.action_mirror_vertical)
        transform_menu.addSeparator()
        transform_menu.addAction(self.action_rotate_90)
        transform_menu.addAction(self.action_rotate_180)
        
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_cylinder_engraving)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        view_menu.addAction(self.action_zoom_in)
        view_menu.addAction(self.action_zoom_out)
        view_menu.addAction(self.action_zoom_fit)
        view_menu.addSeparator()
        view_menu.addAction(self.action_workspace_size)
        view_menu.addSeparator()
        # Panel visibility submenu
        panels_menu = view_menu.addMenu("&Panels")
        panels_menu.addAction(self.action_show_layers)
        panels_menu.addAction(self.action_show_properties)
        panels_menu.addAction(self.action_show_laser)
        panels_menu.addAction(self.action_show_materials)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        tools_menu.addAction(self.action_tool_select)
        tools_menu.addSeparator()
        tools_menu.addAction(self.action_tool_line)
        tools_menu.addAction(self.action_tool_rect)
        tools_menu.addAction(self.action_tool_ellipse)
        tools_menu.addAction(self.action_tool_polygon)
        tools_menu.addAction(self.action_tool_pen)
        tools_menu.addAction(self.action_tool_text)
        
        # Laser menu
        laser_menu = menubar.addMenu("&Laser")
        laser_menu.addAction(self.action_connect)
        laser_menu.addAction(self.action_disconnect)
        laser_menu.addSeparator()
        laser_menu.addAction(self.action_home)
        laser_menu.addAction(self.action_frame)
        laser_menu.addSeparator()
        laser_menu.addAction(self.action_start_job)
        laser_menu.addAction(self.action_pause_job)
        laser_menu.addAction(self.action_resume_job)
        laser_menu.addAction(self.action_stop_job)
    
    def _create_toolbars(self):
        """Create toolbars."""
        # File toolbar
        file_toolbar = QToolBar("File")
        file_toolbar.setObjectName("FileToolBar")
        file_toolbar.setIconSize(QSize(24, 24))
        file_toolbar.addAction(self.action_new)
        file_toolbar.addAction(self.action_open)
        file_toolbar.addAction(self.action_save)
        self.addToolBar(file_toolbar)
        
        # Edit toolbar
        edit_toolbar = QToolBar("Edit")
        edit_toolbar.setObjectName("EditToolBar")
        edit_toolbar.setIconSize(QSize(24, 24))
        edit_toolbar.addAction(self.action_undo)
        edit_toolbar.addAction(self.action_redo)
        self.addToolBar(edit_toolbar)
        
        # Drawing tools toolbar
        tools_toolbar = QToolBar("Tools")
        tools_toolbar.setObjectName("ToolsToolBar")
        tools_toolbar.setIconSize(QSize(24, 24))
        tools_toolbar.addAction(self.action_tool_select)
        tools_toolbar.addSeparator()
        tools_toolbar.addAction(self.action_tool_line)
        tools_toolbar.addAction(self.action_tool_rect)
        tools_toolbar.addAction(self.action_tool_ellipse)
        tools_toolbar.addAction(self.action_tool_polygon)
        tools_toolbar.addAction(self.action_tool_pen)
        tools_toolbar.addAction(self.action_tool_text)
        self.addToolBar(tools_toolbar)
        
        # Laser toolbar
        laser_toolbar = QToolBar("Laser")
        laser_toolbar.setObjectName("LaserToolBar")
        laser_toolbar.setIconSize(QSize(24, 24))
        laser_toolbar.addAction(self.action_connect)
        laser_toolbar.addAction(self.action_disconnect)
        laser_toolbar.addSeparator()
        laser_toolbar.addAction(self.action_home)
        laser_toolbar.addAction(self.action_frame)
        laser_toolbar.addSeparator()
        laser_toolbar.addAction(self.action_start_job)
        laser_toolbar.addAction(self.action_pause_job)
        laser_toolbar.addAction(self.action_resume_job)
        laser_toolbar.addAction(self.action_stop_job)
        self.addToolBar(laser_toolbar)
    
    def _create_central_widget(self):
        """Create the central canvas widget."""
        self.canvas = LaserCanvas(self.document)
        self.setCentralWidget(self.canvas)
    
    def _create_dock_panels(self):
        """Create dockable panels."""
        # Layers panel (left)
        self.layers_panel = LayersPanel(self.document)
        self.layers_dock = QDockWidget("Layers", self)
        self.layers_dock.setObjectName("LayersDock")
        self.layers_dock.setWidget(self.layers_panel)
        self.layers_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.layers_dock.setMinimumSize(200, 300)
        self.layers_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.TopDockWidgetArea |
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.layers_dock)
        
        # Properties panel (right)
        self.properties_panel = PropertiesPanel()
        self.properties_dock = QDockWidget("Properties", self)
        self.properties_dock.setObjectName("PropertiesDock")
        self.properties_dock.setWidget(self.properties_panel)
        self.properties_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.properties_dock.setMinimumSize(200, 300)
        self.properties_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.TopDockWidgetArea |
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.properties_dock)
        
        # Laser settings panel (right, below properties)
        self.laser_panel = LaserPanel()
        self.laser_dock = QDockWidget("Laser", self)
        self.laser_dock.setObjectName("LaserDock")
        self.laser_dock.setWidget(self.laser_panel)
        self.laser_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        # Allow resizing when floating
        self.laser_dock.setMinimumSize(300, 400)
        self.laser_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.TopDockWidgetArea |
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.laser_dock)
        
        # Materials panel (right, tabbed with laser)
        self.materials_panel = MaterialsPanel()
        self.materials_dock = QDockWidget("Materials", self)
        self.materials_dock.setObjectName("MaterialsDock")
        self.materials_dock.setWidget(self.materials_panel)
        self.materials_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.materials_dock.setMinimumSize(200, 300)
        self.materials_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.TopDockWidgetArea |
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.materials_dock)
        
        # Tab the laser and materials panels
        self.tabifyDockWidget(self.laser_dock, self.materials_dock)
        self.laser_dock.raise_()  # Show laser tab by default
        
        # Connect dock widget visibility to actions (sync checkboxes with actual visibility)
        self.layers_dock.visibilityChanged.connect(
            lambda visible: self.action_show_layers.setChecked(visible)
        )
        self.properties_dock.visibilityChanged.connect(
            lambda visible: self.action_show_properties.setChecked(visible)
        )
        self.laser_dock.visibilityChanged.connect(
            lambda visible: self.action_show_laser.setChecked(visible)
        )
        self.materials_dock.visibilityChanged.connect(
            lambda visible: self.action_show_materials.setChecked(visible)
        )
    
    def _create_status_bar(self):
        """Create status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _init_laser_system(self):
        """Initialize laser controller and job manager."""
        # Create controller
        self._controller = GRBLController()
        
        # Create job manager
        self._job_manager = JobManager(self._controller)
        
        # Connect controller status updates
        self._controller.add_status_callback(self._on_controller_status)
        
        # Connect console callback
        self._controller.add_console_callback(self._on_grbl_console_response)
        
        # Set in laser panel
        self.laser_panel.set_controller(self._controller)
        self.laser_panel.set_job_manager(self._job_manager)
        
        # Connect laser panel signals
        self.laser_panel.connect_requested.connect(self._on_connect_laser)
        self.laser_panel.disconnect_requested.connect(self._on_disconnect_laser)
        self.laser_panel.home_requested.connect(self._on_home)
        self.laser_panel.set_home_requested.connect(self._on_set_home)
        self.laser_panel.abort_home_requested.connect(self._on_abort_home)
        self.laser_panel.frame_requested.connect(self._on_frame)
        self.laser_panel.start_job_requested.connect(self._on_start_job)
        self.laser_panel.pause_job_requested.connect(self._on_pause_job)
        self.laser_panel.resume_job_requested.connect(self._on_resume_job)
        self.laser_panel.stop_job_requested.connect(self._on_stop_job)
        self.laser_panel.jog_requested.connect(self._on_jog)
        self.laser_panel.console_command.connect(self._on_console_command)
    
    def _connect_signals(self):
        """Connect signals between components."""
        try:
            # Canvas selection changes update properties panel
            self.canvas.selection_changed.connect(
                self.properties_panel.update_selection
            )
            
            # Layer panel updates
            self.layers_panel.layer_selected.connect(
                self.canvas.set_active_layer
            )
            
            # Material selection updates laser settings
            self.materials_panel.material_selected.connect(
                self.laser_panel.apply_material
            )
        except Exception as e:
            print(f"Warning: Error connecting signals: {e}")
            traceback.print_exc()
    
    def _on_controller_status(self, status):
        """Handle controller status updates."""
        self.laser_panel.update_controller_status()
        
        # Update action states
        connected = status.state == ConnectionState.CONNECTED
        self.action_connect.setEnabled(not connected)
        self.action_disconnect.setEnabled(connected)
        self.action_home.setEnabled(connected)
        self.action_frame.setEnabled(connected)
        self.action_start_job.setEnabled(connected)
        
        # Update status bar
        if connected:
            self.status_bar.showMessage(
                f"Connected - Position: X:{status.position_x:.2f} Y:{status.position_y:.2f}"
            )
        elif status.state == ConnectionState.ERROR:
            self.status_bar.showMessage(f"Error: {status.error_message}", 5000)
        
        # Display status responses in console
        if hasattr(self.laser_panel, 'console'):
            if status.error_message:
                self.laser_panel.append_console_response(status.error_message, "error")
    
    def _on_grbl_console_response(self, text: str, message_type: str = "response"):
        """Handle GRBL console response."""
        if hasattr(self.laser_panel, 'console'):
            self.laser_panel.append_console_response(text, message_type)
    
    def _load_settings(self):
        """Load application settings."""
        settings = QSettings("LaserBurn", "LaserBurn")
        
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        state = settings.value("windowState")
        if state:
            self.restoreState(state)
    
    def _save_settings(self):
        """Save application settings."""
        settings = QSettings("LaserBurn", "LaserBurn")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
    
    def closeEvent(self, event):
        """Handle window close."""
        # Disconnect laser if connected
        if self._controller and self._controller.status.state == ConnectionState.CONNECTED:
            reply = QMessageBox.question(
                self,
                "Laser Connected",
                "Laser is still connected. Disconnect before closing?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._on_disconnect_laser()
        
        # Shutdown job manager
        if self._job_manager:
            self._job_manager.shutdown()
        
        self._save_settings()
        event.accept()
    
    # Action handlers
    def _on_new(self):
        """Create new document."""
        self.document = Document(name="Untitled")
        self.document.add_layer(Layer(name="Layer 1"))
        self.canvas.set_document(self.document)
        self.layers_panel.set_document(self.document)
        self.setWindowTitle("LaserBurn - Untitled")
    
    def _on_open(self):
        """Open existing file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "LaserBurn Files (*.lbrn);;All Files (*)"
        )
        if filepath:
            # TODO: Load document
            self.status_bar.showMessage(f"Opening {filepath}...")
    
    def _on_save(self):
        """Save current document."""
        self.status_bar.showMessage("Saving...")
    
    def _on_save_as(self):
        """Save document with new name."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save As",
            "",
            "LaserBurn Files (*.lbrn);;All Files (*)"
        )
        if filepath:
            # TODO: Save document
            self.status_bar.showMessage(f"Saving to {filepath}...")
    
    def _on_import(self):
        """Import external file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Import File",
            "",
            "Vector Files (*.svg *.dxf);;Images (*.png *.jpg *.bmp);;All Files (*)"
        )
        if filepath:
            self._import_file(filepath)
    
    def _import_file(self, filepath: str):
        """Import a file into the document."""
        from ..io.svg_parser import SVGParser
        
        ext = filepath.lower().split('.')[-1]
        
        if ext == 'svg':
            try:
                parser = SVGParser()
                imported_doc = parser.parse_file(filepath)
                
                # Count shapes before import
                shapes_before = sum(len(layer.shapes) for layer in self.document.layers)
                
                # Merge imported layers into current document
                for layer in imported_doc.layers:
                    self.document.add_layer(layer)
                
                # Count shapes after import
                shapes_after = sum(len(layer.shapes) for layer in self.document.layers)
                shapes_imported = shapes_after - shapes_before
                
                # Update canvas to show imported shapes
                self.canvas.set_document(self.document)
                self.layers_panel.set_document(self.document)
                self.canvas._update_view()  # Force view update
                if hasattr(self.layers_panel, 'refresh'):
                    self.layers_panel.refresh()
                
                self.status_bar.showMessage(
                    f"Imported {filepath} - {len(imported_doc.layers)} layer(s), {shapes_imported} shape(s)"
                )
            except Exception as e:
                import traceback
                error_msg = f"Failed to import file:\n{str(e)}\n\n{traceback.format_exc()}"
                QMessageBox.warning(self, "Import Error", error_msg)
                self.status_bar.showMessage(f"Import failed: {e}")
        else:
            self.status_bar.showMessage(f"Unsupported file type: {ext}")
    
    def _on_export_gcode(self):
        """Export to G-code."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export G-Code",
            "",
            "G-Code Files (*.gcode *.nc *.ngc);;All Files (*)"
        )
        if filepath:
            try:
                from ..laser.gcode_generator import GCodeGenerator, GCodeSettings
                from ..image.cylinder_warp import apply_cylinder_compensation_to_gcode
                
                generator = GCodeGenerator(GCodeSettings())
                gcode, warnings = generator.generate(self.document)
                
                # Apply cylinder compensation if enabled
                if (self.document.cylinder_params and 
                    self.document.cylinder_compensate_power):
                    # Convert gcode string to lines
                    gcode_lines = gcode.split('\n')
                    
                    # Get design center for compensation
                    bounds = self.document.get_design_bounds()
                    design_center_x = (bounds.min_x + bounds.max_x) / 2 if bounds else 0
                    
                    # Get base power from settings (default to 255)
                    base_power = 255  # Could get from GCodeSettings
                    
                    # Apply compensation
                    gcode_lines = apply_cylinder_compensation_to_gcode(
                        gcode_lines,
                        self.document.cylinder_params,
                        design_center_x=design_center_x,
                        base_power=base_power,
                        include_z=self.document.cylinder_compensate_z
                    )
                    
                    # Convert back to string
                    gcode = '\n'.join(gcode_lines)
                
                if warnings:
                    QMessageBox.warning(self, "G-code Warnings", "\n".join(warnings))
                generator.save_to_file(gcode, filepath)
                self.status_bar.showMessage(f"Exported to {filepath}")
            except Exception as e:
                QMessageBox.warning(self, "Export Error", f"Failed to export G-code:\n{e}")
                self.status_bar.showMessage(f"Export failed: {e}")
    
    def _on_undo(self):
        """Undo last action."""
        pass
    
    def _on_redo(self):
        """Redo last undone action."""
        pass
    
    def _on_delete(self):
        """Delete selected objects."""
        self.canvas._delete_selection()
    
    def _on_select_all(self):
        """Select all objects."""
        self.canvas.select_all()
    
    def _on_mirror_horizontal(self):
        """Mirror selected shapes horizontally."""
        self.canvas.mirror_horizontal()
    
    def _on_mirror_vertical(self):
        """Mirror selected shapes vertically."""
        self.canvas.mirror_vertical()
    
    def _on_rotate(self, angle: float):
        """Rotate selected shapes by angle (in radians)."""
        self.canvas.rotate(angle)
    
    def _on_cylinder_engraving(self):
        """Open cylinder engraving settings dialog."""
        from .dialogs.cylinder_dialog import CylinderDialog
        
        # Get existing params if any
        initial_params = self.document.cylinder_params
        
        dialog = CylinderDialog(self, initial_params)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_params()
            # Store params for use during export
            self.document.cylinder_params = params
            self.document.cylinder_warp_image = dialog.should_warp_image()
            self.document.cylinder_compensate_power = dialog.should_compensate_power()
            self.document.cylinder_compensate_z = dialog.should_compensate_z()
            
            self.status_bar.showMessage(
                f"Cylinder engraving enabled: {params.diameter}mm diameter, "
                f"±{params.max_angle}° max angle"
            )
    
    def _on_zoom_in(self):
        """Zoom in."""
        self.canvas.zoom_in()
    
    def _on_zoom_out(self):
        """Zoom out."""
        self.canvas.zoom_out()
    
    def _on_zoom_fit(self):
        """Zoom to fit content."""
        self.canvas.zoom_to_fit()
    
    def _on_workspace_size(self):
        """Open workspace size dialog."""
        from .dialogs.workspace_dialog import WorkspaceDialog
        
        dialog = WorkspaceDialog(
            self.document.width,
            self.document.height,
            self
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            width, height = dialog.get_size()
            self.document.width = width
            self.document.height = height
            self.canvas.set_document(self.document)
            self.status_bar.showMessage(f"Workspace size set to {width:.1f} x {height:.1f} mm")
    
    # Laser action handlers
    def _on_connect_laser(self):
        """Connect to laser controller."""
        # Check if already connected
        if self._controller and self._controller.status.state == ConnectionState.CONNECTED:
            reply = QMessageBox.question(
                self,
                "Already Connected",
                "Laser is already connected. Disconnect and reconnect?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._on_disconnect_laser()
            else:
                return
        
        dialog = ConnectionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            port, baudrate = dialog.get_connection_info()
            
            if not port:
                QMessageBox.warning(
                    self,
                    "No Port Selected",
                    "Please select a serial port to connect."
                )
                return
            
            self.status_bar.showMessage(f"Connecting to {port}...")
            
            if self._controller.connect(port, baudrate):
                self.status_bar.showMessage(f"Connected to {port}")
                # Update laser panel with detected settings
                if hasattr(self._controller, 'get_work_area'):
                    x, y, z = self._controller.get_work_area()
                    self.laser_panel.workarea_x_spin.setValue(x)
                    self.laser_panel.workarea_y_spin.setValue(y)
                    self.laser_panel.workarea_z_spin.setValue(z)
                if hasattr(self._controller, 'get_max_spindle_speed'):
                    spindle = self._controller.get_max_spindle_speed()
                    self.laser_panel.set_max_spindle_speed(spindle)
            else:
                # Show detailed error message
                error_msg = self._controller.status.error_message
                QMessageBox.warning(
                    self,
                    "Connection Failed",
                    f"Failed to connect to {port}.\n\n{error_msg}"
                )
                self.status_bar.showMessage("Connection failed")
    
    def _on_disconnect_laser(self):
        """Disconnect from laser controller."""
        if self._controller:
            # Stop any running jobs
            if self._job_manager and self._job_manager.get_current_job():
                reply = QMessageBox.question(
                    self,
                    "Job Running",
                    "A job is currently running. Stop and disconnect?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._job_manager.cancel_current_job()
                else:
                    return
            
            self._controller.disconnect()
            self.status_bar.showMessage("Disconnected from laser")
    
    def _on_home(self):
        """Home the laser."""
        if not self._controller:
            return
        
        reply = QMessageBox.question(
            self,
            "Home Laser",
            "This will move the laser to the home position. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.status_bar.showMessage("Homing laser...")
            if self._controller.home():
                self.status_bar.showMessage("Homing started - watch for completion or click 'Stop Home' if it grinds")
            else:
                QMessageBox.warning(self, "Home Failed", "Failed to start homing sequence")
    
    def _on_set_home(self):
        """Set current position as home (0,0,0)."""
        if not self._controller:
            return
        
        reply = QMessageBox.question(
            self,
            "Set Home Position",
            "Set the current position as home (0,0,0)?\n\n"
            "This will mark the current position as the origin\n"
            "without running the homing sequence.\n\n"
            "Use this when the machine is already at the desired home position.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if hasattr(self._controller, 'set_home_position'):
                if self._controller.set_home_position():
                    self.status_bar.showMessage("Home position set to current location")
                else:
                    QMessageBox.warning(self, "Set Home Failed", "Failed to set home position")
            else:
                # Fallback: send G92 command directly
                response = self._controller.send_command("G92 X0 Y0 Z0", wait_for_ok=True)
                if "ok" in response.lower():
                    self.status_bar.showMessage("Home position set to current location")
                else:
                    QMessageBox.warning(self, "Set Home Failed", f"Failed to set home position: {response}")
    
    def _on_abort_home(self):
        """Abort the current homing sequence."""
        if not self._controller:
            return
        
        reply = QMessageBox.question(
            self,
            "Abort Homing",
            "Stop the current homing sequence?\n\n"
            "This will immediately stop all motion.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if hasattr(self._controller, 'abort_homing'):
                if self._controller.abort_homing():
                    self.status_bar.showMessage("Homing aborted")
                else:
                    self.status_bar.showMessage("No homing in progress")
            else:
                # Fallback: use stop_job which also handles homing
                self._controller.stop_job()
                self.status_bar.showMessage("Homing stopped")
    
    def _on_frame(self):
        """Frame the job (trace outline)."""
        if not self._controller:
            QMessageBox.warning(
                self,
                "Not Connected",
                "Please connect to the laser first."
            )
            return
        
        if not self._controller.status.is_homed:
            reply = QMessageBox.question(
                self,
                "Not Homed",
                "Laser is not homed. Home before framing?\n\n"
                "Framing will trace the outline of your design without enabling the laser.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                if not self._controller.home():
                    return
            else:
                return
        
        # Generate G-code for frame (outline of document) - NO LASER
        from ..laser.gcode_generator import GCodeGenerator, GCodeSettings
        
        # Generate frame G-code (traces outline without enabling laser)
        settings = GCodeSettings()
        settings.optimize_paths = True  # Optimize frame path
        # Get work area from controller if available
        if self._controller and hasattr(self._controller, 'get_work_area'):
            x, y, z = self._controller.get_work_area()
            settings.work_area_x = x
            settings.work_area_y = y
            settings.work_area_z = z
        generator = GCodeGenerator(settings)
        gcode, warnings = generator.generate_frame(self.document)
        
        if warnings:
            QMessageBox.warning(self, "Framing Warnings", "\n".join(warnings))
        
        # Create and start frame job directly (bypass queue for frame)
        if self._controller.start_job(gcode):
            self.status_bar.showMessage("Framing job started - tracing design outline")
            self.laser_panel.append_console_response("Frame job started", "info")
        else:
            QMessageBox.warning(self, "Frame Failed", "Failed to start framing job")
    
    def _on_start_job(self):
        """Start a laser job from the current document."""
        if not self._controller:
            QMessageBox.warning(self, "Not Connected", "Please connect to laser first.")
            return
        
        if not self._controller.status.is_homed:
            reply = QMessageBox.question(
                self,
                "Not Homed",
                "Laser is not homed. Home before starting job?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                if not self._controller.home():
                    return
            else:
                return
        
        # Get laser settings from panel
        laser_settings = self.laser_panel.get_laser_settings()
        
        # Apply settings to all layers
        for layer in self.document.layers:
            layer.laser_settings = laser_settings
            layer.use_layer_settings = True
        
        # Create job with work area validation
        settings = GCodeSettings()
        # Get work area from controller if available
        if self._controller and hasattr(self._controller, 'get_work_area'):
            x, y, z = self._controller.get_work_area()
            settings.work_area_x = x
            settings.work_area_y = y
            settings.work_area_z = z
        elif hasattr(self._controller, '_work_area_x'):
            settings.work_area_x = self._controller._work_area_x
            settings.work_area_y = self._controller._work_area_y
            settings.work_area_z = self._controller._work_area_z
        
        # Get max spindle speed from UI panel (or controller as fallback)
        # This is CRITICAL - if $30 is 1000 but we send S255, power will be wrong
        if hasattr(self.laser_panel, 'get_max_spindle_speed'):
            settings.max_power = self.laser_panel.get_max_spindle_speed()
        elif self._controller and hasattr(self._controller, 'get_max_spindle_speed'):
            settings.max_power = self._controller.get_max_spindle_speed()
        elif hasattr(self._controller, '_max_spindle_speed'):
            settings.max_power = self._controller._max_spindle_speed
        
        # Validate work area before creating job
        generator = GCodeGenerator(settings)
        _, warnings = generator.generate(self.document)
        
        # Show warnings if any
        if warnings:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Work Area Warnings")
            msg.setText("Some parts of your design exceed the machine work area:")
            msg.setDetailedText("\n".join(warnings))
            msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            reply = msg.exec()
            if reply == QMessageBox.StandardButton.Cancel:
                return
        
        # Create job using job manager (handles G-code generation internally)
        job = self._job_manager.create_job_from_document(
            self.document,
            name=self.document.name,
            priority=JobPriority.NORMAL,
            settings=settings
        )
        
        # Add to queue
        if self._job_manager.add_job(job):
            self.status_bar.showMessage(f"Job '{job.name}' added to queue")
        else:
            QMessageBox.warning(self, "Job Failed", "Failed to add job to queue")
    
    def _on_pause_job(self):
        """Pause the current job."""
        if self._job_manager:
            if self._job_manager.pause_current_job():
                self.status_bar.showMessage("Job paused")
            else:
                QMessageBox.warning(self, "Pause Failed", "No job running to pause")
    
    def _on_resume_job(self):
        """Resume the paused job."""
        if self._job_manager:
            if self._job_manager.resume_current_job():
                self.status_bar.showMessage("Job resumed")
            else:
                QMessageBox.warning(self, "Resume Failed", "No paused job to resume")
    
    def _on_stop_job(self):
        """Stop the current job."""
        if not self._job_manager:
            return
        
        reply = QMessageBox.question(
            self,
            "Stop Job",
            "Are you sure you want to stop the current job?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self._job_manager.cancel_current_job():
                self.status_bar.showMessage("Job stopped")
            else:
                QMessageBox.warning(self, "Stop Failed", "No job running to stop")
    
    def _on_jog(self, x: float, y: float, z: float):
        """Jog the laser head."""
        if not self._controller:
            return
        
        # Get jog speed from panel
        jog_speed = self.laser_panel._jog_speed
        
        if self._controller.jog(x, y, z, speed=jog_speed, relative=True):
            self.status_bar.showMessage(f"Jogging: X:{x:+.2f} Y:{y:+.2f} Z:{z:+.2f}")
        else:
            self.status_bar.showMessage("Jog failed", 2000)
    
    def _on_console_command(self, command: str):
        """Handle command from console."""
        if not self._controller:
            self.laser_panel.append_console_response("Not connected to laser", "error")
            return
        
        # Send command to controller
        response = self._controller.send_command(command, wait_for_ok=True)
        
        # Display response in console
        if response and response != "ok":
            if "error" in response.lower():
                self.laser_panel.append_console_response(response, "error")
            else:
                self.laser_panel.append_console_response(response, "response")
    
    def _toggle_layers_panel(self):
        """Toggle layers panel visibility."""
        self.layers_dock.setVisible(self.action_show_layers.isChecked())
    
    def _toggle_properties_panel(self):
        """Toggle properties panel visibility."""
        self.properties_dock.setVisible(self.action_show_properties.isChecked())
    
    def _toggle_laser_panel(self):
        """Toggle laser panel visibility."""
        self.laser_dock.setVisible(self.action_show_laser.isChecked())
    
    def _toggle_materials_panel(self):
        """Toggle materials panel visibility."""
        self.materials_dock.setVisible(self.action_show_materials.isChecked())
    
    def keyPressEvent(self, event):
        """Handle key press events for jogging."""
        if not self._controller or self._controller.status.state != ConnectionState.CONNECTED:
            super().keyPressEvent(event)
            return
        
        # Check if canvas or other widget has focus (don't jog if typing in input)
        from PyQt6.QtWidgets import QLineEdit, QTextEdit
        focused = self.focusWidget()
        if isinstance(focused, (QLineEdit, QTextEdit)):
            super().keyPressEvent(event)
            return
        
        # Arrow key jogging
        step = self.laser_panel._jog_distance
        
        if event.key() == Qt.Key.Key_Up:
            self._on_jog(0, step, 0)
            event.accept()
        elif event.key() == Qt.Key.Key_Down:
            self._on_jog(0, -step, 0)
            event.accept()
        elif event.key() == Qt.Key.Key_Left:
            self._on_jog(-step, 0, 0)
            event.accept()
        elif event.key() == Qt.Key.Key_Right:
            self._on_jog(step, 0, 0)
            event.accept()
        elif event.key() == Qt.Key.Key_PageUp:
            self._on_jog(0, 0, step)
            event.accept()
        elif event.key() == Qt.Key.Key_PageDown:
            self._on_jog(0, 0, -step)
            event.accept()
        else:
            super().keyPressEvent(event)

