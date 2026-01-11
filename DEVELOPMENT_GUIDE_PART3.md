# LaserBurn Development Guide - Part 3
## User Interface, Materials, Camera, Testing & Deployment

---

## 11. User Interface Development

### 11.1 Main Window Structure

```python
# src/ui/mainwindow.py

"""
Main Application Window for LaserBurn

This is the primary window containing all UI elements:
- Menu bar
- Toolbars
- Canvas (central widget)
- Dock panels (layers, properties, laser settings)
- Status bar
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QDockWidget, QStatusBar, QMenuBar,
    QMenu, QFileDialog, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, QSettings, QSize
from PyQt6.QtGui import QAction, QIcon, QKeySequence

from ..core.document import Document
from ..core.layer import Layer
from .canvas import LaserCanvas
from .panels.layers_panel import LayersPanel
from .panels.properties_panel import PropertiesPanel
from .panels.laser_panel import LaserPanel
from .panels.materials_panel import MaterialsPanel
from .toolbar import ToolBar


class MainWindow(QMainWindow):
    """
    Main application window.
    
    Structure:
    ┌────────────────────────────────────────────────────────┐
    │  Menu Bar                                              │
    ├────────────────────────────────────────────────────────┤
    │  Tool Bar                                              │
    ├──────────┬──────────────────────────────┬──────────────┤
    │          │                              │              │
    │  Layers  │       Canvas                 │  Properties  │
    │  Panel   │     (Drawing Area)           │    Panel     │
    │          │                              │              │
    │          │                              ├──────────────┤
    │          │                              │    Laser     │
    │          │                              │   Settings   │
    ├──────────┴──────────────────────────────┴──────────────┤
    │  Status Bar                                            │
    └────────────────────────────────────────────────────────┘
    """
    
    def __init__(self):
        super().__init__()
        
        self.document = Document(name="Untitled")
        self.document.add_layer(Layer(name="Layer 1"))
        
        self.setWindowTitle("LaserBurn - Laser Engraving Software")
        self.setMinimumSize(1200, 800)
        
        # Setup UI components
        self._create_actions()
        self._create_menus()
        self._create_toolbars()
        self._create_central_widget()
        self._create_dock_panels()
        self._create_status_bar()
        
        # Load settings
        self._load_settings()
        
        # Connect signals
        self._connect_signals()
    
    def _create_actions(self):
        """Create all menu/toolbar actions."""
        
        # File actions
        self.action_new = QAction(QIcon(":/icons/new.png"), "&New", self)
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        self.action_new.setStatusTip("Create a new document")
        self.action_new.triggered.connect(self._on_new)
        
        self.action_open = QAction(QIcon(":/icons/open.png"), "&Open...", self)
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open.setStatusTip("Open an existing file")
        self.action_open.triggered.connect(self._on_open)
        
        self.action_save = QAction(QIcon(":/icons/save.png"), "&Save", self)
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
        self.action_undo = QAction(QIcon(":/icons/undo.png"), "&Undo", self)
        self.action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.action_undo.triggered.connect(self._on_undo)
        
        self.action_redo = QAction(QIcon(":/icons/redo.png"), "&Redo", self)
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.action_redo.triggered.connect(self._on_redo)
        
        self.action_cut = QAction(QIcon(":/icons/cut.png"), "Cu&t", self)
        self.action_cut.setShortcut(QKeySequence.StandardKey.Cut)
        self.action_cut.triggered.connect(self._on_cut)
        
        self.action_copy = QAction(QIcon(":/icons/copy.png"), "&Copy", self)
        self.action_copy.setShortcut(QKeySequence.StandardKey.Copy)
        self.action_copy.triggered.connect(self._on_copy)
        
        self.action_paste = QAction(QIcon(":/icons/paste.png"), "&Paste", self)
        self.action_paste.setShortcut(QKeySequence.StandardKey.Paste)
        self.action_paste.triggered.connect(self._on_paste)
        
        self.action_delete = QAction("&Delete", self)
        self.action_delete.setShortcut(QKeySequence.StandardKey.Delete)
        self.action_delete.triggered.connect(self._on_delete)
        
        self.action_select_all = QAction("Select &All", self)
        self.action_select_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        self.action_select_all.triggered.connect(self._on_select_all)
        
        # View actions
        self.action_zoom_in = QAction(QIcon(":/icons/zoom_in.png"), "Zoom &In", self)
        self.action_zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self.action_zoom_in.triggered.connect(self._on_zoom_in)
        
        self.action_zoom_out = QAction(QIcon(":/icons/zoom_out.png"), "Zoom &Out", self)
        self.action_zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self.action_zoom_out.triggered.connect(self._on_zoom_out)
        
        self.action_zoom_fit = QAction("Zoom to &Fit", self)
        self.action_zoom_fit.setShortcut("Ctrl+0")
        self.action_zoom_fit.triggered.connect(self._on_zoom_fit)
        
        self.action_zoom_100 = QAction("Zoom &100%", self)
        self.action_zoom_100.setShortcut("Ctrl+1")
        self.action_zoom_100.triggered.connect(self._on_zoom_100)
        
        # Tool actions (drawing tools)
        self.action_tool_select = QAction(QIcon(":/icons/select.png"), "&Select", self)
        self.action_tool_select.setShortcut("V")
        self.action_tool_select.setCheckable(True)
        self.action_tool_select.setChecked(True)
        
        self.action_tool_line = QAction(QIcon(":/icons/line.png"), "&Line", self)
        self.action_tool_line.setShortcut("L")
        self.action_tool_line.setCheckable(True)
        
        self.action_tool_rect = QAction(QIcon(":/icons/rect.png"), "&Rectangle", self)
        self.action_tool_rect.setShortcut("R")
        self.action_tool_rect.setCheckable(True)
        
        self.action_tool_ellipse = QAction(QIcon(":/icons/ellipse.png"), "&Ellipse", self)
        self.action_tool_ellipse.setShortcut("E")
        self.action_tool_ellipse.setCheckable(True)
        
        self.action_tool_polygon = QAction(QIcon(":/icons/polygon.png"), "&Polygon", self)
        self.action_tool_polygon.setShortcut("P")
        self.action_tool_polygon.setCheckable(True)
        
        self.action_tool_text = QAction(QIcon(":/icons/text.png"), "&Text", self)
        self.action_tool_text.setShortcut("T")
        self.action_tool_text.setCheckable(True)
        
        self.action_tool_pen = QAction(QIcon(":/icons/pen.png"), "P&en", self)
        self.action_tool_pen.setShortcut("N")
        self.action_tool_pen.setCheckable(True)
        
        # Laser actions
        self.action_connect = QAction(QIcon(":/icons/connect.png"), "&Connect Laser", self)
        self.action_connect.triggered.connect(self._on_connect_laser)
        
        self.action_home = QAction(QIcon(":/icons/home.png"), "&Home", self)
        self.action_home.triggered.connect(self._on_home)
        
        self.action_frame = QAction(QIcon(":/icons/frame.png"), "&Frame", self)
        self.action_frame.setStatusTip("Trace the outline of the job")
        self.action_frame.triggered.connect(self._on_frame)
        
        self.action_start = QAction(QIcon(":/icons/start.png"), "&Start", self)
        self.action_start.setShortcut("F5")
        self.action_start.setStatusTip("Start the laser job")
        self.action_start.triggered.connect(self._on_start_job)
        
        self.action_pause = QAction(QIcon(":/icons/pause.png"), "P&ause", self)
        self.action_pause.setShortcut("F6")
        self.action_pause.triggered.connect(self._on_pause_job)
        
        self.action_stop = QAction(QIcon(":/icons/stop.png"), "S&top", self)
        self.action_stop.setShortcut("F7")
        self.action_stop.triggered.connect(self._on_stop_job)
    
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
        edit_menu.addAction(self.action_cut)
        edit_menu.addAction(self.action_copy)
        edit_menu.addAction(self.action_paste)
        edit_menu.addAction(self.action_delete)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_select_all)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        view_menu.addAction(self.action_zoom_in)
        view_menu.addAction(self.action_zoom_out)
        view_menu.addAction(self.action_zoom_fit)
        view_menu.addAction(self.action_zoom_100)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        tools_menu.addAction(self.action_tool_select)
        tools_menu.addAction(self.action_tool_line)
        tools_menu.addAction(self.action_tool_rect)
        tools_menu.addAction(self.action_tool_ellipse)
        tools_menu.addAction(self.action_tool_polygon)
        tools_menu.addAction(self.action_tool_text)
        tools_menu.addAction(self.action_tool_pen)
        
        # Laser menu
        laser_menu = menubar.addMenu("&Laser")
        laser_menu.addAction(self.action_connect)
        laser_menu.addSeparator()
        laser_menu.addAction(self.action_home)
        laser_menu.addAction(self.action_frame)
        laser_menu.addSeparator()
        laser_menu.addAction(self.action_start)
        laser_menu.addAction(self.action_pause)
        laser_menu.addAction(self.action_stop)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("&Documentation")
        help_menu.addAction("&About LaserBurn")
    
    def _create_toolbars(self):
        """Create toolbars."""
        # File toolbar
        file_toolbar = QToolBar("File")
        file_toolbar.setIconSize(QSize(24, 24))
        file_toolbar.addAction(self.action_new)
        file_toolbar.addAction(self.action_open)
        file_toolbar.addAction(self.action_save)
        self.addToolBar(file_toolbar)
        
        # Edit toolbar
        edit_toolbar = QToolBar("Edit")
        edit_toolbar.setIconSize(QSize(24, 24))
        edit_toolbar.addAction(self.action_undo)
        edit_toolbar.addAction(self.action_redo)
        edit_toolbar.addSeparator()
        edit_toolbar.addAction(self.action_cut)
        edit_toolbar.addAction(self.action_copy)
        edit_toolbar.addAction(self.action_paste)
        self.addToolBar(edit_toolbar)
        
        # Drawing tools toolbar
        tools_toolbar = QToolBar("Tools")
        tools_toolbar.setIconSize(QSize(24, 24))
        tools_toolbar.addAction(self.action_tool_select)
        tools_toolbar.addAction(self.action_tool_line)
        tools_toolbar.addAction(self.action_tool_rect)
        tools_toolbar.addAction(self.action_tool_ellipse)
        tools_toolbar.addAction(self.action_tool_polygon)
        tools_toolbar.addAction(self.action_tool_text)
        tools_toolbar.addAction(self.action_tool_pen)
        self.addToolBar(tools_toolbar)
        
        # Laser toolbar
        laser_toolbar = QToolBar("Laser")
        laser_toolbar.setIconSize(QSize(24, 24))
        laser_toolbar.addAction(self.action_connect)
        laser_toolbar.addAction(self.action_home)
        laser_toolbar.addAction(self.action_frame)
        laser_toolbar.addSeparator()
        laser_toolbar.addAction(self.action_start)
        laser_toolbar.addAction(self.action_pause)
        laser_toolbar.addAction(self.action_stop)
        self.addToolBar(laser_toolbar)
    
    def _create_central_widget(self):
        """Create the central canvas widget."""
        self.canvas = LaserCanvas(self.document)
        self.setCentralWidget(self.canvas)
    
    def _create_dock_panels(self):
        """Create dockable panels."""
        # Layers panel (left)
        self.layers_panel = LayersPanel(self.document)
        layers_dock = QDockWidget("Layers", self)
        layers_dock.setWidget(self.layers_panel)
        layers_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, layers_dock)
        
        # Properties panel (right)
        self.properties_panel = PropertiesPanel()
        properties_dock = QDockWidget("Properties", self)
        properties_dock.setWidget(self.properties_panel)
        properties_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, properties_dock)
        
        # Laser settings panel (right, below properties)
        self.laser_panel = LaserPanel()
        laser_dock = QDockWidget("Laser", self)
        laser_dock.setWidget(self.laser_panel)
        laser_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, laser_dock)
        
        # Materials panel (right, tabbed with laser)
        self.materials_panel = MaterialsPanel()
        materials_dock = QDockWidget("Materials", self)
        materials_dock.setWidget(self.materials_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, materials_dock)
        
        # Tab the laser and materials panels
        self.tabifyDockWidget(laser_dock, materials_dock)
        laser_dock.raise_()  # Show laser tab by default
    
    def _create_status_bar(self):
        """Create status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _connect_signals(self):
        """Connect signals between components."""
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
        # Check for unsaved changes
        if self._has_unsaved_changes():
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before closing?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self._on_save()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        
        self._save_settings()
        event.accept()
    
    def _has_unsaved_changes(self) -> bool:
        """Check if document has unsaved changes."""
        # Implement change tracking
        return False
    
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
            # Load document
            pass
    
    def _on_save(self):
        """Save current document."""
        pass
    
    def _on_save_as(self):
        """Save document with new name."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save As",
            "",
            "LaserBurn Files (*.lbrn);;All Files (*)"
        )
        if filepath:
            # Save document
            pass
    
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
        from ..io.dxf_parser import DXFParser
        
        ext = filepath.lower().split('.')[-1]
        
        if ext == 'svg':
            parser = SVGParser()
            imported_doc = parser.parse_file(filepath)
        elif ext == 'dxf':
            parser = DXFParser()
            imported_doc = parser.parse_file(filepath)
        else:
            # Handle as image
            return
        
        # Merge imported layers into current document
        for layer in imported_doc.layers:
            self.document.add_layer(layer)
        
        self.canvas.update()
        self.layers_panel.refresh()
    
    def _on_export_gcode(self):
        """Export to G-code."""
        from ..laser.gcode_generator import GCodeGenerator, GCodeSettings
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export G-Code",
            "",
            "G-Code Files (*.gcode *.nc *.ngc);;All Files (*)"
        )
        
        if filepath:
            generator = GCodeGenerator(GCodeSettings())
            gcode = generator.generate(self.document)
            generator.save_to_file(gcode, filepath)
            self.status_bar.showMessage(f"Exported to {filepath}")
    
    def _on_undo(self):
        """Undo last action."""
        pass
    
    def _on_redo(self):
        """Redo last undone action."""
        pass
    
    def _on_cut(self):
        """Cut selected objects."""
        pass
    
    def _on_copy(self):
        """Copy selected objects."""
        pass
    
    def _on_paste(self):
        """Paste objects from clipboard."""
        pass
    
    def _on_delete(self):
        """Delete selected objects."""
        pass
    
    def _on_select_all(self):
        """Select all objects."""
        self.canvas.select_all()
    
    def _on_zoom_in(self):
        """Zoom in."""
        self.canvas.zoom_in()
    
    def _on_zoom_out(self):
        """Zoom out."""
        self.canvas.zoom_out()
    
    def _on_zoom_fit(self):
        """Zoom to fit content."""
        self.canvas.zoom_to_fit()
    
    def _on_zoom_100(self):
        """Zoom to 100%."""
        self.canvas.zoom_to_100()
    
    def _on_connect_laser(self):
        """Connect to laser controller."""
        pass
    
    def _on_home(self):
        """Home the laser."""
        pass
    
    def _on_frame(self):
        """Trace job outline."""
        pass
    
    def _on_start_job(self):
        """Start laser job."""
        pass
    
    def _on_pause_job(self):
        """Pause laser job."""
        pass
    
    def _on_stop_job(self):
        """Stop laser job."""
        pass
```

### 11.2 Canvas Implementation

```python
# src/ui/canvas.py

"""
LaserBurn Canvas - Main drawing and editing surface.

Uses Qt's Graphics View Framework for efficient rendering
and interaction with vector graphics.
"""

from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsPathItem,
    QRubberBand, QApplication
)
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, pyqtSignal, QLineF
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath,
    QTransform, QWheelEvent, QMouseEvent, QKeyEvent
)
from typing import List, Optional
from enum import Enum

from ..core.document import Document
from ..core.layer import Layer
from ..core.shapes import Shape, Rectangle, Ellipse, Path, Point


class Tool(Enum):
    """Drawing/editing tools."""
    SELECT = "select"
    LINE = "line"
    RECTANGLE = "rectangle"
    ELLIPSE = "ellipse"
    POLYGON = "polygon"
    TEXT = "text"
    PEN = "pen"
    NODE_EDIT = "node_edit"


class LaserCanvas(QGraphicsView):
    """
    Main canvas for displaying and editing designs.
    
    Features:
    - Zoom and pan
    - Grid display
    - Shape rendering
    - Tool handling
    - Selection
    - Snapping
    """
    
    # Signals
    selection_changed = pyqtSignal(list)  # List of selected shapes
    cursor_position = pyqtSignal(float, float)  # Mouse position in mm
    zoom_changed = pyqtSignal(float)  # Current zoom level
    
    def __init__(self, document: Document):
        super().__init__()
        
        self.document = document
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # View settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        
        # Canvas state
        self._zoom = 1.0
        self._current_tool = Tool.SELECT
        self._is_panning = False
        self._pan_start = QPointF()
        self._is_drawing = False
        self._draw_start = QPointF()
        self._temp_item: Optional[QGraphicsItem] = None
        self._selected_items: List[QGraphicsItem] = []
        self._active_layer: Optional[Layer] = None
        
        # Grid settings
        self._show_grid = True
        self._grid_spacing = 10.0  # mm
        self._snap_to_grid = True
        self._snap_distance = 2.0  # pixels
        
        # Colors
        self._background_color = QColor(40, 40, 40)
        self._grid_color = QColor(60, 60, 60)
        self._grid_color_major = QColor(80, 80, 80)
        self._workspace_color = QColor(50, 50, 50)
        self._selection_color = QColor(0, 120, 215)
        
        # Setup
        self._setup_scene()
        self._update_view()
        
        # Set active layer
        if document.layers:
            self._active_layer = document.layers[0]
    
    def _setup_scene(self):
        """Initialize scene with workspace."""
        # Set scene rect larger than workspace for scrolling
        padding = 100
        self.scene.setSceneRect(
            -padding, -padding,
            self.document.width + 2 * padding,
            self.document.height + 2 * padding
        )
        
        # Background is handled in drawBackground
        self.setBackgroundBrush(QBrush(self._background_color))
    
    def drawBackground(self, painter: QPainter, rect: QRectF):
        """Draw background with grid."""
        # Draw scene background
        painter.fillRect(rect, self._background_color)
        
        # Draw workspace area
        workspace = QRectF(0, 0, self.document.width, self.document.height)
        painter.fillRect(workspace, self._workspace_color)
        
        # Draw grid if enabled
        if self._show_grid and self._zoom > 0.1:
            self._draw_grid(painter, workspace)
        
        # Draw workspace border
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawRect(workspace)
    
    def _draw_grid(self, painter: QPainter, workspace: QRectF):
        """Draw grid lines."""
        # Calculate visible area
        left = max(0, workspace.left())
        top = max(0, workspace.top())
        right = min(workspace.right(), workspace.right())
        bottom = min(workspace.bottom(), workspace.bottom())
        
        # Minor grid
        painter.setPen(QPen(self._grid_color, 0.5))
        
        x = left - (left % self._grid_spacing)
        while x <= right:
            painter.drawLine(QLineF(x, top, x, bottom))
            x += self._grid_spacing
        
        y = top - (top % self._grid_spacing)
        while y <= bottom:
            painter.drawLine(QLineF(left, y, right, y))
            y += self._grid_spacing
        
        # Major grid (every 10 lines)
        major_spacing = self._grid_spacing * 10
        painter.setPen(QPen(self._grid_color_major, 1))
        
        x = left - (left % major_spacing)
        while x <= right:
            painter.drawLine(QLineF(x, top, x, bottom))
            x += major_spacing
        
        y = top - (top % major_spacing)
        while y <= bottom:
            painter.drawLine(QLineF(left, y, right, y))
            y += major_spacing
    
    def set_document(self, document: Document):
        """Set the document to display."""
        self.document = document
        self._setup_scene()
        self._update_view()
        
        if document.layers:
            self._active_layer = document.layers[0]
    
    def set_active_layer(self, layer: Layer):
        """Set the active layer for drawing."""
        self._active_layer = layer
    
    def set_tool(self, tool: Tool):
        """Set the current drawing tool."""
        self._current_tool = tool
        
        # Update cursor
        if tool == Tool.SELECT:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif tool == Tool.PEN:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)
    
    def _update_view(self):
        """Refresh the view with current document state."""
        # Clear existing items
        for item in list(self.scene.items()):
            if item != self._temp_item:
                self.scene.removeItem(item)
        
        # Add shapes from all layers
        for layer in self.document.layers:
            if not layer.visible:
                continue
            
            color = QColor(layer.color)
            pen = QPen(color, 1)
            pen.setCosmetic(True)  # Constant width regardless of zoom
            
            for shape in layer.shapes:
                item = self._create_graphics_item(shape, pen)
                if item:
                    item.setData(0, shape)  # Store shape reference
                    item.setData(1, layer)  # Store layer reference
                    self.scene.addItem(item)
    
    def _create_graphics_item(self, shape: Shape, 
                              pen: QPen) -> Optional[QGraphicsItem]:
        """Create a QGraphicsItem from a Shape."""
        paths = shape.get_paths()
        if not paths:
            return None
        
        # Create path item
        painter_path = QPainterPath()
        
        for path_points in paths:
            if not path_points:
                continue
            
            painter_path.moveTo(path_points[0].x, path_points[0].y)
            for point in path_points[1:]:
                painter_path.lineTo(point.x, point.y)
        
        item = QGraphicsPathItem(painter_path)
        item.setPen(pen)
        item.setBrush(Qt.BrushStyle.NoBrush)
        
        # Make selectable
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        
        return item
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press."""
        scene_pos = self.mapToScene(event.pos())
        
        # Middle button or Space+Left = Pan
        if (event.button() == Qt.MouseButton.MiddleButton or
            (event.button() == Qt.MouseButton.LeftButton and
             event.modifiers() & Qt.KeyboardModifier.ShiftModifier)):
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        
        # Handle based on current tool
        if event.button() == Qt.MouseButton.LeftButton:
            if self._current_tool == Tool.SELECT:
                # Let scene handle selection
                super().mousePressEvent(event)
                self._update_selection()
            else:
                # Start drawing
                self._is_drawing = True
                self._draw_start = self._snap_point(scene_pos)
                self._start_drawing(self._draw_start)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move."""
        scene_pos = self.mapToScene(event.pos())
        
        # Emit cursor position
        self.cursor_position.emit(scene_pos.x(), scene_pos.y())
        
        # Handle panning
        if self._is_panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            return
        
        # Handle drawing
        if self._is_drawing:
            snapped = self._snap_point(scene_pos)
            self._update_drawing(snapped)
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        if self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return
        
        if self._is_drawing:
            scene_pos = self.mapToScene(event.pos())
            snapped = self._snap_point(scene_pos)
            self._finish_drawing(snapped)
            self._is_drawing = False
        else:
            super().mouseReleaseEvent(event)
            self._update_selection()
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming."""
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom *= factor
        self._zoom = max(0.01, min(100, self._zoom))
        
        self.scale(factor, factor)
        self.zoom_changed.emit(self._zoom)
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press."""
        if event.key() == Qt.Key.Key_Delete:
            self._delete_selection()
        elif event.key() == Qt.Key.Key_Escape:
            if self._is_drawing:
                self._cancel_drawing()
            else:
                self._clear_selection()
        else:
            super().keyPressEvent(event)
    
    def _snap_point(self, point: QPointF) -> QPointF:
        """Snap point to grid if enabled."""
        if not self._snap_to_grid:
            return point
        
        x = round(point.x() / self._grid_spacing) * self._grid_spacing
        y = round(point.y() / self._grid_spacing) * self._grid_spacing
        
        return QPointF(x, y)
    
    def _start_drawing(self, start: QPointF):
        """Start drawing a new shape."""
        if self._current_tool == Tool.LINE:
            path = QPainterPath()
            path.moveTo(start)
            path.lineTo(start)
            self._temp_item = QGraphicsPathItem(path)
        
        elif self._current_tool == Tool.RECTANGLE:
            self._temp_item = QGraphicsRectItem(
                start.x(), start.y(), 0, 0
            )
        
        elif self._current_tool == Tool.ELLIPSE:
            self._temp_item = QGraphicsEllipseItem(
                start.x(), start.y(), 0, 0
            )
        
        if self._temp_item:
            pen = QPen(self._selection_color, 1)
            pen.setCosmetic(True)
            self._temp_item.setPen(pen)
            self.scene.addItem(self._temp_item)
    
    def _update_drawing(self, current: QPointF):
        """Update temporary shape while drawing."""
        if not self._temp_item:
            return
        
        if self._current_tool == Tool.LINE:
            path = QPainterPath()
            path.moveTo(self._draw_start)
            path.lineTo(current)
            self._temp_item.setPath(path)
        
        elif self._current_tool == Tool.RECTANGLE:
            rect = QRectF(self._draw_start, current).normalized()
            self._temp_item.setRect(rect)
        
        elif self._current_tool == Tool.ELLIPSE:
            rect = QRectF(self._draw_start, current).normalized()
            self._temp_item.setRect(rect)
    
    def _finish_drawing(self, end: QPointF):
        """Finish drawing and create the shape."""
        if not self._temp_item or not self._active_layer:
            self._cancel_drawing()
            return
        
        # Create shape based on tool
        shape = None
        
        if self._current_tool == Tool.LINE:
            path = Path()
            path.move_to(self._draw_start.x(), self._draw_start.y())
            path.line_to(end.x(), end.y())
            shape = path
        
        elif self._current_tool == Tool.RECTANGLE:
            rect = QRectF(self._draw_start, end).normalized()
            shape = Rectangle(
                rect.x(), rect.y(),
                rect.width(), rect.height()
            )
        
        elif self._current_tool == Tool.ELLIPSE:
            rect = QRectF(self._draw_start, end).normalized()
            shape = Ellipse(
                rect.center().x(), rect.center().y(),
                rect.width() / 2, rect.height() / 2
            )
        
        if shape:
            self._active_layer.add_shape(shape)
            self._update_view()
        
        # Remove temporary item
        if self._temp_item:
            self.scene.removeItem(self._temp_item)
            self._temp_item = None
    
    def _cancel_drawing(self):
        """Cancel current drawing operation."""
        if self._temp_item:
            self.scene.removeItem(self._temp_item)
            self._temp_item = None
        self._is_drawing = False
    
    def _update_selection(self):
        """Update selection state and emit signal."""
        selected_items = self.scene.selectedItems()
        selected_shapes = []
        
        for item in selected_items:
            shape = item.data(0)
            if shape:
                selected_shapes.append(shape)
        
        self.selection_changed.emit(selected_shapes)
    
    def _clear_selection(self):
        """Clear all selection."""
        self.scene.clearSelection()
        self._update_selection()
    
    def _delete_selection(self):
        """Delete selected shapes."""
        for item in self.scene.selectedItems():
            shape = item.data(0)
            layer = item.data(1)
            
            if shape and layer:
                layer.remove_shape(shape)
        
        self._update_view()
        self._update_selection()
    
    def select_all(self):
        """Select all shapes."""
        for item in self.scene.items():
            if item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable:
                item.setSelected(True)
        self._update_selection()
    
    def zoom_in(self):
        """Zoom in."""
        self._zoom *= 1.25
        self.scale(1.25, 1.25)
        self.zoom_changed.emit(self._zoom)
    
    def zoom_out(self):
        """Zoom out."""
        self._zoom /= 1.25
        self.scale(1 / 1.25, 1 / 1.25)
        self.zoom_changed.emit(self._zoom)
    
    def zoom_to_fit(self):
        """Zoom to fit all content."""
        self.fitInView(
            0, 0,
            self.document.width,
            self.document.height,
            Qt.AspectRatioMode.KeepAspectRatio
        )
        self._zoom = self.transform().m11()
        self.zoom_changed.emit(self._zoom)
    
    def zoom_to_100(self):
        """Reset zoom to 100%."""
        self.resetTransform()
        self._zoom = 1.0
        self.zoom_changed.emit(self._zoom)
```

---

## 12. Material Library System

### 12.1 Material Database

```python
# src/materials/database.py

"""
Material Library Database

Stores and retrieves material settings for consistent
laser parameters across projects.
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class MaterialPreset:
    """A material preset with laser settings."""
    id: int = -1
    name: str = ""
    category: str = ""  # Wood, Acrylic, Leather, etc.
    thickness: float = 3.0  # mm
    description: str = ""
    
    # Cut settings
    cut_power: float = 80.0
    cut_speed: float = 10.0
    cut_passes: int = 1
    cut_air_assist: bool = True
    cut_z_offset: float = 0.0
    
    # Engrave settings
    engrave_power: float = 30.0
    engrave_speed: float = 100.0
    engrave_dpi: int = 254
    engrave_air_assist: bool = False
    
    # Fill settings
    fill_power: float = 25.0
    fill_speed: float = 150.0
    fill_line_interval: float = 0.1
    fill_air_assist: bool = False
    
    # User data
    user_notes: str = ""
    is_builtin: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MaterialPreset':
        return cls(**data)


class MaterialDatabase:
    """
    SQLite-based material library.
    
    Provides:
    - Built-in default materials
    - User-defined materials
    - Search and filter
    - Import/export
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default to user's app data folder
            app_data = Path.home() / ".laserburn"
            app_data.mkdir(exist_ok=True)
            db_path = str(app_data / "materials.db")
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT,
                    thickness REAL,
                    description TEXT,
                    cut_power REAL,
                    cut_speed REAL,
                    cut_passes INTEGER,
                    cut_air_assist INTEGER,
                    cut_z_offset REAL,
                    engrave_power REAL,
                    engrave_speed REAL,
                    engrave_dpi INTEGER,
                    engrave_air_assist INTEGER,
                    fill_power REAL,
                    fill_speed REAL,
                    fill_line_interval REAL,
                    fill_air_assist INTEGER,
                    user_notes TEXT,
                    is_builtin INTEGER DEFAULT 0
                )
            """)
            
            # Check if defaults exist
            count = conn.execute(
                "SELECT COUNT(*) FROM materials WHERE is_builtin = 1"
            ).fetchone()[0]
            
            if count == 0:
                self._insert_defaults(conn)
    
    def _insert_defaults(self, conn: sqlite3.Connection):
        """Insert default material presets."""
        defaults = [
            MaterialPreset(
                name="3mm Plywood",
                category="Wood",
                thickness=3.0,
                description="Standard 3mm plywood",
                cut_power=85,
                cut_speed=8,
                cut_passes=1,
                engrave_power=25,
                engrave_speed=150,
                is_builtin=True
            ),
            MaterialPreset(
                name="6mm Plywood",
                category="Wood",
                thickness=6.0,
                description="Standard 6mm plywood",
                cut_power=95,
                cut_speed=4,
                cut_passes=2,
                engrave_power=25,
                engrave_speed=150,
                is_builtin=True
            ),
            MaterialPreset(
                name="3mm Acrylic",
                category="Acrylic",
                thickness=3.0,
                description="Clear or colored acrylic",
                cut_power=70,
                cut_speed=6,
                cut_passes=1,
                engrave_power=20,
                engrave_speed=200,
                is_builtin=True
            ),
            MaterialPreset(
                name="Cardboard",
                category="Paper",
                thickness=2.0,
                description="Standard corrugated cardboard",
                cut_power=30,
                cut_speed=25,
                cut_passes=1,
                engrave_power=10,
                engrave_speed=300,
                is_builtin=True
            ),
            MaterialPreset(
                name="Leather 2mm",
                category="Leather",
                thickness=2.0,
                description="Vegetable tanned leather",
                cut_power=60,
                cut_speed=10,
                cut_passes=1,
                engrave_power=15,
                engrave_speed=200,
                is_builtin=True
            ),
            MaterialPreset(
                name="Cork Sheet",
                category="Natural",
                thickness=3.0,
                description="Natural cork sheet",
                cut_power=40,
                cut_speed=15,
                cut_passes=1,
                engrave_power=15,
                engrave_speed=250,
                is_builtin=True
            ),
        ]
        
        for preset in defaults:
            self.add_material(preset, conn)
    
    def add_material(self, preset: MaterialPreset, 
                     conn: sqlite3.Connection = None) -> int:
        """Add a new material preset."""
        should_close = conn is None
        if conn is None:
            conn = sqlite3.connect(self.db_path)
        
        try:
            cursor = conn.execute("""
                INSERT INTO materials (
                    name, category, thickness, description,
                    cut_power, cut_speed, cut_passes, cut_air_assist, cut_z_offset,
                    engrave_power, engrave_speed, engrave_dpi, engrave_air_assist,
                    fill_power, fill_speed, fill_line_interval, fill_air_assist,
                    user_notes, is_builtin
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                preset.name, preset.category, preset.thickness, preset.description,
                preset.cut_power, preset.cut_speed, preset.cut_passes,
                int(preset.cut_air_assist), preset.cut_z_offset,
                preset.engrave_power, preset.engrave_speed, preset.engrave_dpi,
                int(preset.engrave_air_assist),
                preset.fill_power, preset.fill_speed, preset.fill_line_interval,
                int(preset.fill_air_assist),
                preset.user_notes, int(preset.is_builtin)
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            if should_close:
                conn.close()
    
    def get_material(self, material_id: int) -> Optional[MaterialPreset]:
        """Get a material by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM materials WHERE id = ?",
                (material_id,)
            ).fetchone()
            
            if row:
                return self._row_to_preset(row)
        return None
    
    def get_all_materials(self) -> List[MaterialPreset]:
        """Get all materials."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM materials ORDER BY category, name"
            ).fetchall()
            
            return [self._row_to_preset(row) for row in rows]
    
    def get_materials_by_category(self, category: str) -> List[MaterialPreset]:
        """Get materials in a specific category."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM materials WHERE category = ? ORDER BY name",
                (category,)
            ).fetchall()
            
            return [self._row_to_preset(row) for row in rows]
    
    def get_categories(self) -> List[str]:
        """Get list of all categories."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT category FROM materials ORDER BY category"
            ).fetchall()
            
            return [row[0] for row in rows if row[0]]
    
    def search_materials(self, query: str) -> List[MaterialPreset]:
        """Search materials by name or description."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT * FROM materials 
                   WHERE name LIKE ? OR description LIKE ?
                   ORDER BY name""",
                (f"%{query}%", f"%{query}%")
            ).fetchall()
            
            return [self._row_to_preset(row) for row in rows]
    
    def update_material(self, preset: MaterialPreset) -> bool:
        """Update an existing material."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE materials SET
                    name = ?, category = ?, thickness = ?, description = ?,
                    cut_power = ?, cut_speed = ?, cut_passes = ?,
                    cut_air_assist = ?, cut_z_offset = ?,
                    engrave_power = ?, engrave_speed = ?, engrave_dpi = ?,
                    engrave_air_assist = ?,
                    fill_power = ?, fill_speed = ?, fill_line_interval = ?,
                    fill_air_assist = ?, user_notes = ?
                WHERE id = ?
            """, (
                preset.name, preset.category, preset.thickness, preset.description,
                preset.cut_power, preset.cut_speed, preset.cut_passes,
                int(preset.cut_air_assist), preset.cut_z_offset,
                preset.engrave_power, preset.engrave_speed, preset.engrave_dpi,
                int(preset.engrave_air_assist),
                preset.fill_power, preset.fill_speed, preset.fill_line_interval,
                int(preset.fill_air_assist), preset.user_notes,
                preset.id
            ))
            conn.commit()
            return conn.total_changes > 0
    
    def delete_material(self, material_id: int) -> bool:
        """Delete a material (only user-defined)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM materials WHERE id = ? AND is_builtin = 0",
                (material_id,)
            )
            conn.commit()
            return conn.total_changes > 0
    
    def export_to_json(self, filepath: str):
        """Export all user materials to JSON."""
        materials = self.get_all_materials()
        user_materials = [m for m in materials if not m.is_builtin]
        
        with open(filepath, 'w') as f:
            json.dump([m.to_dict() for m in user_materials], f, indent=2)
    
    def import_from_json(self, filepath: str) -> int:
        """Import materials from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        count = 0
        for item in data:
            preset = MaterialPreset.from_dict(item)
            preset.id = -1  # Force new ID
            preset.is_builtin = False
            self.add_material(preset)
            count += 1
        
        return count
    
    def _row_to_preset(self, row: sqlite3.Row) -> MaterialPreset:
        """Convert database row to MaterialPreset."""
        return MaterialPreset(
            id=row['id'],
            name=row['name'],
            category=row['category'] or "",
            thickness=row['thickness'] or 0,
            description=row['description'] or "",
            cut_power=row['cut_power'] or 0,
            cut_speed=row['cut_speed'] or 0,
            cut_passes=row['cut_passes'] or 1,
            cut_air_assist=bool(row['cut_air_assist']),
            cut_z_offset=row['cut_z_offset'] or 0,
            engrave_power=row['engrave_power'] or 0,
            engrave_speed=row['engrave_speed'] or 0,
            engrave_dpi=row['engrave_dpi'] or 254,
            engrave_air_assist=bool(row['engrave_air_assist']),
            fill_power=row['fill_power'] or 0,
            fill_speed=row['fill_speed'] or 0,
            fill_line_interval=row['fill_line_interval'] or 0.1,
            fill_air_assist=bool(row['fill_air_assist']),
            user_notes=row['user_notes'] or "",
            is_builtin=bool(row['is_builtin'])
        )
```

---

## 13. Camera Integration

### 13.1 Camera Capture and Overlay

```python
# src/camera/capture.py

"""
Camera Capture Module

Provides camera access for alignment and positioning features.
Uses OpenCV for cross-platform camera support.
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List, Callable
from dataclasses import dataclass
import threading
import time


@dataclass
class CameraCalibration:
    """Camera calibration data."""
    # Camera matrix and distortion coefficients
    camera_matrix: Optional[np.ndarray] = None
    dist_coeffs: Optional[np.ndarray] = None
    
    # Workspace mapping (camera pixels to laser mm)
    transform_matrix: Optional[np.ndarray] = None
    
    # Reference points (4 corners in camera and laser space)
    camera_points: Optional[List[Tuple[float, float]]] = None
    laser_points: Optional[List[Tuple[float, float]]] = None
    
    # Scale and offset
    scale_x: float = 1.0
    scale_y: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    
    @property
    def is_calibrated(self) -> bool:
        return self.transform_matrix is not None


class CameraCapture:
    """
    Camera capture and processing.
    
    Features:
    - Live video capture
    - Distortion correction
    - Perspective transform
    - Frame callbacks for UI updates
    """
    
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.capture: Optional[cv2.VideoCapture] = None
        self.calibration = CameraCalibration()
        
        self._running = False
        self._capture_thread: Optional[threading.Thread] = None
        self._frame_callbacks: List[Callable[[np.ndarray], None]] = []
        self._last_frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
    
    @staticmethod
    def list_cameras() -> List[dict]:
        """List available cameras."""
        cameras = []
        
        # Try to open cameras 0-9
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cameras.append({
                    'index': i,
                    'name': f"Camera {i}",
                    'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                })
                cap.release()
        
        return cameras
    
    def open(self, width: int = 1280, height: int = 720) -> bool:
        """Open the camera."""
        self.capture = cv2.VideoCapture(self.camera_index)
        
        if not self.capture.isOpened():
            return False
        
        # Set resolution
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        return True
    
    def close(self):
        """Close the camera."""
        self.stop_capture()
        
        if self.capture:
            self.capture.release()
            self.capture = None
    
    def start_capture(self):
        """Start continuous capture in background."""
        if self._running:
            return
        
        if not self.capture or not self.capture.isOpened():
            if not self.open():
                return
        
        self._running = True
        self._capture_thread = threading.Thread(target=self._capture_loop)
        self._capture_thread.daemon = True
        self._capture_thread.start()
    
    def stop_capture(self):
        """Stop continuous capture."""
        self._running = False
        
        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None
    
    def add_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """Register callback for new frames."""
        self._frame_callbacks.append(callback)
    
    def remove_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """Remove frame callback."""
        if callback in self._frame_callbacks:
            self._frame_callbacks.remove(callback)
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get the latest frame."""
        with self._lock:
            if self._last_frame is not None:
                return self._last_frame.copy()
        return None
    
    def capture_single(self) -> Optional[np.ndarray]:
        """Capture a single frame."""
        if not self.capture or not self.capture.isOpened():
            if not self.open():
                return None
        
        ret, frame = self.capture.read()
        if ret:
            return self._process_frame(frame)
        return None
    
    def _capture_loop(self):
        """Background capture loop."""
        while self._running and self.capture:
            ret, frame = self.capture.read()
            
            if ret:
                processed = self._process_frame(frame)
                
                with self._lock:
                    self._last_frame = processed
                
                # Notify callbacks
                for callback in self._frame_callbacks:
                    try:
                        callback(processed)
                    except Exception as e:
                        print(f"Frame callback error: {e}")
            
            time.sleep(0.033)  # ~30 fps
    
    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Process captured frame."""
        # Apply distortion correction if calibrated
        if (self.calibration.camera_matrix is not None and
            self.calibration.dist_coeffs is not None):
            frame = cv2.undistort(
                frame,
                self.calibration.camera_matrix,
                self.calibration.dist_coeffs
            )
        
        # Apply perspective transform if calibrated
        if self.calibration.transform_matrix is not None:
            h, w = frame.shape[:2]
            frame = cv2.warpPerspective(
                frame,
                self.calibration.transform_matrix,
                (w, h)
            )
        
        return frame
    
    def camera_to_laser(self, camera_x: float, 
                        camera_y: float) -> Tuple[float, float]:
        """Convert camera coordinates to laser coordinates."""
        if not self.calibration.is_calibrated:
            # Simple linear transform
            laser_x = camera_x * self.calibration.scale_x + self.calibration.offset_x
            laser_y = camera_y * self.calibration.scale_y + self.calibration.offset_y
            return laser_x, laser_y
        
        # Use perspective transform
        point = np.array([[[camera_x, camera_y]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(
            point, self.calibration.transform_matrix
        )
        return float(transformed[0][0][0]), float(transformed[0][0][1])
    
    def laser_to_camera(self, laser_x: float, 
                        laser_y: float) -> Tuple[float, float]:
        """Convert laser coordinates to camera coordinates."""
        if not self.calibration.is_calibrated:
            # Simple linear transform
            camera_x = (laser_x - self.calibration.offset_x) / self.calibration.scale_x
            camera_y = (laser_y - self.calibration.offset_y) / self.calibration.scale_y
            return camera_x, camera_y
        
        # Use inverse transform
        inv_matrix = np.linalg.inv(self.calibration.transform_matrix)
        point = np.array([[[laser_x, laser_y]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(point, inv_matrix)
        return float(transformed[0][0][0]), float(transformed[0][0][1])
    
    def calibrate_from_points(self, 
                              camera_points: List[Tuple[float, float]],
                              laser_points: List[Tuple[float, float]]) -> bool:
        """
        Calibrate camera using 4 corresponding points.
        
        Args:
            camera_points: 4 points in camera pixel coordinates
            laser_points: Corresponding 4 points in laser mm coordinates
        
        Returns:
            True if calibration successful
        """
        if len(camera_points) != 4 or len(laser_points) != 4:
            return False
        
        src = np.array(camera_points, dtype=np.float32)
        dst = np.array(laser_points, dtype=np.float32)
        
        # Compute perspective transform
        matrix = cv2.getPerspectiveTransform(src, dst)
        
        self.calibration.camera_points = camera_points
        self.calibration.laser_points = laser_points
        self.calibration.transform_matrix = matrix
        
        return True
    
    def save_calibration(self, filepath: str):
        """Save calibration data to file."""
        data = {
            'camera_matrix': self.calibration.camera_matrix.tolist() 
                if self.calibration.camera_matrix is not None else None,
            'dist_coeffs': self.calibration.dist_coeffs.tolist()
                if self.calibration.dist_coeffs is not None else None,
            'transform_matrix': self.calibration.transform_matrix.tolist()
                if self.calibration.transform_matrix is not None else None,
            'camera_points': self.calibration.camera_points,
            'laser_points': self.calibration.laser_points,
            'scale_x': self.calibration.scale_x,
            'scale_y': self.calibration.scale_y,
            'offset_x': self.calibration.offset_x,
            'offset_y': self.calibration.offset_y
        }
        
        import json
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_calibration(self, filepath: str) -> bool:
        """Load calibration data from file."""
        import json
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            if data.get('camera_matrix'):
                self.calibration.camera_matrix = np.array(data['camera_matrix'])
            if data.get('dist_coeffs'):
                self.calibration.dist_coeffs = np.array(data['dist_coeffs'])
            if data.get('transform_matrix'):
                self.calibration.transform_matrix = np.array(data['transform_matrix'])
            
            self.calibration.camera_points = data.get('camera_points')
            self.calibration.laser_points = data.get('laser_points')
            self.calibration.scale_x = data.get('scale_x', 1.0)
            self.calibration.scale_y = data.get('scale_y', 1.0)
            self.calibration.offset_x = data.get('offset_x', 0.0)
            self.calibration.offset_y = data.get('offset_y', 0.0)
            
            return True
        except Exception as e:
            print(f"Failed to load calibration: {e}")
            return False
```

---

## 14. Testing Strategy

### 14.1 Test Structure

```python
# tests/test_core/test_shapes.py

"""
Unit tests for shape classes.
"""

import pytest
import math
from src.core.shapes import (
    Point, BoundingBox, Rectangle, Ellipse, Path,
    flatten_cubic_bezier, point_in_polygon
)


class TestPoint:
    """Tests for Point class."""
    
    def test_creation(self):
        p = Point(10.0, 20.0)
        assert p.x == 10.0
        assert p.y == 20.0
    
    def test_addition(self):
        p1 = Point(10, 20)
        p2 = Point(5, 10)
        result = p1 + p2
        assert result.x == 15
        assert result.y == 30
    
    def test_subtraction(self):
        p1 = Point(10, 20)
        p2 = Point(5, 10)
        result = p1 - p2
        assert result.x == 5
        assert result.y == 10
    
    def test_distance(self):
        p1 = Point(0, 0)
        p2 = Point(3, 4)
        assert p1.distance_to(p2) == 5.0
    
    def test_rotation(self):
        p = Point(1, 0)
        rotated = p.rotate(math.pi / 2)  # 90 degrees
        assert abs(rotated.x) < 0.0001
        assert abs(rotated.y - 1) < 0.0001


class TestBoundingBox:
    """Tests for BoundingBox class."""
    
    def test_creation(self):
        bb = BoundingBox(0, 0, 100, 50)
        assert bb.width == 100
        assert bb.height == 50
    
    def test_center(self):
        bb = BoundingBox(0, 0, 100, 50)
        center = bb.center
        assert center.x == 50
        assert center.y == 25
    
    def test_contains_inside(self):
        bb = BoundingBox(0, 0, 100, 100)
        assert bb.contains(Point(50, 50))
    
    def test_contains_outside(self):
        bb = BoundingBox(0, 0, 100, 100)
        assert not bb.contains(Point(150, 50))
    
    def test_intersects_overlap(self):
        bb1 = BoundingBox(0, 0, 100, 100)
        bb2 = BoundingBox(50, 50, 150, 150)
        assert bb1.intersects(bb2)
    
    def test_intersects_no_overlap(self):
        bb1 = BoundingBox(0, 0, 100, 100)
        bb2 = BoundingBox(200, 200, 300, 300)
        assert not bb1.intersects(bb2)


class TestRectangle:
    """Tests for Rectangle class."""
    
    def test_creation(self):
        rect = Rectangle(10, 20, 100, 50)
        assert rect.position.x == 10
        assert rect.position.y == 20
        assert rect.width == 100
        assert rect.height == 50
    
    def test_get_paths_simple(self):
        rect = Rectangle(0, 0, 100, 50)
        paths = rect.get_paths()
        assert len(paths) == 1
        assert len(paths[0]) == 5  # 4 corners + close
    
    def test_get_paths_rounded(self):
        rect = Rectangle(0, 0, 100, 50, corner_radius=10)
        paths = rect.get_paths()
        assert len(paths) == 1
        assert len(paths[0]) > 5  # More points for curves
    
    def test_bounding_box(self):
        rect = Rectangle(10, 20, 100, 50)
        bb = rect.get_bounding_box()
        assert bb.min_x == 10
        assert bb.min_y == 20
        assert bb.max_x == 110
        assert bb.max_y == 70
    
    def test_clone(self):
        rect = Rectangle(10, 20, 100, 50)
        clone = rect.clone()
        assert clone.position.x == rect.position.x
        assert clone.width == rect.width
        assert clone.id != rect.id  # Different ID


class TestEllipse:
    """Tests for Ellipse class."""
    
    def test_creation(self):
        ellipse = Ellipse(50, 50, 30, 20)
        assert ellipse.position.x == 50
        assert ellipse.position.y == 50
        assert ellipse.radius_x == 30
        assert ellipse.radius_y == 20
    
    def test_get_paths(self):
        ellipse = Ellipse(50, 50, 30, 20)
        paths = ellipse.get_paths()
        assert len(paths) == 1
        assert len(paths[0]) >= 32  # At least 32 segments
    
    def test_contains_point_inside(self):
        ellipse = Ellipse(50, 50, 30, 20)
        assert ellipse.contains_point(Point(50, 50))  # Center
    
    def test_contains_point_outside(self):
        ellipse = Ellipse(50, 50, 30, 20)
        assert not ellipse.contains_point(Point(100, 100))


class TestPath:
    """Tests for Path class."""
    
    def test_line_path(self):
        path = Path()
        path.move_to(0, 0)
        path.line_to(100, 0)
        path.line_to(100, 100)
        
        paths = path.get_paths()
        assert len(paths) == 1
        assert len(paths[0]) == 3
    
    def test_closed_path(self):
        path = Path()
        path.move_to(0, 0)
        path.line_to(100, 0)
        path.line_to(100, 100)
        path.close()
        
        paths = path.get_paths()
        assert len(paths) == 1
        assert paths[0][0].x == paths[0][-1].x
        assert paths[0][0].y == paths[0][-1].y


class TestBezierFlattening:
    """Tests for bezier curve flattening."""
    
    def test_flatten_straight_line(self):
        # Bezier that's actually a straight line
        p0 = Point(0, 0)
        p1 = Point(33, 0)
        p2 = Point(66, 0)
        p3 = Point(100, 0)
        
        points = flatten_cubic_bezier(p0, p1, p2, p3, tolerance=0.1)
        
        # Should be relatively few points
        assert len(points) <= 10
        
        # All points should be on x-axis
        for p in points:
            assert abs(p.y) < 0.1
    
    def test_flatten_curve(self):
        p0 = Point(0, 0)
        p1 = Point(0, 100)
        p2 = Point(100, 100)
        p3 = Point(100, 0)
        
        points = flatten_cubic_bezier(p0, p1, p2, p3, tolerance=0.1)
        
        # Should produce multiple points
        assert len(points) > 4
        
        # First and last should match
        assert points[0].x == 0 and points[0].y == 0
        assert abs(points[-1].x - 100) < 0.1
        assert abs(points[-1].y) < 0.1


class TestPointInPolygon:
    """Tests for point-in-polygon algorithm."""
    
    def test_square_inside(self):
        square = [Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)]
        assert point_in_polygon(Point(50, 50), square)
    
    def test_square_outside(self):
        square = [Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)]
        assert not point_in_polygon(Point(150, 50), square)
    
    def test_square_on_edge(self):
        square = [Point(0, 0), Point(100, 0), Point(100, 100), Point(0, 100)]
        # Edge cases can vary by implementation
        pass  # Implementation-dependent
```

### 14.2 Running Tests

```bash
# Install test dependencies
pip install pytest pytest-qt pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_core/test_shapes.py -v

# Run tests matching pattern
pytest tests/ -k "test_rectangle" -v
```

---

## 15. Deployment

### 15.1 PyInstaller Configuration

```python
# scripts/build.py

"""
Build script for creating standalone executables.
"""

import PyInstaller.__main__
import sys
import os

# Application info
APP_NAME = "LaserBurn"
VERSION = "1.0.0"

# Entry point
ENTRY_POINT = "src/main.py"

# Build options
common_opts = [
    ENTRY_POINT,
    f'--name={APP_NAME}',
    '--windowed',
    '--onedir',
    '--clean',
    '--noconfirm',
    
    # Add data files
    '--add-data=resources:resources',
    
    # Hidden imports (modules that PyInstaller misses)
    '--hidden-import=PyQt6.QtSvg',
    '--hidden-import=cv2',
    '--hidden-import=pyclipper',
    
    # Exclude unnecessary modules
    '--exclude-module=matplotlib',
    '--exclude-module=scipy',
    '--exclude-module=pandas',
]

# Platform-specific options
if sys.platform == 'win32':
    platform_opts = [
        '--icon=resources/icons/laserburn.ico',
    ]
elif sys.platform == 'darwin':
    platform_opts = [
        '--icon=resources/icons/laserburn.icns',
        '--osx-bundle-identifier=com.laserburn.app',
    ]
else:
    platform_opts = []

# Run PyInstaller
PyInstaller.__main__.run(common_opts + platform_opts)
```

### 15.2 Installer Creation (Windows)

```nsis
; laserburn.nsi - NSIS Installer Script

!define APP_NAME "LaserBurn"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "LaserBurn Team"
!define APP_URL "https://laserburn.app"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "LaserBurn-${APP_VERSION}-Setup.exe"
InstallDir "$PROGRAMFILES\${APP_NAME}"
RequestExecutionLevel admin

; Pages
Page directory
Page instfiles

Section "Install"
    SetOutPath "$INSTDIR"
    
    ; Copy all files
    File /r "dist\LaserBurn\*.*"
    
    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\LaserBurn.exe"
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\LaserBurn.exe"
    
    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    ; Registry entries for Add/Remove Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayName" "${APP_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "Publisher" "${APP_PUBLISHER}"
SectionEnd

Section "Uninstall"
    ; Remove files
    RMDir /r "$INSTDIR"
    
    ; Remove shortcuts
    Delete "$SMPROGRAMS\${APP_NAME}\*.*"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"
    
    ; Remove registry entries
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
SectionEnd
```

---

## Quick Reference

### Key Commands to Remember

```bash
# Setup development environment
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run the application
python -m src.main

# Run tests
pytest tests/ -v

# Build executable
python scripts/build.py

# Format code
black src/ tests/

# Type checking
mypy src/
```

### Important Libraries

| Library | Purpose | Documentation |
|---------|---------|---------------|
| PyQt6 | GUI Framework | https://doc.qt.io/qtforpython-6/ |
| OpenCV | Image Processing | https://docs.opencv.org/ |
| pyclipper | Boolean Operations | https://pypi.org/project/pyclipper/ |
| pyserial | Serial Communication | https://pyserial.readthedocs.io/ |
| ezdxf | DXF File Support | https://ezdxf.readthedocs.io/ |
| NumPy | Numerical Computing | https://numpy.org/doc/ |
| Pillow | Image Handling | https://pillow.readthedocs.io/ |

---

## Conclusion

This guide provides a comprehensive roadmap for developing LaserBurn, a laser engraving software with feature parity to LightBurn. The key milestones are:

1. **Phase 1 (Weeks 1-4):** Core infrastructure - shapes, paths, document model
2. **Phase 2 (Weeks 5-8):** File I/O - SVG, DXF parsing and export
3. **Phase 3 (Weeks 9-12):** Graphics engine - canvas, tools, selection
4. **Phase 4 (Weeks 13-16):** Laser control - G-code generation, GRBL communication
5. **Phase 5 (Weeks 17-20):** Image processing - dithering, tracing
6. **Phase 6 (Weeks 21-24):** Polish - UI refinement, testing, documentation

Remember:
- Start with the core data structures
- Build incrementally and test continuously
- Reference LightBurn's UX for design decisions
- Engage with the laser cutting community for feedback

Good luck with your development!

