from constants import OPENAI_VISION_MODELS, ANTHROPIC_MODELS
import re
import requests
import tiktoken

def count_tokens(messages, model):
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found for token counter. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if "gpt-3.5-turbo" in model:
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    else:
        tokens_per_message = 3
        tokens_per_name = 1
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens

def convert_text_to_tokens(text, model):
    """Converts some text to tokens using the appropriate encoding for the model."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found for token counter. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    return encoding.encode(text)

def convert_tokens_to_text(tokens, model):
    """Converts tokens to text using the appropriate decoding for the model."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found for token counter. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    return encoding.decode(tokens)

def is_url(str):
    url_pattern = r"https?://[^\s,\"\{\}]+"
    return re.match(url_pattern, str)

def is_image_url(url):
    if not is_url(url):
        return False
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.head(url, timeout=5, headers=headers)
        content_type = response.headers.get('Content-Type', '')
        return 'image' in content_type
    except requests.RequestException as e:
        return False

def parse_and_create_image_messages(content, image_detail):
    url_pattern = r"(https?://[^\s,\"\{\}]+)"
    parts = re.split(url_pattern, content)

    messages = []
    for text in parts:
        if is_image_url(text):
            messages.append({"type": "image_url", "image_url": {"url": text, "detail": image_detail}})
        elif messages and messages[-1].get("type") == "text":
            messages[-1]["text"] += text
        elif text:
            messages.append({"type": "text", "text": text})
    return {"role": "user", "content": messages}

def convert_messages_for_model(model, messages, image_detail="low"):
    if model in OPENAI_VISION_MODELS:
        # Update the messages to include image data if any image URLs are found in the user's input
        new_messages = []
        for message in messages:
            if message["role"] == "user" and "content" in message:
                # Check for image URLs and create a single message with a 'content' array
                message_with_images = parse_and_create_image_messages(message["content"], image_detail)
                new_messages.append(message_with_images)
            else:
                # System or assistant messages are added unchanged
                new_messages.append(message)
        return new_messages, None
    elif model in ANTHROPIC_MODELS:
        # Anthropic API has a bunch of extra requirements not present in OpenAI's API
        anthropic_messages = []
        system_content = ""
        for message in messages:
            if message["role"] == "system":
                system_content += message["content"] + "\n"
            elif message["content"]:
                anthropic_messages.append({"role": message["role"], "content": message["content"]})
        if len(anthropic_messages) == 0 or anthropic_messages[0]["role"] == "assistant":
            anthropic_messages.insert(0, {"role": "user", "content": "<no message>"})
        for i in range(len(anthropic_messages) - 1, 0, -1):
            if anthropic_messages[i]["role"] == anthropic_messages[i - 1]["role"]:
                anthropic_messages.insert(i, {"role": "user" if anthropic_messages[i]["role"] == "assistant" else "assistant", "content": "<no message>"})
        if anthropic_messages[-1]["role"] == "assistant":
            anthropic_messages.append({"role": "user", "content": "<no message>"})
        return anthropic_messages, system_content
    return messages, None