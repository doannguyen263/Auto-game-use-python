"""
Emulator Controller - Control Android emulators via ADB
"""
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import numpy as np


class EmulatorController:
    """Control Android emulator via ADB"""
    
    def __init__(self, emulator_type: str = "auto", adb_path: str = None, logger=None):
        """
        Initialize emulator controller
        
        Args:
            emulator_type: Type of emulator (auto/bluestacks/nox/ldplayer)
            adb_path: Path to ADB executable (None to auto-detect)
            logger: Logger instance for logging (optional)
        """
        self.emulator_type = emulator_type
        if adb_path is None:
            self.adb_path = self._find_adb()
        else:
            self.adb_path = adb_path
        self.connected = False
        self.device_id = None
        self.logger = logger  # Logger instance for logging
    
    def set_logger(self, logger):
        """Set logger instance"""
        self.logger = logger
    
    def _log(self, message, level='info'):
        """Log message using logger if available, otherwise print"""
        if self.logger:
            if level == 'info':
                self.logger.info(message)
            elif level == 'warning':
                self.logger.warning(message)
            elif level == 'error':
                self.logger.error(message)
            else:
                self.logger.info(message)
        else:
            print(message)
    
    @staticmethod
    def list_all_devices(adb_path: str = None) -> list:
        """
        List all connected devices/emulators
        
        Args:
            adb_path: Path to ADB executable (None to auto-detect)
        
        Returns:
            List of device IDs
        """
        if adb_path is None:
            controller = EmulatorController()
            adb_path = controller.adb_path
        
        try:
            result = subprocess.run(
                [adb_path, "devices"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            devices = []
            for line in result.stdout.strip().split('\n')[1:]:
                if line.strip() and 'device' in line:
                    device_id = line.split()[0]
                    devices.append(device_id)
            
            return devices
        except Exception as e:
            print(f"Error listing devices: {e}")
            return []
    
    def connect_to_device(self, device_id: str) -> bool:
        """
        Connect to a specific device
        
        Args:
            device_id: Device ID to connect to
        
        Returns:
            True if connected successfully
        """
        try:
            # Check if device exists
            result = subprocess.run(
                [self.adb_path, "devices"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            devices = [line.split()[0] for line in result.stdout.strip().split('\n')[1:] 
                      if line.strip() and 'device' in line]
            
            if device_id not in devices:
                print(f"Device {device_id} not found")
                return False
            
            self.device_id = device_id
            self.connected = True
            print(f"Connected to device: {self.device_id}")
            return True
            
        except Exception as e:
            print(f"Error connecting to device: {e}")
            return False
    
    def _find_adb(self):
        """Find ADB executable"""
        import os
        import shutil
        
        # Try to find ADB in PATH first
        adb_path = shutil.which("adb")
        if adb_path:
            return adb_path
        
        # Try user's platform-tools directory first
        user_paths = [
            r"D:\platform-tools\adb.exe",
            r"C:\platform-tools\adb.exe",
            os.path.expanduser(r"~\platform-tools\adb.exe"),
        ]
        
        for path in user_paths:
            if os.path.exists(path):
                return path
        
        # Find LDPlayer ADB
        ldplayer_paths = [
            r"C:\LDPlayer\LDPlayer4.0\adb.exe",
            r"C:\LDPlayer\LDPlayer\adb.exe",
            r"C:\LDPlayer64\LDPlayer4.0\adb.exe",
            r"C:\LDPlayer64\LDPlayer\adb.exe",
            os.path.expanduser(r"~\LDPlayer\LDPlayer4.0\adb.exe"),
            os.path.expanduser(r"~\LDPlayer\LDPlayer\adb.exe"),
        ]
        
        for path in ldplayer_paths:
            if os.path.exists(path):
                return path
        
        # Try common ADB locations
        common_paths = [
            r"C:\Android\platform-tools\adb.exe",
            os.path.expanduser(r"~\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
            os.path.expanduser(r"~\Android\Sdk\platform-tools\adb.exe"),
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        # Fallback to "adb" (hopefully in PATH)
        return "adb"
    
    def connect(self) -> bool:
        """
        Connect to emulator
        
        Returns:
            True if connected successfully
        """
        try:
            # Check ADB availability
            result = subprocess.run(
                [self.adb_path, "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                print("ADB not found. Please install Android SDK Platform Tools")
                return False
            
            # Handle LDPlayer specifically
            if self.emulator_type == "ldplayer":
                return self._connect_ldplayer()
            
            # Get connected devices
            result = subprocess.run(
                [self.adb_path, "devices"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            devices = [line.split()[0] for line in result.stdout.strip().split('\n')[1:] 
                      if line.strip() and 'device' in line]
            
            if not devices:
                # Try auto-connect for common emulators
                if self.emulator_type == "auto":
                    # Try LDPlayer ports
                    for port in [5555, 5557, 5565, 5575]:
                        if self._try_connect_port(port):
                            return True
                
                print("No emulator/device connected")
                return False
            
            self.device_id = devices[0]
            self.connected = True
            print(f"Connected to device: {self.device_id}")
            return True
            
        except subprocess.TimeoutExpired:
            print("ADB connection timeout")
            return False
        except Exception as e:
            print(f"Error connecting to emulator: {e}")
            return False
    
    def _connect_ldplayer(self) -> bool:
        """Connect to LDPlayer emulator"""
        # LDPlayer typically uses ports: 5555 (first), 5557 (second), 5565 (third), etc.
        common_ports = [5555, 5557, 5565, 5575, 5585]
        
        for port in common_ports:
            if self._try_connect_port(port):
                return True
        
        print("LDPlayer not found on common ports.")
        return False
    
    def _try_connect_port(self, port: int) -> bool:
        """Try to connect to a specific port"""
        try:
            # Try to connect
            result = subprocess.run(
                [self.adb_path, "connect", f"127.0.0.1:{port}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Check if connected
            result = subprocess.run(
                [self.adb_path, "devices"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            devices = [line.split()[0] for line in result.stdout.strip().split('\n')[1:] 
                      if line.strip() and 'device' in line and f":{port}" in line]
            
            if devices:
                self.device_id = devices[0]
                self.connected = True
                print(f"Connected to device: {self.device_id}")
                return True
            
            return False
        except:
            return False
    
    def _run_adb_command(self, command: list, timeout: int = 10) -> Optional[str]:
        """
        Run ADB command
        
        Args:
            command: ADB command as list
            timeout: Command timeout in seconds
        
        Returns:
            Command output or None if failed
        """
        if not self.connected:
            return None
        
        try:
            full_command = [self.adb_path, "-s", self.device_id] + command
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                print(f"ADB command failed: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Error running ADB command: {e}")
            return None
    
    def screenshot(self, save_path: Optional[str] = None) -> Optional[Image.Image]:
        """
        Take screenshot of emulator screen
        
        Args:
            save_path: Optional path to save screenshot
        
        Returns:
            PIL Image or None if failed
        """
        if not self.connected:
            self._log(f"Warning: Screenshot called but emulator not connected. Device ID: {self.device_id}", 'warning')
            return None
        
        if not self.device_id:
            self._log("Warning: Screenshot called but device_id is None", 'warning')
            return None
        
        try:
            import io
            import subprocess
            
            # Take screenshot via ADB (binary output)
            full_command = [self.adb_path, "-s", self.device_id, "exec-out", "screencap", "-p"]
            # Debug: log the command being executed
            self._log(f"📸 Chụp màn hình từ device: {self.device_id}")
            process = subprocess.run(
                full_command,
                capture_output=True,
                timeout=10
            )
            
            if process.returncode != 0:
                error_msg = f"Screenshot failed for device {self.device_id}, return code: {process.returncode}"
                if process.stderr:
                    error_detail = process.stderr.decode('utf-8', errors='ignore')
                    error_msg += f" - Error: {error_detail}"
                self._log(error_msg, 'error')
                return None
            
            # Convert bytes to image
            image = Image.open(io.BytesIO(process.stdout))
            
            # Save if path provided
            if save_path:
                image.save(save_path)
                self._log(f"✓ Đã lưu screenshot: {save_path}")
            
            return image
            
        except Exception as e:
            self._log(f"Error taking screenshot from device {self.device_id}: {e}", 'error')
            return None
    
    def click(self, x: int, y: int) -> bool:
        """
        Click at coordinates
        
        Args:
            x: X coordinate
            y: Y coordinate
        
        Returns:
            True if successful
        """
        if not self.connected:
            return False
        
        result = self._run_adb_command(["shell", "input", "tap", str(x), str(y)])
        return result is not None
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """
        Swipe from point to point
        
        Args:
            x1: Start X coordinate
            y1: Start Y coordinate
            x2: End X coordinate
            y2: End Y coordinate
            duration: Swipe duration in milliseconds
        
        Returns:
            True if successful
        """
        if not self.connected:
            return False
        
        result = self._run_adb_command([
            "shell", "input", "swipe",
            str(x1), str(y1), str(x2), str(y2), str(duration)
        ])
        return result is not None
    
    def input_text(self, text: str) -> bool:
        """
        Input text
        
        Args:
            text: Text to input
        
        Returns:
            True if successful
        """
        if not self.connected:
            return False
        
        # Escape special characters
        text = text.replace(" ", "%s").replace("&", "\\&")
        result = self._run_adb_command(["shell", "input", "text", text])
        return result is not None
    
    def press_key(self, keycode: str) -> bool:
        """
        Press key
        
        Args:
            keycode: Android keycode (e.g., "KEYCODE_BACK", "KEYCODE_HOME")
        
        Returns:
            True if successful
        """
        if not self.connected:
            return False
        
        result = self._run_adb_command(["shell", "input", "keyevent", keycode])
        return result is not None
    
    def get_screen_size(self) -> Optional[Tuple[int, int]]:
        """
        Get screen size
        
        Returns:
            Tuple of (width, height) or None if failed
        """
        if not self.connected:
            return None
        
        result = self._run_adb_command(["shell", "wm", "size"])
        
        if result:
            # Parse output like "Physical size: 1080x1920"
            try:
                size_str = result.strip().split()[-1]
                width, height = map(int, size_str.split('x'))
                return (width, height)
            except:
                pass
        
        return None

