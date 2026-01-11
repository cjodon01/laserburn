"""
Job Manager for Laser Operations

Manages laser job execution, queueing, and progress tracking.
"""

from typing import List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import threading
import time

from .controller import LaserController, JobState, ControllerStatus
from .gcode_generator import GCodeGenerator, GCodeSettings
from ..core.document import Document


class JobPriority(Enum):
    """Job priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class LaserJob:
    """Represents a laser job to be executed."""
    id: str
    name: str
    gcode: str
    document: Optional[Document] = None
    priority: JobPriority = JobPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: JobState = JobState.IDLE
    progress: float = 0.0
    error_message: str = ""
    
    # Estimated time
    estimated_time: float = 0.0  # seconds
    elapsed_time: float = 0.0  # seconds


class JobManager:
    """
    Manages laser job queue and execution.
    
    Features:
    - Job queueing with priorities
    - Progress tracking
    - Job cancellation
    - Status callbacks
    """
    
    def __init__(self, controller: LaserController):
        self.controller = controller
        self._queue: List[LaserJob] = []
        self._current_job: Optional[LaserJob] = None
        self._queue_lock = threading.Lock()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        
        # Callbacks
        self._job_callbacks: List[Callable[[LaserJob], None]] = []
        
        # Connect to controller status updates
        self.controller.add_status_callback(self._on_controller_status)
    
    def add_job(self, job: LaserJob) -> bool:
        """
        Add a job to the queue.
        
        Args:
            job: The laser job to add
        
        Returns:
            True if job added successfully
        """
        with self._queue_lock:
            # Insert based on priority
            inserted = False
            for i, queued_job in enumerate(self._queue):
                if job.priority.value > queued_job.priority.value:
                    self._queue.insert(i, job)
                    inserted = True
                    break
            
            if not inserted:
                self._queue.append(job)
            
            # Notify callbacks
            self._notify_job_callbacks(job)
            
            # Start worker if not running
            if not self._running:
                self._start_worker()
        
        return True
    
    def create_job_from_document(self, 
                                 document: Document,
                                 name: str = "",
                                 priority: JobPriority = JobPriority.NORMAL,
                                 settings: Optional[GCodeSettings] = None) -> LaserJob:
        """
        Create a job from a document.
        
        Args:
            document: The document to convert to G-code
            name: Job name (defaults to document name)
            priority: Job priority
            settings: G-code generation settings
        
        Returns:
            Created LaserJob
        """
        generator = GCodeGenerator(settings or GCodeSettings())
        gcode, warnings = generator.generate(document)
        
        # Apply cylinder compensation if enabled
        if (document.cylinder_params and 
            document.cylinder_compensate_power):
            from ..image.cylinder_warp import apply_cylinder_compensation_to_gcode
            
            # Convert gcode string to lines
            gcode_lines = gcode.split('\n')
            
            # Get design center for compensation
            bounds = document.get_design_bounds()
            design_center_x = (bounds.min_x + bounds.max_x) / 2 if bounds else 0
            
            # Get base power from settings (default to 255)
            base_power = 255  # Could get from GCodeSettings or layer settings
            
            # Apply compensation
            gcode_lines = apply_cylinder_compensation_to_gcode(
                gcode_lines,
                document.cylinder_params,
                design_center_x=design_center_x,
                base_power=base_power,
                include_z=document.cylinder_compensate_z
            )
            
            # Convert back to string
            gcode = '\n'.join(gcode_lines)
        
        # Log warnings if any
        if warnings:
            print("G-code generation warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        
        job = LaserJob(
            id=f"job_{int(time.time())}",
            name=name or document.name,
            gcode=gcode,
            document=document,
            priority=priority
        )
        
        return job
    
    def remove_job(self, job_id: str) -> bool:
        """
        Remove a job from the queue.
        
        Args:
            job_id: ID of job to remove
        
        Returns:
            True if job removed
        """
        with self._queue_lock:
            # Can't remove current job
            if self._current_job and self._current_job.id == job_id:
                return False
            
            # Remove from queue
            self._queue = [j for j in self._queue if j.id != job_id]
            return True
    
    def cancel_current_job(self) -> bool:
        """Cancel the currently running job."""
        if not self._current_job:
            return False
        
        if self.controller.stop_job():
            self._current_job.status = JobState.CANCELLED
            self._current_job.completed_at = datetime.now()
            self._notify_job_callbacks(self._current_job)
            self._current_job = None
            return True
        
        return False
    
    def pause_current_job(self) -> bool:
        """Pause the currently running job."""
        if not self._current_job:
            return False
        
        if self.controller.pause_job():
            self._current_job.status = JobState.PAUSED
            self._notify_job_callbacks(self._current_job)
            return True
        
        return False
    
    def resume_current_job(self) -> bool:
        """Resume the currently paused job."""
        if not self._current_job:
            return False
        
        if self.controller.resume_job():
            self._current_job.status = JobState.RUNNING
            self._notify_job_callbacks(self._current_job)
            return True
        
        return False
    
    def get_queue(self) -> List[LaserJob]:
        """Get list of queued jobs."""
        with self._queue_lock:
            return self._queue.copy()
    
    def get_current_job(self) -> Optional[LaserJob]:
        """Get the currently running job."""
        return self._current_job
    
    def clear_queue(self):
        """Clear all queued jobs (except current)."""
        with self._queue_lock:
            self._queue.clear()
    
    def add_job_callback(self, callback: Callable[[LaserJob], None]):
        """Register callback for job status updates."""
        self._job_callbacks.append(callback)
    
    def remove_job_callback(self, callback: Callable[[LaserJob], None]):
        """Remove a job callback."""
        if callback in self._job_callbacks:
            self._job_callbacks.remove(callback)
    
    def _start_worker(self):
        """Start the worker thread."""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop)
        self._worker_thread.daemon = True
        self._worker_thread.start()
    
    def _worker_loop(self):
        """Main worker loop for processing jobs."""
        while self._running:
            # Get next job
            job = None
            with self._queue_lock:
                if self._queue:
                    job = self._queue.pop(0)
            
            if job:
                self._execute_job(job)
            
            time.sleep(0.1)
    
    def _execute_job(self, job: LaserJob):
        """Execute a single job."""
        self._current_job = job
        job.status = JobState.RUNNING
        job.started_at = datetime.now()
        self._notify_job_callbacks(job)
        
        # Start job on controller
        if not self.controller.start_job(job.gcode):
            job.status = JobState.ERROR
            job.error_message = "Failed to start job on controller"
            job.completed_at = datetime.now()
            self._notify_job_callbacks(job)
            self._current_job = None
            return
        
        # Wait for completion
        start_time = time.time()
        while job.status == JobState.RUNNING:
            time.sleep(0.1)
            job.elapsed_time = time.time() - start_time
        
        # Job completed
        job.completed_at = datetime.now()
        self._notify_job_callbacks(job)
        self._current_job = None
    
    def _on_controller_status(self, status: ControllerStatus):
        """Handle controller status updates."""
        if self._current_job:
            # Update job status from controller
            if status.job_state != self._current_job.status:
                self._current_job.status = status.job_state
                self._notify_job_callbacks(self._current_job)
            
            # Update progress
            if status.progress != self._current_job.progress:
                self._current_job.progress = status.progress
                self._notify_job_callbacks(self._current_job)
            
            # Update error message
            if status.error_message:
                self._current_job.error_message = status.error_message
                if status.state.value == "error" or status.state.value == "alarm":
                    self._current_job.status = JobState.ERROR
                    self._notify_job_callbacks(self._current_job)
    
    def _notify_job_callbacks(self, job: LaserJob):
        """Notify all callbacks of job status change using Qt signals."""
        # Use QMetaObject.invokeMethod to safely call callbacks from worker thread
        # This avoids the "QBasicTimer can only be used with threads started with QThread" error
        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
        
        for callback in self._job_callbacks:
            try:
                # Try to invoke the callback in a thread-safe manner
                callback(job)
            except RuntimeError as e:
                # If we get a threading error, log it but don't crash
                if "different thread" in str(e).lower():
                    print(f"Job callback thread safety issue (safe to ignore): {e}")
                else:
                    print(f"Job callback error: {e}")
            except Exception as e:
                print(f"Job callback error: {e}")
    
    def shutdown(self):
        """Shutdown the job manager."""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
        
        # Cancel current job
        if self._current_job:
            self.cancel_current_job()

