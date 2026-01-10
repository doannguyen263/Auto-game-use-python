"""
Game Automation Tool
Main Entry Point - Supports both GUI and CLI mode
"""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Game Automation Tool - Tự động hóa game trên emulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Chạy GUI (mặc định)
  python main.py
  
  # Chạy từ command line
  python main.py --game my_game --task daily_quest
  python main.py --game my_game --task auto_battle --debug
  python main.py --game my_game --list-tasks
        """
    )
    parser.add_argument("--gui", action="store_true", default=True, help="Run GUI mode (default)")
    parser.add_argument("--no-gui", dest="gui", action="store_false", help="Run CLI mode")
    parser.add_argument("--game", type=str, help="Game name (for CLI mode)")
    parser.add_argument("--task", type=str, help="Task name to execute (for CLI mode)")
    parser.add_argument("--list-tasks", action="store_true", help="List all available tasks (for CLI mode)")
    parser.add_argument("--emulator", type=str, default="auto", help="Emulator type (auto/bluestacks/nox/ldplayer)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Run GUI mode (default)
    if args.gui or (not args.game and not args.list_tasks):
        try:
            from gui.main_window import MainWindow
            import tkinter as tk
            
            root = tk.Tk()
            app = MainWindow(root)
            root.mainloop()
            return 0
        except ImportError as e:
            print(f"Error importing GUI: {e}")
            print("Falling back to CLI mode...")
            # Fall through to CLI mode
    
    # CLI mode
    from config.manager import ConfigManager
    from emulator.controller import EmulatorController
    from task.manager import TaskManager
    from utils.logger import setup_logger
    
    logger = setup_logger(debug=args.debug)
    
    # List tasks if requested
    if args.list_tasks:
        if not args.game:
            print("❌ Error: --game is required for --list-tasks")
            return 1
        
        config_manager = ConfigManager()
        game_config = config_manager.load_game_config(args.game)
        
        if not game_config:
            print(f"❌ Config not found for game: {args.game}")
            return 1
        
        tasks = game_config.get("tasks", {})
        print(f"\n📋 Available tasks for {args.game}:\n")
        
        for task_name, task_config in tasks.items():
            name = task_config.get("name", task_name)
            description = task_config.get("description", "No description")
            print(f"  • {task_name}")
            print(f"    Name: {name}")
            print(f"    Description: {description}\n")
        
        return 0
    
    # Task execution
    if not args.game or not args.task:
        parser.print_help()
        print("\n❌ Error: --game and --task are required for CLI mode")
        print("   Or run without arguments to start GUI mode")
        return 1
    
    logger.info(f"Starting Game Automation Tool")
    logger.info(f"Game: {args.game}, Task: {args.task}")
    
    try:
        # Load config
        config_manager = ConfigManager()
        game_config = config_manager.load_game_config(args.game)
        
        if not game_config:
            logger.error(f"Game config not found: {args.game}")
            logger.info("Please ensure config/games/{args.game}.yaml exists")
            return 1
        
        # Initialize emulator controller
        emulator = EmulatorController(emulator_type=args.emulator)
        if not emulator.connect():
            logger.error("Failed to connect to emulator")
            logger.info("Please ensure:")
            logger.info("1. Emulator is running")
            logger.info("2. USB debugging is enabled")
            logger.info("3. Run: python test_connection.py to test connection")
            return 1
        
        # Initialize task manager
        task_manager = TaskManager(emulator, game_config, logger, game_name=args.game)
        
        # Run task
        success = task_manager.run_task(args.task)
        
        if success:
            logger.info("Task completed successfully")
            return 0
        else:
            logger.error("Task failed")
            return 1
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

