from constants import OPENAI_VISION_MODELS, OPENAI_REASONING_MODELS, ANTHROPIC_MODELS, GOOGLE_MODELS, ANTHROPIC_VISION_MODELS, GOOGLE_VISION_MODELS
import re
import requests
import tiktoken
import base64
import os

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
            if key == "local_images":
                continue  # Skip local_images field - not sent to API
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

def encode_image_to_base64(image_path):
    """Encode a local image file to base64 for API use"""
    try:
        with open(image_path, "rb") as image_file:
            encoded_data = base64.b64encode(image_file.read()).decode('utf-8')
            # Get MIME type based on file extension
            ext = os.path.splitext(image_path)[1].lower()
            mime_type = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg', 
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp',
                '.webp': 'image/webp'
            }.get(ext, 'image/jpeg')
            
            return f"data:{mime_type};base64,{encoded_data}"
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None

def parse_and_create_image_messages(content, image_detail, local_images=None):
    """Parse content with URLs and image placeholders, create proper message format"""
    if local_images is None:
        local_images = []
    
    # First handle local image placeholders like [image #0]
    image_placeholder_pattern = r"\[image #(\d+)\]"
    
    # Replace image placeholders with their base64 data URLs
    def replace_placeholder(match):
        image_index = int(match.group(1))
        if image_index < len(local_images):
            base64_url = encode_image_to_base64(local_images[image_index])
            if base64_url:
                return f"LOCAL_IMAGE:{base64_url}"
        return match.group(0)  # Return original if can't process
    
    content_with_local = re.sub(image_placeholder_pattern, replace_placeholder, content)
    
    # Now handle both URLs and local images
    url_pattern = r"(https?://[^\s,\"\{\}]+|LOCAL_IMAGE:data:[^,]+;base64,[A-Za-z0-9+/=]+)"
    parts = re.split(url_pattern, content_with_local)

    messages = []
    for text in parts:
        if text.startswith("LOCAL_IMAGE:"):
            # Handle local base64 image
            base64_url = text[12:]  # Remove "LOCAL_IMAGE:" prefix
            messages.append({"type": "image_url", "image_url": {"url": base64_url, "detail": image_detail}})
        elif is_image_url(text):
            # Handle remote URL image
            messages.append({"type": "image_url", "image_url": {"url": text, "detail": image_detail}})
        elif messages and messages[-1].get("type") == "text":
            messages[-1]["text"] += text
        elif text:
            messages.append({"type": "text", "text": text})
    return {"role": "user", "content": messages}

def parse_and_create_image_messages_legacy(content, image_detail):
    """Legacy function for backwards compatibility"""
    return parse_and_create_image_messages(content, image_detail)

def _convert_image_url_to_part(image_url):
    """Convert image URL to Google GenAI Part object"""
    try:
        from google.genai import types
        
        if image_url.startswith("data:"):
            # Handle base64 encoded images
            parts = image_url.split(";base64,", 1)
            if len(parts) == 2:
                mime_type = parts[0].replace("data:", "")
                base64_data = parts[1]
                
                import base64
                image_bytes = base64.b64decode(base64_data)
                return types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        else:
            # Handle URL images - fetch and convert
            import requests
            response = requests.get(image_url, timeout=10)
            if response.status_code == 200:
                # Get MIME type from response headers or guess from URL
                mime_type = response.headers.get('content-type')
                if not mime_type:
                    # Guess from URL extension
                    if image_url.lower().endswith('.jpg') or image_url.lower().endswith('.jpeg'):
                        mime_type = 'image/jpeg'
                    elif image_url.lower().endswith('.png'):
                        mime_type = 'image/png'
                    elif image_url.lower().endswith('.gif'):
                        mime_type = 'image/gif'
                    elif image_url.lower().endswith('.webp'):
                        mime_type = 'image/webp'
                    else:
                        mime_type = 'image/jpeg'  # Default fallback
                
                return types.Part.from_bytes(data=response.content, mime_type=mime_type)
    except Exception as e:
        print(f"Error converting image URL to Part: {e}")
        return None
    
    return None

def convert_messages_for_google(messages):
    """Convert messages to Google GenAI format using proper types"""
    try:
        from google.genai import types
    except ImportError:
        # Fallback to dict format if types not available
        return _convert_messages_for_google_dict(messages)
    
    system_texts = []
    contents = []
    
    for message in messages:
        role = message["role"]
        content = message.get("content", "")
        
        if role == "system":
            system_texts.append(content)
        elif role == "user":
            # Handle text content
            if isinstance(content, str):
                contents.append(types.Content(role="user", parts=[types.Part(text=content)]))
            else:
                # Handle complex content (images + text)
                parts = []
                
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                parts.append(types.Part(text=item.get("text", "")))
                            elif item.get("type") == "image_url":
                                # Handle image URLs - convert to bytes for Gemini
                                image_url = item.get("image_url", {}).get("url", "")
                                if image_url:
                                    try:
                                        image_part = _convert_image_url_to_part(image_url)
                                        if image_part:
                                            parts.append(image_part)
                                    except Exception as e:
                                        print(f"Error processing image for Gemini: {e}")
                                        # Skip the image and continue
                else:
                    # Fallback for non-list content
                    text_content = str(content)
                    parts.append(types.Part(text=text_content))
                
                # Only add if we have parts
                if parts:
                    contents.append(types.Content(role="user", parts=parts))
                else:
                    contents.append(types.Content(role="user", parts=[types.Part(text="")]))
        elif role == "assistant":
            # Convert assistant to model role
            if isinstance(content, str):
                contents.append(types.Content(role="model", parts=[types.Part(text=content)]))
            else:
                # Handle complex content - extract text for now
                text_content = ""
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_content += item.get("text", "")
                else:
                    text_content = str(content)
                contents.append(types.Content(role="model", parts=[types.Part(text=text_content)]))
    
    # Create config with system instruction if we have system messages
    config = None
    if system_texts:
        system_instruction = "\n".join(system_texts)
        config = types.GenerateContentConfig(system_instruction=system_instruction)
    
    return contents, config

def _convert_messages_for_google_dict(messages):
    """Fallback conversion to dict format"""
    google_messages = []
    
    for message in messages:
        role = message["role"]
        content = message.get("content", "")
        
        # Skip system messages for fallback
        if role == "system":
            continue
            
        # Convert role names
        if role == "assistant":
            role = "model"
        elif role == "user":
            role = "user"
        
        # Convert content to Google format
        if isinstance(content, str):
            google_messages.append({
                "role": role,
                "parts": [{"text": content}]
            })
        else:
            # Handle complex content - extract text
            text_content = ""
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_content += item.get("text", "")
            else:
                text_content = str(content)
            
            google_messages.append({
                "role": role,
                "parts": [{"text": text_content}]
            })
    
    return google_messages, None

def convert_messages_for_model(model, messages, image_detail="low"):
    if model in OPENAI_REASONING_MODELS:
        # Reasoning models do not support system messages in this chat-completions path,
        # but several of them also support vision and still need image payload conversion.
        new_messages = []
        for message in messages:
            role = message["role"]
            if message["role"] == "system":
                role = "user"

            if (
                role == "user"
                and model in OPENAI_VISION_MODELS
                and image_detail != "none"
                and "content" in message
            ):
                local_images = message.get("local_images", [])
                message_with_images = parse_and_create_image_messages(message["content"], image_detail, local_images)
                message_with_images["role"] = role
                new_messages.append(message_with_images)
            else:
                clean_message = {k: v for k, v in message.items() if k != "local_images"}
                clean_message["role"] = role
                new_messages.append(clean_message)
        return new_messages, None
    elif model in OPENAI_VISION_MODELS and image_detail != "none":
        # Update the messages to include image data if any image URLs are found in the user's input
        new_messages = []
        for message in messages:
            if message["role"] == "user" and "content" in message:
                # Get local images for this message
                local_images = message.get("local_images", [])
                # Check for image URLs and local images, create a single message with a 'content' array
                message_with_images = parse_and_create_image_messages(message["content"], image_detail, local_images)
                new_messages.append(message_with_images)
            else:
                # System or assistant messages are added unchanged (remove local_images field if present)
                clean_message = {k: v for k, v in message.items() if k != "local_images"}
                new_messages.append(clean_message)
        return new_messages, None
    elif model in ANTHROPIC_MODELS:
        # Anthropic API has a bunch of extra requirements not present in OpenAI's API
        anthropic_messages = []
        system_content = ""
        for message in messages:
            if message["role"] == "system":
                system_content += message["content"] + "\n"
            elif message["content"]:
                # Handle vision models
                if model in ANTHROPIC_VISION_MODELS and message["role"] == "user" and image_detail != "none":
                    local_images = message.get("local_images", [])
                    # Parse content for URLs and local images
                    parsed_message = parse_and_create_image_messages(message["content"], image_detail, local_images)
                    # Convert to Anthropic format
                    anthropic_content = []
                    for content_item in parsed_message["content"]:
                        if content_item["type"] == "text":
                            anthropic_content.append({"type": "text", "text": content_item["text"]})
                        elif content_item["type"] == "image_url":
                            url = content_item["image_url"]["url"]
                            if url.startswith("data:"):
                                # Extract base64 data
                                media_type, base64_data = url.split(";base64,", 1)
                                media_type = media_type.replace("data:", "")
                                anthropic_content.append({
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": base64_data
                                    }
                                })
                            else:
                                # For URL images, we need to fetch and convert to base64
                                # This is a limitation - Anthropic doesn't support URL images directly
                                try:
                                    response = requests.get(url, timeout=10)
                                    if response.status_code == 200:
                                        base64_data = base64.b64encode(response.content).decode('utf-8')
                                        # Guess media type from response headers or URL
                                        media_type = response.headers.get('content-type', 'image/jpeg')
                                        anthropic_content.append({
                                            "type": "image",
                                            "source": {
                                                "type": "base64",
                                                "media_type": media_type,
                                                "data": base64_data
                                            }
                                        })
                                except:
                                    # If we can't fetch the image, skip it
                                    pass
                    anthropic_messages.append({"role": message["role"], "content": anthropic_content})
                else:
                    # Non-vision message or non-user message
                    clean_message = {k: v for k, v in message.items() if k != "local_images"}
                    anthropic_messages.append({"role": clean_message["role"], "content": clean_message["content"]})
        if len(anthropic_messages) == 0 or anthropic_messages[0]["role"] == "assistant":
            anthropic_messages.insert(0, {"role": "user", "content": "<no message>"})
        return anthropic_messages, system_content
    elif model in GOOGLE_MODELS:
        # For Google vision models, convert to the expected format with image URLs
        if model in GOOGLE_VISION_MODELS and image_detail != "none":
            new_messages = []
            for message in messages:
                if message["role"] == "user" and "content" in message:
                    # Get local images for this message
                    local_images = message.get("local_images", [])
                    # Check for image URLs and local images, create message with content array
                    message_with_images = parse_and_create_image_messages(message["content"], image_detail, local_images)
                    new_messages.append(message_with_images)
                else:
                    # System or assistant messages are added unchanged (remove local_images field if present)
                    clean_message = {k: v for k, v in message.items() if k != "local_images"}
                    new_messages.append(clean_message)
            return new_messages, None
        else:
            # For non-vision Google models, just return messages unchanged
            return messages, None
    # Clean up local_images field for non-vision models
    clean_messages = []
    for message in messages:
        clean_message = {k: v for k, v in message.items() if k != "local_images"}
        clean_messages.append(clean_message)
    return clean_messages, None
