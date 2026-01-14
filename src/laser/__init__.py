"""
LaserBurn Laser Module

Laser control and G-code generation.
"""

from .gcode_generator import GCodeGenerator, GCodeSettings, LaserMode
from .path_optimizer import (
    optimize_paths, optimize_closed_path_start,
    calculate_total_distance, estimate_job_time, OptimizedPath
)
from .controller import (
    LaserController, ControllerStatus, ConnectionState, JobState
)
from .grbl import GRBLController
from .job_manager import JobManager, LaserJob, JobPriority

__all__ = [
    # G-code generation
    'GCodeGenerator', 'GCodeSettings', 'LaserMode', 'StartFrom', 'JobOrigin',
    # Path optimization
    'optimize_paths', 'optimize_closed_path_start',
    'calculate_total_distance', 'estimate_job_time', 'OptimizedPath',
    # Controller base
    'LaserController', 'ControllerStatus', 'ConnectionState', 'JobState',
    # GRBL controller
    'GRBLController',
    # Job management
    'JobManager', 'LaserJob', 'JobPriority',
]
