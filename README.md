# Chat Completions GUI

This is a simple Graphical User Interface (GUI) application for working with the OpenAI API, allowing you to use OpenAI's Chat Completions (GPT-3.5-turbo, GPT-4, and now GPT-4-turbo) in your local desktop environment.

![Screenshot of Chat Completions GUI](chat_completions_gui.png)

## Getting Started

### Prerequisites

- Python 3.7 or higher (If installing from source)
- An OpenAI API key
- (Optional) An Anthropic API key

### Installing from Source

1. Clone the repository:

    ```
    git clone https://github.com/MultitudeVR/ChatCompletionsGUI.git
    cd ChatCompletionsGUI
    ```

2. Install the required packages:

    `pip install -r requirements.txt`

3. Run the application:

    `python chat.py`

    **Note for Mac users:** If you get an error about a missing package, you may need to install `python-tk`. This can be done by executing `brew install python-tk` in your terminal. And if that doesn't work, you may need to specify your python version (i.e. `brew install python-tk@3.12`).

After installation, enter your OpenAI API key and Organization ID (if applicable) in the configuration fields.

## Features

- Interact with openai and anthropic models
- Easily add, edit, and delete chat messages
- Save and load chat logs in JSON format
- Image analysis via vision API (currently supports web links only)
- Customizable system message and model selection
- Customizable temperature and max response length settings
- Windows, Mac, Linux, and Android support

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This project is not officially affiliated with or endorsed by OpenAI. It is an independent project developed by the Multitude VR team, licensed under the MIT License. The use of the OpenAI API is subject to OpenAI's terms and policies, which can be found at https://www.openai.com/usage-policies/.

Please be aware that this tool does not itself collect or store any data; all data exchanged with the OpenAI API is handled directly by OpenAI. As a developer using this tool, it is your responsibility to ensure compliance with OpenAI's terms and policies. We kindly ask you to review OpenAI's policies and understand the implications of using the API with your own keys.
