# HTML Tool Manager

A simple web application to manage and host a collection of single-page HTML/JS tools. This project was developed as a collaboration between a human user and an AI assistant.

## Features

- **Tool Management:** Create, read, update, and delete tools via a web interface.
- **Content Creation:** Create new tools by directly pasting HTML content.
- **Live Hosting:** "Use" a tool to render it within an `iframe`.
- **Advanced Search:** A powerful search bar supports:
  - General text search across name, description, and tags.
  - Prefix-based search (e.g., `name:my-tool`, `desc:calculator`, `tag:json`).
  - Phrase search using double quotes (e.g., `name:"My Awesome Tool"`).
- **Sorting:** Sort the tool list by relevance, name, or update date.
- **Modern UI:** A clean and responsive user interface built with [Pico.css](https://picocss.com/).
- **Containerized:** A `Dockerfile` is included for easy containerization and deployment.

## Tech Stack

- **Backend:** Python 3.12+ with [FastAPI](https://fastapi.tiangolo.com/)
- **Database:** [SQLite](https://www.sqlite.org/index.html) (with FTS5 for full-text search)
- **ORM:** [SQLModel](https://sqlmodel.tiangolo.com/)
- **Frontend:** Plain HTML, CSS, and JavaScript, styled with [Pico.css](https://picocss.com/)
- **Python Environment:** `uv` for package and virtual environment management
- **Task Runner:** `poethepoet` for running development tasks

## Getting Started

### Prerequisites

- Python 3.12+
- `uv` (can be installed via `pip`, `pipx`, or your system's package manager)

### Development Environment

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd html_tool_manager
    ```

2.  **Create virtual environment and install dependencies:**
    `uv` will create a `.venv` directory and install all required packages.
    ```bash
    uv pip install -e .[dev]
    ```

3.  **Run the development server:**
    This command uses `poethepoet` to run `uvicorn` with hot-reloading enabled.
    ```bash
    uv run poe dev
    ```
    The application will be available at `http://127.0.0.1:8000`.

4.  **Run tests:**
    ```bash
    uv run pytest
    ```

### Docker

1.  **Build the Docker image:**
    ```bash
    docker build -t html-tool-manager .
    ```

2.  **Run the Docker container:**
    This command maps the container's port 80 to the host's port 8000. It also creates a volume named `html-tool-manager-data` to persist the SQLite database and uploaded tool files.
    ```bash
    docker run -d -p 8000:80 -v html-tool-manager-data:/app/static/tools -v html-tool-manager-db:/app --name html-tool-manager-app html-tool-manager
    ```
    - The application will be available at `http://127.0.0.1:8000`.
    - The database file (`sql_app.db`) will be persisted in the `html-tool-manager-db` volume.
    - Uploaded tools will be persisted in the `html-tool-manager-data` volume.