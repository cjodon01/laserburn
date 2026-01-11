"""
Base classes for laser controller communication.

Provides abstract interface that all controller implementations
must follow, enabling support for multiple controller types.
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable, List
import serial
import serial.tools.list_ports
import threading
import queue
import time


class ConnectionState(Enum):
    """Controller connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    BUSY = "busy"
    ERROR = "error"
    ALARM = "alarm"


class JobState(Enum):
    """Job execution states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class ControllerStatus:
    """Current status of the laser controller."""
    state: ConnectionState = ConnectionState.DISCONNECTED
    job_state: JobState = JobState.IDLE
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    progress: float = 0.0  # 0-100%
    buffer_space: int = 0
    error_message: str = ""
    is_homed: bool = False


class LaserController(ABC):
    """
    Abstract base class for laser controllers.
    
    Implementations must provide:
    - connect/disconnect
    - send_command
    - home
    - jog
    - start_job/pause_job/stop_job
    - get_status
    """
    
    def __init__(self):
        self.status = ControllerStatus()
        self._status_callbacks: List[Callable[[ControllerStatus], None]] = []
        self._serial: Optional[serial.Serial] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._command_queue: queue.Queue = queue.Queue()
        self._running = False
    
    @abstractmethod
    def connect(self, port: str, baudrate: int = 115200) -> bool:
        """
        Connect to the controller.
        
        Args:
            port: Serial port (e.g., 'COM3', '/dev/ttyUSB0')
            baudrate: Communication speed
        
        Returns:
            True if connection successful
        """
        pass
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from the controller."""
        pass
    
    @abstractmethod
    def send_command(self, command: str, wait_for_ok: bool = True) -> str:
        """
        Send a command to the controller.
        
        Args:
            command: Command string (e.g., 'G0 X10')
            wait_for_ok: Wait for acknowledgment
        
        Returns:
            Response from controller
        """
        pass
    
    @abstractmethod
    def home(self, axes: str = "XY") -> bool:
        """
        Home the specified axes.
        
        Args:
            axes: Axes to home (e.g., 'XY', 'Z', 'XYZ')
        
        Returns:
            True if homing started successfully
        """
        pass
    
    @abstractmethod
    def jog(self, x: float = 0, y: float = 0, z: float = 0,
            speed: float = 1000, relative: bool = True) -> bool:
        """
        Jog the laser head.
        
        Args:
            x, y, z: Movement distances/positions
            speed: Movement speed in mm/min
            relative: True for relative movement
        
        Returns:
            True if jog command sent successfully
        """
        pass
    
    @abstractmethod
    def start_job(self, gcode: str) -> bool:
        """
        Start executing a G-code job.
        
        Args:
            gcode: Complete G-code program
        
        Returns:
            True if job started successfully
        """
        pass
    
    @abstractmethod
    def pause_job(self) -> bool:
        """Pause the current job."""
        pass
    
    @abstractmethod
    def resume_job(self) -> bool:
        """Resume a paused job."""
        pass
    
    @abstractmethod
    def stop_job(self) -> bool:
        """Stop and cancel the current job."""
        pass
    
    @abstractmethod
    def get_status(self) -> ControllerStatus:
        """Get current controller status."""
        pass
    
    def add_status_callback(self, callback: Callable[[ControllerStatus], None]):
        """Register callback for status updates."""
        self._status_callbacks.append(callback)
    
    def remove_status_callback(self, callback: Callable[[ControllerStatus], None]):
        """Remove a status callback."""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)
    
    def _notify_status(self):
        """Notify all callbacks of status change."""
        for callback in self._status_callbacks:
            try:
                callback(self.status)
            except Exception as e:
                print(f"Status callback error: {e}")
    
    @staticmethod
    def list_ports() -> List[dict]:
        """List available serial ports."""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'port': port.device,
                'description': port.description,
                'hwid': port.hwid
            })
        return ports


