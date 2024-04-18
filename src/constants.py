
system_message_default_text = ""
vision_models = [
    'gpt-4-vision-preview', 
    'gpt-4-1106-vision-preview', 
    'gpt-4-turbo', 
    'gpt-4-turbo-2024-04-09',
]
openai_models = [
    "gpt-3.5-turbo",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-4-32k",
    "gpt-4-turbo-preview",
    "gpt-4-vision-preview",
    "gpt-4-0125-preview",
    "gpt-4-0613",
    "gpt-4-1106-preview",
    "gpt-4-1106-vision-preview",
    "gpt-3.5-turbo-16k",
    "gpt-3.5-turbo-0125",
    "gpt-3.5-turbo-0301",
    "gpt-3.5-turbo-0613",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-16k-0613",
]
anthropic_models = [
    "claude-3-opus-20240229", 
    "claude-3-sonnet-20240229", 
    "claude-3-haiku-20240307", 
    "claude-2.1", 
    "claude-2.0", 
    "claude-instant-1.2"
]
pricing_info = {
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4-turbo-2024-04-09": {"input": 0.01, "output": 0.03},
    "gpt-4-0125-preview": {"input": 0.01, "output": 0.03},
    "gpt-4-1106-preview": {"input": 0.01, "output": 0.03},
    "gpt-4-1106-vision-preview": {"input": 0.01, "output": 0.03},
    "gpt-4-vision-preview": {"input": 0.01, "output": 0.03},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-0613": {"input": 0.03, "output": 0.06},
    "gpt-4-0314": {"input": 0.03, "output": 0.06},
    "gpt-4-32k": {"input": 0.06, "output": 0.12},
    "gpt-3.5-turbo-0125": {"input": 0.0005, "output": 0.0015},
    "gpt-3.5-turbo": {"input": 0.0010, "output": 0.0020},
    "gpt-3.5-turbo-0613": {"input": 0.0010, "output": 0.0020},
    "gpt-3.5-turbo-0301": {"input": 0.0010, "output": 0.0020},
    "gpt-3.5-turbo-16k": {"input": 0.0010, "output": 0.0020},
    "gpt-3.5-turbo-1106": {"input": 0.0010, "output": 0.0020},
    "gpt-3.5-turbo-instruct": {"input": 0.0015, "output": 0.0020},
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    "claude-2.1": {"input": 0.008, "output": 0.024},
    "claude-2.0": {"input": 0.008, "output": 0.024},
    "claude-instant-1.2": {"input": 0.0008, "output": 0.0024},
}
# Estimation for high detail image cost based on a 1024x1024 image
# todo: get the actual image sizes for a more accurate estimation
high_detail_cost_per_image = (170 * 4 + 85) / 1000 * 0.01  # 4 tiles for 1024x1024 + base tokens
# low detail images have a fixed cost
low_detail_cost_per_image = 0.00085