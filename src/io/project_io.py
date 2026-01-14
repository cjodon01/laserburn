"""
Project File I/O for LaserBurn

Handles saving and loading .lbrn project files.
Uses JSON format with base64 encoding for binary data (images).
"""

import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from ..core.document import Document
from ..core.layer import Layer
from ..core.shapes import (
    Shape, Rectangle, Ellipse, Path, Text, ImageShape,
    Point, LaserSettings, PathSegment,
    MoveToSegment, LineToSegment, CubicBezierSegment, QuadraticBezierSegment
)


def save_project(document: Document, filepath: str) -> bool:
    """
    Save a document to a .lbrn project file.
    
    Args:
        document: The document to save
        filepath: Path to save the file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Convert document to dictionary
        doc_dict = document_to_dict(document)
        
        # Add metadata
        doc_dict['version'] = '1.0'
        doc_dict['saved_at'] = datetime.now().isoformat()
        
        # Update document modified time
        document.modified_at = doc_dict['saved_at']
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(doc_dict, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"Error saving project: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_project(filepath: str) -> Optional[Document]:
    """
    Load a document from a .lbrn project file.
    
    Args:
        filepath: Path to the project file
        
    Returns:
        Document object if successful, None otherwise
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            doc_dict = json.load(f)
        
        # Convert dictionary to document
        document = dict_to_document(doc_dict)
        
        return document
    except Exception as e:
        print(f"Error loading project: {e}")
        import traceback
        traceback.print_exc()
        return None


def document_to_dict(document: Document) -> Dict[str, Any]:
    """Convert Document to dictionary."""
    doc_dict = {
        'id': str(document.id),
        'name': document.name,
        'width': document.width,
        'height': document.height,
        'device_profile': document.device_profile,
        'origin': document.origin,
        'cylinder_warp_image': document.cylinder_warp_image,
        'cylinder_compensate_power': document.cylinder_compensate_power,
        'cylinder_compensate_z': document.cylinder_compensate_z,
        'created_at': document.created_at,
        'modified_at': document.modified_at,
        'layers': [layer_to_dict(layer) for layer in document.layers]
    }
    
    # Handle cylinder params
    if document.cylinder_params:
        doc_dict['cylinder_params'] = {
            'radius': document.cylinder_params.radius,
            'height': document.cylinder_params.height,
            'center_x': document.cylinder_params.center_x,
            'center_y': document.cylinder_params.center_y
        }
    
    return doc_dict


def dict_to_document(doc_dict: Dict[str, Any]) -> Document:
    """Convert dictionary to Document."""
    from uuid import UUID, uuid4
    
    # Parse UUID safely
    doc_id = uuid4()
    if 'id' in doc_dict:
        try:
            doc_id = UUID(doc_dict['id'])
        except (ValueError, TypeError):
            pass  # Use default uuid4()
    
    document = Document(
        id=doc_id,
        name=doc_dict.get('name', 'Untitled'),
        width=doc_dict.get('width', 300.0),
        height=doc_dict.get('height', 200.0),
        device_profile=doc_dict.get('device_profile'),
        origin=doc_dict.get('origin', 'bottom-left'),
        cylinder_warp_image=doc_dict.get('cylinder_warp_image', False),
        cylinder_compensate_power=doc_dict.get('cylinder_compensate_power', False),
        cylinder_compensate_z=doc_dict.get('cylinder_compensate_z', False),
        created_at=doc_dict.get('created_at', ''),
        modified_at=doc_dict.get('modified_at', '')
    )
    
    # Handle cylinder params
    if 'cylinder_params' in doc_dict and doc_dict['cylinder_params']:
        from ..image.cylinder_warp import CylinderParams
        cp = doc_dict['cylinder_params']
        document.cylinder_params = CylinderParams(
            radius=cp.get('radius', 50.0),
            height=cp.get('height', 100.0),
            center_x=cp.get('center_x', 0.0),
            center_y=cp.get('center_y', 0.0)
        )
    
    # Load layers
    for layer_dict in doc_dict.get('layers', []):
        layer = dict_to_layer(layer_dict)
        document.add_layer(layer)
    
    return document


def layer_to_dict(layer: Layer) -> Dict[str, Any]:
    """Convert Layer to dictionary."""
    from uuid import UUID
    
    return {
        'id': str(layer.id),
        'name': layer.name,
        'visible': layer.visible,
        'locked': layer.locked,
        'color': layer.color,
        'cut_order': layer.cut_order,
        'use_layer_settings': layer.use_layer_settings,
        'laser_settings': laser_settings_to_dict(layer.laser_settings),
        'shapes': [shape_to_dict(shape) for shape in layer.shapes]
    }


def dict_to_layer(layer_dict: Dict[str, Any]) -> Layer:
    """Convert dictionary to Layer."""
    from uuid import UUID, uuid4
    
    # Parse UUID safely
    layer_id = uuid4()
    if 'id' in layer_dict:
        try:
            layer_id = UUID(layer_dict['id'])
        except (ValueError, TypeError):
            pass  # Use default uuid4()
    
    layer = Layer(
        id=layer_id,
        name=layer_dict.get('name', 'Layer'),
        visible=layer_dict.get('visible', True),
        locked=layer_dict.get('locked', False),
        color=layer_dict.get('color', '#0000FF'),
        cut_order=layer_dict.get('cut_order', 0),
        use_layer_settings=layer_dict.get('use_layer_settings', True)
    )
    
    # Load laser settings
    if 'laser_settings' in layer_dict:
        layer.laser_settings = dict_to_laser_settings(layer_dict['laser_settings'])
    
    # Load shapes
    for shape_dict in layer_dict.get('shapes', []):
        shape = dict_to_shape(shape_dict)
        if shape:
            layer.add_shape(shape)
    
    return layer


def laser_settings_to_dict(settings: LaserSettings) -> Dict[str, Any]:
    """Convert LaserSettings to dictionary."""
    return {
        'power': settings.power,
        'speed': settings.speed,
        'passes': settings.passes,
        'z_offset': settings.z_offset,
        'air_assist': settings.air_assist,
        'line_interval': settings.line_interval,
        'operation': settings.operation,
        'fill_enabled': settings.fill_enabled,
        'fill_pattern': settings.fill_pattern,
        'fill_angle': settings.fill_angle
    }


def dict_to_laser_settings(settings_dict: Dict[str, Any]) -> LaserSettings:
    """Convert dictionary to LaserSettings."""
    return LaserSettings(
        power=settings_dict.get('power', 50.0),
        speed=settings_dict.get('speed', 100.0),
        passes=settings_dict.get('passes', 1),
        z_offset=settings_dict.get('z_offset', 0.0),
        air_assist=settings_dict.get('air_assist', True),
        line_interval=settings_dict.get('line_interval', 0.1),
        operation=settings_dict.get('operation', 'cut'),
        fill_enabled=settings_dict.get('fill_enabled', False),
        fill_pattern=settings_dict.get('fill_pattern', 'horizontal'),
        fill_angle=settings_dict.get('fill_angle', 0.0)
    )


def shape_to_dict(shape: Shape) -> Dict[str, Any]:
    """Convert Shape to dictionary."""
    from uuid import UUID
    
    base_dict = {
        'type': shape.__class__.__name__,
        'id': str(shape.id),
        'name': shape.name,
        'visible': shape.visible,
        'locked': shape.locked,
        'position': {'x': shape.position.x, 'y': shape.position.y},
        'rotation': shape.rotation,
        'scale_x': shape.scale_x,
        'scale_y': shape.scale_y,
        'laser_settings': laser_settings_to_dict(shape.laser_settings)
    }
    
    # Add type-specific data
    if isinstance(shape, Rectangle):
        base_dict.update({
            'width': shape.width,
            'height': shape.height,
            'corner_radius': shape.corner_radius
        })
    elif isinstance(shape, Ellipse):
        base_dict.update({
            'radius_x': shape.radius_x,
            'radius_y': shape.radius_y
        })
    elif isinstance(shape, Text):
        base_dict.update({
            'text': shape.text,
            'font_family': shape.font_family,
            'font_size': shape.font_size,
            'bold': shape.bold,
            'italic': shape.italic
        })
    elif isinstance(shape, Path):
        base_dict.update({
            'segments': [path_segment_to_dict(seg) for seg in shape.segments],
            'closed': shape.closed
        })
    elif isinstance(shape, ImageShape):
        base_dict.update({
            'width': shape.width,
            'height': shape.height,
            'filepath': shape.filepath,
            'dpi': shape.dpi,
            'invert': shape.invert,
            'threshold': shape.threshold,
            'dither_mode': shape.dither_mode,
            'brightness': getattr(shape, 'brightness', 0.0),
            'contrast': getattr(shape, 'contrast', 1.0),
            'skip_white': getattr(shape, 'skip_white', True),
            'white_threshold': getattr(shape, 'white_threshold', 250)
        })
        # Encode image data as base64
        if shape.image_data is not None and HAS_NUMPY:
            # Convert numpy array to base64
            image_bytes = shape.image_data.tobytes()
            base_dict['image_data'] = base64.b64encode(image_bytes).decode('utf-8')
            base_dict['image_shape'] = list(shape.image_data.shape)
            base_dict['image_dtype'] = str(shape.image_data.dtype)
        
        # Encode alpha channel if present
        if hasattr(shape, 'alpha_channel') and shape.alpha_channel is not None and HAS_NUMPY:
            alpha_bytes = shape.alpha_channel.tobytes()
            base_dict['alpha_channel'] = base64.b64encode(alpha_bytes).decode('utf-8')
            base_dict['alpha_shape'] = list(shape.alpha_channel.shape)
            base_dict['alpha_dtype'] = str(shape.alpha_channel.dtype)
    
    return base_dict


def dict_to_shape(shape_dict: Dict[str, Any]) -> Optional[Shape]:
    """Convert dictionary to Shape."""
    from uuid import UUID, uuid4
    
    shape_type = shape_dict.get('type')
    if not shape_type:
        return None
    
    # Parse UUID safely
    shape_id = uuid4()
    if 'id' in shape_dict:
        try:
            shape_id = UUID(shape_dict['id'])
        except (ValueError, TypeError):
            pass  # Use default uuid4()
    
    # Get base properties
    position = Point(
        shape_dict['position']['x'],
        shape_dict['position']['y']
    )
    rotation = shape_dict.get('rotation', 0.0)
    scale_x = shape_dict.get('scale_x', 1.0)
    scale_y = shape_dict.get('scale_y', 1.0)
    laser_settings = dict_to_laser_settings(shape_dict.get('laser_settings', {}))
    
    # Create shape based on type
    if shape_type == 'Rectangle':
        shape = Rectangle(
            position.x, position.y,
            shape_dict.get('width', 100.0),
            shape_dict.get('height', 100.0),
            shape_dict.get('corner_radius', 0.0)
        )
    elif shape_type == 'Ellipse':
        shape = Ellipse(
            position.x, position.y,
            shape_dict.get('radius_x', 50.0),
            shape_dict.get('radius_y', 50.0)
        )
    elif shape_type == 'Text':
        shape = Text(
            position.x, position.y,
            shape_dict.get('text', ''),
            shape_dict.get('font_family', 'Arial'),
            shape_dict.get('font_size', 12.0),
            shape_dict.get('bold', False),
            shape_dict.get('italic', False)
        )
    elif shape_type == 'Path':
        shape = Path()
        # Load segments
        for seg_dict in shape_dict.get('segments', []):
            seg = dict_to_path_segment(seg_dict)
            if seg:
                shape.segments.append(seg)
        shape.closed = shape_dict.get('closed', False)
    elif shape_type == 'ImageShape':
        shape = ImageShape(
            position.x, position.y,
            shape_dict.get('width', 100.0),
            shape_dict.get('height', 100.0),
            image_data=None,  # Will load below
            filepath=shape_dict.get('filepath', '')
        )
        shape.dpi = shape_dict.get('dpi', 254.0)
        shape.invert = shape_dict.get('invert', False)
        shape.threshold = shape_dict.get('threshold', 128)
        shape.dither_mode = shape_dict.get('dither_mode', 'floyd_steinberg')
        shape.brightness = shape_dict.get('brightness', 0.0)
        shape.contrast = shape_dict.get('contrast', 1.0)
        shape.skip_white = shape_dict.get('skip_white', True)
        shape.white_threshold = shape_dict.get('white_threshold', 250)
        
        # Decode image data from base64
        if 'image_data' in shape_dict and HAS_NUMPY:
            try:
                image_bytes = base64.b64decode(shape_dict['image_data'])
                shape_info = shape_dict.get('image_shape', [1, 1])
                dtype_str = shape_dict.get('image_dtype', 'uint8')
                dtype = np.dtype(dtype_str)
                shape.image_data = np.frombuffer(image_bytes, dtype=dtype).reshape(shape_info)
            except Exception as e:
                print(f"Warning: Could not decode image data: {e}")
                shape.image_data = None
        
        # Decode alpha channel from base64 if present
        if 'alpha_channel' in shape_dict and HAS_NUMPY:
            try:
                alpha_bytes = base64.b64decode(shape_dict['alpha_channel'])
                alpha_info = shape_dict.get('alpha_shape', [1, 1])
                dtype_str = shape_dict.get('alpha_dtype', 'uint8')
                dtype = np.dtype(dtype_str)
                shape.alpha_channel = np.frombuffer(alpha_bytes, dtype=dtype).reshape(alpha_info)
            except Exception as e:
                print(f"Warning: Could not decode alpha channel: {e}")
                shape.alpha_channel = None
    else:
        print(f"Warning: Unknown shape type: {shape_type}")
        return None
    
    # Set common properties
    shape.id = shape_id
    shape.name = shape_dict.get('name', '')
    shape.visible = shape_dict.get('visible', True)
    shape.locked = shape_dict.get('locked', False)
    shape.rotation = rotation
    shape.scale_x = scale_x
    shape.scale_y = scale_y
    shape.laser_settings = laser_settings
    
    return shape


def path_segment_to_dict(segment: PathSegment) -> Dict[str, Any]:
    """Convert PathSegment to dictionary."""
    if isinstance(segment, MoveToSegment):
        return {
            'type': 'MoveTo',
            'point': {'x': segment.point.x, 'y': segment.point.y}
        }
    elif isinstance(segment, LineToSegment):
        return {
            'type': 'LineTo',
            'point': {'x': segment.point.x, 'y': segment.point.y}
        }
    elif isinstance(segment, CubicBezierSegment):
        return {
            'type': 'CubicBezier',
            'cp1': {'x': segment.cp1.x, 'y': segment.cp1.y},
            'cp2': {'x': segment.cp2.x, 'y': segment.cp2.y},
            'end_point': {'x': segment.end_point.x, 'y': segment.end_point.y}
        }
    elif isinstance(segment, QuadraticBezierSegment):
        return {
            'type': 'QuadraticBezier',
            'control_point': {'x': segment.control_point.x, 'y': segment.control_point.y},
            'end_point': {'x': segment.end_point.x, 'y': segment.end_point.y}
        }
    return {}


def dict_to_path_segment(seg_dict: Dict[str, Any]) -> Optional[PathSegment]:
    """Convert dictionary to PathSegment."""
    seg_type = seg_dict.get('type')
    
    if seg_type == 'MoveTo':
        pt = seg_dict.get('point', {})
        return MoveToSegment(Point(pt.get('x', 0), pt.get('y', 0)))
    elif seg_type == 'LineTo':
        pt = seg_dict.get('point', {})
        return LineToSegment(Point(pt.get('x', 0), pt.get('y', 0)))
    elif seg_type == 'CubicBezier':
        cp1 = seg_dict.get('cp1', {})
        cp2 = seg_dict.get('cp2', {})
        end = seg_dict.get('end_point', {})
        return CubicBezierSegment(
            Point(cp1.get('x', 0), cp1.get('y', 0)),
            Point(cp2.get('x', 0), cp2.get('y', 0)),
            Point(end.get('x', 0), end.get('y', 0))
        )
    elif seg_type == 'QuadraticBezier':
        cp = seg_dict.get('control_point', {})
        end = seg_dict.get('end_point', {})
        return QuadraticBezierSegment(
            Point(cp.get('x', 0), cp.get('y', 0)),
            Point(end.get('x', 0), end.get('y', 0))
        )
    
    return None
