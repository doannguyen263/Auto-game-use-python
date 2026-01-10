"""
Game Manager Window - Create and manage games
"""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import yaml


class GameManagerWindow:
    """Game manager window"""
    
    def __init__(self, parent, config_manager, main_window):
        self.parent = parent
        self.config_manager = config_manager
        self.main_window = main_window
        
        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("Quản lý Game")
        self.window.geometry("600x400")
        
        self.setup_ui()
        self.load_games()
    
    def setup_ui(self):
        """Setup user interface"""
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Game list
        list_frame = ttk.LabelFrame(main_frame, text="Danh sách Game", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.games_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.games_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.games_listbox.yview)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="➕ Tạo Game mới", command=self.create_game).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="✏️ Sửa", command=self.edit_game).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🗑️ Xóa", command=self.delete_game).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Đóng", command=self.window.destroy).pack(side=tk.RIGHT, padx=5)
    
    def load_games(self):
        """Load games list"""
        self.games_listbox.delete(0, tk.END)
        games_dir = Path("config/games")
        if games_dir.exists():
            for config_file in games_dir.glob("*.yaml"):
                self.games_listbox.insert(tk.END, config_file.stem)
    
    def create_game(self):
        """Create new game"""
        dialog = tk.Toplevel(self.window)
        dialog.title("Tạo Game mới")
        dialog.geometry("400x200")
        
        ttk.Label(dialog, text="Tên game:").pack(pady=5)
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=30).pack(pady=5)
        
        ttk.Label(dialog, text="Resolution (Width x Height):").pack(pady=5)
        res_frame = ttk.Frame(dialog)
        res_frame.pack(pady=5)
        
        width_var = tk.StringVar(value="1080")
        height_var = tk.StringVar(value="1920")
        ttk.Entry(res_frame, textvariable=width_var, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Label(res_frame, text="x").pack(side=tk.LEFT)
        ttk.Entry(res_frame, textvariable=height_var, width=10).pack(side=tk.LEFT, padx=2)
        
        def save():
            game_name = name_var.get().strip()
            if not game_name:
                messagebox.showerror("Lỗi", "Vui lòng nhập tên game!")
                return
            
            # Create game config
            config = {
                "name": game_name,
                "version": "1.0.0",
                "screen_width": int(width_var.get()),
                "screen_height": int(height_var.get()),
                "tasks": {}
            }
            
            # Save config
            config_file = Path(f"config/games/{game_name}.yaml")
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            messagebox.showinfo("Thành công", f"Đã tạo game: {game_name}")
            self.load_games()
            self.main_window.load_games()
            dialog.destroy()
        
        ttk.Button(dialog, text="Tạo", command=save).pack(pady=10)
    
    def edit_game(self):
        """Edit game (placeholder)"""
        selection = self.games_listbox.curselection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn game!")
            return
        
        messagebox.showinfo("Thông tin", "Tính năng sửa game sẽ được thêm sau")
    
    def delete_game(self):
        """Delete game"""
        selection = self.games_listbox.curselection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn game!")
            return
        
        game_name = self.games_listbox.get(selection[0])
        if messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa game: {game_name}?"):
            config_file = Path(f"config/games/{game_name}.yaml")
            if config_file.exists():
                config_file.unlink()
                self.load_games()
                self.main_window.load_games()
                messagebox.showinfo("Thành công", f"Đã xóa game: {game_name}")

