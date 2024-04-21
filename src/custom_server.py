
from openai import AsyncOpenAI
import tkinter as tk

class CustomServer:
    def __init__(self, base_url, api_key, org_id, models, on_config_changed):
        self.models = models
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key, organization=org_id)
        self.baseurl_var = tk.StringVar(value=self.client.base_url)
        self.apikey_var = tk.StringVar(value=self.client.api_key)
        self.models_var = tk.StringVar(value=", ".join(self.models))
        self.baseurl_var.trace("w", on_config_changed)
        self.apikey_var.trace("w", on_config_changed)
        self.models_var.trace("w", on_config_changed)