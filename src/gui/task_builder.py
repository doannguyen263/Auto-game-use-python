"""
Task Builder Window - Create and edit tasks visually
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from pathlib import Path
import yaml
from typing import Dict, Any, List
from PIL import Image, ImageTk
from utils.text_utils import sanitize_filename


class TaskBuilderWindow:
    """Task builder window for creating tasks step by step"""
    
    def __init__(self, parent, game_name: str, config_manager, main_window):
        self.parent = parent
        self.game_name = game_name
        self.config_manager = config_manager
        self.main_window = main_window
        
        # Create window (2/3 of original size)
        self.window = tk.Toplevel(parent)
        self.window.title(f"Task Builder - {game_name}")
        
        # Set window size
        width = 667
        height = 750
        
        # Get screen dimensions
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        # Calculate position to top right
        margin = 10
        x = screen_width - width - margin
        y = margin
        
        # Set window geometry with top right position
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        self.window.resizable(True, True)
        
        # Store reference in window for easy lookup
        self.window.task_builder_ref = self
        
        # Variables
        self.steps: List[Dict[str, Any]] = []
        self.current_step_index = None
        
        # Load game config
        self.game_config = config_manager.load_game_config(game_name)
        if not self.game_config:
            messagebox.showerror("Lỗi", f"Không tìm thấy config cho game: {game_name}")
            self.window.destroy()
            return
        
        # Setup UI
        self.setup_ui()
        self.load_tasks()
    
    def setup_ui(self):
        """Setup user interface"""
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top frame - Task info
        top_frame = ttk.LabelFrame(main_frame, text="Thông tin Task", padding="10")
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Task selector
        ttk.Label(top_frame, text="Chọn Task:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.task_selector_var = tk.StringVar()
        tasks = list(self.game_config.get("tasks", {}).keys())
        task_selector = ttk.Combobox(top_frame, textvariable=self.task_selector_var, values=tasks, width=25, state="readonly")
        task_selector.grid(row=0, column=1, padx=5, pady=5)
        task_selector.bind("<<ComboboxSelected>>", self.on_task_selected)
        
        ttk.Label(top_frame, text="Tên Task:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.task_name_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.task_name_var, width=30).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(top_frame, text="Mô tả:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.task_desc_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.task_desc_var, width=40).grid(row=1, column=3, padx=5, pady=5)
        
        # Middle frame - Steps list
        steps_frame = ttk.LabelFrame(main_frame, text="Danh sách Steps", padding="10")
        steps_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Steps listbox with scrollbar
        list_frame = ttk.Frame(steps_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.steps_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=7)
        self.steps_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.steps_listbox.bind("<<ListboxSelect>>", self.on_step_selected)
        scrollbar.config(command=self.steps_listbox.yview)
        
        # Step buttons
        step_buttons_frame = ttk.Frame(steps_frame)
        step_buttons_frame.pack(fill=tk.X, pady=5)
        
        # Always show both buttons
        self.add_button = ttk.Button(step_buttons_frame, text="➕ Thêm Step", command=self.add_step)
        self.add_button.pack(side=tk.LEFT, padx=2)
        
        self.update_button = ttk.Button(step_buttons_frame, text="💾 Cập nhật Step", command=self.update_step, state=tk.DISABLED)
        self.update_button.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(step_buttons_frame, text="⬆️ Lên", command=self.move_step_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(step_buttons_frame, text="⬇️ Xuống", command=self.move_step_down).pack(side=tk.LEFT, padx=2)
        ttk.Button(step_buttons_frame, text="🗑️ Xóa", command=self.delete_step).pack(side=tk.LEFT, padx=2)
        
        # Bottom frame - Step editor
        editor_frame = ttk.LabelFrame(main_frame, text="Chỉnh sửa Step", padding="10")
        editor_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Step type
        ttk.Label(editor_frame, text="Loại Step:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.step_type_var = tk.StringVar(value="wait")
        step_types = ["wait", "click", "swipe", "find_and_click", "wait_template", "screenshot", "notification"]
        step_type_combo = ttk.Combobox(editor_frame, textvariable=self.step_type_var, values=step_types, width=20)
        step_type_combo.grid(row=0, column=1, padx=5, pady=5)
        step_type_combo.bind("<<ComboboxSelected>>", self.on_step_type_changed)
        
        # Step name
        ttk.Label(editor_frame, text="Tên:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.step_name_var = tk.StringVar()
        ttk.Entry(editor_frame, textvariable=self.step_name_var, width=30).grid(row=0, column=3, padx=5, pady=5)
        
        # Parameters frame (will be populated based on step type)
        self.params_frame = ttk.Frame(editor_frame)
        self.params_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=10)
        
        # Action buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X)
        
        ttk.Button(action_frame, text="💾 Lưu Task", command=self.save_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="❌ Đóng", command=self.window.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Initialize step type UI
        self.on_step_type_changed()
    
    def load_tasks(self):
        """Load existing tasks"""
        tasks = self.game_config.get("tasks", {})
        # Populate task selector if needed
    
    def on_step_type_changed(self, event=None):
        """Handle step type change"""
        # Initialize templates list when switching to find_and_click
        if not hasattr(self, 'templates_list'):
            self.templates_list = []
        
        # Clear params frame
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        
        step_type = self.step_type_var.get()
        row = 0
        
        if step_type == "wait":
            ttk.Label(self.params_frame, text="Thời gian (giây):").grid(row=row, column=0, sticky=tk.W, padx=5)
            self.duration_var = tk.StringVar(value="1.0")
            ttk.Entry(self.params_frame, textvariable=self.duration_var, width=15).grid(row=row, column=1, padx=5)
        
        elif step_type == "click":
            ttk.Label(self.params_frame, text="X:").grid(row=row, column=0, sticky=tk.W, padx=5)
            self.x_var = tk.StringVar()
            ttk.Entry(self.params_frame, textvariable=self.x_var, width=15).grid(row=row, column=1, padx=5)
            
            ttk.Label(self.params_frame, text="Y:").grid(row=row, column=2, sticky=tk.W, padx=5)
            self.y_var = tk.StringVar()
            ttk.Entry(self.params_frame, textvariable=self.y_var, width=15).grid(row=row, column=3, padx=5)
            
            ttk.Button(self.params_frame, text="🖱️ Lấy tọa độ", command=self.pick_coordinates).grid(row=row, column=4, padx=5)
            
            ttk.Label(self.params_frame, text="Delay (giây):").grid(row=row+1, column=0, sticky=tk.W, padx=5)
            self.delay_var = tk.StringVar(value="0.5")
            ttk.Entry(self.params_frame, textvariable=self.delay_var, width=15).grid(row=row+1, column=1, padx=5)
        
        elif step_type == "swipe":
            ttk.Label(self.params_frame, text="X1:").grid(row=row, column=0, sticky=tk.W, padx=5)
            self.x1_var = tk.StringVar()
            ttk.Entry(self.params_frame, textvariable=self.x1_var, width=15).grid(row=row, column=1, padx=5)
            
            ttk.Label(self.params_frame, text="Y1:").grid(row=row, column=2, sticky=tk.W, padx=5)
            self.y1_var = tk.StringVar()
            ttk.Entry(self.params_frame, textvariable=self.y1_var, width=15).grid(row=row, column=3, padx=5)
            
            ttk.Label(self.params_frame, text="X2:").grid(row=row+1, column=0, sticky=tk.W, padx=5)
            self.x2_var = tk.StringVar()
            ttk.Entry(self.params_frame, textvariable=self.x2_var, width=15).grid(row=row+1, column=1, padx=5)
            
            ttk.Label(self.params_frame, text="Y2:").grid(row=row+1, column=2, sticky=tk.W, padx=5)
            self.y2_var = tk.StringVar()
            ttk.Entry(self.params_frame, textvariable=self.y2_var, width=15).grid(row=row+1, column=3, padx=5)
            
            ttk.Label(self.params_frame, text="Duration (ms):").grid(row=row+2, column=0, sticky=tk.W, padx=5)
            self.duration_swipe_var = tk.StringVar(value="300")
            ttk.Entry(self.params_frame, textvariable=self.duration_swipe_var, width=15).grid(row=row+2, column=1, padx=5)
        
        elif step_type in ["find_and_click", "wait_template"]:
            # Multi-template support for find_and_click
            if step_type == "find_and_click":
                ttk.Label(self.params_frame, text="Templates (tìm theo thứ tự):").grid(row=row, column=0, sticky=tk.NW, padx=5, pady=5)
                
                # Frame for template list
                template_list_frame = ttk.Frame(self.params_frame)
                template_list_frame.grid(row=row, column=1, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
                
                # Listbox for templates
                listbox_frame = ttk.Frame(template_list_frame)
                listbox_frame.pack(fill=tk.BOTH, expand=True)
                
                scrollbar = ttk.Scrollbar(listbox_frame)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                self.templates_listbox = tk.Listbox(listbox_frame, height=4, yscrollcommand=scrollbar.set)
                self.templates_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.config(command=self.templates_listbox.yview)
                
                # Buttons for template management
                template_buttons_frame = ttk.Frame(template_list_frame)
                template_buttons_frame.pack(fill=tk.X, pady=2)
                
                ttk.Button(template_buttons_frame, text="➕ Thêm", command=self.add_template_to_list).pack(side=tk.LEFT, padx=2)
                ttk.Button(template_buttons_frame, text="➖ Xóa", command=self.remove_template_from_list).pack(side=tk.LEFT, padx=2)
                ttk.Button(template_buttons_frame, text="⬆ Lên", command=self.move_template_up).pack(side=tk.LEFT, padx=2)
                ttk.Button(template_buttons_frame, text="⬇ Xuống", command=self.move_template_down).pack(side=tk.LEFT, padx=2)
                
                # Store templates list
                self.templates_list = []
                row += 1
            else:
                # wait_template: keep single template
                ttk.Label(self.params_frame, text="Template:").grid(row=row, column=0, sticky=tk.W, padx=5)
                self.template_var = tk.StringVar()
                template_entry = ttk.Entry(self.params_frame, textvariable=self.template_var, width=30)
                template_entry.grid(row=row, column=1, padx=5)
                
                button_frame_template = ttk.Frame(self.params_frame)
                button_frame_template.grid(row=row, column=2, padx=5)
                ttk.Button(button_frame_template, text="📁 Chọn file", command=self.browse_template).pack(side=tk.LEFT, padx=2)
                ttk.Button(button_frame_template, text="📸 Chụp màn hình", command=self.capture_template).pack(side=tk.LEFT, padx=2)
            
            ttk.Label(self.params_frame, text="Timeout (giây):").grid(row=row+1, column=0, sticky=tk.W, padx=5)
            self.timeout_var = tk.StringVar(value="10")
            ttk.Entry(self.params_frame, textvariable=self.timeout_var, width=15).grid(row=row+1, column=1, padx=5)
            
            ttk.Label(self.params_frame, text="Threshold:").grid(row=row+1, column=2, sticky=tk.W, padx=5)
            self.threshold_var = tk.StringVar(value="0.8")
            ttk.Entry(self.params_frame, textvariable=self.threshold_var, width=15).grid(row=row+1, column=3, padx=5)
            
            if step_type == "find_and_click":
                ttk.Label(self.params_frame, text="Delay (giây):").grid(row=row+2, column=0, sticky=tk.W, padx=5)
                self.delay_template_var = tk.StringVar(value="0.5")
                ttk.Entry(self.params_frame, textvariable=self.delay_template_var, width=15).grid(row=row+2, column=1, padx=5)
                
                # Click all option
                self.click_all_var = tk.BooleanVar(value=False)
                ttk.Checkbutton(
                    self.params_frame, 
                    text="Click tất cả các hình tìm thấy", 
                    variable=self.click_all_var
                ).grid(row=row+2, column=2, columnspan=2, sticky=tk.W, padx=5)
                
                # Continue if not found option
                self.continue_if_not_found_var = tk.BooleanVar(value=False)
                ttk.Checkbutton(
                    self.params_frame,
                    text="Tiếp tục step tiếp theo nếu không tìm thấy",
                    variable=self.continue_if_not_found_var
                ).grid(row=row+3, column=0, columnspan=2, sticky=tk.W, padx=5)
                
                # Conditional branching: goto step if found/not found
                ttk.Label(self.params_frame, text="Nếu tìm thấy, nhảy đến step:").grid(row=row+4, column=0, sticky=tk.W, padx=5)
                self.goto_step_if_found_var = tk.StringVar()
                ttk.Entry(self.params_frame, textvariable=self.goto_step_if_found_var, width=10).grid(row=row+4, column=1, padx=5, sticky=tk.W)
                ttk.Label(self.params_frame, text="(để trống = tiếp tục bình thường)").grid(row=row+4, column=2, sticky=tk.W, padx=5)
                
                ttk.Label(self.params_frame, text="Nếu không tìm thấy, nhảy đến step:").grid(row=row+5, column=0, sticky=tk.W, padx=5)
                self.goto_step_if_not_found_var = tk.StringVar()
                ttk.Entry(self.params_frame, textvariable=self.goto_step_if_not_found_var, width=10).grid(row=row+5, column=1, padx=5, sticky=tk.W)
                ttk.Label(self.params_frame, text="(để trống = dùng option trên)").grid(row=row+5, column=2, sticky=tk.W, padx=5)
        
        elif step_type == "screenshot":
            ttk.Label(self.params_frame, text="Đường dẫn lưu:").grid(row=row, column=0, sticky=tk.W, padx=5)
            # Default path: screenshots/game_name/task_name/
            default_path = f"screenshots/{self.game_name}/<task_name>/screenshot.png"
            self.save_path_var = tk.StringVar(value=default_path)
            ttk.Entry(self.params_frame, textvariable=self.save_path_var, width=40).grid(row=row, column=1, columnspan=2, padx=5)
            ttk.Label(
                self.params_frame,
                text="(Để trống sẽ tự động: screenshots/<game>/<task>/screenshot_<timestamp>.png)",
                font=("Arial", 8),
                foreground="gray"
            ).grid(row=row+1, column=0, columnspan=4, sticky=tk.W, padx=5)
        
        elif step_type == "notification":
            ttk.Label(self.params_frame, text="Nội dung thông báo:").grid(row=row, column=0, sticky=tk.NW, padx=5, pady=5)
            # Use ScrolledText for multi-line input
            self.notification_text = scrolledtext.ScrolledText(self.params_frame, width=50, height=6, wrap=tk.WORD)
            self.notification_text.grid(row=row, column=1, columnspan=3, padx=5, pady=5, sticky=(tk.W, tk.E))
            ttk.Label(
                self.params_frame,
                text="(Thông báo này sẽ hiển thị khi chạy đến step này, người dùng có thể chọn Tiếp tục hoặc Dừng lại)",
                font=("Arial", 8),
                foreground="gray"
            ).grid(row=row+1, column=0, columnspan=4, sticky=tk.W, padx=5)
    
    def browse_template(self):
        """Browse for template image"""
        filename = filedialog.askopenfilename(
            title="Chọn template image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")]
        )
        if filename:
            # Copy to templates directory if not already there
            sanitized_game_name = sanitize_filename(self.game_name)
            template_dir = Path("config/templates") / sanitized_game_name
            template_dir.mkdir(parents=True, exist_ok=True)
            template_name = Path(filename).name
            template_path = template_dir / template_name
            
            # Copy file if not already in templates directory
            if Path(filename) != template_path:
                from shutil import copy2
                copy2(filename, template_path)
            
            # If find_and_click with multi-template support, add to list
            if hasattr(self, 'templates_listbox'):
                # Ensure templates_list exists
                if not hasattr(self, 'templates_list'):
                    self.templates_list = []
                self.templates_list.append(template_name)
                self.update_templates_listbox()
                self.templates_listbox.selection_clear(0, tk.END)
                self.templates_listbox.selection_set(len(self.templates_list) - 1)
                self.templates_listbox.see(len(self.templates_list) - 1)
            elif hasattr(self, 'template_var'):
                self.template_var.set(template_name)
    
    def add_template_to_list(self):
        """Add template to list (via browse or capture)"""
        # Show dialog to choose: browse file or capture screenshot
        dialog = tk.Toplevel(self.window)
        dialog.title("Thêm Template")
        dialog.transient(self.window)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Chọn cách thêm template:").pack(pady=10)
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def browse_and_add():
            dialog.destroy()
            self.browse_template()
        
        def capture_and_add():
            dialog.destroy()
            self.capture_template()
        
        ttk.Button(button_frame, text="📁 Chọn file", command=browse_and_add).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📸 Chụp màn hình", command=capture_and_add).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Hủy", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def remove_template_from_list(self):
        """Remove selected template from list"""
        if not hasattr(self, 'templates_listbox'):
            return
        
        selection = self.templates_listbox.curselection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn template để xóa!")
            return
        
        index = selection[0]
        if 0 <= index < len(self.templates_list):
            removed = self.templates_list.pop(index)
            self.update_templates_listbox()
            messagebox.showinfo("Thành công", f"Đã xóa template: {removed}")
    
    def move_template_up(self):
        """Move selected template up in list"""
        if not hasattr(self, 'templates_listbox'):
            return
        
        selection = self.templates_listbox.curselection()
        if not selection or selection[0] == 0:
            return
        
        index = selection[0]
        if 0 < index < len(self.templates_list):
            self.templates_list[index], self.templates_list[index - 1] = self.templates_list[index - 1], self.templates_list[index]
            self.update_templates_listbox()
            self.templates_listbox.selection_set(index - 1)
            self.templates_listbox.see(index - 1)
    
    def move_template_down(self):
        """Move selected template down in list"""
        if not hasattr(self, 'templates_listbox'):
            return
        
        selection = self.templates_listbox.curselection()
        if not selection or selection[0] >= len(self.templates_list) - 1:
            return
        
        index = selection[0]
        if 0 <= index < len(self.templates_list) - 1:
            self.templates_list[index], self.templates_list[index + 1] = self.templates_list[index + 1], self.templates_list[index]
            self.update_templates_listbox()
            self.templates_listbox.selection_set(index + 1)
            self.templates_listbox.see(index + 1)
    
    def update_templates_listbox(self):
        """Update templates listbox display"""
        if not hasattr(self, 'templates_listbox'):
            return
        
        self.templates_listbox.delete(0, tk.END)
        for i, template in enumerate(self.templates_list):
            self.templates_listbox.insert(tk.END, f"{i+1}. {template}")
    
    def capture_template(self):
        """Capture template from emulator screen"""
        try:
            # Import emulator controller
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
            from emulator.controller import EmulatorController
            
            # Get ADB path
            adb_path = self.main_window.find_adb()
            if not adb_path:
                messagebox.showerror("Lỗi", "Không tìm thấy ADB. Vui lòng kiểm tra kết nối emulator.")
                return
            
            # Always refresh devices list first
            all_devices = EmulatorController.list_all_devices(adb_path)
            
            # Get selected device from main window
            selected_device = self.main_window.selected_device_var.get()
            emulator_type = self.main_window.emulator_type_var.get()
            
            # Create emulator instance
            emulator = EmulatorController(emulator_type=emulator_type, adb_path=adb_path)
            
            # Priority: Use selected device if available
            if selected_device and selected_device.strip() and selected_device in all_devices:
                # Connect to selected device
                if not emulator.connect_to_device(selected_device):
                    messagebox.showerror("Lỗi", f"Không thể kết nối đến giả lập đã chọn: {selected_device}\nVui lòng chọn lại giả lập hoặc kiểm tra kết nối.")
                    return
            else:
                # No device selected or selected device not available, try to connect automatically
                if not all_devices:
                    # Try to connect using emulator type
                    if not emulator.connect():
                        # Try auto if emulator type fails
                        emulator = EmulatorController(emulator_type="auto", adb_path=adb_path)
                        if not emulator.connect():
                            messagebox.showerror("Lỗi", "Không thể kết nối đến emulator.\nVui lòng chọn giả lập từ dropdown hoặc kiểm tra kết nối.")
                            return
                elif len(all_devices) == 1:
                    # Only one device, connect directly
                    device_id = all_devices[0]
                    if not emulator.connect_to_device(device_id):
                        messagebox.showerror("Lỗi", "Không thể kết nối đến emulator.")
                        return
                    # Update selected device in main window
                    self.main_window.root.after(0, lambda: self.main_window.selected_device_var.set(device_id))
                else:
                    # Multiple devices - use first one but warn user
                    device_id = all_devices[0]
                    if not emulator.connect_to_device(device_id):
                        messagebox.showerror("Lỗi", "Không thể kết nối đến emulator.")
                        return
                    # Update selected device in main window
                    self.main_window.root.after(0, lambda: self.main_window.selected_device_var.set(device_id))
            
            # Final verification: ensure emulator is connected with correct device_id
            if not emulator.connected or not emulator.device_id:
                messagebox.showerror("Lỗi", "Emulator không được kết nối đúng cách.")
                return
            
            # Take screenshot
            screenshot = emulator.screenshot()
            if not screenshot:
                messagebox.showerror("Lỗi", f"Không thể chụp màn hình emulator.\nDevice ID: {emulator.device_id}, Connected: {emulator.connected}")
                return
            
            # Create template picker window
            self._show_template_picker(screenshot, emulator)
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi chụp template: {e}")
            import traceback
            print(traceback.format_exc())
    
    def _show_template_picker(self, screenshot, emulator):
        """Show screenshot and allow user to select region for template"""
        picker_window = tk.Toplevel(self.window)
        picker_window.title("Chọn vùng template - Kéo thả để chọn vùng")
        
        # Get screen size for scaling
        screen_size = emulator.get_screen_size()
        if not screen_size:
            screen_size = (1080, 1920)  # Default
        
        # Get screen resolution to fit window (full image display)
        screen_width = picker_window.winfo_screenwidth()
        screen_height = picker_window.winfo_screenheight()
        
        # Maximize window to full screen
        picker_window.state('zoomed')  # Windows
        try:
            picker_window.attributes('-zoomed', True)  # Alternative for some systems
        except:
            pass
        
        # Wait for window to be displayed to get actual size
        picker_window.update_idletasks()
        actual_width = picker_window.winfo_width()
        actual_height = picker_window.winfo_height()
        
        # Calculate initial scale to fit window (leave margin for buttons and labels)
        max_display_width = actual_width - 50
        max_display_height = actual_height - 250  # More space for buttons and zoom controls
        
        scale_x = max_display_width / screenshot.width
        scale_y = max_display_height / screenshot.height
        initial_scale = min(scale_x, scale_y, 1.0)  # Don't scale up, only down if needed
        
        # Zoom variables
        zoom_factor = 1.0  # Current zoom (1.0 = initial scale)
        min_zoom = 0.5
        max_zoom = 5.0
        pan_x = 0  # Pan offset
        pan_y = 0
        
        # Store original screenshot
        original_screenshot = screenshot
        
        # Use grid layout for better control
        picker_window.columnconfigure(0, weight=1)
        picker_window.rowconfigure(1, weight=1)
        
        # Top frame with controls
        top_frame = ttk.Frame(picker_window)
        top_frame.grid(row=0, column=0, pady=5, sticky=(tk.W, tk.E))
        
        # Coordinate display
        coord_label = ttk.Label(top_frame, text="Kéo thả để chọn vùng template", font=("Arial", 12))
        coord_label.pack(side=tk.LEFT, padx=10)
        
        # Zoom controls
        zoom_frame = ttk.Frame(top_frame)
        zoom_frame.pack(side=tk.RIGHT, padx=10)
        
        ttk.Label(zoom_frame, text="Zoom:", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_frame, text="➖", command=lambda: zoom_image(-0.2), width=3).pack(side=tk.LEFT, padx=2)
        zoom_label = ttk.Label(zoom_frame, text="100%", font=("Arial", 10), width=6)
        zoom_label.pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_frame, text="➕", command=lambda: zoom_image(0.2), width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_frame, text="Reset", command=lambda: reset_zoom(), width=6).pack(side=tk.LEFT, padx=2)
        
        # Canvas frame (middle, expandable) - centered
        canvas_frame = ttk.Frame(picker_window)
        canvas_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=5)
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)
        
        # Create canvas with scrollbars
        canvas = tk.Canvas(canvas_frame, cursor="cross", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Store original image dimensions
        canvas.original_width = screenshot.width
        canvas.original_height = screenshot.height
        
        def update_image():
            """Update displayed image with current zoom and pan"""
            nonlocal pan_x, pan_y
            
            # Calculate current scale
            current_scale = initial_scale * zoom_factor
            
            # Calculate new dimensions
            new_width = int(screenshot.width * current_scale)
            new_height = int(screenshot.height * current_scale)
            
            # Resize image
            resized_screenshot = screenshot.resize((new_width, new_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(resized_screenshot)
            
            # Clear canvas
            canvas.delete("all")
            
            # Get canvas dimensions
            canvas.update_idletasks()
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            
            if canvas_width > 0 and canvas_height > 0:
                # Calculate image position (centered + pan)
                img_x = canvas_width // 2 + pan_x
                img_y = canvas_height // 2 + pan_y
                
                # Draw image
                canvas.create_image(img_x, img_y, anchor=tk.CENTER, image=photo)
                canvas.image = photo  # Keep a reference
                
                # Store current dimensions and scale for coordinate calculation
                canvas.image_width = new_width
                canvas.image_height = new_height
                canvas.scale_factor = current_scale
                canvas.image_x = img_x
                canvas.image_y = img_y
                
                # Update zoom label
                zoom_label.config(text=f"{int(zoom_factor * 100)}%")
        
        def zoom_image(delta):
            """Zoom in/out"""
            nonlocal zoom_factor, pan_x, pan_y
            
            old_zoom = zoom_factor
            zoom_factor = max(min_zoom, min(max_zoom, zoom_factor + delta))
            
            # Adjust pan to zoom towards center
            if zoom_factor != old_zoom:
                # Get mouse position relative to canvas center
                canvas.update_idletasks()
                canvas_width = canvas.winfo_width()
                canvas_height = canvas.winfo_height()
                
                # Zoom towards center
                zoom_ratio = zoom_factor / old_zoom
                pan_x = pan_x * zoom_ratio
                pan_y = pan_y * zoom_ratio
                
                update_image()
        
        def reset_zoom():
            """Reset zoom and pan"""
            nonlocal zoom_factor, pan_x, pan_y
            zoom_factor = 1.0
            pan_x = 0
            pan_y = 0
            update_image()
        
        # Mouse wheel zoom
        def on_mousewheel(event):
            """Handle mouse wheel zoom"""
            if event.delta > 0:
                zoom_image(0.1)
            else:
                zoom_image(-0.1)
        
        # Pan with Ctrl+drag
        pan_start_x = None
        pan_start_y = None
        is_panning = False
        
        def on_pan_start(event):
            """Start panning (only if Ctrl is pressed)"""
            nonlocal pan_start_x, pan_start_y, is_panning
            if event.state & 0x4:  # Ctrl key pressed
                is_panning = True
                pan_start_x = event.x
                pan_start_y = event.y
        
        def on_pan_move(event):
            """Pan image"""
            nonlocal pan_x, pan_y
            if is_panning and pan_start_x is not None and pan_start_y is not None:
                if event.state & 0x4:  # Ctrl key still pressed
                    dx = event.x - pan_start_x
                    dy = event.y - pan_start_y
                    pan_x += dx
                    pan_y += dy
                    pan_start_x = event.x
                    pan_start_y = event.y
                    update_image()
        
        def on_pan_end(event):
            """End panning"""
            nonlocal pan_start_x, pan_start_y, is_panning
            pan_start_x = None
            pan_start_y = None
            is_panning = False
        
        # Bind mouse wheel (Windows)
        canvas.bind("<MouseWheel>", on_mousewheel)
        # Bind mouse wheel (Linux)
        canvas.bind("<Button-4>", lambda e: zoom_image(0.1))
        canvas.bind("<Button-5>", lambda e: zoom_image(-0.1))
        
        # Bind pan (Ctrl+drag) - must be before selection bindings
        canvas.bind("<Button-1>", on_pan_start)
        canvas.bind("<B1-Motion>", on_pan_move)
        canvas.bind("<ButtonRelease-1>", on_pan_end)
        
        # Initial image display
        picker_window.after(100, update_image)
        
        # Selection variables
        start_x = None
        start_y = None
        rect_id = None
        selected_region = None
        is_selecting = False
        
        def on_select_press(event):
            """Start selection (only if not panning)"""
            nonlocal start_x, start_y, rect_id, is_selecting
            # Only start selection if Ctrl is not pressed (Ctrl is for panning)
            if not (event.state & 0x4):  # Ctrl key not pressed
                is_selecting = True
                start_x = event.x
                start_y = event.y
                # Delete previous rectangle
                if rect_id:
                    canvas.delete(rect_id)
        
        def on_select_move(event):
            """Update selection rectangle"""
            nonlocal rect_id
            if is_selecting and start_x is not None and start_y is not None:
                # Delete previous rectangle
                if rect_id:
                    canvas.delete(rect_id)
                # Draw new rectangle
                rect_id = canvas.create_rectangle(
                    start_x, start_y, event.x, event.y,
                    outline="red", width=2
                )
        
        def on_select_release(event):
            """Finish selection and calculate region"""
            nonlocal selected_region, start_x, start_y, is_selecting
            if is_selecting and start_x is not None and start_y is not None:
                # Get image position (stored during update_image)
                img_x = getattr(canvas, 'image_x', canvas.winfo_width() // 2)
                img_y = getattr(canvas, 'image_y', canvas.winfo_height() // 2)
                
                # Calculate offset from image center
                offset_x = event.x - img_x
                offset_y = event.y - img_y
                start_offset_x = start_x - img_x
                start_offset_y = start_y - img_y
                
                # Convert to image coordinates (relative to image center)
                img_x1 = start_offset_x
                img_y1 = start_offset_y
                img_x2 = offset_x
                img_y2 = offset_y
                
                # Convert to image top-left coordinates
                img_x1 += canvas.image_width // 2
                img_y1 += canvas.image_height // 2
                img_x2 += canvas.image_width // 2
                img_y2 += canvas.image_height // 2
                
                # Only process if coordinates are within image bounds
                if (0 <= img_x1 <= canvas.image_width and 0 <= img_y1 <= canvas.image_height and
                    0 <= img_x2 <= canvas.image_width and 0 <= img_y2 <= canvas.image_height):
                    
                    # Calculate actual coordinates on original screenshot
                    x1 = int(min(img_x1, img_x2) / canvas.scale_factor)
                    y1 = int(min(img_y1, img_y2) / canvas.scale_factor)
                    x2 = int(max(img_x1, img_x2) / canvas.scale_factor)
                    y2 = int(max(img_y1, img_y2) / canvas.scale_factor)
                    
                    # Clamp to screen size
                    x1 = max(0, min(x1, screen_size[0] - 1))
                    y1 = max(0, min(y1, screen_size[1] - 1))
                    x2 = max(0, min(x2, screen_size[0] - 1))
                    y2 = max(0, min(y2, screen_size[1] - 1))
                    
                    # Ensure valid region
                    if x2 > x1 and y2 > y1:
                        selected_region = (x1, y1, x2 - x1, y2 - y1)
                        coord_label.config(text=f"Vùng đã chọn: ({x1}, {y1}) - ({x2}, {y2})")
            
            is_selecting = False
        
        # Bind selection events (after pan bindings, so pan takes priority)
        canvas.bind("<Button-1>", on_select_press, add="+")
        canvas.bind("<B1-Motion>", on_select_move, add="+")
        canvas.bind("<ButtonRelease-1>", on_select_release, add="+")
        
        def confirm():
            if selected_region:
                # Crop template from original screenshot
                x, y, w, h = selected_region
                template_image = screenshot.crop((x, y, x + w, y + h))
                
                # Generate template name
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                template_name = f"template_{timestamp}.png"
                
                # Save template - use sanitized game name (no accents)
                sanitized_game_name = sanitize_filename(self.game_name)
                template_dir = Path("config/templates") / sanitized_game_name
                template_dir.mkdir(parents=True, exist_ok=True)
                template_path = template_dir / template_name
                
                template_image.save(template_path)
                
                # Set template name (relative to templates directory)
                # If find_and_click with multi-template support, add to list
                if hasattr(self, 'templates_listbox'):
                    # Ensure templates_list exists
                    if not hasattr(self, 'templates_list'):
                        self.templates_list = []
                    self.templates_list.append(template_name)
                    self.update_templates_listbox()
                    self.templates_listbox.selection_clear(0, tk.END)
                    self.templates_listbox.selection_set(len(self.templates_list) - 1)
                    self.templates_listbox.see(len(self.templates_list) - 1)
                elif hasattr(self, 'template_var'):
                    self.template_var.set(template_name)
                
                picker_window.destroy()
                messagebox.showinfo("Thành công", f"Đã lưu template: {template_name}")
            else:
                messagebox.showwarning("Cảnh báo", "Vui lòng chọn vùng trên màn hình!")
        
        def cancel():
            picker_window.destroy()
        
        # Buttons frame (bottom)
        button_frame = ttk.Frame(picker_window)
        button_frame.grid(row=2, column=0, pady=10)
        
        ttk.Button(button_frame, text="✓ Xác nhận", command=confirm).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Hủy", command=cancel).pack(side=tk.LEFT, padx=5)
        
        # Instructions (bottom)
        instructions = ttk.Label(
            picker_window,
            text="Hướng dẫn: Kéo thả chuột để chọn vùng | Scroll để zoom | Ctrl+Kéo để di chuyển | Nút Reset để về mặc định",
            font=("Arial", 9),
            foreground="gray"
        )
        instructions.grid(row=3, column=0, pady=5)
    
    def add_step(self):
        """Add new step"""
        try:
            step = self.get_step_from_ui()
            if step:
                self.steps.append(step)
                self.update_steps_list()
                
                # Auto-select the newly added step for editing
                new_step_index = len(self.steps) - 1
                self.steps_listbox.selection_clear(0, tk.END)
                self.steps_listbox.selection_set(new_step_index)
                self.steps_listbox.see(new_step_index)
                
                # Load the step into UI for editing
                self.current_step_index = new_step_index
                self.load_step_to_ui(step)
                
                # Enable update button for editing
                self.add_button.config(state=tk.NORMAL)
                self.update_button.config(state=tk.NORMAL)
        except ValueError as e:
            messagebox.showerror("Lỗi", str(e))
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi thêm step: {e}")
    
    
    def update_step(self):
        """Update current step"""
        if self.current_step_index is None:
            messagebox.showwarning("Cảnh báo", "Không có step nào đang được chỉnh sửa!")
            return
        
        try:
            step = self.get_step_from_ui()
            if step:
                self.steps[self.current_step_index] = step
                self.update_steps_list()
                
                # Keep selection on updated step
                self.steps_listbox.selection_clear(0, tk.END)
                self.steps_listbox.selection_set(self.current_step_index)
                self.steps_listbox.see(self.current_step_index)
                
                # Clear edit mode
                self.current_step_index = None
                self.clear_step_ui()
                
                # Update button states
                self.add_button.config(state=tk.NORMAL)
                self.update_button.config(state=tk.DISABLED)
                
                messagebox.showinfo("Thành công", "Đã cập nhật step!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi cập nhật step: {e}")
            import traceback
            print(traceback.format_exc())
    
    def delete_step(self):
        """Delete selected step"""
        selection = self.steps_listbox.curselection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn step để xóa!")
            return
        
        if messagebox.askyesno("Xác nhận", "Bạn có chắc muốn xóa step này?"):
            index = selection[0]
            del self.steps[index]
            self.update_steps_list()
    
    def move_step_up(self):
        """Move step up"""
        selection = self.steps_listbox.curselection()
        if not selection or selection[0] == 0:
            return
        
        index = selection[0]
        self.steps[index], self.steps[index-1] = self.steps[index-1], self.steps[index]
        self.update_steps_list()
        self.steps_listbox.selection_set(index-1)
    
    def move_step_down(self):
        """Move step down"""
        selection = self.steps_listbox.curselection()
        if not selection or selection[0] == len(self.steps) - 1:
            return
        
        index = selection[0]
        self.steps[index], self.steps[index+1] = self.steps[index+1], self.steps[index]
        self.update_steps_list()
        self.steps_listbox.selection_set(index+1)
    
    def get_step_from_ui(self) -> Dict[str, Any]:
        """Get step data from UI"""
        step_type = self.step_type_var.get()
        step_name = self.step_name_var.get() or f"Step {len(self.steps) + 1}"
        
        step = {
            "type": step_type,
            "name": step_name
        }
        
        try:
            if step_type == "wait":
                step["duration"] = float(self.duration_var.get() or "1.0")
            
            elif step_type == "click":
                step["x"] = int(self.x_var.get() or "0")
                step["y"] = int(self.y_var.get() or "0")
                step["delay"] = float(self.delay_var.get() or "0.5")
            
            elif step_type == "swipe":
                step["x1"] = int(self.x1_var.get() or "0")
                step["y1"] = int(self.y1_var.get() or "0")
                step["x2"] = int(self.x2_var.get() or "0")
                step["y2"] = int(self.y2_var.get() or "0")
                step["duration"] = int(self.duration_swipe_var.get() or "300")
            
            elif step_type in ["find_and_click", "wait_template"]:
                # For find_and_click, support multiple templates
                if step_type == "find_and_click" and hasattr(self, 'templates_list') and self.templates_list:
                    step["templates"] = self.templates_list.copy()  # Save as list
                    # Also keep single template for backward compatibility
                    if self.templates_list:
                        step["template"] = self.templates_list[0]
                else:
                    # Single template (for wait_template or backward compatibility)
                    template_value = self.template_var.get() or ""
                    step["template"] = template_value
                    if template_value:
                        step["templates"] = [template_value]  # Convert to list for consistency
                
                step["timeout"] = int(self.timeout_var.get() or "10")
                step["threshold"] = float(self.threshold_var.get() or "0.8")
                if step_type == "find_and_click":
                    step["delay"] = float(self.delay_template_var.get() or "0.5")
                    step["click_all"] = self.click_all_var.get() if hasattr(self, 'click_all_var') else False
                    step["continue_if_not_found"] = self.continue_if_not_found_var.get() if hasattr(self, 'continue_if_not_found_var') else False
                    
                    # Conditional branching
                    if hasattr(self, 'goto_step_if_found_var'):
                        goto_found = self.goto_step_if_found_var.get().strip()
                        if goto_found:
                            try:
                                step["goto_step_if_found"] = int(goto_found)
                            except ValueError:
                                raise ValueError(f"Step index không hợp lệ: {goto_found}")
                    
                    if hasattr(self, 'goto_step_if_not_found_var'):
                        goto_not_found = self.goto_step_if_not_found_var.get().strip()
                        if goto_not_found:
                            try:
                                step["goto_step_if_not_found"] = int(goto_not_found)
                            except ValueError:
                                raise ValueError(f"Step index không hợp lệ: {goto_not_found}")
            
            elif step_type == "screenshot":
                step["save_path"] = self.save_path_var.get() or ""
            
            elif step_type == "notification":
                if hasattr(self, 'notification_text'):
                    step["message"] = self.notification_text.get("1.0", tk.END).strip()
                else:
                    step["message"] = ""
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Lỗi nhập liệu: {e}. Vui lòng kiểm tra lại các giá trị.")
        
        return step
    
    def load_step_to_ui(self, step: Dict[str, Any]):
        """Load step data to UI"""
        self.step_type_var.set(step.get("type", "wait"))
        self.step_name_var.set(step.get("name", ""))
        self.on_step_type_changed()
        
        step_type = step.get("type")
        if step_type == "wait":
            self.duration_var.set(str(step.get("duration", 1.0)))
        elif step_type == "click":
            self.x_var.set(str(step.get("x", 0)))
            self.y_var.set(str(step.get("y", 0)))
            self.delay_var.set(str(step.get("delay", 0.5)))
        elif step_type == "swipe":
            self.x1_var.set(str(step.get("x1", 0)))
            self.y1_var.set(str(step.get("y1", 0)))
            self.x2_var.set(str(step.get("x2", 0)))
            self.y2_var.set(str(step.get("y2", 0)))
            self.duration_swipe_var.set(str(step.get("duration", 300)))
        elif step_type in ["find_and_click", "wait_template"]:
            # Load templates: support both list and single template
            if step_type == "find_and_click" and hasattr(self, 'templates_listbox'):
                templates = step.get("templates", [])
                if not templates and step.get("template"):
                    # Backward compatibility: convert single template to list
                    templates = [step.get("template")]
                self.templates_list = templates.copy() if templates else []
                self.update_templates_listbox()
            else:
                # Single template for wait_template
                template_value = step.get("template", "")
                if not template_value and step.get("templates"):
                    # If templates list exists but no single template, use first one
                    template_value = step.get("templates", [""])[0]
                self.template_var.set(template_value)
            
            self.timeout_var.set(str(step.get("timeout", 10)))
            self.threshold_var.set(str(step.get("threshold", 0.8)))
            if step_type == "find_and_click":
                self.delay_template_var.set(str(step.get("delay", 0.5)))
                if hasattr(self, 'click_all_var'):
                    self.click_all_var.set(step.get("click_all", False))
                if hasattr(self, 'continue_if_not_found_var'):
                    self.continue_if_not_found_var.set(step.get("continue_if_not_found", False))
                
                # Load conditional branching
                if hasattr(self, 'goto_step_if_found_var'):
                    goto_found = step.get("goto_step_if_found")
                    self.goto_step_if_found_var.set(str(goto_found) if goto_found else "")
                if hasattr(self, 'goto_step_if_not_found_var'):
                    goto_not_found = step.get("goto_step_if_not_found")
                    self.goto_step_if_not_found_var.set(str(goto_not_found) if goto_not_found else "")
        elif step_type == "screenshot":
            self.save_path_var.set(step.get("save_path", "screenshots/screenshot.png"))
        
        elif step_type == "notification":
            if hasattr(self, 'notification_text'):
                self.notification_text.delete("1.0", tk.END)
                self.notification_text.insert("1.0", step.get("message", ""))
    
    def clear_step_ui(self):
        """Clear step UI and exit edit mode"""
        self.step_name_var.set("")
        self.current_step_index = None
        self.on_step_type_changed()
        
        # Clear selection in listbox
        self.steps_listbox.selection_clear(0, tk.END)
        
        # Reset button states to add mode
        self.add_button.config(state=tk.NORMAL)  # Keep add button enabled
        self.update_button.config(state=tk.DISABLED)  # Disable update button
    
    def update_steps_list(self):
        """Update steps listbox"""
        self.steps_listbox.delete(0, tk.END)
        for i, step in enumerate(self.steps):
            step_type = step.get("type", "unknown")
            step_name = step.get("name", f"Step {i+1}")
            self.steps_listbox.insert(tk.END, f"{i+1}. [{step_type}] {step_name}")
    
    def on_step_selected(self, event):
        """Handle step selection - automatically enter edit mode"""
        selection = self.steps_listbox.curselection()
        if selection:
            index = selection[0]
            step = self.steps[index]
            self.load_step_to_ui(step)
            self.current_step_index = index
            
            # Automatically enter edit mode - enable update button
            self.add_button.config(state=tk.NORMAL)  # Keep add button enabled
            self.update_button.config(state=tk.NORMAL)  # Enable update button
    
    def save_task(self):
        """Save task to config"""
        task_name = self.task_name_var.get()
        if not task_name:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên task!")
            return
        
        if not self.steps:
            messagebox.showerror("Lỗi", "Task phải có ít nhất 1 step!")
            return
        
        # Update game config
        if "tasks" not in self.game_config:
            self.game_config["tasks"] = {}
        
        self.game_config["tasks"][task_name] = {
            "name": self.task_name_var.get(),
            "description": self.task_desc_var.get(),
            "steps": self.steps
        }
        
        # Save config
        config_file = Path(f"config/games/{self.game_name}.yaml")
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.game_config, f, default_flow_style=False, allow_unicode=True)
        
        # Show success message
        messagebox.showinfo("Thành công", f"Đã lưu task: {task_name}")
        
        # Update main window (without showing multiple dialogs)
        self.main_window.load_games()
        self.main_window.on_game_selected()
        
        # Update task selector in this window
        self.load_tasks()
        if hasattr(self, 'task_selector_var'):
            self.task_selector_var.set(task_name)
    
    def load_task(self):
        """Load existing task"""
        tasks = self.game_config.get("tasks", {})
        if not tasks:
            messagebox.showinfo("Thông tin", "Không có task nào để load")
            return
        
        # Create selection dialog
        dialog = tk.Toplevel(self.window)
        dialog.title("Chọn Task")
        
        # Position dialog at top right
        dialog_width = 300
        dialog_height = 200
        screen_width = dialog.winfo_screenwidth()
        margin = 10
        x = screen_width - dialog_width - margin
        y = margin
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        ttk.Label(dialog, text="Chọn task để load:").pack(pady=10)
        
        task_var = tk.StringVar()
        task_combo = ttk.Combobox(dialog, textvariable=task_var, values=list(tasks.keys()), width=30)
        task_combo.pack(pady=10)
        
        def load():
            task_name = task_var.get()
            if task_name and task_name in tasks:
                task = tasks[task_name]
                self.task_name_var.set(task_name)
                self.task_desc_var.set(task.get("description", ""))
                self.steps = task.get("steps", [])
                self.update_steps_list()
                dialog.destroy()
        
        ttk.Button(dialog, text="Load", command=load).pack(pady=10)
    
    def on_task_selected(self, event=None):
        """Handle task selection from dropdown"""
        # Auto-load when task is selected
        self.load_selected_task()
    
    def load_selected_task(self):
        """Load selected task from dropdown"""
        task_name = self.task_selector_var.get()
        if not task_name:
            return
        
        self.load_task_by_name(task_name)
    
    def load_task_by_name(self, task_name: str):
        """Load task by name (can be called from outside)"""
        tasks = self.game_config.get("tasks", {})
        if task_name in tasks:
            task = tasks[task_name]
            self.task_name_var.set(task_name)
            self.task_desc_var.set(task.get("description", ""))
            self.steps = task.get("steps", [])[:]  # Copy list
            self.update_steps_list()
            self.clear_step_ui()
            self.current_step_index = None
            # Update task selector dropdown if it exists
            if hasattr(self, 'task_selector_var'):
                self.task_selector_var.set(task_name)
    
    def pick_coordinates(self):
        """Pick coordinates from emulator screen"""
        try:
            # Import emulator controller
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
            from emulator.controller import EmulatorController
            
            # Connect to emulator
            adb_path = self.main_window.find_adb()
            if not adb_path:
                messagebox.showerror("Lỗi", "Không tìm thấy ADB. Vui lòng kiểm tra kết nối emulator.")
                return
            
            emulator = EmulatorController(emulator_type="ldplayer", adb_path=adb_path)
            if not emulator.connect():
                # Try auto
                emulator = EmulatorController(emulator_type="auto", adb_path=adb_path)
                if not emulator.connect():
                    messagebox.showerror("Lỗi", "Không thể kết nối đến emulator. Vui lòng kiểm tra kết nối.")
                    return
            
            # Take screenshot
            screenshot = emulator.screenshot()
            if not screenshot:
                messagebox.showerror("Lỗi", "Không thể chụp màn hình emulator.")
                return
            
            # Create coordinate picker window
            self._show_coordinate_picker(screenshot, emulator)
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi lấy tọa độ: {e}")
            import traceback
            print(traceback.format_exc())
    
    def _show_coordinate_picker(self, screenshot, emulator):
        """Show screenshot and allow user to click to get coordinates"""
        picker_window = tk.Toplevel(self.window)
        picker_window.title("Chọn tọa độ - Click vào màn hình để lấy tọa độ")
        
        # Get screen size for scaling
        screen_size = emulator.get_screen_size()
        if not screen_size:
            screen_size = (1080, 1920)  # Default
        
        # Maximize window to full screen
        picker_window.state('zoomed')  # Windows
        try:
            picker_window.attributes('-zoomed', True)  # Alternative for some systems
        except:
            pass
        
        # Wait for window to be displayed to get actual size
        picker_window.update_idletasks()
        actual_width = picker_window.winfo_width()
        actual_height = picker_window.winfo_height()
        
        # Get screen resolution to fit window (full image display)
        screen_width = picker_window.winfo_screenwidth()
        screen_height = picker_window.winfo_screenheight()
        
        # Calculate scale to fit screen (leave margin for buttons and labels)
        max_display_width = actual_width - 50
        max_display_height = actual_height - 200  # More space for buttons
        
        scale_x = max_display_width / screenshot.width
        scale_y = max_display_height / screenshot.height
        scale = min(scale_x, scale_y, 1.0)  # Don't scale up, only down if needed
        
        new_width = int(screenshot.width * scale)
        new_height = int(screenshot.height * scale)
        
        resized_screenshot = screenshot.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to PhotoImage
        photo = ImageTk.PhotoImage(resized_screenshot)
        
        # Use grid layout for better control
        picker_window.columnconfigure(0, weight=1)
        picker_window.rowconfigure(1, weight=1)
        
        # Coordinate display (top)
        coord_label = ttk.Label(picker_window, text="Click vào màn hình để lấy tọa độ", font=("Arial", 12))
        coord_label.grid(row=0, column=0, pady=10)
        
        # Canvas frame (middle, expandable)
        canvas_frame = ttk.Frame(picker_window)
        canvas_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=5)
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)
        
        # Create canvas - make it fill the frame
        canvas = tk.Canvas(canvas_frame, cursor="cross", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Store image dimensions and scale for coordinate calculation
        canvas.image_width = new_width
        canvas.image_height = new_height
        canvas.scale_factor = scale
        
        # Function to center image after canvas is displayed
        def center_image():
            canvas.update_idletasks()
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            if canvas_width > 0 and canvas_height > 0:
                img_x = canvas_width // 2
                img_y = canvas_height // 2
                canvas.create_image(img_x, img_y, anchor=tk.CENTER, image=photo)
                canvas.image = photo  # Keep a reference
        
        # Center image after window is displayed
        picker_window.after(100, center_image)
        
        selected_coords = [None, None]
        
        def on_canvas_click(event):
            # Get canvas dimensions
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            
            # Calculate offset to center image
            offset_x = (canvas_width - canvas.image_width) // 2
            offset_y = (canvas_height - canvas.image_height) // 2
            
            # Adjust coordinates relative to image position (image is centered)
            img_x = event.x - offset_x
            img_y = event.y - offset_y
            
            # Only process if coordinates are within image bounds
            if (0 <= img_x <= canvas.image_width and 0 <= img_y <= canvas.image_height):
                # Calculate actual coordinates
                x = int(img_x / canvas.scale_factor)
                y = int(img_y / canvas.scale_factor)
                
                # Clamp to screen size
                x = max(0, min(x, screen_size[0] - 1))
                y = max(0, min(y, screen_size[1] - 1))
                
                selected_coords[0] = x
                selected_coords[1] = y
                
                coord_label.config(text=f"Tọa độ: X={x}, Y={y} (Click lại để thay đổi)")
                
                # Draw crosshair
                canvas.delete("crosshair")
                canvas.create_line(event.x - 10, event.y, event.x + 10, event.y, fill="red", width=2, tags="crosshair")
                canvas.create_line(event.x, event.y - 10, event.x, event.y + 10, fill="red", width=2, tags="crosshair")
        
        canvas.bind("<Button-1>", on_canvas_click)
        
        def confirm():
            if selected_coords[0] is not None and selected_coords[1] is not None:
                self.x_var.set(str(selected_coords[0]))
                self.y_var.set(str(selected_coords[1]))
                picker_window.destroy()
                messagebox.showinfo("Thành công", f"Đã lấy tọa độ: X={selected_coords[0]}, Y={selected_coords[1]}")
            else:
                messagebox.showwarning("Cảnh báo", "Vui lòng click vào màn hình để chọn tọa độ!")
        
        def cancel():
            picker_window.destroy()
        
        # Buttons frame (bottom)
        button_frame = ttk.Frame(picker_window)
        button_frame.grid(row=2, column=0, pady=10)
        
        ttk.Button(button_frame, text="✓ Xác nhận", command=confirm).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Hủy", command=cancel).pack(side=tk.LEFT, padx=5)
        
        # Instructions (bottom)
        instructions = ttk.Label(
            picker_window,
            text="Hướng dẫn: Click vào vị trí trên màn hình emulator để lấy tọa độ, sau đó click 'Xác nhận'",
            font=("Arial", 9),
            foreground="gray"
        )
        instructions.grid(row=3, column=0, pady=5)
    
    def pick_coordinates(self):
        """Pick coordinates from emulator screen"""
        try:
            # Import emulator controller
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
            from emulator.controller import EmulatorController
            
            # Connect to emulator
            adb_path = self.main_window.find_adb()
            if not adb_path:
                messagebox.showerror("Lỗi", "Không tìm thấy ADB. Vui lòng kiểm tra kết nối emulator.")
                return
            
            emulator = EmulatorController(emulator_type="ldplayer", adb_path=adb_path)
            if not emulator.connect():
                # Try auto
                emulator = EmulatorController(emulator_type="auto", adb_path=adb_path)
                if not emulator.connect():
                    messagebox.showerror("Lỗi", "Không thể kết nối đến emulator. Vui lòng kiểm tra kết nối.")
                    return
            
            # Take screenshot
            screenshot = emulator.screenshot()
            if not screenshot:
                messagebox.showerror("Lỗi", "Không thể chụp màn hình emulator.")
                return
            
            # Create coordinate picker window
            self._show_coordinate_picker(screenshot, emulator)
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi lấy tọa độ: {e}")
            import traceback
            print(traceback.format_exc())
    
    def _show_coordinate_picker(self, screenshot, emulator):
        """Show screenshot and allow user to click to get coordinates"""
        picker_window = tk.Toplevel(self.window)
        picker_window.title("Chọn tọa độ - Click vào màn hình để lấy tọa độ")
        
        # Get screen size for scaling
        screen_size = emulator.get_screen_size()
        if not screen_size:
            screen_size = (1080, 1920)  # Default
        
        # Maximize window to full screen
        picker_window.state('zoomed')  # Windows
        try:
            picker_window.attributes('-zoomed', True)  # Alternative for some systems
        except:
            pass
        
        # Wait for window to be displayed to get actual size
        picker_window.update_idletasks()
        actual_width = picker_window.winfo_width()
        actual_height = picker_window.winfo_height()
        
        # Calculate scale to fit screen (leave margin for buttons and labels)
        max_display_width = actual_width - 50
        max_display_height = actual_height - 200  # More space for buttons
        
        scale_x = max_display_width / screenshot.width
        scale_y = max_display_height / screenshot.height
        scale = min(scale_x, scale_y, 1.0)  # Don't scale up, only down if needed
        
        new_width = int(screenshot.width * scale)
        new_height = int(screenshot.height * scale)
        
        resized_screenshot = screenshot.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to PhotoImage
        photo = ImageTk.PhotoImage(resized_screenshot)
        
        # Use grid layout for better control
        picker_window.columnconfigure(0, weight=1)
        picker_window.rowconfigure(1, weight=1)
        
        # Coordinate display (top)
        coord_label = ttk.Label(picker_window, text="Click vào màn hình để lấy tọa độ", font=("Arial", 12))
        coord_label.grid(row=0, column=0, pady=10)
        
        # Canvas frame (middle, expandable)
        canvas_frame = ttk.Frame(picker_window)
        canvas_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=5)
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)
        
        # Create canvas - make it fill the frame
        canvas = tk.Canvas(canvas_frame, cursor="cross", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Store image dimensions and scale for coordinate calculation
        canvas.image_width = new_width
        canvas.image_height = new_height
        canvas.scale_factor = scale
        
        # Function to center image after canvas is displayed
        def center_image():
            canvas.update_idletasks()
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            if canvas_width > 0 and canvas_height > 0:
                img_x = canvas_width // 2
                img_y = canvas_height // 2
                canvas.create_image(img_x, img_y, anchor=tk.CENTER, image=photo)
                canvas.image = photo  # Keep a reference
        
        # Center image after window is displayed
        picker_window.after(100, center_image)
        
        selected_coords = [None, None]
        
        def on_canvas_click(event):
            # Get canvas dimensions
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            
            # Calculate offset to center image
            offset_x = (canvas_width - canvas.image_width) // 2
            offset_y = (canvas_height - canvas.image_height) // 2
            
            # Adjust coordinates relative to image position (image is centered)
            img_x = event.x - offset_x
            img_y = event.y - offset_y
            
            # Only process if coordinates are within image bounds
            if (0 <= img_x <= canvas.image_width and 0 <= img_y <= canvas.image_height):
                # Calculate actual coordinates
                x = int(img_x / canvas.scale_factor)
                y = int(img_y / canvas.scale_factor)
                
                # Clamp to screen size
                x = max(0, min(x, screen_size[0] - 1))
                y = max(0, min(y, screen_size[1] - 1))
                
                selected_coords[0] = x
                selected_coords[1] = y
                
                coord_label.config(text=f"Tọa độ: X={x}, Y={y} (Click lại để thay đổi)")
                
                # Draw crosshair
                canvas.delete("crosshair")
                canvas.create_line(event.x - 10, event.y, event.x + 10, event.y, fill="red", width=2, tags="crosshair")
                canvas.create_line(event.x, event.y - 10, event.x, event.y + 10, fill="red", width=2, tags="crosshair")
        
        canvas.bind("<Button-1>", on_canvas_click)
        
        def confirm():
            if selected_coords[0] is not None and selected_coords[1] is not None:
                self.x_var.set(str(selected_coords[0]))
                self.y_var.set(str(selected_coords[1]))
                picker_window.destroy()
                messagebox.showinfo("Thành công", f"Đã lấy tọa độ: X={selected_coords[0]}, Y={selected_coords[1]}")
            else:
                messagebox.showwarning("Cảnh báo", "Vui lòng click vào màn hình để chọn tọa độ!")
        
        def cancel():
            picker_window.destroy()
        
        # Buttons frame (bottom)
        button_frame = ttk.Frame(picker_window)
        button_frame.grid(row=2, column=0, pady=10)
        
        ttk.Button(button_frame, text="✓ Xác nhận", command=confirm).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Hủy", command=cancel).pack(side=tk.LEFT, padx=5)
        
        # Instructions (bottom)
        instructions = ttk.Label(
            picker_window,
            text="Hướng dẫn: Click vào vị trí trên màn hình emulator để lấy tọa độ, sau đó click 'Xác nhận'",
            font=("Arial", 9),
            foreground="gray"
        )
        instructions.grid(row=3, column=0, pady=5)

