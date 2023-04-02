# Contributing to Chat Completions GUI

We're excited that you're interested in contributing to the Chat Completions GUI! This document will guide you through the process of setting up your development environment and making changes to the codebase.

## Getting Started

1. Fork the repository on GitHub.

2. Clone your fork:

    `git clone https://github.com/yourusername/chat-completions-gui.git`\
    `cd chat-completions-gui`

3. Add the original repository as a remote:

    `git remote add upstream https://github.com/yourusername/chat-completions-gui.git`

4. Create a new branch for your changes:

    `git checkout -b your-feature-branch`

5. Install the required packages:

    `pip install -r requirements.txt`

## Making Changes

1. Make your changes to the codebase.

2. Test your changes by running the application:
   - `python chat.py`
   - or by building then running the executable in the /dist/ folder
     - For Windows: `build.bat`
     - For Linux / macOS: `./build.sh`

3. Commit your changes:

    `git add .`\
    `git commit -m "Your commit message"`

4. Push your changes to your fork:

    `git push origin your-feature-branch`

## Submitting a Pull Request

1. Open a pull request on GitHub, comparing your fork's `your-feature-branch` to the original repository's `main` branch.

2. Describe your changes in the pull request description.

3. Wait for a review from the repository maintainers. They may request additional changes or approve the pull request.

4. If additional changes are requested, make the necessary changes and push them to your feature branch.

5. Once the pull request is approved, the maintainers will merge your changes.

## Code of Conduct

Please be respectful and considerate to other contributors. We want to maintain a positive and inclusive environment for everyone involved in the project.

Thank you for contributing to Chat Completions GUI!