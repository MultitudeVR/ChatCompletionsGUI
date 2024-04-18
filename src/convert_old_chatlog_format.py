"""
Conversion Script for Chat Logs

Purpose:
This script is designed to convert chat logs from a custom text format to a JSON format. It is part of a migration process to standardize chat log storage for improved maintainability and future-proofing.

Description:
The script processes chat logs that contain messages from a system, users, and an assistant. The first system message in each log is treated as a special case and is stored separately, while subsequent system messages are kept within the chat history along with user and assistant messages.

Usage:
Place this script in the root directory where the 'chat_logs' folder is located. It will recursively search for all '.txt' files within 'chat_logs', convert them to '.json' format, and save the results in a new folder called 'new_chat_logs'. The original folder structure within 'chat_logs' is preserved in the 'new_chat_logs' folder.

Error Handling:
During conversion, if any file fails to process, the script will log the error message and the filename to 'conversion_errors.log' and continue processing the rest of the files. This ensures that a single error does not halt the entire conversion process.

Output:
Each JSON file will contain a 'system_message' key for the first system message and a 'chat_history' key with an array of all other messages. Each message in the 'chat_history' array is an object containing 'role' and 'content' keys.

Note:
Ensure that you have a backup of the original 'chat_logs' directory before running this script, as the conversion process is not reversible.
"""

import json
import os
import traceback

old_chat_logs_dir = "chat_logs"
new_chat_logs_dir = "new_chat_logs"
error_log_file = "conversion_errors.log"

def clean_content(content):
    return content.rstrip("\n\"")

def convert_file(old_file_path, new_file_path):
    with open(old_file_path, "r", encoding='utf-8') as f:
        lines = f.readlines()

    chat_data = {"system_message": "", "chat_history": []}
    current_entry = None
    first_system = True

    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith(('system: "', 'user: "', 'assistant: "')):
            if current_entry is not None:
                # Finalize the current entry before starting the new one
                current_entry["content"] = clean_content(current_entry["content"])
                chat_data["chat_history"].append(current_entry)
            role, content = stripped_line.split(': "', 1)
            current_entry = {"role": role, "content": content}
            if role == "system" and first_system:
                # Handle the first system message differently
                chat_data["system_message"] = clean_content(content)
                current_entry = None
                first_system = False
        else:
            # Continuation of the current message content
            if current_entry is not None:
                current_entry["content"] += line

    # Don't forget to add the last message if present
    if current_entry is not None:
        current_entry["content"] = clean_content(current_entry["content"])
        chat_data["chat_history"].append(current_entry)

    with open(new_file_path, "w", encoding='utf-8') as f:
        json.dump(chat_data, f, indent=4)

def convert_directory(directory):
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.txt'):
                old_file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(old_file_path, old_chat_logs_dir)
                new_file_path = os.path.join(new_chat_logs_dir, relative_path.replace('.txt', '.json'))
                new_file_dir = os.path.dirname(new_file_path)

                if not os.path.exists(new_file_dir):
                    os.makedirs(new_file_dir)

                try:
                    convert_file(old_file_path, new_file_path)
                except Exception as e:
                    error_message = f"Failed to convert {old_file_path}: {e}"
                    print(error_message)
                    with open(error_log_file, "a", encoding='utf-8') as error_log:
                        error_log.write(f"{error_message}\n{traceback.format_exc()}\n")

if not os.path.exists(new_chat_logs_dir):
    os.makedirs(new_chat_logs_dir)

convert_directory(old_chat_logs_dir)

print("Conversion complete. Check 'conversion_errors.log' for any errors.")