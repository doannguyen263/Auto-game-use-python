"""
Main GUI Window - Game Automation Tool
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
from pathlib import Path
import sys

# Add parent to path
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(parent_dir / "src"))

from config.manager import ConfigManager
from emulator.controller import EmulatorController
from task.manager import TaskManager
from utils.text_utils import sanitize_filename
from utils.logger import setup_logger


class MainWindow:
    """Main GUI window"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Game Automation Tool")
        
        # Hide window until positioned
        self.root.withdraw()
        
        # Set window size (2/3 of original)
        width = 600
        height = 700
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate position to top right
        margin = 10
        x = screen_width - width - margin
        y = margin
        
        # Set window geometry with top right position
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.resizable(True, True)
        
        # Variables
        self.config_manager = ConfigManager()
        self.emulator = None
        self.task_manager = None
        self.logger = None
        self.running = False
        self.current_game = tk.StringVar()
        self.current_task = tk.StringVar()
        self.task_builder_window = None  # Track task builder window
        self.repeat_mode = tk.StringVar(value="none")  # "none", "manual", "infinite"
        self.repeat_count = tk.IntVar(value=1)
        self.iteration_counter = 0  # Track iteration count across runs
        
        # Setup UI
        self.setup_ui()
        self.load_games()
        
        # Show window after setup
        self.root.deiconify()
        
    def setup_ui(self):
        """Setup user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Game Automation Tool",
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # Emulator connection section
        emulator_frame = ttk.LabelFrame(main_frame, text="Kết nối Giả lập", padding="10")
        emulator_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5, padx=5)
        emulator_frame.columnconfigure(1, weight=1)
        
        # Emulator type selection
        ttk.Label(emulator_frame, text="Loại giả lập:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.emulator_type_var = tk.StringVar(value="auto")
        emulator_combo = ttk.Combobox(
            emulator_frame, 
            textvariable=self.emulator_type_var, 
            values=["auto", "ldplayer", "bluestacks", "nox"],
            state="readonly",
            width=15
        )
        emulator_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Emulator info label
        self.emulator_info_label = ttk.Label(
            emulator_frame, 
            text="Các giả lập hỗ trợ: LDPlayer, BlueStacks, Nox",
            font=("Arial", 9),
            foreground="gray"
        )
        self.emulator_info_label.grid(row=0, column=2, sticky=tk.W, padx=10, pady=5)
        
        # Connection buttons
        emulator_button_frame = ttk.Frame(emulator_frame)
        emulator_button_frame.grid(row=1, column=0, columnspan=3, pady=5)
        
        ttk.Button(emulator_button_frame, text="🔌 Kiểm tra kết nối", command=self.test_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(emulator_button_frame, text="🎮 Kết nối LDPlayer", command=self.connect_ldplayer).pack(side=tk.LEFT, padx=5)
        ttk.Button(emulator_button_frame, text="📸 Chụp màn hình", command=self.take_screenshot).pack(side=tk.LEFT, padx=5)
        
        # Game selection
        ttk.Label(main_frame, text="Chọn Game:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.game_combo = ttk.Combobox(main_frame, textvariable=self.current_game, width=30, state="readonly")
        self.game_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        self.game_combo.bind("<<ComboboxSelected>>", self.on_game_selected)
        
        ttk.Button(main_frame, text="Quản lý Game", command=self.open_game_manager).grid(row=2, column=2, padx=5)
        
        # Task selection
        ttk.Label(main_frame, text="Chọn Task:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.task_combo = ttk.Combobox(main_frame, textvariable=self.current_task, width=30, state="readonly")
        self.task_combo.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        self.task_combo.bind("<<ComboboxSelected>>", self.on_task_selected)
        
        # Task buttons frame
        task_button_frame = ttk.Frame(main_frame)
        task_button_frame.grid(row=3, column=2, padx=5)
        
        self.task_button = ttk.Button(task_button_frame, text="Tạo Task", command=self.open_task_builder)
        self.task_button.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(task_button_frame, text="➕ Tạo Task Mới", command=self.create_new_task).pack(side=tk.LEFT, padx=2)
        
        # Repeat options
        repeat_frame = ttk.LabelFrame(main_frame, text="Tùy chọn Lặp", padding="10")
        repeat_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5, padx=5)
        repeat_frame.columnconfigure(1, weight=1)
        
        # Repeat mode selection
        ttk.Radiobutton(
            repeat_frame, 
            text="Không lặp", 
            variable=self.repeat_mode, 
            value="none"
        ).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        
        ttk.Radiobutton(
            repeat_frame, 
            text="Lặp thủ công", 
            variable=self.repeat_mode, 
            value="manual",
            command=self.on_repeat_mode_changed
        ).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        self.repeat_count_entry = ttk.Entry(repeat_frame, textvariable=self.repeat_count, width=10, state=tk.DISABLED)
        self.repeat_count_entry.grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(repeat_frame, text="lần").grid(row=0, column=3, sticky=tk.W, padx=2, pady=2)
        
        ttk.Radiobutton(
            repeat_frame, 
            text="Lặp vô hạn", 
            variable=self.repeat_mode, 
            value="infinite"
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        self.start_button = ttk.Button(button_frame, text="▶ Bắt đầu", command=self.start_task, state=tk.NORMAL)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="⏹ Dừng", command=self.stop_task, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_label = ttk.Label(main_frame, text="Sẵn sàng", relief=tk.SUNKEN)
        self.status_label.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
    def load_games(self):
        """Load available games"""
        games_dir = Path("config/games")
        games = []
        
        if games_dir.exists():
            for config_file in games_dir.glob("*.yaml"):
                games.append(config_file.stem)
        
        if games:
            self.game_combo['values'] = games
            if games:
                self.current_game.set(games[0])
                self.on_game_selected()
        else:
            self.log("Không tìm thấy game nào. Vui lòng tạo game mới.")
    
    def on_game_selected(self, event=None):
        """Handle game selection"""
        game_name = self.current_game.get()
        if not game_name:
            return
        
        # Load tasks for selected game
        game_config = self.config_manager.load_game_config(game_name)
        if game_config:
            tasks = list(game_config.get("tasks", {}).keys())
            self.task_combo['values'] = tasks
            if tasks:
                self.current_task.set(tasks[0])
                self.on_task_selected()  # Update button state
        else:
            self.task_combo['values'] = []
            self.current_task.set("")
            self.update_task_button()
    
    def on_task_selected(self, event=None):
        """Handle task selection - update button text"""
        self.update_task_button()
    
    def update_task_button(self):
        """Update task button text based on whether task exists"""
        game_name = self.current_game.get()
        task_name = self.current_task.get()
        
        if not game_name or not task_name:
            self.task_button.config(text="Tạo Task")
            return
        
        # Check if task exists
        game_config = self.config_manager.load_game_config(game_name)
        if game_config:
            tasks = game_config.get("tasks", {})
            if task_name in tasks:
                self.task_button.config(text="✏️ Chỉnh sửa Task")
            else:
                self.task_button.config(text="Tạo Task")
        else:
            self.task_button.config(text="Tạo Task")
    
    def on_repeat_mode_changed(self):
        """Handle repeat mode change - enable/disable repeat count entry"""
        if self.repeat_mode.get() == "manual":
            self.repeat_count_entry.config(state=tk.NORMAL)
        else:
            self.repeat_count_entry.config(state=tk.DISABLED)
    
    def log(self, message):
        """Add message to log"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_status(self, status):
        """Update status bar"""
        self.status_label.config(text=status)
    
    def test_connection(self):
        """Test emulator connection"""
        emulator_type = self.emulator_type_var.get()
        self.log(f"Đang kiểm tra kết nối emulator ({emulator_type})...")
        self.update_status("Đang kiểm tra...")
        
        def test():
            try:
                # Check ADB first
                adb_path = self.find_adb()
                if not adb_path:
                    self.log("✗ Không tìm thấy ADB!")
                    self.log("Vui lòng cài đặt Android SDK Platform Tools")
                    self.log("Tải từ: https://developer.android.com/studio/releases/platform-tools")
                    self.root.after(0, lambda: self.update_status("Không tìm thấy ADB"))
                    return
                
                self.log(f"Tìm thấy ADB: {adb_path}")
                
                # Try selected emulator type
                emulator = EmulatorController(emulator_type=emulator_type, adb_path=adb_path)
                if emulator.connect():
                    size = emulator.get_screen_size()
                    if size:
                        self.log(f"✓ Kết nối thành công! Resolution: {size[0]}x{size[1]}")
                        self.log(f"  Device ID: {emulator.device_id}")
                        self.root.after(0, lambda s=size: self.update_status(f"Đã kết nối ({emulator_type}) - {s[0]}x{s[1]}"))
                    else:
                        self.log("✓ Kết nối thành công!")
                        self.log(f"  Device ID: {emulator.device_id}")
                        self.root.after(0, lambda: self.update_status(f"Đã kết nối ({emulator_type})"))
                    return
                
                # If auto failed, try other types
                if emulator_type == "auto":
                    for other_type in ["ldplayer", "bluestacks", "nox"]:
                        self.log(f"Thử kết nối {other_type}...")
                        emulator = EmulatorController(emulator_type=other_type, adb_path=adb_path)
                        if emulator.connect():
                            size = emulator.get_screen_size()
                            if size:
                                self.log(f"✓ Kết nối thành công với {other_type}! Resolution: {size[0]}x{size[1]}")
                                self.root.after(0, lambda s=size, t=other_type: self.update_status(f"Đã kết nối ({t}) - {s[0]}x{s[1]}"))
                            else:
                                self.log(f"✓ Kết nối thành công với {other_type}!")
                                self.root.after(0, lambda t=other_type: self.update_status(f"Đã kết nối ({t})"))
                            return
                
                self.log("✗ Không thể kết nối đến emulator")
                self.log("Vui lòng kiểm tra:")
                self.log("  1. Emulator đang chạy")
                self.log("  2. USB debugging đã bật (hoặc ADB enabled cho LDPlayer)")
                self.log("  3. Click '🎮 Kết nối LDPlayer' để kết nối thủ công")
                self.root.after(0, lambda: self.update_status("Kết nối thất bại"))
            except Exception as e:
                self.log(f"✗ Lỗi: {e}")
                import traceback
                self.log(traceback.format_exc())
                self.root.after(0, lambda: self.update_status("Lỗi"))
        
        threading.Thread(target=test, daemon=True).start()
    
    def take_screenshot(self):
        """Take screenshot"""
        self.log("Đang chụp màn hình...")
        
        def screenshot():
            try:
                # Get current game and task
                game_name = self.current_game.get() or "unknown"
                task_name = self.current_task.get() or "manual"
                
                adb_path = self.find_adb()
                if not adb_path:
                    self.log("✗ Không tìm thấy ADB")
                    return
                
                emulator = EmulatorController(emulator_type="ldplayer", adb_path=adb_path)
                if not emulator.connect():
                    emulator = EmulatorController(emulator_type="auto", adb_path=adb_path)
                    if not emulator.connect():
                        self.log("✗ Không thể kết nối đến emulator")
                        return
                
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Sanitize game and task names to avoid Unicode issues
                sanitized_game_name = sanitize_filename(game_name)
                sanitized_task_name = sanitize_filename(task_name)
                save_path = f"screenshots/{sanitized_game_name}/{sanitized_task_name}/screenshot_{timestamp}.png"
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                
                img = emulator.screenshot(save_path)
                if img:
                    self.log(f"✓ Đã lưu screenshot: {save_path}")
                    self.root.after(0, lambda: self.update_status(f"Screenshot: {save_path}"))
                else:
                    self.log("✗ Không thể chụp màn hình")
            except Exception as e:
                self.log(f"✗ Lỗi: {e}")
                import traceback
                self.log(traceback.format_exc())
        
        threading.Thread(target=screenshot, daemon=True).start()
    
    def find_adb(self):
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
        
        return None
    
    def connect_ldplayer(self):
        """Connect to LDPlayer emulator"""
        self.log("Đang kết nối đến LDPlayer...")
        self.update_status("Đang kết nối LDPlayer...")
        
        def connect():
            try:
                import os
                import subprocess
                
                # Find ADB
                adb_path = self.find_adb()
                
                if not adb_path:
                    self.log("✗ Không tìm thấy ADB!")
                    self.log("Vui lòng:")
                    self.log("  1. Cài đặt Android SDK Platform Tools")
                    self.log("     Tải từ: https://developer.android.com/studio/releases/platform-tools")
                    self.log("  2. Hoặc đảm bảo LDPlayer đã cài đặt (có ADB sẵn)")
                    self.log("  3. Thêm ADB vào PATH hoặc đặt trong thư mục dự án")
                    self.root.after(0, lambda: self.update_status("Không tìm thấy ADB"))
                    return
                
                self.log(f"Sử dụng ADB: {adb_path}")
                
                # Test ADB
                try:
                    result = subprocess.run(
                        [adb_path, "version"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode != 0:
                        self.log("✗ ADB không hoạt động")
                        self.root.after(0, lambda: self.update_status("ADB lỗi"))
                        return
                except Exception as e:
                    self.log(f"✗ Không thể chạy ADB: {e}")
                    self.root.after(0, lambda: self.update_status("ADB lỗi"))
                    return
                
                # Try common LDPlayer ports
                ports = [5555, 5557, 5565, 5575, 5585]
                connected = False
                
                for port in ports:
                    self.log(f"Đang thử kết nối port {port}...")
                    try:
                        result = subprocess.run(
                            [adb_path, "connect", f"127.0.0.1:{port}"],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        
                        self.log(f"Kết quả: {result.stdout.strip()}")
                        
                        if "connected" in result.stdout.lower() or "already connected" in result.stdout.lower():
                            self.log(f"✓ Đã kết nối đến port {port}")
                            
                            # Verify connection
                            result = subprocess.run(
                                [adb_path, "devices"],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            
                            self.log(f"Danh sách devices:\n{result.stdout}")
                            
                            devices = [line.split()[0] for line in result.stdout.strip().split('\n')[1:] 
                                      if line.strip() and 'device' in line and f":{port}" in line]
                            
                            if devices:
                                self.log(f"✓ Kết nối thành công! Device: {devices[0]}")
                                self.root.after(0, lambda d=devices[0]: self.update_status(f"Đã kết nối LDPlayer - {d}"))
                                connected = True
                                break
                    except FileNotFoundError:
                        self.log(f"✗ Không tìm thấy ADB tại: {adb_path}")
                        break
                    except Exception as e:
                        self.log(f"Lỗi khi kết nối port {port}: {e}")
                        continue
                
                if not connected:
                    self.log("✗ Không thể kết nối đến LDPlayer")
                    self.log("Vui lòng kiểm tra:")
                    self.log("  1. LDPlayer đang chạy")
                    self.log("  2. LDPlayer Settings → Advanced → Enable ADB")
                    self.log("  3. Thử restart LDPlayer")
                    self.root.after(0, lambda: self.update_status("Kết nối LDPlayer thất bại"))
                
            except Exception as e:
                self.log(f"✗ Lỗi: {e}")
                import traceback
                self.log(traceback.format_exc())
                self.root.after(0, lambda: self.update_status("Lỗi"))
        
        threading.Thread(target=connect, daemon=True).start()
    
    def start_task(self):
        """Start selected task"""
        game_name = self.current_game.get()
        task_name = self.current_task.get()
        
        if not game_name:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn game!")
            return
        
        if not task_name:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn task!")
            return
        
        # Disable start button, enable stop button
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # Reset iteration counter when starting a new task
        # Only keep counter if in infinite mode and already running
        if self.repeat_mode.get() != "infinite" or not self.running:
            self.iteration_counter = 0
        
        self.running = True
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        self.log(f"Bắt đầu task: {task_name} cho game: {game_name}")
        self.update_status(f"Đang chạy: {task_name}")
        
        def run_task():
            try:
                # Create custom logger that writes to GUI
                class GUILogger:
                    def __init__(self, log_func):
                        self.log_func = log_func
                    
                    def info(self, msg):
                        self.log_func(f"=> {msg}")
                    
                    def error(self, msg, exc_info=False):
                        if exc_info:
                            import traceback
                            self.log_func(f"ERROR: {msg}")
                            self.log_func(traceback.format_exc())
                        else:
                            self.log_func(f"ERROR: {msg}")
                    
                    def warning(self, msg):
                        self.log_func(f"WARNING: {msg}")
                    
                    def debug(self, msg):
                        self.log_func(f"DEBUG: {msg}")
                
                gui_logger = GUILogger(self.log)
                
                # Load config
                game_config = self.config_manager.load_game_config(game_name)
                if not game_config:
                    self.log(f"✗ Không tìm thấy config cho game: {game_name}")
                    return
                
                # Connect emulator - try LDPlayer first
                self.emulator = EmulatorController(emulator_type="ldplayer")
                if not self.emulator.connect():
                    # Try auto if LDPlayer fails
                    self.emulator = EmulatorController(emulator_type="auto")
                    if not self.emulator.connect():
                        self.log("✗ Không thể kết nối đến emulator")
                        self.log("Thử chạy: python connect_ldplayer.py để kết nối LDPlayer")
                        return
                
                self.log("✓ Đã kết nối đến emulator")
                
                # Create task manager
                self.task_manager = TaskManager(self.emulator, game_config, gui_logger, game_name=game_name)
                
                # Get repeat settings
                repeat_mode = self.repeat_mode.get()
                repeat_count = self.repeat_count.get() if repeat_mode == "manual" else 1
                
                # Run task with repeat logic
                self.log(f"Đang thực thi task: {task_name}...")
                
                if repeat_mode == "none":
                    # Run once
                    success = self.task_manager.run_task(task_name)
                    if success:
                        self.log("✓ Task hoàn thành thành công!")
                        self.root.after(0, lambda: self.update_status("Hoàn thành"))
                    else:
                        self.log("✗ Task thất bại")
                        self.root.after(0, lambda: self.update_status("Thất bại"))
                
                elif repeat_mode == "manual":
                    # Run N times
                    total_success = 0
                    for i in range(repeat_count):
                        if not self.running:
                            self.log(f"Đã dừng task (đã chạy {i}/{repeat_count} lần)")
                            break
                        
                        self.log(f"--- Lần lặp {i+1}/{repeat_count} ---")
                        success = self.task_manager.run_task(task_name)
                        if success:
                            total_success += 1
                            self.log(f"✓ Lần {i+1} hoàn thành")
                        else:
                            self.log(f"✗ Lần {i+1} thất bại")
                        
                        # Small delay between iterations (except last)
                        if i < repeat_count - 1 and self.running:
                            import time
                            time.sleep(0.5)
                    
                    if total_success == repeat_count:
                        self.log(f"✓ Tất cả {repeat_count} lần lặp hoàn thành thành công!")
                        self.root.after(0, lambda: self.update_status("Hoàn thành"))
                    else:
                        self.log(f"✗ Hoàn thành {total_success}/{repeat_count} lần lặp")
                        self.root.after(0, lambda: self.update_status("Hoàn thành một phần"))
                
                elif repeat_mode == "infinite":
                    # Run infinitely until stopped
                    while self.running:
                        self.iteration_counter += 1
                        current_iteration = self.iteration_counter
                        self.log(f"--- Lần lặp {current_iteration} ---")
                        success = self.task_manager.run_task(task_name)
                        if success:
                            self.log(f"✓ Lần {current_iteration} hoàn thành")
                        else:
                            self.log(f"✗ Lần {current_iteration} thất bại")
                        
                        # Small delay between iterations
                        if self.running:
                            import time
                            time.sleep(0.5)
                    
                    self.log(f"Đã dừng task (đã chạy {self.iteration_counter} lần)")
                    self.root.after(0, lambda: self.update_status("Đã dừng"))
                    
            except Exception as e:
                self.log(f"✗ Lỗi: {e}")
                import traceback
                self.log(traceback.format_exc())
                self.root.after(0, lambda: self.update_status("Lỗi"))
            finally:
                # Re-enable start button
                self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
                self.running = False
        
        threading.Thread(target=run_task, daemon=True).start()
    
    def stop_task(self):
        """Stop current task"""
        if self.task_manager:
            self.task_manager.stop()
        self.running = False
        self.log("Đã dừng task")
        self.update_status("Đã dừng")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
    
    def open_game_manager(self):
        """Open game manager window"""
        try:
            from gui.game_manager import GameManagerWindow
            window = GameManagerWindow(self.root, self.config_manager, self)
            window.window.grab_set()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở Game Manager: {e}")
    
    def _cleanup_orphaned_windows(self):
        """Clean up any orphaned Task Builder windows"""
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Toplevel):
                try:
                    title = widget.title()
                    if "Task Builder" in title:
                        # Check if it has a valid reference
                        if not hasattr(widget, 'task_builder_ref'):
                            # Orphaned window, destroy it
                            try:
                                widget.destroy()
                            except:
                                pass
                except:
                    pass
    
    def _is_task_builder_open(self):
        """Check if task builder window is still open"""
        # First check reference
        if self.task_builder_window:
            try:
                # Check if window still exists and is mapped
                window = self.task_builder_window.window
                if not window.winfo_exists():
                    self.task_builder_window = None
                    return False
                # Additional check: try to get window state
                try:
                    window.state()  # This will raise error if window is destroyed
                    return True
                except:
                    self.task_builder_window = None
                    return False
            except Exception:
                # Window was destroyed, clear reference
                self.task_builder_window = None
                return False
        
        # Also check all toplevel windows for any Task Builder window
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Toplevel):
                try:
                    title = widget.title()
                    if "Task Builder" in title:
                        # Found a Task Builder window, try to get reference
                        if hasattr(widget, 'task_builder_ref'):
                            self.task_builder_window = widget.task_builder_ref
                            return True
                        # If no reference, window might be orphaned, destroy it
                        try:
                            widget.destroy()
                        except:
                            pass
                except:
                    pass
        
        return False
    
    def open_task_builder(self):
        """Open task builder window for editing existing task"""
        game_name = self.current_game.get()
        if not game_name:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn game trước!")
            self.log("✗ Vui lòng chọn game trước khi tạo task")
            return
        
        task_name = self.current_task.get()
        if not task_name:
            # If no task selected, create new task
            self.create_new_task()
            return
        
        # Check if task builder window already exists
        if self._is_task_builder_open():
            # Window already open, just focus and load task
            self.task_builder_window.window.lift()
            self.task_builder_window.window.focus_force()
            self.task_builder_window.load_task_by_name(task_name)
            self.log(f"✓ Đã focus Task Builder và load task: {task_name}")
            return
        
        try:
            self.log(f"Đang mở Task Builder để chỉnh sửa task: {task_name}")
            from gui.task_builder import TaskBuilderWindow
            window = TaskBuilderWindow(self.root, game_name, self.config_manager, self)
            
            # Store reference BEFORE doing anything else
            self.task_builder_window = window
            
            # Load the selected task
            window.load_task_by_name(task_name)
            window.window.grab_set()
            
            # Handle window close to clear reference
            def on_close():
                if self.task_builder_window == window:
                    self.task_builder_window = None
                try:
                    window.window.destroy()
                except:
                    pass
            window.window.protocol("WM_DELETE_WINDOW", on_close)
            
            self.log(f"✓ Đã mở Task Builder cho task: {task_name}")
        except Exception as e:
            error_msg = f"Không thể mở Task Builder: {e}"
            self.log(f"✗ {error_msg}")
            import traceback
            self.log(traceback.format_exc())
            messagebox.showerror("Lỗi", error_msg)
            # Clear reference on error
            self.task_builder_window = None
    
    def create_new_task(self):
        """Create a new task"""
        game_name = self.current_game.get()
        if not game_name:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn game trước!")
            self.log("✗ Vui lòng chọn game trước khi tạo task")
            return
        
        # Check if task builder window already exists
        if self._is_task_builder_open():
            # Window already open, just focus and clear for new task
            self.task_builder_window.window.lift()
            self.task_builder_window.window.focus_force()
            # Clear current task
            self.task_builder_window.task_name_var.set("")
            self.task_builder_window.task_desc_var.set("")
            self.task_builder_window.steps = []
            self.task_builder_window.update_steps_list()
            self.task_builder_window.clear_step_ui()
            self.log(f"✓ Đã focus Task Builder để tạo task mới")
            return
        
        # Ensure no orphaned windows exist
        self._cleanup_orphaned_windows()
        
        try:
            self.log(f"Đang mở Task Builder để tạo task mới cho game: {game_name}")
            from gui.task_builder import TaskBuilderWindow
            window = TaskBuilderWindow(self.root, game_name, self.config_manager, self)
            
            # Store reference IMMEDIATELY
            self.task_builder_window = window
            window.window.grab_set()
            
            # Handle window close to clear reference
            def on_close():
                if self.task_builder_window == window:
                    self.task_builder_window = None
                try:
                    window.window.destroy()
                except:
                    pass
            window.window.protocol("WM_DELETE_WINDOW", on_close)
            
            self.log(f"✓ Đã mở Task Builder để tạo task mới cho game: {game_name}")
        except Exception as e:
            error_msg = f"Không thể mở Task Builder: {e}"
            self.log(f"✗ {error_msg}")
            import traceback
            self.log(traceback.format_exc())
            messagebox.showerror("Lỗi", error_msg)


def main():
    """Main entry point for GUI"""
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()

