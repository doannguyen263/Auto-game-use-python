"""
Task Manager - Manage and execute game tasks
"""
import time
from typing import Dict, Any, Optional
from pathlib import Path

from emulator.controller import EmulatorController
from recognition.matcher import ImageMatcher
from utils.logger import setup_logger
from utils.text_utils import sanitize_filename


class TaskManager:
    """Manage and execute game tasks"""
    
    def __init__(
        self,
        emulator: EmulatorController,
        game_config: Dict[str, Any],
        logger=None,
        game_name: str = None,
        notification_callback=None
    ):
        """
        Initialize task manager
        
        Args:
            emulator: Emulator controller instance
            game_config: Game configuration
            logger: Logger instance
            game_name: Game name for organizing screenshots
            notification_callback: Callback function to show notification dialog
                Should accept (message: str) and return True to continue, False to stop
        """
        self.emulator = emulator
        self.game_config = game_config
        self.logger = logger or setup_logger()
        self.matcher = ImageMatcher()
        self.running = False
        self.game_name = game_name or game_config.get("name", "unknown")
        self.current_task_name = None
        self.next_step_index = None  # For conditional branching
        self.notification_callback = notification_callback  # Callback to show notification dialog
        self.user_requested_stop = False  # Flag to indicate user requested stop from notification
        self.force_stop_task = False  # Flag to force stop entire task (including all loops)
        
        # Set logger for emulator if it supports it
        if hasattr(self.emulator, 'set_logger'):
            self.emulator.set_logger(self.logger)
    
    def run_task(self, task_name: str) -> bool:
        """
        Run a specific task
        
        Args:
            task_name: Name of the task to run
        
        Returns:
            True if task completed successfully
        """
        tasks = self.game_config.get("tasks", {})
        
        if task_name not in tasks:
            self.logger.error(f"Task not found: {task_name}")
            return False
        
        task_config = tasks[task_name]
        self.logger.info(f"Starting task: {task_name}")
        self.current_task_name = task_name
        
        # Reset flags
        self.running = True
        self.force_stop_task = False
        
        try:
            # Execute task steps
            steps = task_config.get("steps", [])
            step_index = 1  # Start from step 1 (1-based)
            
            while step_index <= len(steps):
                if not self.running:
                    break
                
                step = steps[step_index - 1]  # Convert to 0-based index
                
                # Reset next_step_index before executing
                self.next_step_index = None
                
                if not self._execute_step(step, step_index):
                    self.logger.warning(f"Step failed: {step.get('name', 'unknown')}")
                    if step.get("required", True):
                        return False
                
                # Check if we need to jump to a specific step
                if self.next_step_index is not None:
                    if 1 <= self.next_step_index <= len(steps):
                        self.logger.info(f"Nhảy đến step {self.next_step_index}")
                        step_index = self.next_step_index
                    else:
                        self.logger.warning(f"Step index không hợp lệ: {self.next_step_index}, tiếp tục step tiếp theo")
                        step_index += 1
                else:
                    # Normal flow: continue to next step
                    step_index += 1
            
            self.logger.info(f"Task completed: {task_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing task: {e}", exc_info=True)
            return False
        finally:
            self.running = False
    
    def _execute_step(self, step: Dict[str, Any], step_index: int = None) -> bool:
        """
        Execute a single step
        
        Args:
            step: Step configuration
            step_index: Step index (1-based) for logging
        
        Returns:
            True if step executed successfully
        """
        step_type = step.get("type")
        step_name = step.get("name", "unknown")
        
        if step_index is not None:
            self.logger.info(f"Step {step_index} : {step_name}")
        else:
            self.logger.info(f"Executing step: {step_name} (type: {step_type})")
        
        if step_type == "click":
            return self._step_click(step)
        elif step_type == "swipe":
            return self._step_swipe(step)
        elif step_type == "wait":
            return self._step_wait(step)
        elif step_type == "wait_template":
            return self._step_wait_template(step)
        elif step_type == "find_and_click":
            return self._step_find_and_click(step)
        elif step_type == "screenshot":
            return self._step_screenshot(step)
        elif step_type == "notification":
            return self._step_notification(step)
        elif step_type == "stop_task":
            return self._step_stop_task(step)
        else:
            self.logger.warning(f"Unknown step type: {step_type}")
            return False
    
    def _step_click(self, step: Dict[str, Any]) -> bool:
        """Execute click step"""
        x = step.get("x")
        y = step.get("y")
        
        if x is None or y is None:
            self.logger.error("Click step missing coordinates")
            return False
        
        self.emulator.click(x, y)
        time.sleep(step.get("delay", 0.5))
        return True
    
    def _step_swipe(self, step: Dict[str, Any]) -> bool:
        """Execute swipe step"""
        x1 = step.get("x1")
        y1 = step.get("y1")
        x2 = step.get("x2")
        y2 = step.get("y2")
        duration = step.get("duration", 300)
        
        if any(v is None for v in [x1, y1, x2, y2]):
            self.logger.error("Swipe step missing coordinates")
            return False
        
        self.emulator.swipe(x1, y1, x2, y2, duration)
        time.sleep(step.get("delay", 0.5))
        return True
    
    def _step_wait(self, step: Dict[str, Any]) -> bool:
        """Execute wait step"""
        duration = step.get("duration", 1.0)
        time.sleep(duration)
        return True
    
    def _step_wait_template(self, step: Dict[str, Any]) -> bool:
        """Wait for template to appear"""
        template = step.get("template")
        timeout = step.get("timeout", 10)
        
        if not template:
            self.logger.error("Wait template step missing template path")
            return False
        
        # Try game-specific template first, then global
        # Use sanitized game name (no accents) for directory
        game_name = self.game_config.get("name", "")
        sanitized_game_name = sanitize_filename(game_name)
        template_path = Path("config/templates") / sanitized_game_name / template
        if not template_path.exists():
            template_path = Path("config/templates") / template
        
        if not template_path.exists():
            self.logger.error(f"Template not found: {template_path}")
            return False
        
        result = self.matcher.wait_for_template(
            self.emulator.screenshot,
            str(template_path),
            timeout=timeout
        )
        
        return result is not None
    
    def _step_find_and_click(self, step: Dict[str, Any]) -> bool:
        """Find template and click on it"""
        # Support multiple templates: try each one in order until found
        templates = step.get("templates", [])
        template = step.get("template")  # Backward compatibility
        
        # If templates list exists, use it; otherwise use single template
        if templates:
            template_list = templates
        elif template:
            template_list = [template]
        else:
            self.logger.error("Find and click step missing template path")
            return False
        
        threshold = step.get("threshold", 0.7)
        timeout = step.get("timeout", 10)
        click_all = step.get("click_all", False)  # Click all occurrences
        continue_if_not_found = step.get("continue_if_not_found", False)  # Continue to next step if not found
        goto_step_if_found = step.get("goto_step_if_found")  # Jump to step index if found
        goto_step_if_not_found = step.get("goto_step_if_not_found")  # Jump to step index if not found
        
        # Try each template in order until one is found on screen
        game_name = self.game_config.get("name", "")
        sanitized_game_name = sanitize_filename(game_name)
        
        found_template = None
        found_template_path = None
        
        # First, verify all template files exist
        valid_templates = []
        for template in template_list:
            # Try game-specific template first, then global
            template_path = Path("config/templates") / sanitized_game_name / template
            if not template_path.exists():
                template_path = Path("config/templates") / template
            
            if template_path.exists():
                valid_templates.append((template, template_path))
            else:
                self.logger.warning(f"Template file không tồn tại: {template}")
        
        if not valid_templates:
            self.logger.error(f"Không tìm thấy file template nào trong danh sách: {template_list}")
            if goto_step_if_not_found:
                self.next_step_index = goto_step_if_not_found
                self.logger.info(f"Không tìm thấy template nào, nhảy đến step {goto_step_if_not_found}")
                return True
            elif continue_if_not_found:
                self.logger.info("Tiếp tục step tiếp theo")
                return True
            return False
        
        # Log all templates that will be tried
        # self.logger.info(f"Sẽ thử tìm {len(valid_templates)} template(s): {[t[0] for t in valid_templates]}")
        
        if click_all:
            # Find and click all occurrences
            # Log device info for debugging
            if hasattr(self.emulator, 'device_id'):
                self.logger.info(f"Chụp hình từ device: {self.emulator.device_id}")
            screenshot = self.emulator.screenshot()
            if not screenshot:
                self.logger.error("Failed to take screenshot")
                if hasattr(self.emulator, 'device_id'):
                    self.logger.error(f"Device ID: {self.emulator.device_id}, Connected: {self.emulator.connected}")
                return False
            
            # Wait a bit for screen to stabilize
            time.sleep(0.5)
            
            # Try each template until one is found
            screenshot_size = screenshot.size if screenshot else None
            found_template = None
            found_template_path = None
            all_matches = []
            
            for template_name, template_path in valid_templates:
                self.logger.info(f"Đang thử tìm template: {template_name} (Threshold: {threshold})")
                # Find all templates
                matches = self.matcher.find_all_templates(
                    screenshot,
                    str(template_path),
                    threshold=threshold
                )
                
                if matches:
                    found_template = template_name
                    found_template_path = template_path
                    all_matches = matches
                    self.logger.info(f"✓ Tìm thấy {len(matches)} lần xuất hiện của template: {template_name}")
                    break
                else:
                    self.logger.debug(f"✗ Không tìm thấy template: {template_name}, thử template tiếp theo...")
            
            if not all_matches:
                # self.logger.warning(f"Không tìm thấy template nào trong {len(valid_templates)} template(s) (Screenshot: {screenshot_size}, Threshold: {threshold})")
                if goto_step_if_not_found:
                    self.next_step_index = goto_step_if_not_found
                    self.logger.info(f"Không tìm thấy template, nhảy đến step {goto_step_if_not_found}")
                    return True
                elif continue_if_not_found:
                    self.logger.info("Tiếp tục step tiếp theo")
                    return True
                return False
            
            # Click all matches
            delay = step.get("delay", 0.5)
            for i, (x, y) in enumerate(all_matches, 1):
                self.logger.info(f"Clicking occurrence {i}/{len(all_matches)} at ({x}, {y})")
                self.emulator.click(x, y)
                time.sleep(delay)
            
            # Check if we need to jump to a specific step after finding
            if goto_step_if_found:
                self.next_step_index = goto_step_if_found
                self.logger.info(f"Đã tìm thấy template, nhảy đến step {goto_step_if_found}")
            
            return True
        else:
            # Original behavior: wait for template and click first occurrence
            # Try each template until one is found
            # Log device info for debugging
            # if hasattr(self.emulator, 'device_id'):
            #     self.logger.info(f"Tìm template từ device: {self.emulator.device_id}")
            
            found_template = None
            found_template_path = None
            result = None
            
            # Try each template in order
            # Divide timeout equally among all templates
            timeout_per_template = max(1.0, timeout / len(valid_templates))
            # self.logger.info(f"Timeout cho mỗi template: {timeout_per_template:.1f} giây (tổng: {timeout} giây)")
            
            for template_name, template_path in valid_templates:
                self.logger.info(f"Đang thử tìm template: {template_name}")
                result = self.matcher.wait_for_template(
                    self.emulator.screenshot,
                    str(template_path),
                    timeout=timeout_per_template,
                    threshold=threshold
                )
                
                if result:
                    found_template = template_name
                    found_template_path = template_path
                    self.logger.info(f"✓ Tìm thấy template: {template_name}")
                    break
                else:
                    self.logger.debug(f"✗ Không tìm thấy template: {template_name}, thử template tiếp theo...")
            
            if result:
                x, y = result
                # self.logger.info(f"Đã tìm thấy và click vào template: {found_template} tại ({x}, {y})")
                self.emulator.click(x, y)
                time.sleep(step.get("delay", 0.5))
                
                # Check if we need to jump to a specific step after finding
                if goto_step_if_found:
                    self.next_step_index = goto_step_if_found
                    self.logger.info(f"Đã tìm thấy template, nhảy đến step {goto_step_if_found}")
                
                return True
            else:
                # self.logger.warning(f"Không tìm thấy template nào trong {len(valid_templates)} template(s) sau {timeout} giây")
                if goto_step_if_not_found:
                    self.next_step_index = goto_step_if_not_found
                    self.logger.info(f"Không tìm thấy template, nhảy đến step {goto_step_if_not_found}")
                    return True
                elif continue_if_not_found:
                    self.logger.info("Tiếp tục step tiếp theo")
                    return True
                return False
    
    def _step_screenshot(self, step: Dict[str, Any]) -> bool:
        """Take screenshot"""
        save_path = step.get("save_path")
        
        # If no path specified, use default structure: screenshots/game_name/task_name/
        if not save_path:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Sanitize game and task names to avoid Unicode issues
            sanitized_game_name = sanitize_filename(self.game_name)
            sanitized_task_name = sanitize_filename(self.current_task_name or "unknown")
            save_path = f"screenshots/{sanitized_game_name}/{sanitized_task_name}/screenshot_{timestamp}.png"
        
        # Ensure directory exists
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        screenshot = self.emulator.screenshot(save_path)
        if screenshot:
            self.logger.info(f"Screenshot saved: {save_path}")
        return screenshot is not None
    
    def _step_notification(self, step: Dict[str, Any]) -> bool:
        """Show notification dialog to user"""
        message = step.get("message", "Đã chạy đến bước thông báo")
        step_name = step.get("name", "Thông báo")
        
        self.logger.info(f"Hiển thị thông báo: {step_name}")
        
        # If callback is provided, use it to show dialog
        if self.notification_callback:
            # Callback should return True to continue, False to stop
            result = self.notification_callback(message, step_name)
            if result:
                self.logger.info("Người dùng chọn: Tiếp tục")
                return True
            else:
                self.logger.info("Người dùng chọn: Dừng lại")
                self.running = False  # Stop task execution
                self.user_requested_stop = True  # Mark that user requested stop
                return False
        else:
            # No callback, just log and continue
            self.logger.warning("Notification callback not set, continuing...")
            return True
    
    def _step_stop_task(self, step: Dict[str, Any]) -> bool:
        """Stop entire task execution (including all loops)"""
        message = step.get("message", "Đã đến step dừng task")
        step_name = step.get("name", "Dừng task")
        
        self.logger.info(f"Step dừng task: {step_name}")
        if message:
            self.logger.info(f"Lý do: {message}")
        
        # Set flags to stop task and all loops
        self.force_stop_task = True
        self.running = False
        
        return True
    
    def stop(self):
        """Stop task execution"""
        self.running = False

