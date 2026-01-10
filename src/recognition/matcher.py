"""
Image Recognition - Template matching and OCR
"""
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Optional, Tuple, List
import pytesseract


class ImageMatcher:
    """Image recognition and template matching"""
    
    def __init__(self, tesseract_path: Optional[str] = None):
        """
        Initialize image matcher
        
        Args:
            tesseract_path: Path to tesseract executable (Windows)
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    def load_template(self, template_path: str) -> Optional[np.ndarray]:
        """
        Load template image
        
        Args:
            template_path: Path to template image
        
        Returns:
            Template image as numpy array or None if failed
        """
        try:
            # Convert to Path object to handle Unicode paths properly
            path_obj = Path(template_path)
            if not path_obj.exists():
                return None
            
            # Use PIL to read image (handles Unicode paths better than cv2.imread)
            pil_image = Image.open(path_obj)
            # Convert PIL to numpy array
            template_array = np.array(pil_image)
            
            # Convert to RGB if needed
            if len(template_array.shape) == 2:
                # Grayscale
                template = cv2.cvtColor(template_array, cv2.COLOR_GRAY2RGB)
            elif template_array.shape[2] == 4:
                # RGBA
                template = cv2.cvtColor(template_array, cv2.COLOR_RGBA2RGB)
            elif template_array.shape[2] == 3:
                # RGB
                template = template_array
            else:
                template = template_array
            
            return template
        except Exception as e:
            print(f"Error loading template: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def find_template(
        self,
        screenshot: Image.Image,
        template_path: str,
        threshold: float = 0.8,
        method: int = cv2.TM_CCOEFF_NORMED
    ) -> Optional[Tuple[int, int]]:
        """
        Find template in screenshot
        
        Args:
            screenshot: Screenshot as PIL Image
            template_path: Path to template image
            threshold: Matching threshold (0-1)
            method: OpenCV template matching method
        
        Returns:
            Tuple of (x, y) center coordinates or None if not found
        """
        # Load template
        template = self.load_template(template_path)
        if template is None:
            return None
        
        # Convert screenshot to numpy array
        screen_array = np.array(screenshot)
        
        # Ensure both are RGB and same dtype
        if len(screen_array.shape) == 2:
            screen_array = cv2.cvtColor(screen_array, cv2.COLOR_GRAY2RGB)
        elif screen_array.shape[2] == 4:
            screen_array = cv2.cvtColor(screen_array, cv2.COLOR_RGBA2RGB)
        
        # Ensure template is RGB
        if len(template.shape) == 2:
            template = cv2.cvtColor(template, cv2.COLOR_GRAY2RGB)
        elif template.shape[2] == 4:
            template = cv2.cvtColor(template, cv2.COLOR_RGBA2RGB)
        
        # Ensure same dtype (uint8)
        if screen_array.dtype != np.uint8:
            screen_array = screen_array.astype(np.uint8)
        if template.dtype != np.uint8:
            template = template.astype(np.uint8)
        
        # Ensure same number of channels
        if screen_array.shape[2] != template.shape[2]:
            if screen_array.shape[2] == 3 and template.shape[2] == 1:
                template = cv2.cvtColor(template, cv2.COLOR_GRAY2RGB)
            elif screen_array.shape[2] == 1 and template.shape[2] == 3:
                screen_array = cv2.cvtColor(screen_array, cv2.COLOR_GRAY2RGB)
        
        # Template matching
        try:
            result = cv2.matchTemplate(screen_array, template, method)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # Check threshold
            if max_val < threshold:
                return None
            
            # Return center coordinates
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            
            return (center_x, center_y)
        except cv2.error as e:
            print(f"OpenCV error in template matching: {e}")
            print(f"Screen array shape: {screen_array.shape}, dtype: {screen_array.dtype}")
            print(f"Template shape: {template.shape}, dtype: {template.dtype}")
            return None
    
    def find_all_templates(
        self,
        screenshot: Image.Image,
        template_path: str,
        threshold: float = 0.8,
        method: int = cv2.TM_CCOEFF_NORMED
    ) -> List[Tuple[int, int]]:
        """
        Find all occurrences of template in screenshot
        
        Args:
            screenshot: Screenshot as PIL Image
            template_path: Path to template image
            threshold: Matching threshold (0-1)
            method: OpenCV template matching method
        
        Returns:
            List of (x, y) center coordinates (deduplicated)
        """
        # Load template
        template = self.load_template(template_path)
        if template is None:
            return []
        
        # Convert screenshot to numpy array
        screen_array = np.array(screenshot)
        
        # Ensure both are RGB and same dtype
        if len(screen_array.shape) == 2:
            screen_array = cv2.cvtColor(screen_array, cv2.COLOR_GRAY2RGB)
        elif screen_array.shape[2] == 4:
            screen_array = cv2.cvtColor(screen_array, cv2.COLOR_RGBA2RGB)
        
        # Ensure template is RGB
        if len(template.shape) == 2:
            template = cv2.cvtColor(template, cv2.COLOR_GRAY2RGB)
        elif template.shape[2] == 4:
            template = cv2.cvtColor(template, cv2.COLOR_RGBA2RGB)
        
        # Ensure same dtype (uint8)
        if screen_array.dtype != np.uint8:
            screen_array = screen_array.astype(np.uint8)
        if template.dtype != np.uint8:
            template = template.astype(np.uint8)
        
        # Ensure same number of channels
        if screen_array.shape[2] != template.shape[2]:
            if screen_array.shape[2] == 3 and template.shape[2] == 1:
                template = cv2.cvtColor(template, cv2.COLOR_GRAY2RGB)
            elif screen_array.shape[2] == 1 and template.shape[2] == 3:
                screen_array = cv2.cvtColor(screen_array, cv2.COLOR_GRAY2RGB)
        
        # Template matching
        result = cv2.matchTemplate(screen_array, template, method)
        
        # Find all matches above threshold
        locations = np.where(result >= threshold)
        matches = []
        
        h, w = template.shape[:2]
        min_distance = max(w, h) // 2  # Minimum distance between matches
        
        # Sort by confidence (higher is better for CCOEFF_NORMED)
        match_points = []
        for pt in zip(*locations[::-1]):
            confidence = result[pt[1], pt[0]]
            center_x = pt[0] + w // 2
            center_y = pt[1] + h // 2
            match_points.append((center_x, center_y, confidence))
        
        # Sort by confidence (descending)
        match_points.sort(key=lambda x: x[2], reverse=True)
        
        # Filter out matches that are too close to each other
        for x, y, conf in match_points:
            # Check if this match is far enough from existing matches
            is_duplicate = False
            for existing_x, existing_y in matches:
                distance = ((x - existing_x) ** 2 + (y - existing_y) ** 2) ** 0.5
                if distance < min_distance:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                matches.append((x, y))
        
        return matches
    
    def extract_text(
        self,
        screenshot: Image.Image,
        region: Optional[Tuple[int, int, int, int]] = None,
        lang: str = "eng"
    ) -> str:
        """
        Extract text from screenshot using OCR
        
        Args:
            screenshot: Screenshot as PIL Image
            region: Optional region (x, y, width, height) to extract text from
            lang: Tesseract language code
        
        Returns:
            Extracted text
        """
        try:
            if region:
                x, y, w, h = region
                screenshot = screenshot.crop((x, y, x + w, y + h))
            
            text = pytesseract.image_to_string(screenshot, lang=lang)
            return text.strip()
        except Exception as e:
            print(f"Error extracting text: {e}")
            return ""
    
    def wait_for_template(
        self,
        screenshot_func,
        template_path: str,
        timeout: int = 10,
        interval: float = 0.5,
        threshold: float = 0.8
    ) -> Optional[Tuple[int, int]]:
        """
        Wait for template to appear on screen
        
        Args:
            screenshot_func: Function that returns PIL Image screenshot
            template_path: Path to template image
            timeout: Timeout in seconds
            interval: Check interval in seconds
            threshold: Matching threshold
        
        Returns:
            Tuple of (x, y) coordinates or None if timeout
        """
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            screenshot = screenshot_func()
            if screenshot:
                result = self.find_template(screenshot, template_path, threshold)
                if result:
                    return result
            time.sleep(interval)
        
        return None

