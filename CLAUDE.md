# Beeper Texts MCP Server (mcp-beeper-texts) - Claude Development Guide

This document provides essential information for developing the `mcp-beeper-texts` server with assistance from Claude.

## 1. Project Overview

-   **Name:** `mcp-beeper-texts`
-   **Description:** A local-only MCP server for macOS that exposes Beeper Texts data (messages, contacts, chats) for use with AI assistants and automation tools.
-   **Technology Stack:** Python, `mcp` SDK, `uv`, SQLite.
-   **Transport:** `stdio` (Standard I/O).

## 2. Developer Environment Setup (macOS)

1.  **Locate Beeper Database Path:**
    -   The server needs read/write access to the Beeper application support directory. The default path is:
        `~/Library/Application Support/BeeperTexts/`
    -   The server will attempt to find this path automatically. Knowing its location is crucial for debugging.

## 3. Common Commands

-   **Run the server for development (with MCP Inspector):**
    ```bash
    # This command assumes a console script is configured in pyproject.toml
    uv run mcp dev mcp-beeper-texts
    ```

-   **Run tests:**
    ```bash
    uv run pytest
    ```

-   **Lint and format code:**
    ```bash
    uv run ruff check . --fix
    uv run ruff format .
    ```

-   **Build the package for PyPI:**
    ```bash
    uv run python -m build
    ```

## 4. Core Files & Architecture

The project follows a standard `src` layout for packaging and distribution.

-   `src/mcp_beeper_texts/`: The main Python package directory. All installable source code lives here.
    -   `server.py`: The core of the application. It defines the `FastMCP` server, registers all the tools (e.g., `list_chats`, `send_message`), and contains the main entry point.
    -   `db.py` Contains utility functions for connecting to the Beeper SQLite databases.
    -   `queries.py` Holds SQL query strings and data access logic.
    -   `models.py` Defines Pydantic models for API responses (e.g., `Chat`, `Message`, `Contact`).
-   `tests/` contains unit and integration tests.
-   `pyproject.toml`: Defines project metadata, dependencies, scripts, and build configuration for PyPI.
-   `README.md`: Public-facing documentation for the package.
-   `docs/beeper-texts-schema.md`: Detailed description of the Beeper Texts database architecture.
-   `docs/mcp-full-docs.md`: The most comprehensive MCP documentation with all APIs, best practices, and examples.
-   `docs/mcp-sdk-readme.md`: README from the MCP Python SDK.

## 5. Beeper Database Schema Highlights

The server interacts with three main database types:

-   **`account.db`**: The unified Matrix event store.
    -   **Primary Use:** Searching all messages via the `local_events` table.
-   **`index.db`**: UI-optimized cache and application state.
    -   **Primary Use:** Listing chats (`threads`, `breadcrumbs`), getting recent messages (`mx_room_messages`), and managing drafts (`thread_props`).
-   **`local-{platform}/megabridge.db`**: Platform-specific data bridges.
    -   **Primary Use:** Resolving contact information (`ghost` table) and chat participants (`portal`, `user_portal` tables).

More details on the database schema are in @docs/beeper-texts-schema.md

## 6. Code Style & Repository Etiquette

-   **Formatting & Linting:** We use `ruff format` and `ruff check`. Please run these before committing.
-   **Branching:** Use prefixes: `feat/`, `fix/`, `docs/`, `refactor/`. Example: `feat/search-messages-tool`.
-   **Commits:** Adhere to the Conventional Commits specification.
-   **Pull Requests:** Rebase your branch on `main` before requesting a review to resolve conflicts. All PRs require at least one approval.
-   **Legacy Code:** Always remove legacy code and comments and refactor to keep the codebase clean.
-   **Coding Style:** Aim for functional, readable, clean code with minimal LOC without excessive logging or error handling.
-   **Scripts:** If you create temporary scripts, please remove them after the task is complete.
-   **Testing:** We use `pytest` for testing. Please write tests for new features and refactorings. Tests must actually test the code in the package. If sending messages, tests must ONLY use the `Note to self` chat on the beeper network.

## 7. Important Warnings & Behaviors

-   **macOS ONLY:** This server is designed exclusively for macOS and relies on the Beeper Desktop application's local database structure. It will not run on other operating systems.
-   **Beeper Desktop Required:** The user must have the Beeper Desktop application installed and configured.
-   **NO STDOUT LOGGING:** The server uses `stdio` transport. Using `print()` or any other function that writes to `stdout` will corrupt the JSON-RPC stream and break communication. Use the Python `logging` module (configured for `stderr`) or the `ctx.info()` family of methods provided by `FastMCP` for logging.