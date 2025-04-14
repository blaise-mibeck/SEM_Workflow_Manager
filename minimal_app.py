"""
Minimal test application for SEM Coordinate Matching
"""

import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class MinimalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Minimal SEM App Test")
        self.root.geometry("800x600")
        
        # Simple frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Simple label
        ttk.Label(main_frame, text="Testing app initialization").pack(pady=10)
        
        # Simple matplotlib figure
        self.fig = plt.Figure(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=main_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Test Plot")
        self.ax.plot([1, 2, 3, 4], [1, 4, 9, 16])
        self.fig.tight_layout()
        self.canvas.draw()
        
        # Simple button
        ttk.Button(main_frame, text="Test Button", 
                  command=lambda: print("Button clicked")).pack(pady=10)
        
        print("App initialized successfully!")

def main():
    print("Starting minimal test app...")
    root = tk.Tk()
    app = MinimalApp(root)
    print("Entering mainloop...")
    root.mainloop()
    print("Exited mainloop.")

if __name__ == "__main__":
    main()
