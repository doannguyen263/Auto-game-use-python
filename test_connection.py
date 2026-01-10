"""
Test script to verify emulator connection and basic functionality
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from emulator.controller import EmulatorController
from utils.logger import setup_logger


def test_connection():
    """Test emulator connection"""
    logger = setup_logger(debug=True)
    logger.info("Testing emulator connection...")
    
    # Initialize emulator
    emulator = EmulatorController()
    
    # Connect
    if not emulator.connect():
        logger.error("Failed to connect to emulator")
        logger.info("Please ensure:")
        logger.info("1. Emulator is running")
        logger.info("2. USB debugging is enabled")
        logger.info("3. ADB is installed and in PATH")
        return False
    
    logger.info("✓ Connected to emulator")
    
    # Get screen size
    size = emulator.get_screen_size()
    if size:
        logger.info(f"✓ Screen size: {size[0]}x{size[1]}")
    else:
        logger.warning("Could not get screen size")
    
    # Take screenshot
    logger.info("Taking screenshot...")
    screenshot = emulator.screenshot("screenshots/test_screenshot.png")
    
    if screenshot:
        logger.info(f"✓ Screenshot saved: screenshots/test_screenshot.png")
        logger.info(f"  Size: {screenshot.size[0]}x{screenshot.size[1]}")
    else:
        logger.error("Failed to take screenshot")
        return False
    
    logger.info("\n✓ All tests passed!")
    logger.info("You can now use the tool with:")
    logger.info("  python main.py --game <game_name> --task <task_name>")
    
    return True


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

