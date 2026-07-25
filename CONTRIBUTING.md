# Contributing to Spripe

First off, thank you for considering contributing to Spripe! It's people like you that make open-source software such a great community to be a part of.

## How to Contribute

1. **Fork the Repository**: Start by forking the repository to your own GitHub account.
2. **Read the Architecture Docs**: Before diving into the code, please read our [Architecture Overview](docs/dev/architecture.md) and [Core Services](docs/dev/core_services.md) documentation to understand how Spripe is structured. We heavily rely on an Event Bus (`SignalManager`) to keep our UI decoupled from the backend.
3. **Create a Branch**: Create a new branch for your feature or bugfix (e.g. `git checkout -b feature/awesome-new-tool`).
4. **Write Code**: Implement your changes. Make sure to document any new functionality.
5. **Commit & Push**: Commit your changes with a descriptive message and push to your fork.
6. **Submit a Pull Request (PR)**: Open a Pull Request against the `main` branch. Provide a clear description of what you've done and why it's needed.

## Development Setup

To run Spripe locally for development:

1. Clone your fork.
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment.
4. Install the requirements in editable mode (with CPU/GPU options and dev tools): `pip install -e .[cpu,dev]` or `pip install -e .[gpu,dev]`
5. Run the application: `spripe gui`

## Reporting Bugs
If you find a bug, please create an Issue on GitHub. Include:
- A clear, descriptive title.
- Steps to reproduce the bug.
- The expected behavior vs the actual behavior.
- Your OS and Python version.
