import tkinter as tk
import os

from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from threading import Thread
import asyncio
import json
from datetime import datetime
import random
import string
import sys
from tooltip import ToolTip
from constants import OPENAI_VISION_MODELS, OPENAI_MODELS, ANTHROPIC_MODELS, GOOGLE_MODELS, \
    SYSTEM_MESSAGE_DEFAULT_TEXT, DEFAULT_FILE_NAMING_MODEL, MODEL_INFO, \
    HIGH_DETAIL_COST_PER_IMAGE, LOW_DETAIL_COST_PER_IMAGE
from prompts import file_naming_prompt
from utils import convert_messages_for_model, parse_and_create_image_messages, count_tokens, convert_text_to_tokens, convert_tokens_to_text
from custom_server import CustomServer

class ChatWindow:
    def __init__(self, root, config, os_name):
        self.app = root
        self.config = config
        self.os_name = os_name
        # Initialize the main application window
        self.app.geometry("800x600")
        self.app.title("Chat Completions GUI")

        self.is_streaming_cancelled = False

        self.settings_window = None
        self.settings_frame = None

        self.setup_openai_client()
        self.setup_anthropic_client()
        self.setup_google_client()
        self.custom_servers = []
        custom_server_count = 0
        while config.has_section(f"custom_server_{custom_server_count}"):
            base_url = config.get(f"custom_server_{custom_server_count}", "base_url", fallback="http://localhost:11434/v1/")
            api_key = config.get(f"custom_server_{custom_server_count}", "api_key", fallback="ollama")
            org_id = config.get(f"custom_server_{custom_server_count}", "organization", fallback="")
            custom_models = [model.strip() for model in config.get(f"custom_server_{custom_server_count}", "models", fallback="").split(",") if model.strip()]
            self.custom_servers.append(CustomServer(base_url, api_key, org_id, custom_models, on_config_changed=lambda *args: self.on_config_changed()))
            custom_server_count += 1

        # Create the main_frame for holding the chat and other widgets
        self.main_frame = ttk.Frame(self.app, padding="10")
        self.main_frame.grid(row=1, column=0, sticky="nsew")

        # System message and model selection
        system_message = tk.StringVar(value=SYSTEM_MESSAGE_DEFAULT_TEXT)
        ttk.Label(self.main_frame, text="System message:").grid(row=0, column=0, sticky="w")
        self.system_message_widget = tk.Text(self.main_frame, wrap=tk.WORD, height=5, width=50, undo=True)
        self.system_message_widget.grid(row=0, column=1, sticky="we", pady=3)
        self.system_message_widget.insert(tk.END, system_message.get())

        last_used_model = self.config.get("app", "last_used_model", fallback="gpt-4-turbo")
        self.model_var = tk.StringVar(value=last_used_model)
        ttk.Label(self.main_frame, text="Model:").grid(row=0, column=6, sticky="ne")
        self.update_models_dropdown()

        # Add sliders for temperature, max length, and top p
        self.temperature_var = tk.DoubleVar(value=0.7)
        ttk.Label(self.main_frame, text="Temperature:").grid(row=0, column=6, sticky="e")
        self.temperature_scale = ttk.Scale(self.main_frame, variable=self.temperature_var, from_=0, to=1, orient="horizontal")
        self.temperature_scale.grid(row=0, column=7, sticky="w")

        self.max_length_var = tk.IntVar(value=4000)
        ttk.Label(self.main_frame, text="Max Length:").grid(row=0, column=6, sticky="se")
        self.max_length_scale = ttk.Scale(self.main_frame, variable=self.max_length_var, from_=1, to=8000, orient="horizontal")
        self.max_length_scale.grid(row=0, column=7, sticky="sw")

        # Add Entry widgets for temperature and max length
        self.temp_entry_var = tk.StringVar()
        self.temp_entry = ttk.Entry(self.main_frame, textvariable=self.temp_entry_var, width=5)
        self.temp_entry.grid(row=0, column=8, sticky="w")
        self.temp_entry_var.set(self.temperature_var.get())
        self.temperature_var.trace("w", lambda *args: self.temp_entry_var.set(f"{self.temperature_var.get():.2f}"))
        self.temp_entry_var.trace("w", self.on_temp_entry_change)

        self.max_len_entry_var = tk.StringVar()
        self.max_len_entry = ttk.Entry(self.main_frame, textvariable=self.max_len_entry_var, width=5)
        self.max_len_entry.grid(row=0, column=8, sticky="sw")
        self.max_len_entry_var.set(self.max_length_var.get())
        self.max_length_var.trace("w", lambda *args: self.max_len_entry_var.set(self.max_length_var.get()))
        self.max_len_entry_var.trace("w", self.on_max_len_entry_change)

        # Chat frame and scrollbar
        self.chat_history = []
        self.chat_frame = tk.Canvas(self.main_frame, highlightthickness=0)
        self.chat_frame.grid(row=1, column=0, columnspan=9, sticky="nsew")

        self.inner_frame = ttk.Frame(self.chat_frame)
        self.inner_frame.rowconfigure(0, weight=1)
        self.chat_frame.create_window((0, 0), window=self.inner_frame, anchor="nw")

        chat_scroll = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.chat_frame.yview)
        chat_scroll.grid(row=1, column=9, sticky="ns")
        self.chat_frame.configure(yscrollcommand=chat_scroll.set)

        # Add button for chat messages
        self.add_button_row = 1
        self.add_button = ttk.Button(self.inner_frame, text="+", width=2, command=self.add_message_via_button)
        self.add_button_label = ttk.Label(self.inner_frame, text="Add")
        ToolTip(self.add_button, "Add new message")

        # Submit button
        self.submit_button_text = tk.StringVar()  # Create a StringVar variable to control the text of the submit button
        self.submit_button_text.set("Submit")  # Set the initial text of the submit button to "Submit"
        self.submit_button = ttk.Button(self.main_frame, textvariable=self.submit_button_text, command=self.submit_chat_request)  # Use textvariable instead of text
        self.submit_button.grid(row=7, column=7, sticky="e")

        # Add a new button for counting tokens (new code)
        self.token_count_button = ttk.Button(self.main_frame, text="Count Tokens", command=self.show_token_count_message)
        self.token_count_button.grid(row=7, column=0, sticky="w")  # Place it on the bottom left, same row as 'Submit'

        self.add_message("user", "")

        # Configuration frame for API key, Org ID, and buttons
        self.configuration_frame = ttk.Frame(self.app, padding="3")
        self.configuration_frame.grid(row=0, column=0, sticky="new")
        config_row = 0

        # Add a dropdown menu to select a chat log file to load
        self.chat_filename_var = tk.StringVar()
        self.chat_files = sorted(
            [f for f in os.listdir("chat_logs") if os.path.isfile(os.path.join("chat_logs", f)) and f.endswith('.json')],
            key=lambda x: os.path.getmtime(os.path.join("chat_logs", x)),
            reverse=True
        )
        ttk.Label(self.configuration_frame, text="Chat Log:").grid(row=config_row, column=0, sticky="w")
        default_chat_file = "<new-log>"
        self.chat_files.insert(0, default_chat_file)
        self.chat_file_dropdown = ttk.OptionMenu(self.configuration_frame, self.chat_filename_var, default_chat_file, *self.chat_files)
        self.chat_file_dropdown.grid(row=config_row, column=1, sticky="w")

        # Add a button to load the selected chat log
        self.load_button = ttk.Button(self.configuration_frame, text="Load Chat", command=self.load_chat_history)
        self.load_button.grid(row=config_row, column=2, sticky="w")

        # Add a button to save the chat history
        self.save_button = ttk.Button(self.configuration_frame, text="Save Chat", command=self.save_chat_history)
        self.save_button.grid(row=config_row, column=3, sticky="w")

        # Add image detail dropdown
        self.image_detail_var = tk.StringVar(value="low")
        self.image_detail_dropdown = ttk.OptionMenu(self.main_frame, self.image_detail_var, "low", "low", "high")
        self.update_image_detail_visibility()

        # Update image detail visibility based on selected model
        self.model_var.trace("w", self.update_image_detail_visibility)
        # Create the hamburger menu button and bind it to the show_popup function
        self.hamburger_button = ttk.Button(self.configuration_frame, text="≡", command=self.toggle_settings_window)
        self.hamburger_button.grid(row=config_row, column=9, padx=10, pady=10, sticky="w")

        self.default_bg_color = self.get_default_bg_color(self.app)
        # Create styles for light and dark modes
        self.style = ttk.Style(self.app)
        self.style.configure("Dark.TFrame", background="#2c2c2c")
        self.style.configure("Dark.TLabel", background="#2c2c2c", foreground="#ffffff")
        # style.configure("Dark.TButton", background="#2c2c2c", foreground="2c2c2c")
        self.style.configure("Dark.TOptionMenu", background="#2c2c2c", foreground="#ffffff")
        self.style.configure("Dark.TCheckbutton", background="#2c2c2c", foreground="#ffffff")

        self.dark_mode_var = tk.BooleanVar()
        if self.load_dark_mode_state():
            self.dark_mode_var.set(True)
            self.toggle_dark_mode()

        self.file_naming_model_var = tk.StringVar(value=DEFAULT_FILE_NAMING_MODEL)

        # Add a separator
        ttk.Separator(self.configuration_frame, orient='horizontal').grid(row=config_row+1, column=0, columnspan=10, sticky="we", pady=3)

        # Set the weights for the configuration frame
        self.configuration_frame.columnconfigure(3, weight=1)

        # Configure weights for resizing behavior
        self.app.columnconfigure(0, weight=1)
        self.app.rowconfigure(0, weight=0)
        self.app.rowconfigure(1, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(1, weight=1)

        # Initialize the previous_focused_widget variable
        self.previous_focused_widget = None

        # Bind events
        self.inner_frame.bind("<Configure>", self.configure_scrollregion)
        self.app.bind("<Configure>", self.update_entry_widths)
        self.app.bind_class('Entry', '<FocusOut>', self.update_previous_focused_widget)
        self.app.bind("<Escape>", lambda event: self.toggle_settings_window())
        # Bind Command-N to open new windows (Control-N on Windows/Linux)
        # modifier = 'Command' if sys.platform == 'darwin' else 'Control'
        modifier = 'Control'
        self.app.bind_all(f'<{modifier}-n>', self.create_new_window)
        # Add a protocol to handle the close event
        self.app.protocol("WM_DELETE_WINDOW", self.on_close)
        # Start the application main loop
        self.app.mainloop()

    def setup_openai_client(self):
        if not hasattr(self, "openai_apikey_var"):
            self.openai_apikey_var = tk.StringVar(value=self.config.get("openai", "api_key", fallback=""))
            self.openai_orgid_var = tk.StringVar(value=self.config.get("openai", "organization", fallback=""))
            self.openai_apikey_var.trace("w", self.on_config_changed)
            self.openai_orgid_var.trace("w", self.on_config_changed)
        if self.openai_apikey_var.get():
            try:
                from openai import OpenAI, AsyncOpenAI
            except:
                error_message = "WARNING: OpenAI API not installed. If you wish to use OpenAI or custom server models, install the 'openai' package with the `pip install openai` command."
                print(error_message)
                # self.show_error_popup(error_message)
                self.openai_aclient = None
                self.openai_client = None
                return
            self.openai_client = OpenAI(api_key=self.openai_apikey_var.get(), organization=self.openai_orgid_var.get())
            self.openai_aclient = AsyncOpenAI(api_key=self.openai_apikey_var.get(), organization=self.openai_orgid_var.get())
        else:
            self.openai_client = None
            self.openai_aclient = None

    def setup_anthropic_client(self):
        if not hasattr(self, "anthropic_apikey_var"):
            self.anthropic_apikey_var = tk.StringVar(value=self.config.get("anthropic", "api_key", fallback=""))
            self.anthropic_apikey_var.trace("w", self.on_config_changed)
        if self.anthropic_apikey_var.get():
            try:
                import anthropic
            except:
                error_message = "WARNING: Anthropic API not installed. If you wish to use Anthropic models, install the 'anthropic' package with the `pip install anthropic` command."
                # self.show_error_popup(error_message)
                print(error_message)
                self.anthropic_client = None
                return
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_apikey_var.get())
        else:
            self.anthropic_client = None

    def setup_google_client(self):
        if not hasattr(self, "google_apikey_var"):
            self.google_apikey_var = tk.StringVar(value=self.config.get("google", "api_key", fallback=""))
            self.google_apikey_var.trace("w", self.on_config_changed)
        if self.google_apikey_var.get():
            try:
                import google.generativeai as genai
            except:
                error_message = "WARNING: Google GenerativeAI API not installed. If you wish to use Google Gemini models, install the 'google-generativeai' package with the `pip install google-generativeai` command."
                # self.show_error_popup(error_message)
                print(error_message)
                return
            genai.configure(api_key=self.google_apikey_var.get())
    
    def clear_chat_history(self):
        for row in reversed(range(len(self.chat_history))):
            self.delete_message(row + 1)

        self.chat_history.clear()

    def save_chat_history(self):
        filename = self.chat_filename_var.get()
        chat_data = {
            "system_message": self.system_message_widget.get("1.0", tk.END).strip(),
            "chat_history": [
                {
                    "role": message["role"].get(),
                    "content": message["content_widget"].get("1.0", tk.END).strip()
                }
                for message in self.chat_history
            ]
        }

        if filename == "<new-log>":
            # Get a file name suggestion from the API
            suggested_filename = self.request_file_name()
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json", initialdir="chat_logs", initialfile=suggested_filename, title="Save Chat Log",
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]  # Add a file type filter for JSON
            )
        else:
            file_path = os.path.join("chat_logs", filename)
            # Check for overwrite confirmation
            if not messagebox.askokcancel("Overwrite Confirmation", f"Do you want to overwrite '{filename}'?"):
                return

        if not file_path:
            return

        with open(file_path, "w", encoding='utf-8') as f:
            json.dump(chat_data, f, indent=4)

        self.update_chat_file_dropdown(file_path)

    def get_messages_from_chat_history(self):
        messages = [
            {"role": "system", "content": self.system_message_widget.get("1.0", tk.END).strip()}
        ]
        for message in self.chat_history:
            messages.append(
                {
                    "role": message["role"].get(),
                    "content": message["content_widget"].get("1.0", tk.END).strip()
                }
            )
        return messages

    def request_file_name(self):
        if not self.file_naming_model_var.get() or self.openai_client is None:
            return "chat_log.json"
        file_naming_model = self.file_naming_model_var.get()
        # add to messages a system message informing the AI to create a title
        messages = self.get_messages_from_chat_history()
        # trim messages if they exceed the token limit
        num_tokens = count_tokens(messages, file_naming_model)
        num_messages = len(messages)
        if num_tokens > 3500:
            ratio = 3500 / num_tokens
            for i in range(num_messages):
                if i < 0:
                    break
                tokens = convert_text_to_tokens(messages[i]["content"], file_naming_model)
                messages[i]["content"] = convert_tokens_to_text(tokens[:int(ratio * len(tokens))], file_naming_model)
        # get completion
        messages.append(
            {
                "role": "system",
                "content": file_naming_prompt
            }
        )
        print("requesting file name using ", count_tokens(messages, file_naming_model), f"tokens and {file_naming_model} model.")
        response = self.openai_client.chat.completions.create(model=file_naming_model, messages=messages)
        # return the filename
        suggested_filename = response.choices[0].message.content.strip()
        return suggested_filename

    def check_token_limits(self, messages):
        model = self.model_var.get()
        model_max_context_window = MODEL_INFO[model]["max_tokens"] if model in MODEL_INFO else 128000
        num_prompt_tokens = count_tokens(messages, model)
        num_completion_tokens = int(self.max_length_var.get())

        if num_prompt_tokens + num_completion_tokens > model_max_context_window:
            error_msg = (f"combined prompt and completion tokens ({num_prompt_tokens} + {num_completion_tokens} = "
                        f"{num_prompt_tokens + num_completion_tokens}) exceeds this model's maximum context window of "
                        f"{model_max_context_window}.")
            self.show_error_popup(error_msg)
            return False
        return True

    def submit_chat_request(self):
        messages = self.get_messages_from_chat_history()
        if not self.check_token_limits(messages):
            return
        messages, anthropic_system_message = convert_messages_for_model(self.model_var.get(), messages, self.image_detail_var.get())
        # send request
        def request_thread():
            model_name = self.model_var.get()
            if model_name in ANTHROPIC_MODELS:
                self.stream_anthropic_model_output(messages, anthropic_system_message)
            elif model_name in GOOGLE_MODELS:
                self.stream_google_model_output(messages)
            else:
                self.stream_openai_model_output(messages)
        self.is_streaming_cancelled = False
        self.set_submit_button(False)
        Thread(target=request_thread).start()

    def stream_openai_model_output(self, messages):
        async def streaming_chat_completion():
            if self.model_var.get() in OPENAI_MODELS:
                streaming_client = self.openai_aclient
                if not streaming_client:
                    self.show_error_popup("OpenAI API not installed. Please install the 'openai' package with the `pip install openai` command.")
                    return
            else:
                streaming_client = next((server.client for server in self.custom_servers if self.model_var.get() in server.models), None)
                if len(self.custom_servers) > 0 and self.custom_servers[0].client is None:
                    self.show_error_popup("OpenAI package not found, custom servers will be disabled! Install the OpenAI API with `pip install openai`")
                    return
                elif not streaming_client:
                    error_message = f"Model {self.model_var.get()} not found in custom servers."
                    self.show_error_popup(error_message)
                    return
            try:
                response = streaming_client.chat.completions.create(model=self.model_var.get(),
                    messages=messages,
                    temperature=self.temperature_var.get(),
                    max_tokens=self.max_length_var.get(),
                    # top_p=1,
                    # frequency_penalty=0,
                    # presence_penalty=0,
                    stream=True)
            except Exception as e:
                error_message = f"An error occurred: {e}"
                loop.call_soon_threadsafe(self.show_error_popup, error_message)
                return
            try:
                async for chunk in await response:
                    content = chunk.choices[0].delta.content
                    if content is not None:
                        self.app.after(0, self.add_to_last_message, content)
                    if self.is_streaming_cancelled:
                        break
            except Exception as e:
                if "Incorrect API key" in str(e):
                    error_message = "API key is incorrect, please configure it in the settings."
                    loop.call_soon_threadsafe(self.show_error_and_open_settings, error_message)
                elif "No such organization" in str(e):
                    error_message = "Organization not found, please configure it in the settings."
                    loop.call_soon_threadsafe(self.show_error_and_open_settings, error_message)
                else:
                    error_message = f"An unexpected error occurred: {e}"
                    loop.call_soon_threadsafe(self.show_error_popup, error_message)
            finally:
                response.close()
                print("Closed response")
            if not self.is_streaming_cancelled:
                self.app.after(0, self.add_empty_user_message)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(streaming_chat_completion())

    def stream_anthropic_model_output(self, messages, system_message):
        if self.config.get("anthropic", "api_key", fallback="") == "":
            error_message = "Anthropic API key is not configured. Please configure it in the settings."
            self.show_error_and_open_settings(error_message)
            return
        if not self.anthropic_client:
            error_message = "Anthropic API not installed. Please install the 'anthropic' package with the `pip install anthropic` command."
            self.show_error_popup(error_message)
            return
        async def streaming_anthropic_chat_completion():
            with self.anthropic_client.messages.stream(
                    model=self.model_var.get(),
                    max_tokens=min(self.max_length_var.get(), 4000), # 4000 is the max tokens for anthropic
                    messages=messages,
                    system=system_message.strip(),
                    temperature=self.temperature_var.get()
                ) as stream:
                try:
                    for text in stream.text_stream:
                        self.app.after(0, self.add_to_last_message, text)
                        if self.is_streaming_cancelled:
                            break
                except Exception as e:
                    error_message = f"An unexpected error occurred: {e}"
                    loop.call_soon_threadsafe(self.show_error_popup, error_message)
                finally:
                    stream.close()
            if not self.is_streaming_cancelled:
                self.app.after(0, self.add_empty_user_message)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(streaming_anthropic_chat_completion())

    def stream_google_model_output(self, messages):
        if self.config.get("google", "api_key", fallback="") == "":
            error_message = "Google API key is not configured. Please configure it in the settings."
            self.show_error_and_open_settings(error_message)
            return
        try:
            import google.generativeai as genai
        except:
            error_message = "Google GenerativeAI API not installed. If you wish to use Google Gemini models, install the 'google-generativeai' package with the `pip install google-generativeai` command."
            self.show_error_popup(error_message)
            return
        async def streaming_google_chat_completion():
            try:
                google_model = genai.GenerativeModel(self.model_var.get(), 
                                    generation_config={"temperature": self.temperature_var.get(), 
                                                        "max_output_tokens": self.max_length_var.get()})
                response = google_model.generate_content(messages, stream=True)
            except Exception as e:
                error_message = "Error: " + str(e)
                self.show_error_popup(error_message)
                return
            try:
                for chunk in response:
                    self.app.after(0, self.add_to_last_message, chunk.parts[0].text)
                    if self.is_streaming_cancelled:
                        break
            except Exception as e:
                error_message = f"An unexpected error occurred: {e}"
                loop.call_soon_threadsafe(self.show_error_popup, error_message)
            finally:
                response.resolve()
            if not self.is_streaming_cancelled:
                self.app.after(0, self.add_empty_user_message)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(streaming_google_chat_completion())

    def update_chat_file_dropdown(self, new_file_path):
        # Refresh the list of chat files from the directory
        self.chat_files = sorted(
            [f for f in os.listdir("chat_logs") if os.path.isfile(os.path.join("chat_logs", f)) and f.endswith('.json')],
            key=lambda x: os.path.getmtime(os.path.join("chat_logs", x)),
            reverse=True
        )

        new_file_name = os.path.basename(new_file_path)

        # Check if the new file name is already in the list of chat files
        if new_file_name not in self.chat_files:
            self.chat_files.insert(0, new_file_name)  # Insert the file at the beginning if it's not there

        self.chat_filename_var.set(new_file_name)  # Select the newly created log

        # Clear and repopulate the dropdown menu with the refreshed list of files
        menu = self.chat_file_dropdown["menu"]
        menu.delete(0, "end")
        menu.add_command(label="<new-log>", command=lambda value="<new-log>": self.chat_filename_var.set(value))
        for file in self.chat_files:
            menu.add_command(label=file, command=lambda value=file: self.chat_filename_var.set(value))

    def update_models_dropdown(self):
        # Update the model dropdown menu with available models
        current_model = self.model_var.get()
        anthropic_models = ANTHROPIC_MODELS if "anthropic" in sys.modules and self.anthropic_apikey_var.get() else []
        google_models = GOOGLE_MODELS if "google.generativeai" in sys.modules and self.google_apikey_var.get() else []
        openai_models = OPENAI_MODELS if "openai" in sys.modules and self.openai_apikey_var.get() else []
        custom_models = [model for server in self.custom_servers for model in server.models]
        possible_models = [*openai_models, *anthropic_models, *google_models, *custom_models]
        ttk.OptionMenu(self.main_frame, self.model_var, current_model, *possible_models).grid(row=0, column=7, sticky="nw")
        # add separators to the dropdown menu
        dropdown_menu = self.main_frame.winfo_children()[len(self.main_frame.children)-1]['menu']
        sep = -1
        if openai_models:
            sep+=len(openai_models)+1
            dropdown_menu.insert_separator(sep)
        if anthropic_models:
            sep+=len(anthropic_models)+1
            dropdown_menu.insert_separator(sep)
        if google_models:
            sep+=len(google_models)+1
            dropdown_menu.insert_separator(sep)
        for server in self.custom_servers:
            sep += len(server.models)+1
            dropdown_menu.insert_separator(sep)

    def load_chat_history(self):
        filename = self.chat_filename_var.get()

        if not filename or filename == "<new-log>":
            self.clear_chat_history()
            self.system_message_widget.delete("1.0", tk.END)
            self.system_message_widget.insert(tk.END, SYSTEM_MESSAGE_DEFAULT_TEXT)
            self.add_message("user", "")
            return

        filepath = os.path.join("chat_logs", filename)
        if os.path.exists(filepath) and filepath.endswith('.json'):
            with open(filepath, "r", encoding='utf-8') as f:
                chat_data = json.load(f)

            self.clear_chat_history()

            system_message = chat_data["system_message"]
            self.system_message_widget.delete("1.0", tk.END)
            self.system_message_widget.insert(tk.END, system_message)

            for entry in chat_data["chat_history"]:
                self.add_message(entry["role"], entry["content"])

        self.app.after(100, self.update_height_of_all_messages)


    def update_height_of_all_messages(self):
        for message in self.chat_history:
            self.update_content_height(None, message["content_widget"])

    def add_to_last_message(self, content):
        last_message = self.chat_history[-1]
        if last_message["role"].get() == "assistant":
            last_message["content_widget"].insert(tk.END, content)
            self.update_content_height(None, last_message["content_widget"])
        else:
            self.add_message("assistant", content)

    def cancel_streaming(self):
        self.is_streaming_cancelled = True
        self.set_submit_button(True)

    def add_empty_user_message(self):
        self.add_message("user", "")
        self.set_submit_button(True)

    # Hack. Not sure why the message entries don't just scale to fit the canvas automatically
    def update_entry_widths(self, event=None):
        window_width = self.app.winfo_width()
        screen_width = self.app.winfo_screenwidth()
        dpi = self.app.winfo_fpixels('1i')
        if sys.platform == 'darwin':
            scaling_factor = 0.09 * (96/dpi)
        elif os.name == 'posix':
            scaling_factor = 0.08 * (96/dpi)
        else:
            scaling_factor = 0.12 * (96/dpi)
        # Calculate the new width of the Text widgets based on the window width
        new_entry_width = int((window_width - scaling_factor*1000) * scaling_factor)

        for message in self.chat_history:
            message["content_widget"].configure(width=new_entry_width)


    def update_content_height(self, event, content_widget):
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

    def add_message(self, role="user", content=""):
        message = {
            "role": tk.StringVar(value=role),
            "content": tk.StringVar(value=content)
        }
        self.chat_history.append(message)

        row = len(self.chat_history)
        message["role_button"] = ttk.Button(self.inner_frame, textvariable=message["role"], command=lambda: self.toggle_role(message), width=8)
        message["role_button"].grid(row=row, column=0, sticky="nw")
        message["content_widget"] = tk.Text(self.inner_frame, wrap=tk.WORD, height=1, width=50, undo=True)
        message["content_widget"].grid(row=row, column=1, sticky="we")
        message["content_widget"].insert(tk.END, content)
        message["content_widget"].bind("<KeyRelease>", lambda event, content_widget=message["content_widget"]: self.update_content_height(event, content_widget))
        self.update_content_height(None, message["content_widget"])

        self.add_button_row += 1
        self.align_add_button()

        message["delete_button"] = ttk.Button(self.inner_frame, text="-", width=3, command=lambda: self.delete_message(row))
        message["delete_button"].grid(row=row, column=2, sticky="ne")

        self.chat_frame.yview_moveto(1.5)

    def align_add_button(self):
        self.add_button.grid(row=self.add_button_row, column=0, sticky="e", pady=(5, 0))
        self.add_button_label.grid(row=self.add_button_row, column=1, sticky="sw")

    def delete_message(self, row):
        for widget in self.inner_frame.grid_slaves():
            if int(widget.grid_info()["row"]) == row:
                widget.destroy()

        del self.chat_history[row - 1]

        for i, message in enumerate(self.chat_history[row - 1:], start=row):
            for widget in self.inner_frame.grid_slaves():
                if int(widget.grid_info()["row"]) == i + 1:
                    widget.grid(row=i)

            message["delete_button"].config(command=lambda row=i: self.delete_message(row))

        self.add_button_row -= 1
        self.align_add_button()
        self.cancel_streaming()

    def toggle_role(self, message):
        current_role = message["role"].get()
        if current_role == "user":
            message["role"].set("assistant")
        elif current_role == "assistant":
            message["role"].set("system")
        else:
            message["role"].set("user")

    def set_submit_button(self, active):
        if active:
            self.submit_button_text.set("Submit")
            self.submit_button.configure(command=self.submit_chat_request)
        else:
            self.submit_button_text.set("Cancel")
            self.submit_button.configure(command=self.cancel_streaming)

    def configure_scrollregion(self, event):
        self.chat_frame.configure(scrollregion=self.chat_frame.bbox("all"))

    def add_message_via_button(self):
        self.add_message("user" if len(self.chat_history) == 0 or self.chat_history[-1]["role"].get() == "assistant" else "assistant", "")

    def update_image_detail_visibility(self, *args):
        if self.model_var.get() in OPENAI_VISION_MODELS:
            self.image_detail_dropdown.grid(row=0, column=8, sticky="ne")
        else:
            self.image_detail_dropdown.grid_remove()

    # Functions for synchronizing slider and entry
    def on_temp_entry_change(self, *args):
        try:
            value = float(self.temp_entry_var.get())
            if 0 <= value <= 1:
                self.temperature_var.set(value)
            else:
                raise ValueError
        except ValueError:
            self.temp_entry_var.set(f"{self.temperature_var.get():.2f}")

    def on_max_len_entry_change(self, *args):
        try:
            value = int(self.max_len_entry_var.get())
            if 1 <= value <= 8000:
               self.max_length_var.set(value)
            else:
                raise ValueError
        except ValueError:
            self.max_len_entry_var.set(self.max_length_var.get())

    def on_close(self):
        # Generate a timestamp string with the format "YYYYMMDD_HHMMSS"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Generate a random 6-character alphanumeric ID
        random_id = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        # Combine the timestamp and random ID to create the filename
        filename = f"{timestamp}_{random_id}.json"

        # Create the 'temp/backup/' directory if it doesn't exist
        backup_path = "temp/backup"
        if not os.path.exists(backup_path):
            os.makedirs(backup_path)

        # Construct the full file path
        file_path = os.path.join(backup_path, filename)

        # Get the chat history data
        chat_data = {
            "system_message": self.system_message_widget.get("1.0", tk.END).strip(),
            "chat_history": [
                {
                    "role": message["role"].get(),
                    "content": message["content_widget"].get("1.0", tk.END).strip()
                }
                for message in self.chat_history
            ]
        }

        # Save the chat history to the file
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump(chat_data, f, indent=4)

        # Save the last used model
        self.config.read("config.ini")
        self.config.set("app", "last_used_model", self.model_var.get())
        with open("config.ini", "w") as config_file:
            self.config.write(config_file)

        # Close the application
        self.app.destroy()

    def show_error_popup(self, message):
        error_popup = tk.Toplevel(self.app)
        error_popup.title("Error")
        error_popup.geometry("350x100")

        error_label = ttk.Label(error_popup, text=message, wraplength=300)
        error_label.pack(padx=20, pady=20)

        error_popup.focus_force()
        self.center_popup_over_chat_window(error_popup, self.app, 0, -150)

    def show_error_and_open_settings(self, message):
        if self.settings_window is not None:
            self.settings_window.focus_force()
        else:
            self.toggle_settings_window()
        self.show_error_popup(message)

    def show_token_count_message(self):
        messages = self.get_messages_from_chat_history()
        num_input_tokens = count_tokens(messages, self.model_var.get())
        num_output_tokens = self.max_length_var.get()
        total_tokens = num_input_tokens + num_output_tokens
        model = self.model_var.get()

        # Calculate input and output costs for non-vision models
        input_cost = MODEL_INFO[model]["input_price"] * num_input_tokens / 1000 if model in MODEL_INFO else 0
        output_cost = MODEL_INFO[model]["output_price"] * num_output_tokens / 1000 if model in MODEL_INFO else 0
        total_cost = input_cost + output_cost
        cost_message = f"Input Cost: ${input_cost:.5f}\nOutput Cost: ${output_cost:.5f}"

        if model in OPENAI_VISION_MODELS:
            # Count the number of images in the messages
            num_images = 0
            parsed_messages = [parse_and_create_image_messages(message.get("content",""), self.image_detail_var.get()) for message in messages]
            for message in parsed_messages:
                for content in message["content"]:
                    if "image_url" in content.get("type", ""):
                        num_images+=1

            # Calculate vision cost if the model is vision preview
            vision_cost = 0
            if self.image_detail_var.get() == "low":
                vision_cost = LOW_DETAIL_COST_PER_IMAGE * num_images * (0.5 if model == 'gpt-4o' else 1)
            else:
                # Estimated cost for high detail images
                vision_cost = HIGH_DETAIL_COST_PER_IMAGE * num_images * (0.5 if model == 'gpt-4o' else 1)
            total_cost = vision_cost
            cost_message += f"\nVision Cost: ${total_cost:.5f} for {num_images} images"

        messagebox.showinfo("Token Count and Cost", f"Number of tokens: {total_tokens} (Input: {num_input_tokens}, Output: {num_output_tokens})\n{cost_message}")

    def on_config_changed(self, *args):
        self.save_api_key()

    def save_api_key(self):
        if self.openai_apikey_var.get() != "":
            self.config.set("openai", "api_key", self.openai_apikey_var.get())
            self.config.set("openai", "organization", self.openai_orgid_var.get())
            self.setup_openai_client()
        if self.anthropic_apikey_var.get() != "":
            self.config.set("anthropic", "api_key", self.anthropic_apikey_var.get())
            self.setup_anthropic_client()
        if self.google_apikey_var.get() != "":
            self.config.set("google", "api_key", self.google_apikey_var.get())
            self.setup_google_client()
        for i, custom_server in enumerate(self.custom_servers):
            if not self.config.has_section(f"custom_server_{i}"):
                self.config.add_section(f"custom_server_{i}")
            if custom_server.baseurl_var.get() != "":
                custom_server.update_client()
                self.config.set(f"custom_server_{i}", "base_url", str(custom_server.baseurl_var.get()))
                self.config.set(f"custom_server_{i}", "api_key", str(custom_server.apikey_var.get()))
            if custom_server.models_var.get() != "":
                custom_server.update_models()
                self.config.set(f"custom_server_{i}", "models", custom_server.models_var.get())

        self.config.set("app", "file_naming_model", self.file_naming_model_var.get())
        self.update_models_dropdown()

        with open("config.ini", "w") as config_file:
            self.config.write(config_file)

    def save_dark_mode_state(self):
        self.config.set("app", "dark_mode", str(self.dark_mode_var.get()))
        with open("config.ini", "w") as f:
            self.config.write(f)

    def load_dark_mode_state(self):
        return self.config.getboolean("app", "dark_mode", fallback=False)

    def toggle_dark_mode(self):
        if self.dark_mode_var.get():
            self.app.configure(bg="#2c2c2c")
            self.main_frame.configure(style="Dark.TFrame")
            self.configuration_frame.configure(style="Dark.TFrame")
            self.chat_frame.configure(bg="#2c2c2c") # Change chat_frame background color
            self.inner_frame.configure(style="Dark.TFrame")

            for widget in self.main_frame.winfo_children():
                if isinstance(widget, (ttk.Label, ttk.OptionMenu, ttk.Checkbutton)):
                    widget.configure(style="Dark." + widget.winfo_class())
            for widget in self.configuration_frame.winfo_children():
                if isinstance(widget, (ttk.Label, ttk.OptionMenu, ttk.Checkbutton)):
                    widget.configure(style="Dark." + widget.winfo_class())
            if self.settings_frame is not None:
                self.settings_frame.configure(style="Dark.TFrame")
                for widget in self.settings_frame.winfo_children():
                    if isinstance(widget, (ttk.Label, ttk.OptionMenu, ttk.Checkbutton)):
                        widget.configure(style="Dark." + widget.winfo_class())
        else:
            self.app.configure(bg=self.default_bg_color)
            self.main_frame.configure(style="")
            self.configuration_frame.configure(style="")
            self.chat_frame.configure(bg=self.default_bg_color) # Reset chat_frame background color
            self.inner_frame.configure(style="")

            for widget in self.main_frame.winfo_children():
                if isinstance(widget, (ttk.Label, ttk.Button, ttk.OptionMenu, ttk.Checkbutton, ttk.Scrollbar)):
                    widget.configure(style=widget.winfo_class())
            for widget in self.configuration_frame.winfo_children():
                if isinstance(widget, (ttk.Label, ttk.Button, ttk.OptionMenu, ttk.Checkbutton, ttk.Scrollbar)):
                    widget.configure(style=widget.winfo_class())
            if self.settings_frame is not None:
                self.settings_frame.configure(style="")
                for widget in self.settings_frame.winfo_children():
                    if isinstance(widget, (ttk.Label, ttk.Button, ttk.OptionMenu, ttk.Checkbutton, ttk.Scrollbar)):
                        widget.configure(style=widget.winfo_class())
        self.save_dark_mode_state()

    def get_default_bg_color(self, root):
        # Create a temporary button widget to get the default background color
        temp_button = tk.Button(root)
        default_bg_color = temp_button.cget('bg')
        # Destroy the temporary button
        temp_button.destroy()
        return default_bg_color
    
    def add_new_custom_server(self):
        new_custom_server = CustomServer("", "", "", [], on_config_changed=lambda *args: self.on_config_changed())
        self.custom_servers.append(new_custom_server)
        self.save_api_key()
        self.toggle_settings_window()
        self.toggle_settings_window()
    def remove_last_custom_server(self):
        if len(self.custom_servers) > 0:
            self.config.remove_section(f"custom_server_{len(self.custom_servers)-1}")
            self.config.write(open("config.ini", "w"))
            self.custom_servers.pop()
        self.save_api_key()
        self.toggle_settings_window()
        self.toggle_settings_window()

    def toggle_settings_window(self):
        # If the settings window already exists, close it and set our settings window to None
        if self.settings_window is not None:
            self.settings_window.destroy()
            self.settings_window = None
            return

        self.settings_window = tk.Toplevel(self.app)
        self.settings_window.title("Settings")
        self.settings_frame = ttk.Frame(self.settings_window, padding="3")
        self.settings_frame.grid(row=0, column=0, sticky="new")

        # Create a Checkbutton widget for dark mode toggle
        self.dark_mode_var.set(self.load_dark_mode_state())
        dark_mode_checkbutton = ttk.Checkbutton(self.settings_frame, text="Dark mode", variable=self.dark_mode_var, command=self.toggle_dark_mode)
        dark_mode_checkbutton.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        self.toggle_dark_mode()

        # Add API key / Org ID configurations
        ttk.Label(self.settings_frame, text="OpenAI API Key:").grid(row=1, column=0, sticky="e")
        openai_apikey_entry = ttk.Entry(self.settings_frame, textvariable=self.openai_apikey_var, width=60)
        openai_apikey_entry.grid(row=1, column=1, sticky="e")

        ttk.Label(self.settings_frame, text="OpenAI Org ID:").grid(row=2, column=0, sticky="e")
        openai_orgid_entry = ttk.Entry(self.settings_frame, textvariable=self.openai_orgid_var, width=60)
        openai_orgid_entry.grid(row=2, column=1, sticky="e")

        # Add Anthropic API key configuration
        ttk.Label(self.settings_frame, text="Anthropic API Key:").grid(row=3, column=0, sticky="e")
        anthropic_apikey_entry = ttk.Entry(self.settings_frame, textvariable=self.anthropic_apikey_var, width=60)
        anthropic_apikey_entry.grid(row=3, column=1, sticky="e")
        # Add Google API key configuration
        ttk.Label(self.settings_frame, text="Google API Key:").grid(row=4, column=0, sticky="e")
        google_apikey_entry = ttk.Entry(self.settings_frame, textvariable=self.google_apikey_var, width=60)
        google_apikey_entry.grid(row=4, column=1, sticky="e")

        # Add file naming model configuration
        ttk.Label(self.settings_frame, text="File Naming Model (OpenAI only):").grid(row=5, column=0, sticky="e")
        file_naming_model_entry = ttk.Entry(self.settings_frame, textvariable=self.file_naming_model_var, width=60)
        file_naming_model_entry.grid(row=5, column=1, sticky="e")

        # Add Custom Server configuration
        cur_row = 6
        for i, custom_server in enumerate(self.custom_servers):
            ttk.Separator(self.settings_frame, orient='horizontal').grid(row=cur_row, column=0, columnspan=2, sticky="we", pady=10)
            ttk.Label(self.settings_frame, text=f"Custom Server {i+1} Configuration").grid(row=cur_row+1, column=0, sticky="e")
            ttk.Label(self.settings_frame, text="Base URL:").grid(row=cur_row+2, column=0, sticky="e")
            custom_baseurl_entry = ttk.Entry(self.settings_frame, textvariable=custom_server.baseurl_var, width=60)
            custom_baseurl_entry.grid(row=cur_row+2, column=1, sticky="e")
            ttk.Label(self.settings_frame, text="API Key:").grid(row=cur_row+3, column=0, sticky="e")
            custom_apikey_entry = ttk.Entry(self.settings_frame, textvariable=custom_server.apikey_var, width=60)
            custom_apikey_entry.grid(row=cur_row+3, column=1, sticky="e")
            ttk.Label(self.settings_frame, text="Models (comma-separated):").grid(row=cur_row+4, column=0, sticky="e")
            custom_models_entry = ttk.Entry(self.settings_frame, textvariable=custom_server.models_var, width=60)
            custom_models_entry.grid(row=cur_row+4, column=1, sticky="e")
            cur_row += 5
        
        # add a button to remove the last custom server
        remove_custom_server_button = ttk.Button(self.settings_frame, text="Remove Last Custom Server", command=self.remove_last_custom_server)
        remove_custom_server_button.grid(row=cur_row+1, column=1, columnspan=1, sticky="e")
        ttk.Separator(self.settings_frame, orient='horizontal').grid(row=cur_row+2, column=0, columnspan=2, sticky="we", pady=10)
        # add a button to add a new custom server
        add_custom_server_button = ttk.Button(self.settings_frame, text="Add Custom Server", command=self.add_new_custom_server)
        add_custom_server_button.grid(row=cur_row+3, column=0, columnspan=1, sticky="w")

        # Add a button to close the popup
        close_button = ttk.Button(self.settings_frame, text="Close", command=self.close_settings_window)
        close_button.grid(row=100, column=0, columnspan=2, pady=10)
        # Bind the on_popup_close function to the WM_DELETE_WINDOW protocol
        self.settings_window.protocol("WM_DELETE_WINDOW", self.on_settings_window_close)
        # Bind events for api/org clipboard prompts, only in Android
        if(self.os_name == 'Android'):
            openai_apikey_entry.bind("<Button-1>", lambda event, entry=openai_apikey_entry: self.prompt_paste_from_clipboard(event, entry))
            openai_orgid_entry.bind("<Button-1>", lambda event, entry=openai_orgid_entry: self.prompt_paste_from_clipboard(event, entry))
            openai_apikey_entry.bind("<FocusOut>", self.update_previous_focused_widget)
            openai_orgid_entry.bind("<FocusOut>", self.update_previous_focused_widget)

        # Center the popup over the main window
        self.center_popup_over_chat_window(self.settings_window, self.app)

        self.settings_window.focus_force()

    def on_settings_window_close(self):
        self.settings_window.destroy()
        self.settings_window = None

    def close_settings_window(self):
        if self.settings_window is not None:
            self.settings_window.destroy()
            self.settings_window = None

    def center_popup_over_chat_window(self, popup_window, main_window, x_offset=0, y_offset=0):
        main_window.update_idletasks()

        main_window_width = main_window.winfo_width()
        main_window_height = main_window.winfo_height()
        main_window_x = main_window.winfo_rootx()
        main_window_y = main_window.winfo_rooty()

        popup_width = popup_window.winfo_reqwidth()
        popup_height = popup_window.winfo_reqheight()

        x_position = main_window_x + (main_window_width // 2) - (popup_width // 2) + x_offset
        y_position = main_window_y + (main_window_height // 2) - (popup_height // 2) + y_offset

        popup_window.geometry(f"+{x_position}+{y_position}")

    def prompt_paste_from_clipboard(self, event, entry):
        # Check if the previously focused widget is the same as the clicked one
        if self.previous_focused_widget != entry:
            clipboard_content = self.app.clipboard_get()
            if messagebox.askyesno("Paste from Clipboard", f"Do you want to paste the following content from the clipboard?\n\n{clipboard_content}"):
                entry.delete(0, tk.END)
                entry.insert(0, clipboard_content)
        self.previous_focused_widget = entry

    def update_previous_focused_widget(self, event):
        self.previous_focused_widget = event.widget

    def create_new_window(self, event):
        # Handle key press event
        if event.state == 0x0004 and event.keysym == 'n':  # 0x0004 is the mask for the Control key on Windows/Linux
            new_root = tk.Toplevel(self.app)
            new_window = ChatWindow(new_root, self.config, self.os_name)