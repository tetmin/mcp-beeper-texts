# Beeper Texts MCP Server

A local-only MCP (Model Context Protocol) server tested on macOS that exposes Beeper Texts data (messages, contacts, chats) for use with AI assistants and automation tools. Local-only means the MCP accesses your local Beeper SQLite database only, and does not make or trigger **any network requests**.

## Features

- **Chat Management**: List and browse conversations across platforms
- **Message Access**: Retrieve messages from specific chats
- **Search**: Search messages by content, chat name, or by sender
- **Media Access**: Fetch attachment bytes/paths via a URI returned in messages
- **Multi-Platform Support**: Tested with WhatsApp, Telegram, Signal, Instagram, Twitter/X and LinkedIn. Should work with any Beeper-supported platform.

## Requirements

- **macOS only**: This server relies on Beeper Desktop's local database structure only
- **Beeper Desktop**: Must be installed, configured with at least one connected account and running to receive new messages
- **Python 3.10+**: Required for running the server

## Installation

Install from PyPI using pip or uvx:

```bash
pip install mcp-beeper-texts
```

Or use uvx for isolated execution:

```bash
uvx mcp-beeper-texts
```

## Configuration

### Claude Desktop

Add the following to your Claude Desktop configuration file (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "beeper": {
      "command": "uvx",
      "args": ["mcp-beeper-texts"]
    }
  }
}
```

### Other MCP Clients

For other MCP clients, use the command:

```bash
uvx mcp-beeper-texts
```

The server communicates over stdio transport.

## TODO

Add support for:
- [ ] Creating, Editing, and Deleting drafts
- [ ] Sending messages
- [ ] Sending media attachments

## Available Tools

### `list_chats`

List group and DM chats with metadata.

- `label` (optional): Filter set: `inbox`, `archive`, `favourite`, `all`, `unread` (default: `inbox`)
- `sort_by` (optional): `latest_message`, `last_active`, or `name` (default: `latest_message`)
- `limit` (optional): Max chats to return (default: 25)
- `recent_messages_limit` (optional): Include last N messages per chat (default: 3, set 0 to disable)
- `max_participants` (optional): Max participant names for groups (default: 5)
- `include_low_priority` (optional): Include low priority in non-inbox views (default: false)

### `get_messages`

Get chronologically ordered messages from a specific chat.

- `chat_id` (required)
- `limit` (optional): Default 50
- `before`/`after` (optional): ISO-8601 timestamps to page

### `search_message_contents`

Search message contents across chats with optional context.

- `query` (required)
- `chat_id` (optional): Limit to one chat
- `limit` (optional): Default 25
- `include_context` (optional): Include surrounding messages (default: true)

### `search_chat_names`

Search chats by name/title with label filtering.

- `query` (required)
- `label` (optional): Default `all`
- `limit` (optional): Default 25

### `get_person_messages`

Get messages sent by a specific person across chats.

- `person_name` (required)
- `limit` (optional): Max per chat (default: 50)
- `platform` (optional): Platform filter
- `chat_type` (optional): `dm`, `group`, or `all`
- `days_back` (optional): Only include messages from the last N days
- `include_context` (optional): Include surrounding messages

### `get_media_attachment`

Retrieve media attachment bytes/path by URI returned in `Message.attachments`.

- `attachment_uri` (required): e.g., `beeper://attachment/{message_id}/{attachment_index}`
- `optimize_for_context` (optional): For images, resize to ≤1568px for efficiency (default: true)

## Development

### Setup

1. Clone the repository
2. Install dependencies: `uv sync`
3. Run tests: `uv run pytest`
4. Format code: `uv run ruff format .`
5. Lint code: `uv run ruff check . --fix`

### Testing

Run the test suite:

```bash
uv run pytest tests/ -v
```

### MCP Inspector

Use the MCP Inspector for development and testing:

```bash
uv run mcp dev src/mcp_beeper_texts/server.py
```

### Claude Desktop

For Claude Desktop testing (or other local MCP clients), use this configuration in `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "Beeper": {
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "run",
        "--dev",
        "--project",
        "/path/to/your/mcp-beeper-texts",
        "mcp-beeper-texts"
      ]
    }
  }
}
```

Replace `/path/to/your/mcp-beeper-texts` with the actual path to your local repository.

### Hot-Reload Development

For faster development with automatic reloading when files change, you can use [MCP Reloader](https://glama.ai/mcp/servers/@mizchi/mcp-reloader):

```bash
# Install MCP Reloader (one-time setup)
git clone https://github.com/mizchi/mcp-reloader.git
cd mcp-reloader
npm install
npm run build

# Run with hot-reload (from your project directory)
npx mcp-reloader --command "uv run src/mcp_beeper_texts/server.py"
```

This automatically restarts the server when you modify any Python files, providing a faster development workflow.

## Database Access

The server reads from Beeper's local SQLite databases located at:

`~/Library/Application Support/BeeperTexts/`

- `index.db`: Beeper UI-optimized message and chat index and metadata
- `local-{platform}/megabridge.db`: Platform-specific data and contacts

The server only requires read access for most operations, with write access eventually needed for draft management and message sending.

## Troubleshooting

### "Beeper directory not found"

Ensure Beeper Desktop is installed and has been run at least once. The application creates its data directory on first launch.

### "Database not found"

Make sure Beeper Desktop is properly configured with at least one connected account. The databases are created when platforms are connected.

### Permission errors

Ensure the server has read access to `~/Library/Application Support/BeeperTexts/`. This should be automatic on macOS.

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome. Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/new-feature`)
3. Add functionality and tests if applicable
4. Run the test suite (`uv run pytest`)
5. Format and lint your code (`uv run ruff format . && uv run ruff check . --fix`)
6. Commit, Push, and create a Pull Request

## Changelog

### 0.0.1

- Initial release
- Basic chat, message, and contact management
- Search functionality across all platforms
- Basic test suite