# Contributing to BoxCast Recordings Exporter

First off, thank you for considering contributing to the BoxCast Recordings Exporter!

## Getting Started

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/boxcast-recordings-exporter.git
   ```
3. **Set up your development environment**:
   - The repository provides a DevContainer, which is the easiest way to get started. Just open the repository in VS Code and click "Reopen in Container".
   - Alternatively, you can use a Python virtual environment:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     pip install -r requirements.txt
     ```

## Code Quality and Formatting

This project uses `ruff` for linting and formatting, and `dotenv-linter` for `.env` files. Ensure you have them installed (they are in `requirements.txt` or available globally).

To check your code:
```bash
ruff check .
ruff format .
```

## Creating a Pull Request

1. Create a new branch for your feature or bug fix:
   ```bash
   git checkout -b your-feature-branch
   ```
2. Commit your changes with descriptive messages.
3. Push to your fork:
   ```bash
   git push origin your-feature-branch
   ```
4. Open a Pull Request from your fork against the `main` branch of this repository.

Please provide a clear description of the problem you are solving and the changes you have made in your PR description.

## Bug Reports and Feature Requests

We use GitHub Issues to track bugs and feature requests. Please use the provided issue templates when creating a new issue.

## License

By contributing to this repository, you agree that your contributions will be licensed under the project's MIT License.
