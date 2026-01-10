"""
Build script to create executable file
"""
import PyInstaller.__main__
import sys
from pathlib import Path

def build_exe():
    """Build executable using PyInstaller"""
    
    # PyInstaller options
    options = [
        'main.py',
        '--name=GameAutomationTool',
        '--onefile',
        '--windowed',  # No console window for GUI
        '--icon=NONE',  # Add icon file path if you have one
        '--add-data=config;config',  # Include config directory
        '--hidden-import=tkinter',
        '--hidden-import=PIL',
        '--hidden-import=cv2',
        '--hidden-import=yaml',
        '--collect-all=tkinter',
        '--collect-all=PIL',
    ]
    
    print("Building executable...")
    print("This may take a few minutes...")
    
    PyInstaller.__main__.run(options)
    
    print("\n✅ Build complete!")
    print("Executable file: dist/GameAutomationTool.exe")
    print("\nNote: First run may be slow as files are extracted.")


if __name__ == "__main__":
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("❌ PyInstaller not found!")
        print("Install it with: pip install pyinstaller")
        sys.exit(1)
    
    build_exe()

