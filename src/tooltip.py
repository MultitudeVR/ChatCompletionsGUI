
import tkinter as tk
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.tooltip_id = None  # ID of the scheduled tooltip
        self.delay = 650  # Delay in milliseconds (0.65 seconds)
        self.widget.bind("<Enter>", self.schedule_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def schedule_tooltip(self, event=None):
        # Cancel any existing scheduled tooltip
        if self.tooltip_id:
            self.widget.after_cancel(self.tooltip_id)
        # Schedule the tooltip to be shown after the delay
        self.tooltip_id = self.widget.after(self.delay, self.show_tooltip)

    def show_tooltip(self):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip_window, text=self.text, background="black", foreground="white", relief="solid", borderwidth=1)
        label.pack()

    def hide_tooltip(self, event=None):
        # Cancel any scheduled tooltip
        if self.tooltip_id:
            self.widget.after_cancel(self.tooltip_id)
            self.tooltip_id = None
        # Destroy the tooltip window if it exists
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None