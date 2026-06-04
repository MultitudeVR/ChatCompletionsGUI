import tkinter as tk

class CustomServer:
    def __init__(self, base_url, api_key, org_id, models, on_config_changed, initialize_client=True):
        self.models = models
        self.baseurl_var = tk.StringVar(value=base_url)
        self.apikey_var = tk.StringVar(value=api_key)
        self.models_var = tk.StringVar(value=", ".join(self.models))
        self.baseurl_var.trace("w", on_config_changed)
        self.apikey_var.trace("w", on_config_changed)
        self.models_var.trace("w", on_config_changed)
        self.client = None
        if initialize_client:
            self.update_client()
        self.update_models()
    
    def update_client(self):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            self.client = None
            print("OpenAI package not found, custom servers will be disabled! Install the OpenAI API with `pip install openai`")
            return
        try:
            self.client = AsyncOpenAI(base_url=self.baseurl_var.get(), api_key=self.apikey_var.get())
        except Exception as exc:
            self.client = None
            print(f"WARNING: Custom server client initialization failed: {exc}")

    def update_models(self):
        self.models.clear()
        self.models.extend([model.strip() for model in self.models_var.get().split(",") if model.strip()])
