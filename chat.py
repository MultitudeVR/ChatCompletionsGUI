import openai
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from threading import Thread
import configparser
import re
import os
import platform
import asyncio

config_filename = "config.ini"
system_message_default_text = "You are a helpful assistant."
os_name = platform.system()
if os_name == 'Linux' and "ANDROID_BOOTLOGO" in os.environ:
	os_name = 'Android'

if not os.path.exists(config_filename):
    with open(config_filename, "w") as f:
        f.write("[openai]\n")

config = configparser.ConfigParser()
config.read(config_filename)

openai.api_key = config.get("openai", "api_key", fallback="insert-key")
openai.organization = config.get("openai", "organization", fallback="")

if not os.path.exists("chat_logs"):
    os.makedirs("chat_logs")

def clear_chat_history():
    for row in reversed(range(len(chat_history))):
        delete_message(row + 1)

    chat_history.clear()

def save_chat_history():
    filename = chat_filename_var.get()

    if filename == "<new-log>":
        # Get a file name suggestion from the API
        def request_file_name():
            messages = [
                {"role": "system", "content": system_message_widget.get("1.0", tk.END).strip()}
            ]
            for message in chat_history:
                messages.append(
                    {
                        "role": message["role"].get(),
                        "content": message["content_widget"].get("1.0", tk.END).strip(),
                    }
                )
            messages.append(
                {
                    "role": "system",
                    "content": "The user is saving this chat log. In your next message, please write only a suggested name for the file. It should be in the format 'file-name-is-separated-by-hyphens', it should be descriptive of the chat you had with the user, and it should be very concise - no more than 4 words (and ideally just 2 or 3). Do not acknowledge this system message with any additional words, please simply write the suggested filename.",
                }
            )
            culled_messages = apply_sliding_context_window(messages, max_tokens=4096)
            response = openai.ChatCompletion.create(
              model="gpt-3.5-turbo",
              messages=culled_messages
            )
            suggested_filename = response["choices"][0]["message"]["content"].strip()
            return suggested_filename

        suggested_filename = request_file_name()
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt", initialdir="chat_logs", initialfile=suggested_filename, title="Save Chat Log"
        )
    else:
        file_path = os.path.join("chat_logs", filename)
        # Check for overwrite confirmation
        if not messagebox.askokcancel("Overwrite Confirmation", f"Do you want to overwrite '{filename}'?"):
            return

    if not file_path:
        return

    # Save the chat history to the file
    with open(file_path, "w", encoding='utf-8') as f:
        # Add the system message to the beginning of the chat history
        system_message = system_message_widget.get("1.0", tk.END).strip()
        f.write(f"system: \"{system_message}\"\n")

        for message in chat_history:
            role = message["role"].get()
            content = message["content_widget"].get("1.0", tk.END).strip()
            f.write(f"{role}: \"{content}\"\n")

    update_chat_file_dropdown(file_path)
    
def count_tokens(text):
    return len(text.encode('utf-8')) // 4

def apply_sliding_context_window(messages, max_tokens):
    tokens_to_keep = max_tokens // 4
    culled_messages = messages.copy()

    current_tokens = sum(count_tokens(msg["content"]) for msg in culled_messages)
    tokens_to_remove = current_tokens - max_tokens
    # print(str(current_tokens) + " " + str(tokens_to_remove))
    if tokens_to_remove > 0:
        index_to_start_culling = 0
        tokens_counted = 0
        for i, message in enumerate(culled_messages):
            tokens_counted += count_tokens(message["content"])
            if tokens_counted >= tokens_to_keep:
                index_to_start_culling = i
                break

        while tokens_to_remove > 0 and index_to_start_culling < len(culled_messages):
            message = culled_messages[index_to_start_culling]
            message_tokens = count_tokens(message["content"])
            chars_to_remove = min(tokens_to_remove * 4, message_tokens * 4)
            culled_messages[index_to_start_culling]["content"] = message["content"][:-chars_to_remove]
            tokens_to_remove -= (chars_to_remove // 4)
            index_to_start_culling += 1
    # print(sum(count_tokens(msg["content"]) for msg in culled_messages))
    return culled_messages
    
def update_chat_file_dropdown(new_file_path):
    new_file_name = os.path.basename(new_file_path)
    if new_file_name not in chat_files:
        chat_files.append(new_file_name)
        chat_file_dropdown["menu"].add_command(label=new_file_name, command=tk._setit(chat_filename_var, new_file_name))
    chat_filename_var.set(new_file_name)

def load_chat_history():
    filename = chat_filename_var.get()
    if not filename or filename == "<new-log>":
        # No file selected? Load default
        clear_chat_history()
        system_message_widget.delete("1.0", tk.END)
        system_message_widget.insert(tk.END, system_message_default_text)
        add_message("user", "")
        return

    filepath = os.path.join("chat_logs", filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding='utf-8') as f:
            content = f.read()

        clear_chat_history()

        # Extract the system message and the remaining chat content using a regex pattern
        pattern = re.compile(r'^system: "(?P<system_message>.*?)"\n(?P<chat_content>.+)', re.DOTALL)
        match = pattern.match(content)

        if match:
            system_message = match.group("system_message")
            chat_content = match.group("chat_content")

            system_message_widget.delete("1.0", tk.END)
            system_message_widget.insert(tk.END, system_message)

            lines = chat_content.splitlines()

            for line in lines:
                if line.startswith("user: ") or line.startswith("assistant: "):
                    role, content = line.strip().split(": ", 1)
                    add_message(role, content[1:-1] if line.endswith("\"") else content[1:] + "\n")
                else:
                    chat_history[-1]["content_widget"].insert(tk.END, line[:-1] if line.endswith("\"") else line + "\n")

    app.after(100, update_height_of_all_messages)


def update_height_of_all_messages():
    for message in chat_history:
        update_content_height(None, message["content_widget"])

is_streaming_cancelled = False

def send_request():
    global is_streaming_cancelled
    is_streaming_cancelled = False
    cancel_button.config(state=tk.NORMAL)

    def request_thread():
        global is_streaming_cancelled
        messages = [{"role": "system", "content": system_message_widget.get("1.0", tk.END).strip()}]
        for message in chat_history:
            messages.append({"role": message["role"].get(), "content": message["content_widget"].get("1.0", tk.END).strip()})
        
        max_tokens_for_context_window = (8192 if model_var.get() == 'gpt-4' else 4096) - max_length_var.get()
        culled_messages = apply_sliding_context_window(messages, max_tokens=max_tokens_for_context_window)
        async def streaming_chat_completion():
            global is_streaming_cancelled
            async for chunk in await openai.ChatCompletion.acreate(
                model=model_var.get(),
                messages=culled_messages,
                temperature=temperature_var.get(),
                max_tokens=max_length_var.get(),
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                stream=True,
            ):
                content = chunk["choices"][0].get("delta", {}).get("content")
                if content is not None:
                    app.after(0, add_to_last_message, content)
                if is_streaming_cancelled:
                    break

            if not is_streaming_cancelled:
                app.after(0, add_empty_user_message)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(streaming_chat_completion())

    Thread(target=request_thread).start()

def add_to_last_message(content):
    last_message = chat_history[-1]
    if last_message["role"].get() == "assistant":
        last_message["content_widget"].insert(tk.END, content)
        update_content_height(None, last_message["content_widget"])
    else:
        add_message("assistant", content)

def cancel_streaming():
    global is_streaming_cancelled
    is_streaming_cancelled = True
    cancel_button.config(state=tk.DISABLED)

def add_empty_user_message():
    add_message("user", "")
    cancel_button.config(state=tk.DISABLED)
    
def update_entry_widths(event=None):
    window_width = app.winfo_width()
    screen_width = app.winfo_screenwidth()
    dpi = app.winfo_fpixels('1i')
    scaling_factor = 0.12 * ( 96/dpi)
    # Calculate the new width of the Text widgets based on the window width
    new_entry_width = int((window_width - scaling_factor*1000) * scaling_factor)

    for message in chat_history:
        message["content_widget"].configure(width=new_entry_width)


def update_content_height(event, content_widget):
    lines = content_widget.get("1.0", "end-1c").split("\n")
    widget_width = int(content_widget["width"])
    wrapped_lines = 0
    for line in lines:
        if line == "":
            wrapped_lines += 1
        else:
            line_length = len(line)
            wrapped_lines += -(-line_length // widget_width)  # Equivalent to math.ceil(line_length / widget_width)
    content_widget.configure(height=wrapped_lines)

def add_message(role="user", content=""):
    global add_button_row
    message = {
        "role": tk.StringVar(value=role),
        "content": tk.StringVar(value=content)
    }
    chat_history.append(message)

    row = len(chat_history)
    message["role_button"] = ttk.Button(inner_frame, textvariable=message["role"], command=lambda: toggle_role(message))
    message["role_button"].grid(row=row, column=0, sticky="w")

    message["content_widget"] = tk.Text(inner_frame, wrap=tk.WORD, height=1, width=50)
    message["content_widget"].grid(row=row, column=1, sticky="we")
    message["content_widget"].insert(tk.END, content)
    message["content_widget"].bind("<KeyRelease>", lambda event, content_widget=message["content_widget"]: update_content_height(event, content_widget))
    update_content_height(None, message["content_widget"])

    add_button_row += 1
    align_add_button()

    message["delete_button"] = ttk.Button(inner_frame, text="-", width=3, command=lambda: delete_message(row))
    message["delete_button"].grid(row=row, column=2, sticky="ne")

    chat_frame.yview_moveto(1.5)

def align_add_button():
    add_button.grid(row=add_button_row, column=0, sticky="e", pady=(5, 0))
    add_button_label.grid(row=add_button_row, column=1, sticky="w")
    cancel_button.grid(row=add_button_row, column=1, sticky="e")

def delete_message(row):
    for widget in inner_frame.grid_slaves():
        if int(widget.grid_info()["row"]) == row:
            widget.destroy()

    del chat_history[row - 1]

    for i, message in enumerate(chat_history[row - 1:], start=row):
        for widget in inner_frame.grid_slaves():
            if int(widget.grid_info()["row"]) == i + 1:
                widget.grid(row=i)

        message["delete_button"].config(command=lambda row=i: delete_message(row))

    global add_button_row
    add_button_row -= 1
    align_add_button()
    cancel_streaming()

def toggle_role(message):
    if message["role"].get() == "user":
        message["role"].set("assistant")
    else:
        message["role"].set("user")

def configure_scrollregion(event):
    chat_frame.configure(scrollregion=chat_frame.bbox("all"))

def save_api_key():
    openai.api_key = apikey_var.get()
    openai.organization = orgid_var.get()
    config.set("openai", "api_key", openai.api_key)
    config.set("openai", "organization", openai.organization)

    with open("config.ini", "w") as config_file:
        config.write(config_file)

def add_message_via_button():
    add_message("user" if len(chat_history) == 0 or chat_history[-1]["role"].get() == "assistant" else "assistant", "")

def prompt_paste_from_clipboard(event, entry):
    global previous_focused_widget
    # Check if the previously focused widget is the same as the clicked one
    if previous_focused_widget != entry:
        clipboard_content = app.clipboard_get()
        if messagebox.askyesno("Paste from Clipboard", f"Do you want to paste the following content from the clipboard?\n\n{clipboard_content}"):
            entry.delete(0, tk.END)
            entry.insert(0, clipboard_content)
    previous_focused_widget = entry

def update_previous_focused_widget(event):
    global previous_focused_widget
    previous_focused_widget = event.widget
    
# Functions for synchronizing slider and entry
def on_temp_entry_change(*args):
    try:
        value = float(temp_entry_var.get())
        if 0 <= value <= 1:
            temperature_var.set(value)
        else:
            raise ValueError
    except ValueError:
        temp_entry_var.set(f"{temperature_var.get():.2f}")

def on_max_len_entry_change(*args):
    try:
        value = int(max_len_entry_var.get())
        if 1 <= value <= 4000:
            max_length_var.set(value)
        else:
            raise ValueError
    except ValueError:
        max_len_entry_var.set(max_length_var.get())
        
def toggle_dark_mode():
    if dark_mode_var.get():
        app.configure(bg="#2c2c2c")
        main_frame.configure(style="Dark.TFrame")
        configuration_frame.configure(style="Dark.TFrame")
        chat_frame.configure(bg="#2c2c2c") # Change chat_frame background color
        inner_frame.configure(style="Dark.TFrame")
        
        for widget in main_frame.winfo_children():
            if isinstance(widget, (ttk.Label, ttk.OptionMenu, ttk.Checkbutton)):
                widget.configure(style="Dark." + widget.winfo_class())
        for widget in configuration_frame.winfo_children():
            if isinstance(widget, (ttk.Label, ttk.OptionMenu, ttk.Checkbutton)):
                widget.configure(style="Dark." + widget.winfo_class())

    else:
        app.configure(bg=default_bg_color)
        main_frame.configure(style="")
        configuration_frame.configure(style="")
        chat_frame.configure(bg=default_bg_color) # Reset chat_frame background color
        inner_frame.configure(style="")
        
        for widget in main_frame.winfo_children():
            if isinstance(widget, (ttk.Label, ttk.Button, ttk.OptionMenu, ttk.Checkbutton, ttk.Scrollbar)):
                widget.configure(style=widget.winfo_class())
        for widget in configuration_frame.winfo_children():
            if isinstance(widget, (ttk.Label, ttk.Button, ttk.OptionMenu, ttk.Checkbutton, ttk.Scrollbar)):
                widget.configure(style=widget.winfo_class())
    
# Initialize the main application window
app = tk.Tk()
app.geometry("800x600")
app.title("Chat Completions GUI")

# Create the main_frame for holding the chat and other widgets
main_frame = ttk.Frame(app, padding="10")
main_frame.grid(row=1, column=0, sticky="nsew")

# System message and model selection
system_message = tk.StringVar(value=system_message_default_text)
ttk.Label(main_frame, text="System message:").grid(row=0, column=0, sticky="w")
system_message_widget = tk.Text(main_frame, wrap=tk.WORD, height=5, width=50)
system_message_widget.grid(row=0, column=1, sticky="we", pady=3)
system_message_widget.insert(tk.END, system_message.get())

model_var = tk.StringVar(value="gpt-3.5-turbo")
ttk.Label(main_frame, text="Model:").grid(row=0, column=6, sticky="ne")
ttk.OptionMenu(main_frame, model_var, "gpt-3.5-turbo", "gpt-3.5-turbo", "gpt-4").grid(row=0, column=7, sticky="ne")

# Add sliders for temperature, max length, and top p
temperature_var = tk.DoubleVar(value=0.7)
ttk.Label(main_frame, text="Temperature:").grid(row=0, column=6, sticky="e")
temperature_scale = ttk.Scale(main_frame, variable=temperature_var, from_=0, to=1, orient="horizontal")
temperature_scale.grid(row=0, column=7, sticky="w")

max_length_var = tk.IntVar(value=256)
ttk.Label(main_frame, text="Max Length:").grid(row=0, column=6, sticky="se")
max_length_scale = ttk.Scale(main_frame, variable=max_length_var, from_=1, to=4000, orient="horizontal")
max_length_scale.grid(row=0, column=7, sticky="sw")

# Add Entry widgets for temperature and max length
temp_entry_var = tk.StringVar()
temp_entry = ttk.Entry(main_frame, textvariable=temp_entry_var, width=5)
temp_entry.grid(row=0, column=8, sticky="w")
temp_entry_var.set(temperature_var.get())
temperature_var.trace("w", lambda *args: temp_entry_var.set(f"{temperature_var.get():.2f}"))
temp_entry_var.trace("w", on_temp_entry_change)

max_len_entry_var = tk.StringVar()
max_len_entry = ttk.Entry(main_frame, textvariable=max_len_entry_var, width=5)
max_len_entry.grid(row=0, column=8, sticky="sw")
max_len_entry_var.set(max_length_var.get())
max_length_var.trace("w", lambda *args: max_len_entry_var.set(max_length_var.get()))
max_len_entry_var.trace("w", on_max_len_entry_change)

# Chat frame and scrollbar
chat_history = []
chat_frame = tk.Canvas(main_frame, highlightthickness=0)
chat_frame.grid(row=1, column=0, columnspan=9, sticky="nsew")

inner_frame = ttk.Frame(chat_frame)
inner_frame.rowconfigure(0, weight=1)
chat_frame.create_window((0, 0), window=inner_frame, anchor="nw")

chat_scroll = ttk.Scrollbar(main_frame, orient="vertical", command=chat_frame.yview)
chat_scroll.grid(row=1, column=9, sticky="ns")
chat_frame.configure(yscrollcommand=chat_scroll.set)

# Add button for chat messages
add_button_row = 1
add_button = ttk.Button(inner_frame, text="+", width=3, command=add_message_via_button)
add_button_label = ttk.Label(inner_frame, text="Add message")

# Add a "cancel" button
cancel_button = tk.Button(inner_frame, text="Cancel", command=cancel_streaming, state=tk.DISABLED)

# Submit button
submit_button = ttk.Button(main_frame, text="Submit", command=send_request).grid(row=7, column=7, sticky="e")
add_message("user", "")

# Configuration frame for API key, Org ID, and buttons
configuration_frame = ttk.Frame(app, padding="3")
configuration_frame.grid(row=0, column=0, sticky="new")
config_row = 0
# Add a dropdown menu to select a chat log file to load
chat_filename_var = tk.StringVar()
chat_files = [f for f in os.listdir("chat_logs") if os.path.isfile(os.path.join("chat_logs", f))]
ttk.Label(configuration_frame, text="Chat Log:").grid(row=config_row, column=0, sticky="w")
default_chat_file = "<new-log>"
chat_files.insert(0, default_chat_file)
chat_file_dropdown = ttk.OptionMenu(configuration_frame, chat_filename_var, default_chat_file, *chat_files)
chat_file_dropdown.grid(row=config_row, column=1, sticky="w")

# Add a button to load the selected chat log
load_button = ttk.Button(configuration_frame, text="Load Chat Log", command=load_chat_history)
load_button.grid(row=config_row, column=2, sticky="w")

# Add a button to save the chat history
save_button = ttk.Button(configuration_frame, text="Save Chat Log", command=save_chat_history)
save_button.grid(row=config_row, column=3, sticky="w")

# Add API key / Org ID configurations
apikey_var = tk.StringVar(value=openai.api_key)
ttk.Label(configuration_frame, text="API Key:").grid(row=config_row, column=4, sticky="e")
apikey_entry = ttk.Entry(configuration_frame, textvariable=apikey_var, width=10)
apikey_entry.grid(row=config_row, column=5, sticky="e")

orgid_var = tk.StringVar(value=openai.organization)
ttk.Label(configuration_frame, text="Org ID:").grid(row=config_row, column=6, sticky="e")
orgid_entry = ttk.Entry(configuration_frame, textvariable=orgid_var, width=10)
orgid_entry.grid(row=config_row, column=7, sticky="e")

save_button = ttk.Button(configuration_frame, text="Save API Key", command=save_api_key)
save_button.grid(row=config_row, column=8, sticky="e")

dark_mode = False
# Create a variable for dark mode toggle
dark_mode_var = tk.BooleanVar()
dark_mode_var.set(False)

# Create a Checkbutton widget for dark mode toggle
dark_mode_checkbutton = ttk.Checkbutton(configuration_frame, text="Dark mode", variable=dark_mode_var, command=toggle_dark_mode)
dark_mode_checkbutton.grid(row=0, column=9, padx=10, pady=10, sticky="w")     

default_bg_color = "SystemButtonFace"
# Create styles for light and dark modes
style = ttk.Style(app)
style.configure("Dark.TFrame", background="#2c2c2c")
style.configure("Dark.TLabel", background="#2c2c2c", foreground="#ffffff")
# style.configure("Dark.TButton", background="#2c2c2c", foreground="2c2c2c")
style.configure("Dark.TOptionMenu", background="#2c2c2c", foreground="#ffffff")
style.configure("Dark.TCheckbutton", background="#2c2c2c", foreground="#ffffff")

# Add a separator
ttk.Separator(configuration_frame, orient='horizontal').grid(row=config_row+1, column=0, columnspan=9, sticky="we", pady=3)

# Set the weights for the configuration frame
configuration_frame.columnconfigure(3, weight=1)

# Configure weights for resizing behavior
app.columnconfigure(0, weight=1)
app.rowconfigure(0, weight=0)
app.rowconfigure(1, weight=1)

main_frame.columnconfigure(1, weight=1)
main_frame.rowconfigure(1, weight=1)

# Initialize the previous_focused_widget variable
previous_focused_widget = None

# Bind events for scrollregion and entry widths updates
inner_frame.bind("<Configure>", configure_scrollregion)
app.bind("<Configure>", update_entry_widths)

if(os_name == 'Android'): # Bind events for api/org clipboard prompts, only in Android
    apikey_entry.bind("<Button-1>", lambda event, entry=apikey_entry: prompt_paste_from_clipboard(event, entry))
    orgid_entry.bind("<Button-1>", lambda event, entry=orgid_entry: prompt_paste_from_clipboard(event, entry))

# Bind events for tracking the focused widget
app.bind_class('Entry', '<FocusOut>', update_previous_focused_widget)

# Start the application main loop
app.mainloop()
