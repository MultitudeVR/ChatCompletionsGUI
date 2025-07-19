# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

The main entry point is `src/main.py`. To run the application:

```bash
python src/main.py
# or use the provided scripts:
./run.sh   # Linux/Mac
run.bat    # Windows
```

## Project Architecture

This is a Tkinter-based desktop GUI application for interacting with AI chat completion APIs (OpenAI, Anthropic, Google, and custom servers).

### Key Components

1. **src/main.py** - Entry point that initializes config and launches the GUI
2. **src/chat_window.py** - Main GUI window containing all UI components and chat logic
3. **src/constants.py** - Model definitions, pricing info, and default values
4. **src/custom_server.py** - Handles custom API server configurations (e.g., Ollama)
5. **src/utils.py** - Token counting, message conversion, and image processing utilities
6. **src/prompts.py** - System prompts for features like automatic file naming
7. **src/tooltip.py** - Helper for displaying tooltips in the GUI

### Configuration

The app uses `config.ini` to store API keys and settings:
- `[openai]` section for OpenAI credentials
- `[anthropic]` section for Anthropic credentials
- `[custom_server_N]` sections for custom servers like Ollama
- `[app]` section for UI preferences (dark mode, last used model, etc.)

### Data Storage

- Chat logs are saved in `chat_logs/` directory as JSON files
- Temporary backups are stored in `temp/backup/`

## Development Notes

- No formal test suite exists - manual testing required
- No linting configuration - follow existing code style
- Uses async/await for API calls to support streaming responses
- Supports vision models for image analysis (web links only currently)
- Includes token counting for cost estimation

## Dependencies

Core dependencies (from requirements.txt):
- `openai==1.17.0` - OpenAI API client
- `anthropic==0.25.1` - Anthropic API client  
- `tiktoken==0.6.0` - Token counting library

The application requires Python 3.7+ and tkinter (python-tk on some systems).