
SYSTEM_MESSAGE_DEFAULT_TEXT = ""
FILE_NAMING_MODEL="gpt-3.5-turbo" # if empty, won't name files automatically
OPENAI_MODELS = [
    "gpt-3.5-turbo",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-4-32k",
    "gpt-4-turbo-preview",
    "gpt-4-vision-preview",
    "gpt-4-0125-preview",
    "gpt-4-0613",
    "gpt-4-1106-preview",
    "gpt-3.5-turbo-16k",
    "gpt-3.5-turbo-0125",
    "gpt-3.5-turbo-0301",
    "gpt-3.5-turbo-0613",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-16k-0613",
]
ANTHROPIC_MODELS = [
    "claude-3-opus-20240229", 
    "claude-3-sonnet-20240229", 
    "claude-3-haiku-20240307", 
    "claude-2.1", 
    "claude-2.0", 
    "claude-instant-1.2"
]
OPENAI_VISION_MODELS = [
    'gpt-4-vision-preview', 
    'gpt-4-1106-vision-preview', 
    'gpt-4-turbo', 
    'gpt-4-turbo-2024-04-09',
]
MODEL_INFO = {
    "gpt-4-turbo": {"max_tokens": 128000, "input_price": 0.01, "output_price": 0.03},
    "gpt-4-turbo-2024-04-09": {"max_tokens": 128000, "input_price": 0.01, "output_price": 0.03},
    "gpt-4-0125-preview": {"max_tokens": 128000, "input_price": 0.01, "output_price": 0.03},
    "gpt-4-1106-preview": {"max_tokens": 128000, "input_price": 0.01, "output_price": 0.03},
    "gpt-4-1106-vision-preview": {"max_tokens": 128000, "input_price": 0.01, "output_price": 0.03},
    "gpt-4-vision-preview": {"max_tokens": 128000, "input_price": 0.01, "output_price": 0.03},
    "gpt-4": {"max_tokens": 8192, "input_price": 0.03, "output_price": 0.06},
    "gpt-4-0613": {"max_tokens": 8192, "input_price": 0.03, "output_price": 0.06},
    "gpt-4-0314": {"max_tokens": 8192, "input_price": 0.03, "output_price": 0.06},
    "gpt-4-32k": {"max_tokens": 32768, "input_price": 0.06, "output_price": 0.12},
    "gpt-3.5-turbo-0125": {"max_tokens": 16385, "input_price": 0.0005, "output_price": 0.0015},
    "gpt-3.5-turbo": {"max_tokens": 16385, "input_price": 0.0010, "output_price": 0.0020},
    "gpt-3.5-turbo-0613": {"max_tokens": 4096, "input_price": 0.0010, "output_price": 0.0020},
    "gpt-3.5-turbo-0301": {"max_tokens": 4096, "input_price": 0.0010, "output_price": 0.0020},
    "gpt-3.5-turbo-16k": {"max_tokens": 16384, "input_price": 0.0010, "output_price": 0.0020},
    "gpt-3.5-turbo-16k-0613": {"max_tokens": 16385, "input_price": 0.0010, "output_price": 0.0020},
    "gpt-3.5-turbo-1106": {"max_tokens": 16385, "input_price": 0.0010, "output_price": 0.0020},
    "gpt-3.5-turbo-instruct": {"max_tokens": 4096, "input_price": 0.0015, "output_price": 0.0020},
    "claude-3-opus-20240229": {"max_tokens": 128000, "input_price": 0.015, "output_price": 0.075},
    "claude-3-sonnet-20240229": {"max_tokens": 128000, "input_price": 0.003, "output_price": 0.015},
    "claude-3-haiku-20240307": {"max_tokens": 128000, "input_price": 0.00025, "output_price": 0.00125},
    "claude-2.1": {"max_tokens": 128000, "input_price": 0.008, "output_price": 0.024},
    "claude-2.0": {"max_tokens": 128000, "input_price": 0.008, "output_price": 0.024},
    "claude-instant-1.2": {"max_tokens": 128000, "input_price": 0.0008, "output_price": 0.0024},
}
# Estimation for high detail image cost based on a 1024x1024 image
# todo: get the actual image sizes for a more accurate estimation
HIGH_DETAIL_COST_PER_IMAGE = (170 * 4 + 85) / 1000 * 0.01  # 4 tiles for 1024x1024 + base tokens
# low detail images have a fixed cost
LOW_DETAIL_COST_PER_IMAGE = 0.00085
