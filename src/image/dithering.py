"""
Image Dithering Module

Implements various dithering algorithms for converting grayscale images
to binary patterns suitable for laser engraving.
"""

import numpy as np
from typing import Tuple, Optional
from enum import Enum

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class DitheringMethod(Enum):
    """Available dithering algorithms."""
    FLOYD_STEINBERG = "floyd_steinberg"
    JARVIS_JUDICE_NINKE = "jarvis_judice_ninke"
    ATKINSON = "atkinson"
    BAYER_2x2 = "bayer_2x2"
    BAYER_4x4 = "bayer_4x4"
    BAYER_8x8 = "bayer_8x8"
    STUCKI = "stucki"
    NONE = "none"


class ImageDitherer:
    """Dither images for laser engraving."""
    
    def __init__(self, method: DitheringMethod = DitheringMethod.FLOYD_STEINBERG):
        self.method = method
    
    def dither(self, image: np.ndarray, threshold: int = 128) -> np.ndarray:
        """Apply dithering to a grayscale image."""
        if image.dtype != np.uint8:
            if image.max() <= 1.0:
                image = (image * 255).astype(np.uint8)
            else:
                image = image.astype(np.uint8)
        
        if len(image.shape) == 3:
            image = np.dot(image[...,:3], [0.299, 0.587, 0.114]).astype(np.uint8)
        
        if self.method == DitheringMethod.NONE:
            return self._threshold(image, threshold)
        elif self.method == DitheringMethod.FLOYD_STEINBERG:
            return self._floyd_steinberg(image, threshold)
        elif self.method == DitheringMethod.JARVIS_JUDICE_NINKE:
            return self._jarvis_judice_ninke(image, threshold)
        elif self.method == DitheringMethod.ATKINSON:
            return self._atkinson(image, threshold)
        elif self.method == DitheringMethod.BAYER_2x2:
            return self._bayer(image, 2, threshold)
        elif self.method == DitheringMethod.BAYER_4x4:
            return self._bayer(image, 4, threshold)
        elif self.method == DitheringMethod.BAYER_8x8:
            return self._bayer(image, 8, threshold)
        elif self.method == DitheringMethod.STUCKI:
            return self._stucki(image, threshold)
        else:
            return self._threshold(image, threshold)
    
    def _threshold(self, image: np.ndarray, threshold: int) -> np.ndarray:
        return np.where(image >= threshold, 255, 0).astype(np.uint8)
    
    def _floyd_steinberg(self, image: np.ndarray, threshold: int) -> np.ndarray:
        result = image.copy().astype(np.float32)
        height, width = result.shape
        
        for y in range(height):
            for x in range(width):
                old_pixel = result[y, x]
                new_pixel = 255 if old_pixel >= threshold else 0
                result[y, x] = new_pixel
                error = old_pixel - new_pixel
                
                if x + 1 < width:
                    result[y, x + 1] += error * 7 / 16
                if y + 1 < height:
                    if x - 1 >= 0:
                        result[y + 1, x - 1] += error * 3 / 16
                    result[y + 1, x] += error * 5 / 16
                    if x + 1 < width:
                        result[y + 1, x + 1] += error * 1 / 16
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def _jarvis_judice_ninke(self, image: np.ndarray, threshold: int) -> np.ndarray:
        result = image.copy().astype(np.float32)
        height, width = result.shape
        kernel = np.array([[0, 0, 0, 7, 5], [3, 5, 7, 5, 3], [1, 3, 5, 3, 1]], dtype=np.float32) / 48
        
        for y in range(height):
            for x in range(width):
                old_pixel = result[y, x]
                new_pixel = 255 if old_pixel >= threshold else 0
                result[y, x] = new_pixel
                error = old_pixel - new_pixel
                
                for ky in range(3):
                    for kx in range(5):
                        if kernel[ky, kx] == 0:
                            continue
                        ny, nx = y + ky, x + kx - 2
                        if 0 <= ny < height and 0 <= nx < width:
                            result[ny, nx] += error * kernel[ky, kx]
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def _atkinson(self, image: np.ndarray, threshold: int) -> np.ndarray:
        result = image.copy().astype(np.float32)
        height, width = result.shape
        
        for y in range(height):
            for x in range(width):
                old_pixel = result[y, x]
                new_pixel = 255 if old_pixel >= threshold else 0
                result[y, x] = new_pixel
                error = (old_pixel - new_pixel) / 8
                
                for dy, dx in [(0, 1), (0, 2), (1, -1), (1, 0), (1, 1), (2, 0)]:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < height and 0 <= nx < width:
                        result[ny, nx] += error
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def _stucki(self, image: np.ndarray, threshold: int) -> np.ndarray:
        result = image.copy().astype(np.float32)
        height, width = result.shape
        kernel = np.array([[0, 0, 0, 8, 4], [2, 4, 8, 4, 2], [1, 2, 4, 2, 1]], dtype=np.float32) / 42
        
        for y in range(height):
            for x in range(width):
                old_pixel = result[y, x]
                new_pixel = 255 if old_pixel >= threshold else 0
                result[y, x] = new_pixel
                error = old_pixel - new_pixel
                
                for ky in range(3):
                    for kx in range(5):
                        if kernel[ky, kx] == 0:
                            continue
                        ny, nx = y + ky, x + kx - 2
                        if 0 <= ny < height and 0 <= nx < width:
                            result[ny, nx] += error * kernel[ky, kx]
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def _bayer(self, image: np.ndarray, size: int, threshold: int) -> np.ndarray:
        if size == 2:
            matrix = np.array([[0, 2], [3, 1]], dtype=np.float32) * (255 / 4)
        elif size == 4:
            matrix = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32) * (255 / 16)
        elif size == 8:
            matrix = np.array([[0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26], [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22], [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25], [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]], dtype=np.float32) * (255 / 64)
        else:
            matrix = np.array([[0, 2], [3, 1]], dtype=np.float32) * (255 / 4)
        
        result = image.copy().astype(np.float32)
        height, width = result.shape
        
        for y in range(height):
            for x in range(width):
                mx, my = x % size, y % size
                bayer_threshold = threshold + (matrix[my, mx] - 127.5)
                result[y, x] = 255 if result[y, x] >= bayer_threshold else 0
        
        return result.astype(np.uint8)


def load_image(filepath: str) -> Optional[np.ndarray]:
    """Load an image file and convert to numpy array."""
    if not HAS_PIL:
        raise ImportError("Pillow (PIL) is required for image loading")
    
    try:
        img = Image.open(filepath)
        if img.mode != 'RGB' and img.mode != 'L':
            img = img.convert('RGB')
        if img.mode == 'RGB':
            img = img.convert('L')
        return np.array(img, dtype=np.uint8)
    except Exception as e:
        print(f"Error loading image {filepath}: {e}")
        return None


def adjust_brightness_contrast(image: np.ndarray, brightness: float = 0.0, contrast: float = 1.0) -> np.ndarray:
    """Adjust brightness and contrast of an image."""
    result = image.copy().astype(np.float32)
    result = (result - 127.5) * contrast + 127.5
    result += brightness
    return np.clip(result, 0, 255).astype(np.uint8)
