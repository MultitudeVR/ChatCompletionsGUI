# Chat Completions GUI

This is a simple Graphical User Interface (GUI) application for working with the OpenAI API, allowing you to use OpenAI's Chat Completions (GPT-3.5-turbo, GPT-4, and now GPT-4-turbo) in your local desktop environment.

![Screenshot of Chat Completions GUI](chat_completions_gui.png)

## Getting Started

### Prerequisites

- Python 3.7 or higher (If installing from source)
- An OpenAI API key (get one from https://beta.openai.com/signup/)

### Installing

There are two methods to install Chat Completions GUI:

#### Method 1: Installing from Source

1. Clone the repository:

    ```
    git clone https://github.com/MultitudeVR/ChatCompletionsGUI.git
    cd ChatCompletionsGUI
    ```

2. Install the required packages:

    `pip install -r requirements.txt`

3. Run the application:

    `python chat.py`

After installation, enter your OpenAI API key and Organization ID (if applicable) in the configuration fields, and click "Save API Key".

#### Method 2: Windows Executable

For Windows users, download the executable file from the [GitHub release page](https://github.com/MultitudeVR/ChatCompletionsGUI/releases/tag/v1.0.0). Simply run the downloaded executable to launch the application.

Note that application startup time is somewhat slow when running from the .exe (it takes approximately 10 seconds).

Also note that this is an old version of the gui.

## Features

- Interact with GPT-3.5-turbo, GPT-4, and GPT-4-turbo models
- Easily add, edit, and delete chat messages
- Save and load chat logs in JSON format
- Image analysis via vision API (currently supports web links only)
- Customizable system message and model selection
- Customizable temperature and max response length settings
- Windows, Mac, Linux, and Android support

## Latest Changes

11/6/23
- Implemented vision API which currently supports image analysis via web links
- Added the new gpt-4-turbo model
- Chat logs are now saved automatically on-close in the `/temp/backup/` folder
- Chat logs are now saved as JSON. A conversion script has been added to convert old format logs
- Chat logs are now sorted by date
- Removed the concept of an 'important message' as well as the sliding context window feature
- Set default max length for messages to 4000
- Made token counting more accurate using tiktoken
- Enabled 'undo' on message text contents

8/14/23
- Added support for system messages besides the first one

7/21/23
- Added Mac support

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This project is not officially affiliated with or endorsed by OpenAI. It is an independent project developed by the Multitude VR team, licensed under the MIT License. The use of the OpenAI API is subject to OpenAI's terms and policies, which can be found at https://www.openai.com/usage-policies/.

Please be aware that this tool does not itself collect or store any data; all data exchanged with the OpenAI API is handled directly by OpenAI. As a developer using this tool, it is your responsibility to ensure compliance with OpenAI's terms and policies. We kindly ask you to review OpenAI's policies and understand the implications of using the API with your own keys.
