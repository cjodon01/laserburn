"""
Path Optimization for Laser Cutting

Minimizes non-cutting travel distance by reordering paths
and optimizing start points.
"""

import math
from typing import List, Tuple, Optional
from dataclasses import dataclass

from ..core.shapes import Point


@dataclass
class OptimizedPath:
    """A path with optimized direction and order."""
    points: List[Point]
    reversed: bool = False
    start_index: int = 0


def optimize_paths(paths: List[List[Point]], 
                   start_point: Point = None) -> List[List[Point]]:
    """
    Optimize path order to minimize travel distance.
    
    Uses nearest neighbor heuristic for TSP approximation.
    Also optimizes each path's start point and direction.
    
    Args:
        paths: List of paths to optimize
        start_point: Starting position (default: origin)
    
    Returns:
        Reordered and optimized paths
    """
    if not paths:
        return []
    
    if start_point is None:
        start_point = Point(0, 0)
    
    # Convert to optimized path objects (deep copy points)
    opt_paths = []
    for p in paths:
        # Create new list with new Point objects
        copied_points = [Point(point.x, point.y) for point in p]
        opt_paths.append(OptimizedPath(points=copied_points))
    
    # Track which paths have been visited
    remaining = set(range(len(opt_paths)))
    ordered = []
    current_pos = start_point
    
    while remaining:
        # Find nearest path endpoint
        best_idx = None
        best_dist = float('inf')
        best_reversed = False
        
        for idx in remaining:
            path = opt_paths[idx]
            if not path.points:
                remaining.discard(idx)
                continue
            
            # Check distance to start and end of path
            start = path.points[0]
            end = path.points[-1]
            
            dist_to_start = current_pos.distance_to(start)
            dist_to_end = current_pos.distance_to(end)
            
            if dist_to_start < best_dist:
                best_dist = dist_to_start
                best_idx = idx
                best_reversed = False
            
            if dist_to_end < best_dist:
                best_dist = dist_to_end
                best_idx = idx
                best_reversed = True
        
        if best_idx is not None:
            path = opt_paths[best_idx]
            
            if best_reversed:
                path.points.reverse()
                path.reversed = True
            
            ordered.append(path.points)
            remaining.discard(best_idx)
            
            # Update current position
            if path.points:
                current_pos = path.points[-1]
    
    return ordered


def optimize_closed_path_start(path: List[Point], 
                               entry_point: Point) -> List[Point]:
    """
    Optimize the starting point of a closed path.
    
    For closed paths, we can start at any point. This finds
    the point closest to the entry_point to minimize travel.
    
    Args:
        path: Closed path (first point == last point expected)
        entry_point: The position we're coming from
    
    Returns:
        Rotated path starting at optimal point
    """
    if len(path) < 3:
        return path
    
    # Remove closing point if present
    is_closed = (path[0].x == path[-1].x and path[0].y == path[-1].y)
    working_path = path[:-1] if is_closed else path
    
    # Find closest point
    best_idx = 0
    best_dist = float('inf')
    
    for i, point in enumerate(working_path):
        dist = entry_point.distance_to(point)
        if dist < best_dist:
            best_dist = dist
            best_idx = i
    
    # Rotate path to start at best_idx
    rotated = working_path[best_idx:] + working_path[:best_idx]
    
    # Re-close if needed
    if is_closed:
        rotated.append(rotated[0])
    
    return rotated


def calculate_total_distance(paths: List[List[Point]], 
                            start_point: Point = None) -> Tuple[float, float]:
    """
    Calculate total cutting and travel distances.
    
    Args:
        paths: Ordered list of paths
        start_point: Starting position
    
    Returns:
        Tuple of (cutting_distance, travel_distance)
    """
    if start_point is None:
        start_point = Point(0, 0)
    
    cutting_dist = 0.0
    travel_dist = 0.0
    current_pos = start_point
    
    for path in paths:
        if not path:
            continue
        
        # Travel to path start
        travel_dist += current_pos.distance_to(path[0])
        
        # Cut along path
        for i in range(1, len(path)):
            cutting_dist += path[i-1].distance_to(path[i])
        
        # Update position
        current_pos = path[-1]
    
    return cutting_dist, travel_dist


def estimate_job_time(paths: List[List[Point]],
                      cut_speed: float,
                      travel_speed: float,
                      start_point: Point = None) -> float:
    """
    Estimate total job time in seconds.
    
    Args:
        paths: Ordered list of paths
        cut_speed: Cutting speed in mm/s
        travel_speed: Rapid travel speed in mm/s
        start_point: Starting position
    
    Returns:
        Estimated time in seconds
    """
    cutting_dist, travel_dist = calculate_total_distance(paths, start_point)
    
    cut_time = cutting_dist / cut_speed if cut_speed > 0 else 0
    travel_time = travel_dist / travel_speed if travel_speed > 0 else 0
    
    return cut_time + travel_time

