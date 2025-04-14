import tkinter as tk
import sys
import traceback

try:
    import coordinate_matching_test
    print("Module imported successfully! Testing class initialization...")
    
    # Try to create a simple root window
    root = tk.Tk()
    root.withdraw()  # Hide the window
    
    # Try to instantiate the main class
    try:
        app = coordinate_matching_test.TemplateMatchingApp(root)
        print("App initialized successfully!")
    except Exception as e:
        print(f"Error initializing app: {e}")
        traceback.print_exc()
    
    print("Test complete!")
except ImportError as e:
    print(f"Import error: {e}")
    traceback.print_exc()
except SyntaxError as e:
    print(f"Syntax error: {e}")
    print(f"File: {e.filename}, Line {e.lineno}, Position {e.offset}")
    print(f"Text: {e.text}")
    traceback.print_exc()
except Exception as e:
    print(f"Unexpected error: {e}")
    traceback.print_exc()
