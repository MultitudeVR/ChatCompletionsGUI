import openai
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from threading import Thread
import configparser
import re
import os

config_filename = "config.ini"
system_message_default_text = "You are a helpful assistant."

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

            response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)

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
    with open(file_path, "w") as f:
        # Add the system message to the beginning of the chat history
        system_message = system_message_widget.get("1.0", tk.END).strip()
        f.write(f"system: \"{system_message}\"\n")

        for message in chat_history:
            role = message["role"].get()
            content = message["content_widget"].get("1.0", tk.END).strip()
            f.write(f"{role}: \"{content}\"\n")

    update_chat_file_dropdown(file_path)

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
        with open(filepath, "r") as f:
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
        
def send_request():
    def request_thread():
        messages = [{"role": "system", "content": system_message_widget.get("1.0", tk.END).strip()}]
        for message in chat_history:
            messages.append({"role": message["role"].get(), "content": message["content_widget"].get("1.0", tk.END).strip()})

        response = openai.ChatCompletion.create(
            model=model_var.get(),
            messages=messages
        )

        assistant_response = response['choices'][0]['message']['content']
        app.after(0, add_message, "assistant", assistant_response)
        app.after(0, add_message, "user", "")

    Thread(target=request_thread).start()

def update_entry_widths(event=None):
    window_width = app.winfo_width()
    
    # Calculate the new width of the Text widgets based on the window width
    new_entry_width = int((window_width - 120) * 0.12)
    
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
    align_add_and_submit_buttons()

    message["delete_button"] = ttk.Button(inner_frame, text="-", width=3, command=lambda: delete_message(row))
    message["delete_button"].grid(row=row, column=2, sticky="ne")

    chat_frame.yview_moveto(1.5)

def align_add_and_submit_buttons():
    add_button.grid(row=add_button_row, column=0, sticky="e", pady=(5, 0))
    add_button_label.grid(row=add_button_row, column=1, sticky="w")
    # submit_button.grid(row=add_button_row + 1, column=0, sticky="w")

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
    align_add_and_submit_buttons();

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
ttk.Label(main_frame, text="Model:").grid(row=0, column=2, sticky="ne")
ttk.OptionMenu(main_frame, model_var, "gpt-3.5-turbo", "gpt-3.5-turbo", "gpt-4").grid(row=0, column=3, sticky="ne")

# Chat frame and scrollbar
chat_history = []
chat_frame = tk.Canvas(main_frame, highlightthickness=0)
chat_frame.grid(row=1, column=0, columnspan=9, sticky="nsew")

inner_frame = ttk.Frame(chat_frame)
inner_frame.rowconfigure(0, weight=1)
chat_frame.create_window((0, 0), window=inner_frame, anchor="nw")

chat_scroll = ttk.Scrollbar(main_frame, orient="vertical", command=chat_frame.yview)
chat_scroll.grid(row=1, column=8, sticky="ns")
chat_frame.configure(yscrollcommand=chat_scroll.set)

# Add button for chat messages
add_button_row = 1
add_button = ttk.Button(inner_frame, text="+", width=3, command=add_message_via_button)
add_button_label = ttk.Label(inner_frame, text="Add message")
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
apikey_entry = ttk.Entry(configuration_frame, textvariable=orgid_var, width=10)
apikey_entry.grid(row=config_row, column=7, sticky="e")

save_button = ttk.Button(configuration_frame, text="Save API Key", command=save_api_key)
save_button.grid(row=config_row, column=8, sticky="e")

# Add a separator
ttk.Separator(configuration_frame, orient='horizontal').grid(row=1, column=0, columnspan=9, sticky="we", pady=3)

# Set the weights for the configuration frame
configuration_frame.columnconfigure(3, weight=1)

# Configure weights for resizing behavior
app.columnconfigure(0, weight=1)
app.rowconfigure(0, weight=0)
app.rowconfigure(1, weight=1)

main_frame.columnconfigure(1, weight=1)
main_frame.rowconfigure(1, weight=1)

# Bind events for scrollregion and entry widths updates
inner_frame.bind("<Configure>", configure_scrollregion)
app.bind("<Configure>", update_entry_widths)

# Start the application main loop
app.mainloop()