"""
GRBL Controller Implementation

Supports GRBL 1.1 and compatible firmware (including laser-specific builds).
"""

import re
import time
import threading
import serial
import serial.tools.list_ports
from typing import Optional
from .controller import (
    LaserController, ControllerStatus, ConnectionState, JobState
)
import serial


class GRBLController(LaserController):
    """
    GRBL controller implementation.
    
    Supports:
    - GRBL 1.1+
    - GRBL-LPC
    - FluidNC (GRBL compatible mode)
    """
    
    # GRBL status parsing regex
    STATUS_REGEX = re.compile(
        r'<(\w+)\|MPos:(-?\d+\.?\d*),(-?\d+\.?\d*),(-?\d+\.?\d*)'
        r'(?:\|Bf:(\d+),(\d+))?'
        r'(?:\|FS:(\d+),(\d+))?'
    )
    
    # GRBL real-time commands (no newline needed)
    CMD_STATUS = b'?'
    CMD_SOFT_RESET = b'\x18'
    CMD_FEED_HOLD = b'!'
    CMD_CYCLE_START = b'~'
    
    def __init__(self):
        super().__init__()
        self._buffer_size = 128  # GRBL serial buffer size
        self._buffer_count = 0
        self._gcode_lines: list = []
        self._current_line: int = 0
        self._response_event = threading.Event()
        self._last_response = ""
        self._console_callbacks = []  # Callbacks for console output
        self._homing_in_progress = False
        self._previous_state = None
        # Machine work area limits (can be configured)
        # Defaults will be overridden by auto-detection or manual setting
        self._work_area_x = 400.0  # Default to 400mm (common size)
        self._work_area_y = 400.0
        self._work_area_z = 50.0
        # Max spindle speed - CRITICAL for correct power output
        # This MUST match GRBL's $30 setting for correct power levels
        # Common values: 255 (PWM), 1000 (common default), 10000 (some controllers)
        self._max_spindle_speed = 1000  # Default to 1000 (GRBL default)
    
    def connect(self, port: str, baudrate: int = 115200) -> bool:
        """Connect to GRBL controller."""
        # Check if already connected
        if self._serial and self._serial.is_open:
            self.status.error_message = "Already connected to a port"
            return False
        
        # Check if port exists in system
        if not self._is_port_available(port):
            self.status.state = ConnectionState.ERROR
            self.status.error_message = (
                f"Port {port} not found.\n\n"
                "Possible causes:\n"
                "- Device not connected\n"
                "- USB cable disconnected\n"
                "- Driver not installed\n\n"
                "Solutions:\n"
                "- Check Device Manager to verify port exists\n"
                "- Unplug and replug USB cable\n"
                "- Install USB-to-serial driver"
            )
            self._notify_status()
            return False
        
        try:
            self.status.state = ConnectionState.CONNECTING
            self._notify_status()
            
            # Open serial port with exclusive access (if supported)
            try:
                # Try with exclusive access first (pyserial 3.5+)
                self._serial = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    timeout=1.0,
                    write_timeout=1.0,
                    exclusive=True  # Request exclusive access on Windows
                )
            except TypeError:
                # Fallback for older pyserial versions
                self._serial = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    timeout=1.0,
                    write_timeout=1.0
                )
            
            # Wait for GRBL startup message
            time.sleep(2)
            
            # Clear any startup messages
            while self._serial.in_waiting:
                self._serial.readline()
            
            # Start reader thread
            self._running = True
            self._reader_thread = threading.Thread(target=self._read_loop)
            self._reader_thread.daemon = True
            self._reader_thread.start()
            
            # Query status to confirm connection
            self._send_realtime(self.CMD_STATUS)
            time.sleep(0.1)
            
            # CRITICAL SAFETY: Ensure laser is OFF immediately after connection
            # Some GRBL controllers may have laser enabled from previous session
            self.send_command("M5", wait_for_ok=False)  # Laser off - don't wait to avoid blocking
            time.sleep(0.1)  # Brief delay to allow command to be processed
            
            self.status.state = ConnectionState.CONNECTED
            self._notify_status()
            
            # Auto-detect work area from GRBL settings
            self._detect_work_area()
            
            # Auto-detect max spindle speed from $30 setting (CRITICAL for correct power)
            self._detect_max_spindle_speed()
            
            return True
            
        except serial.SerialException as e:
            error_msg = str(e)
            
            # Provide more helpful error messages
            if "access denied" in error_msg.lower() or "permission denied" in error_msg.lower():
                self.status.error_message = (
                    f"Access denied to {port}.\n\n"
                    "Possible causes:\n"
                    "- Port is already open in another application\n"
                    "- Another instance of LaserBurn is connected\n"
                    "- Device Manager or other tool has the port open\n\n"
                    "Solutions:\n"
                    "- Close other applications using this port\n"
                    "- Disconnect and reconnect the USB cable\n"
                    "- Restart your computer if the port is stuck"
                )
            elif "could not open port" in error_msg.lower():
                self.status.error_message = (
                    f"Could not open {port}.\n\n"
                    "Possible causes:\n"
                    "- Port does not exist\n"
                    "- Device not connected\n"
                    "- Driver not installed\n\n"
                    "Solutions:\n"
                    "- Check Device Manager to verify port exists\n"
                    "- Unplug and replug USB cable\n"
                    "- Install USB-to-serial driver"
                )
            else:
                self.status.error_message = f"Connection failed: {error_msg}"
            
            self.status.state = ConnectionState.ERROR
            self._notify_status()
            return False
        except Exception as e:
            self.status.state = ConnectionState.ERROR
            self.status.error_message = f"Unexpected error: {str(e)}"
            self._notify_status()
            return False
    
    def _is_port_available(self, port: str) -> bool:
        """
        Check if a serial port exists in the system.
        
        Note: This doesn't check if the port is in use, just if it exists.
        The actual availability check happens when we try to open it.
        
        Args:
            port: Port name to check
        
        Returns:
            True if port exists in system
        """
        try:
            # Check if port exists in the list of available ports
            available_ports = [p.device for p in serial.tools.list_ports.comports()]
            return port in available_ports
        except Exception:
            # If we can't check, assume it might exist and let connect() handle it
            return True
    
    def disconnect(self):
        """Disconnect from GRBL controller."""
        self._running = False
        
        # If a job is running, mark it as cancelled/error
        if self.status.job_state in (JobState.RUNNING, JobState.PAUSED):
            self.status.job_state = JobState.CANCELLED
            self.status.error_message = "Controller disconnected"
            self._notify_status()
        
        # Stop reader thread
        if self._reader_thread:
            self._reader_thread.join(timeout=2.0)
            self._reader_thread = None
        
        # Close serial port
        if self._serial:
            try:
                if self._serial.is_open:
                    # CRITICAL SAFETY: Turn off laser before disconnecting
                    try:
                        self.send_command("M5", wait_for_ok=False)  # Laser off
                        time.sleep(0.1)
                    except:
                        pass
                    # Send soft reset before closing
                    try:
                        self._serial.write(self.CMD_SOFT_RESET)
                        time.sleep(0.1)
                    except:
                        pass
                    self._serial.close()
            except Exception as e:
                print(f"Error closing serial port: {e}")
            finally:
                self._serial = None
        
        # Clear job state
        self._gcode_lines = []
        self._current_line = 0
        self._buffer_count = 0
        self.status.job_state = JobState.IDLE
        self.status.progress = 0.0
        
        self.status.state = ConnectionState.DISCONNECTED
        self.status.error_message = ""
        self._notify_status()
    
    def send_command(self, command: str, wait_for_ok: bool = True) -> str:
        """Send a G-code command to GRBL."""
        if not self._serial or not self._serial.is_open:
            return "ERROR: Not connected"
        
        # Ensure command ends with newline
        if not command.endswith('\n'):
            command += '\n'
        
        self._response_event.clear()
        self._serial.write(command.encode())
        
        if wait_for_ok:
            # Wait for response (ok or error)
            self._response_event.wait(timeout=10.0)
            return self._last_response
        
        return "ok"
    
    def home(self, axes: str = "XY") -> bool:
        """Home the machine."""
        if not self._serial or not self._serial.is_open:
            self.status.error_message = "Not connected to controller"
            self._notify_status()
            return False
        
        # Check if GRBL is in alarm state - need to unlock first
        if self.status.state == ConnectionState.ALARM:
            # Try to unlock
            unlock_response = self.send_command("$X", wait_for_ok=True)
            if "error" in unlock_response.lower():
                self.status.error_message = f"Cannot unlock: {unlock_response}"
                self._notify_status()
                return False
            time.sleep(0.2)
        
        # Note: We'll try to home first, and if we get error 5, we'll handle it
        # Checking settings before homing can be unreliable, so we'll let GRBL tell us
        
        # GRBL homing command is $H for all axes or $HX, $HY, $HZ for specific
        if axes == "XY":
            cmd = "$H"
        elif axes == "X":
            cmd = "$HX"
        elif axes == "Y":
            cmd = "$HY"
        elif axes == "Z":
            cmd = "$HZ"
        elif axes == "XYZ":
            cmd = "$H"
        else:
            cmd = "$H"
        
        # Send homing command
        response = self.send_command(cmd, wait_for_ok=True)
        
        # Wait a bit for homing to start
        time.sleep(0.5)
        
        # Check response immediately for errors
        if "error:5" in response.lower() or "error 5" in response.lower():
            # Try to enable homing automatically
            self._notify_console_response("Homing disabled. Attempting to enable...", "info")
            enable_response = self.send_command("$21=1", wait_for_ok=True)
            if "ok" in enable_response.lower():
                self._notify_console_response("Homing enabled. Verifying setting...", "info")
                # Verify the setting was applied by checking it
                verify_response = self.send_command("$21", wait_for_ok=True)
                time.sleep(0.2)  # Give GRBL time to process
                
                # Try a soft reset to ensure setting takes effect
                self._notify_console_response("Performing soft reset...", "info")
                reset_response = self.send_command("$RST=*", wait_for_ok=False)  # Reset doesn't return ok
                time.sleep(1.0)  # Wait for reset to complete
                
                # Clear any startup messages
                if self._serial and self._serial.in_waiting:
                    while self._serial.in_waiting:
                        try:
                            self._serial.readline()
                        except:
                            break
                
                # Try homing again
                self._notify_console_response("Retrying homing after reset...", "info")
                response = self.send_command(cmd, wait_for_ok=True)
                if "ok" in response.lower():
                    self.status.is_homed = False
                    self._notify_console_response("Homing started successfully", "info")
                    return True
                elif "error:5" in response.lower() or "error 5" in response.lower():
                    # Still error 5 - setting might not persist or firmware doesn't support it
                    self.status.error_message = (
                        "Homing still disabled after enabling.\n\n"
                        "Possible causes:\n"
                        "1. GRBL firmware doesn't support homing\n"
                        "2. Setting not saved to EEPROM\n"
                        "3. Controller needs power cycle\n\n"
                        "Try manually in Console:\n"
                        "1. $21=1 (enable homing)\n"
                        "2. Check if it worked: $21 (should show $21=1)\n"
                        "3. $RST=* (soft reset)\n"
                        "4. Try homing again\n\n"
                        "If still failing:\n"
                        "- Your GRBL firmware may not have homing enabled\n"
                        "- Check GRBL version: $I\n"
                        "- May need to reflash firmware with homing enabled"
                    )
                    self._notify_status()
                    self._notify_console_response("Homing still failing. Check GRBL firmware support.", "error")
                    return False
                else:
                    self.status.error_message = (
                        "Homing failed after enabling.\n\n"
                        f"Response: {response}\n\n"
                        "Possible issues:\n"
                        "1. Limit switches not connected/configured\n"
                        "2. Motors not enabled\n"
                        "3. Homing sequence misconfigured\n"
                        "4. Check GRBL settings ($22, $23, etc.)\n\n"
                        "Use Console to check settings: $$"
                    )
                    self._notify_status()
                    return False
            else:
                self.status.error_message = (
                    "Homing failed: Homing cycle is not enabled.\n\n"
                    "Error 5 means homing is disabled in GRBL settings.\n\n"
                    "To enable homing manually:\n"
                    "1. Go to Console tab\n"
                    "2. Send: $21=1 (enable homing)\n"
                    "3. Send: $21 (verify it's set)\n"
                    "4. Send: $RST=* (soft reset)\n"
                    "5. Try homing again\n\n"
                    f"Enable response: {enable_response}"
                )
                self._notify_status()
                return False
        
        # Check if we got ok response
        if "ok" in response.lower():
            # Homing started successfully
            # The status callback will update is_homed when homing completes
            # Reset is_homed flag since we're starting a new home cycle
            self.status.is_homed = False
            self._homing_in_progress = True
            self.status.error_message = ""  # Clear any previous errors
            self._notify_status()
            self._notify_console_response("Homing started - will complete when limit switches are reached", "info")
            return True
        elif "error" in response.lower():
            self.status.error_message = f"Homing failed: {response}"
            self._notify_status()
            return False
        else:
            # No response or unexpected response - but still try to proceed
            # Sometimes GRBL doesn't respond immediately but homing starts
            self.status.is_homed = False
            self.status.error_message = ""  # Clear errors, assume it started
            self._notify_status()
            return True  # Return True to allow homing to proceed
    
    def jog(self, x: float = 0, y: float = 0, z: float = 0,
            speed: float = 1000, relative: bool = True) -> bool:
        """Jog the laser head."""
        # Validate coordinates if absolute mode
        if not relative:
            if x < 0 or x > self._work_area_x:
                self.status.error_message = f"X coordinate {x:.2f}mm is outside work area (0 - {self._work_area_x:.2f}mm)"
                self._notify_status()
                return False
            if y < 0 or y > self._work_area_y:
                self.status.error_message = f"Y coordinate {y:.2f}mm is outside work area (0 - {self._work_area_y:.2f}mm)"
                self._notify_status()
                return False
            if z < 0 or z > self._work_area_z:
                self.status.error_message = f"Z coordinate {z:.2f}mm is outside work area (0 - {self._work_area_z:.2f}mm)"
                self._notify_status()
                return False
        else:
            # For relative moves, check if result would exceed limits
            # Allow some negative movement (up to -5mm) to allow left/down movement
            # The machine can physically move in negative direction even if work area starts at 0
            new_x = self.status.position_x + x
            new_y = self.status.position_y + y
            new_z = self.status.position_z + z
            
            # Allow small negative values (for left/down movement) but prevent going too far
            if new_x < -5.0 or new_x > self._work_area_x:
                self.status.error_message = f"Jog would exceed X work area limits (would be {new_x:.2f}mm, limit: 0-{self._work_area_x:.2f}mm)"
                self._notify_status()
                return False
            if new_y < -5.0 or new_y > self._work_area_y:
                self.status.error_message = f"Jog would exceed Y work area limits (would be {new_y:.2f}mm, limit: 0-{self._work_area_y:.2f}mm)"
                self._notify_status()
                return False
            if new_z < -5.0 or new_z > self._work_area_z:
                self.status.error_message = f"Jog would exceed Z work area limits (would be {new_z:.2f}mm, limit: 0-{self._work_area_z:.2f}mm)"
                self._notify_status()
                return False
        
        # GRBL jog command format
        mode = "G91" if relative else "G90"
        cmd = f"$J={mode} "
        
        if x != 0:
            cmd += f"X{x:.3f} "
        if y != 0:
            cmd += f"Y{y:.3f} "
        if z != 0:
            cmd += f"Z{z:.3f} "
        
        cmd += f"F{speed:.0f}"
        
        response = self.send_command(cmd, wait_for_ok=True)
        if "error" in response.lower():
            self.status.error_message = f"Jog failed: {response}"
            self._notify_status()
            return False
        return "ok" in response.lower()
    
    def _detect_work_area(self):
        """Auto-detect work area from GRBL settings ($130, $131, $132)."""
        try:
            # Query GRBL settings: $130 = X max travel, $131 = Y max travel, $132 = Z max travel
            x_response = self.send_command("$130", wait_for_ok=True)
            y_response = self.send_command("$131", wait_for_ok=True)
            z_response = self.send_command("$132", wait_for_ok=True)
            
            # Parse responses (format: "$130=400.000" or "$130=400")
            def parse_setting(response: str) -> Optional[float]:
                if "=" in response:
                    try:
                        value_str = response.split("=")[1].strip()
                        # Remove any trailing text
                        value_str = value_str.split()[0] if " " in value_str else value_str
                        return float(value_str)
                    except (ValueError, IndexError):
                        return None
                return None
            
            x_max = parse_setting(x_response)
            y_max = parse_setting(y_response)
            z_max = parse_setting(z_response)
            
            if x_max and x_max > 0:
                self._work_area_x = x_max
                self._notify_console_response(f"Auto-detected X work area: {x_max:.2f}mm", "info")
            if y_max and y_max > 0:
                self._work_area_y = y_max
                self._notify_console_response(f"Auto-detected Y work area: {y_max:.2f}mm", "info")
            if z_max and z_max > 0:
                self._work_area_z = z_max
                self._notify_console_response(f"Auto-detected Z work area: {z_max:.2f}mm", "info")
        except Exception as e:
            # If auto-detection fails, use defaults
            self._notify_console_response(f"Could not auto-detect work area: {e}. Using defaults.", "info")
    
    def get_work_area(self) -> tuple[float, float, float]:
        """Get current work area limits."""
        return (self._work_area_x, self._work_area_y, self._work_area_z)
    
    def set_work_area(self, x: float, y: float, z: float = 50.0):
        """Set the machine work area limits."""
        self._work_area_x = x
        self._work_area_y = y
        self._work_area_z = z
    
    def get_max_spindle_speed(self) -> int:
        """Get the max spindle speed ($30 value) for power calculations."""
        return self._max_spindle_speed
    
    def set_max_spindle_speed(self, value: int):
        """Set the max spindle speed ($30 value) for power calculations."""
        self._max_spindle_speed = max(1, value)  # Ensure at least 1
    
    def _detect_max_spindle_speed(self):
        """Auto-detect max spindle speed from GRBL $30 setting."""
        try:
            response = self.send_command("$30", wait_for_ok=True)
            if "=" in response:
                try:
                    value_str = response.split("=")[1].strip()
                    value_str = value_str.split()[0] if " " in value_str else value_str
                    value = int(float(value_str))
                    if value > 0:
                        self._max_spindle_speed = value
                        self._notify_console_response(f"Auto-detected max spindle speed ($30): {value}", "info")
                        return
                except (ValueError, IndexError):
                    pass
            self._notify_console_response(f"Could not detect $30, using default: {self._max_spindle_speed}", "info")
        except Exception as e:
            self._notify_console_response(f"Could not detect $30: {e}. Using default: {self._max_spindle_speed}", "info")
    
    def start_job(self, gcode: str) -> bool:
        """Start executing G-code."""
        if self.status.job_state == JobState.RUNNING:
            return False
        
        # Parse G-code into lines
        self._gcode_lines = [
            line.strip() for line in gcode.split('\n')
            if line.strip() and not line.strip().startswith(';')
        ]
        self._current_line = 0
        self._buffer_count = 0
        
        self.status.job_state = JobState.RUNNING
        self.status.progress = 0.0
        self._notify_status()
        
        # Start sending in a separate thread
        sender_thread = threading.Thread(target=self._send_job)
        sender_thread.daemon = True
        sender_thread.start()
        
        return True
    
    def pause_job(self) -> bool:
        """Pause the current job (feed hold)."""
        if self.status.job_state != JobState.RUNNING:
            return False
        
        try:
            self._send_realtime(self.CMD_FEED_HOLD)
            self.status.job_state = JobState.PAUSED
            self._notify_status()
            return True
        except Exception as e:
            print(f"Error pausing job: {e}")
            return False
    
    def resume_job(self) -> bool:
        """Resume a paused job."""
        if self.status.job_state != JobState.PAUSED:
            return False
        
        try:
            self._send_realtime(self.CMD_CYCLE_START)
            self.status.job_state = JobState.RUNNING
            self._notify_status()
            return True
        except Exception as e:
            print(f"Error resuming job: {e}")
            return False
    
    def stop_job(self) -> bool:
        """Stop and cancel the current job."""
        # If homing is in progress, stop it
        if self._homing_in_progress:
            self._notify_console_response("Aborting homing sequence...", "info")
            # Send feed hold first to stop motion
            self._send_realtime(self.CMD_FEED_HOLD)
            time.sleep(0.1)
            # Then soft reset
            self._send_realtime(self.CMD_SOFT_RESET)
            self._homing_in_progress = False
            self.status.is_homed = False
        else:
            # Soft reset for regular jobs
            self._send_realtime(self.CMD_SOFT_RESET)
        
        self._gcode_lines = []
        self._current_line = 0
        
        self.status.job_state = JobState.CANCELLED
        self._notify_status()
        
        # Wait for reset to complete
        time.sleep(0.5)
        
        self.status.job_state = JobState.IDLE
        self._notify_status()
        
        return True
    
    def abort_homing(self) -> bool:
        """Abort the current homing sequence."""
        if not self._homing_in_progress:
            return False
        
        self._notify_console_response("Aborting homing...", "info")
        # Send feed hold to stop motion immediately
        self._send_realtime(self.CMD_FEED_HOLD)
        time.sleep(0.1)
        # Soft reset to clear state
        self._send_realtime(self.CMD_SOFT_RESET)
        self._homing_in_progress = False
        self.status.is_homed = False
        time.sleep(0.5)
        self._notify_status()
        return True
    
    def set_home_position(self, x: float = 0, y: float = 0, z: float = 0) -> bool:
        """
        Set the current position as home (work coordinates to 0,0,0).
        
        This sets the current position as the origin without running the homing sequence.
        Useful when the machine is already at the desired home position.
        
        Args:
            x: X coordinate to set (default 0)
            y: Y coordinate to set (default 0)
            z: Z coordinate to set (default 0)
        
        Returns:
            True if successful
        """
        if self.status.state == ConnectionState.DISCONNECTED:
            return False
        
        # Use G92 to set work coordinates (current position becomes the specified values)
        # This is the standard way to set current position as home in GRBL
        cmd = f"G92 X{x} Y{y} Z{z}"
        response = self.send_command(cmd, wait_for_ok=True)
        
        if "ok" in response.lower():
            # Update our status to reflect the new position
            self.status.position_x = x
            self.status.position_y = y
            self.status.position_z = z
            self.status.is_homed = True  # Consider it homed since we set the position
            self._notify_console_response(f"Home position set to X{x} Y{y} Z{z}", "info")
            self._notify_status()
            return True
        else:
            self._notify_console_response(f"Failed to set home position: {response}", "error")
            return False
    
    def get_status(self) -> ControllerStatus:
        """Query current status."""
        self._send_realtime(self.CMD_STATUS)
        time.sleep(0.1)  # Wait for status response
        return self.status
    
    def _send_realtime(self, cmd: bytes):
        """Send a real-time command (no newline)."""
        if self._serial and self._serial.is_open:
            self._serial.write(cmd)
    
    def _read_loop(self):
        """Background thread for reading serial responses."""
        while self._running and self._serial:
            try:
                if self._serial and self._serial.is_open and self._serial.in_waiting:
                    line = self._serial.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self._process_response(line)
            except serial.SerialException as e:
                # Port was closed or disconnected
                if self._running:
                    self.status.state = ConnectionState.ERROR
                    self.status.error_message = f"Serial port error: {e}"
                    self._notify_status()
                    break
            except PermissionError as e:
                # Access denied - port might be in use elsewhere
                # Don't spam errors, just log occasionally
                if self._running and time.time() % 5 < 0.1:  # Log roughly every 5 seconds
                    print(f"Port access issue (may resolve): {e}")
            except Exception as e:
                # Other errors - log but continue
                if self._running:
                    # Only log non-permission errors
                    if "Permission" not in str(e):
                        print(f"Read error: {e}")
            time.sleep(0.01)
    
    def _process_response(self, line: str):
        """Process a response line from GRBL."""
        if not line:
            return
        
        # Status report
        if line.startswith('<'):
            self._parse_status(line)
            # Don't display status reports in console (too frequent)
        
        # Command acknowledgment
        elif line == 'ok':
            self._buffer_count -= 1
            self._last_response = line
            self._response_event.set()
            # Display in console via callback
            self._notify_console_response(line, "response")
        
        # Error
        elif line.startswith('error:'):
            self._last_response = line
            self._response_event.set()
            self.status.error_message = line
            self._notify_status()
            self._notify_console_response(line, "error")
        
        # Alarm
        elif line.startswith('ALARM:'):
            self.status.state = ConnectionState.ALARM
            self.status.error_message = line
            self.status.job_state = JobState.ERROR
            self._notify_status()
            self._notify_console_response(line, "error")
        
        # Welcome/startup message
        elif 'Grbl' in line:
            self.status.state = ConnectionState.CONNECTED
            self._notify_status()
            self._notify_console_response(line, "info")
        
        # Other responses (settings, etc.)
        else:
            self._notify_console_response(line, "response")
    
    def add_console_callback(self, callback):
        """Add callback for console output."""
        if callback not in self._console_callbacks:
            self._console_callbacks.append(callback)
    
    def remove_console_callback(self, callback):
        """Remove console callback."""
        if callback in self._console_callbacks:
            self._console_callbacks.remove(callback)
    
    def _notify_console_response(self, text: str, message_type: str = "response"):
        """Notify console callbacks of response."""
        for callback in self._console_callbacks:
            try:
                callback(text, message_type)
            except Exception as e:
                print(f"Console callback error: {e}")
    
    def _parse_status(self, line: str):
        """Parse GRBL status report."""
        match = self.STATUS_REGEX.match(line)
        if match:
            state = match.group(1)
            self.status.position_x = float(match.group(2))
            self.status.position_y = float(match.group(3))
            self.status.position_z = float(match.group(4))
            
            if match.group(5):  # Buffer info
                self.status.buffer_space = int(match.group(5))
            
            # Map GRBL state to our connection state
            state_map = {
                'Idle': ConnectionState.CONNECTED,
                'Run': ConnectionState.BUSY,
                'Hold': ConnectionState.CONNECTED,
                'Jog': ConnectionState.BUSY,
                'Alarm': ConnectionState.ALARM,
                'Check': ConnectionState.CONNECTED,
                'Home': ConnectionState.BUSY,
            }
            
            # Update job state based on GRBL state
            if state == 'Run':
                # GRBL is running a job
                if self.status.job_state != JobState.RUNNING:
                    self.status.job_state = JobState.RUNNING
            elif state == 'Hold':
                # GRBL is in hold (paused) - update job state if we have a job
                if self.status.job_state == JobState.RUNNING:
                    self.status.job_state = JobState.PAUSED
            elif state == 'Idle':
                # GRBL is idle - check if we had a running job
                if self.status.job_state == JobState.RUNNING:
                    # Job completed
                    self.status.job_state = JobState.COMPLETED
                    self.status.progress = 100.0
                elif self.status.job_state == JobState.PAUSED:
                    # Job was paused and is now idle (might have been cancelled)
                    # Don't change state - keep it paused until user resumes or cancels
                    pass
            
            # Detect homing state transitions
            if 'Home' in state:
                # Homing is in progress
                self._homing_in_progress = True
                self.status.is_homed = False  # Not homed yet, homing in progress
            elif self._homing_in_progress and state == 'Idle':
                # Homing completed - transitioned from Home to Idle
                self._homing_in_progress = False
                self.status.is_homed = True
                self._notify_console_response("Homing completed successfully", "info")
            elif self._homing_in_progress and state == 'Alarm':
                # Homing failed - went to alarm
                self._homing_in_progress = False
                self.status.is_homed = False
                self._notify_console_response("Homing failed - alarm triggered. Use '$X' to unlock.", "error")
            elif state == 'Alarm':
                # General alarm state - provide helpful message
                self.status.error_message = (
                    "GRBL is in ALARM state.\n\n"
                    "Common causes:\n"
                    "- Hit limit switch\n"
                    "- Movement exceeded machine limits\n"
                    "- Hardware fault\n\n"
                    "Use Console to send '$X' to unlock after resolving the issue."
                )
                # If job was running, mark as error
                if self.status.job_state in (JobState.RUNNING, JobState.PAUSED):
                    self.status.job_state = JobState.ERROR
                self._notify_status()
            
            self.status.state = state_map.get(state, ConnectionState.CONNECTED)
            self._notify_status()
    
    def _send_job(self):
        """Send job G-code with flow control."""
        while (self._current_line < len(self._gcode_lines) and 
               self.status.job_state == JobState.RUNNING):
            
            # Check buffer space
            if self._buffer_count >= 5:  # Keep some buffer room
                time.sleep(0.01)
                continue
            
            line = self._gcode_lines[self._current_line]
            
            # Send line
            self._serial.write((line + '\n').encode())
            self._buffer_count += 1
            self._current_line += 1
            
            # Update progress - notify every line or every 10 lines for performance
            if self._current_line % 10 == 0 or self._current_line == len(self._gcode_lines):
                self.status.progress = (self._current_line / len(self._gcode_lines)) * 100
                self._notify_status()
        
        # Final progress update
        if len(self._gcode_lines) > 0:
            self.status.progress = (self._current_line / len(self._gcode_lines)) * 100
            self._notify_status()
        
        # Wait for completion
        while self._buffer_count > 0 and self.status.job_state == JobState.RUNNING:
            time.sleep(0.1)
            # Update progress while waiting (buffer draining)
            if len(self._gcode_lines) > 0:
                # Progress is based on lines sent, but we're waiting for buffer to drain
                # Estimate: lines sent + some buffer progress
                estimated_progress = min(99.0, (self._current_line / len(self._gcode_lines)) * 100)
                if abs(estimated_progress - self.status.progress) > 1.0:  # Update if changed by >1%
                    self.status.progress = estimated_progress
                    self._notify_status()
        
        if self.status.job_state == JobState.RUNNING:
            self.status.job_state = JobState.COMPLETED
            self.status.progress = 100.0
            self._notify_status()

