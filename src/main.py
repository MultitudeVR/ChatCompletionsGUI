import tkinter as tk
import configparser
import os
import platform
from chat_window import ChatWindow

# configure config file
config_filename = "config.ini"
if not os.path.exists(config_filename):
    with open(config_filename, "w") as f:
        f.write("[openai]\n")
        f.write("[anthropic]\n")
        f.write("[custom_server]\n")
        f.write("[app]\n")
config = configparser.ConfigParser()
config.read(config_filename)
if not config.has_section("openai"):
    config.add_section("openai")
    with open(config_filename, "w") as f:
        config.write(f)
if not config.has_section("anthropic"):
    config.add_section("anthropic")
    with open(config_filename, "w") as f:
        config.write(f)
if not config.has_section("custom_server"):
    config.add_section("custom_server")
    with open(config_filename, "w") as f:
        config.write(f)
if not config.has_section("app"):
    config.add_section("app")
    config.set("app", "dark_mode", "False")
    with open(config_filename, "w") as f:
        config.write(f)

os_name = platform.system()
if os_name == 'Linux' and "ANDROID_BOOTLOGO" in os.environ:
	os_name = 'Android'
if not os.path.exists("chat_logs"):
    os.makedirs("chat_logs")
# Hide console window on Windows
if os.name == 'nt':
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

def main():
    root = tk.Tk()
    app = ChatWindow(root, config, os_name)
    root.mainloop()

if __name__ == "__main__":
    main()