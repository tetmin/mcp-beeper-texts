import logging
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

from mcp_beeper_texts.db import get_db_connection, get_platform_db_paths
from mcp_beeper_texts.models import (
    Chat,
    ChatLabel,
    ChatSearchResult,
    Message,
)
from mcp_beeper_texts.queries import (
    fetch_chats,
    fetch_messages,
    get_media_attachment_content,
    get_messages_by_person,
    search_chats_by_name,
    search_messages,
)

# Configure logging to stderr
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize FastMCP server
# The name "Beeper" will be shown in MCP client UIs.
mcp = FastMCP("Beeper")


@mcp.tool()
async def list_chats(
    label: ChatLabel = "inbox",
    sort_by: str = "latest_message",
    limit: int = 25,
    recent_messages_limit: int = 3,
    max_participants: int = 5,
    include_low_priority: bool = False,
) -> List[Chat]:
    """List group and DM chats with metadata, filtering and sorting options.

    Args:
        label: chat label/folder - "inbox", "archive", "all","favourite", "unread" (default "inbox")
        sort_by: Sort order - "latest_message", "last_active" or "name" (default "latest_message")
        limit: Maximum number of chats to return (default 25)
        recent_messages_limit: Number of recent messages to include per chat (default 3, set to 0 to disable)
        max_participants: Maximum number of participant names to list for group chats (default 5)
        include_low_priority: Whether to include low priority chats in archive/all views (default False)

    Returns:
        List of Chat objects with metadata including platform, truncated recent
        messages for context, participants, timestamps etc.
    """
    try:
        platform_dbs = get_platform_db_paths()
        async with get_db_connection("index.db") as index_conn:
            chats = fetch_chats(
                index_conn,
                platform_dbs,
                label=label,
                sort_by=sort_by,
                limit=limit,
                recent_messages_limit=recent_messages_limit,
                max_participants=max_participants,
                include_low_priority=include_low_priority,
            )
            return chats
    except Exception as e:
        logging.error(f"Error listing chats: {e}")
        return []


@mcp.tool()
async def get_messages(
    chat_id: str,
    limit: int = 50,
    before: Optional[str] = None,
    after: Optional[str] = None,
) -> List[Message]:
    """Get chronologically orderedmessages from a specific chat with metadata and optional filtering.

    Args:
        chat_id: ID of the chat/conversation
        limit: Maximum number of messages to return (default 50)
        before: Optional ISO-8601 timestamp to get messages before this date
        after: Optional ISO-8601 timestamp to get messages after this date

    Returns:
        List of Message objects with metadata including platform, sender names, timestamps, reactions etc.
    """
    try:
        platform_dbs = get_platform_db_paths()
        async with get_db_connection("index.db") as conn:
            messages = fetch_messages(
                conn,
                platform_dbs,
                chat_id=chat_id,
                limit=limit,
                before=before,
                after=after,
            )
            return messages
    except Exception as e:
        logging.error(f"Error getting messages for chat {chat_id}: {e}")
        return []


@mcp.tool()
async def search_message_contents(
    query: str,
    chat_id: Optional[str] = None,
    limit: int = 25,
    include_context: bool = True,
) -> List[ChatSearchResult]:
    """Search message contents across all chats with optional context and filtering.

    Args:
        query: Text to search for across message contents
        chat_id: Optional chat ID to limit search to specific chat
        limit: Maximum number of results to return (default 25)
        include_context: Whether to include messages before and after matches (default True)

    Returns:
        List of ChatSearchResult objects with message, chat info, and context
    """
    try:
        platform_dbs = get_platform_db_paths()
        async with get_db_connection("index.db") as index_conn:
            results = search_messages(
                index_conn,
                platform_dbs,
                query=query,
                chat_id=chat_id,
                limit=limit,
                include_context=include_context,
            )
            return results
    except Exception as e:
        logging.error(f"Error searching messages with query '{query}': {e}")
        return []


@mcp.tool()
async def search_chat_names(query: str, label: str = "all", limit: int = 25) -> List[Chat]:
    """Search for chats by name/title with filtering by label.

    Args:
        query: Chat name or partial name to search for
        label: Filter results by chat type: 'inbox', 'archive', 'favourite', 'all' (default 'all')
        limit: Maximum number of results to return (default 25)

    Returns:
        List of Chat objects matching the search criteria
    """
    try:
        platform_dbs = get_platform_db_paths()
        async with get_db_connection("index.db") as index_conn:
            chats = search_chats_by_name(index_conn, platform_dbs, query=query, label=label, limit=limit)
            return chats
    except Exception as e:
        logging.error(f"Error searching chats with query '{query}': {e}")
        return []


@mcp.tool()
async def get_person_messages(
    person_name: str,
    limit: int = 50,
    platform: Optional[str] = None,
    chat_type: Optional[str] = None,
    days_back: Optional[int] = None,
    include_context: bool = False,
) -> List[ChatSearchResult]:
    """Get all messages sent by a specific person across all chats.

    Args:
        person_name: Name of the person to search for
        limit: Maximum number of messages per chat (default 50)
        platform: Filter by platform ("WhatsApp", "Telegram", etc.)
        chat_type: Filter by chat type ("dm", "group", or "all")
        days_back: Only include messages from the last N days
        include_context: Include surrounding messages for context

    Returns:
        List of ChatSearchResult objects, each containing a chat and the person's messages in that chat
    """
    try:
        platform_dbs = get_platform_db_paths()
        async with get_db_connection("index.db") as index_conn:
            results = get_messages_by_person(
                index_conn,
                platform_dbs,
                person_name=person_name,
                limit=limit,
                platform=platform,
                chat_type=chat_type,
                days_back=days_back,
                include_context=include_context,
            )
            return results
    except Exception as e:
        logging.error(f"Error getting messages by person '{person_name}': {e}")
        return []


@mcp.tool()
async def get_media_attachment(attachment_uri: str, optimize_for_context: bool = True) -> dict:
    """Retrieve media attachment content by URI from message attachments.

    Args:
        attachment_uri: URI from Message.attachments (e.g., "beeper://attachment/{message_id}/{attachment_index}")
        optimize_for_context: For images, resize to ≤1568px max dimension for cost efficiency (default True)

    Returns:
        For images: {"type": "image", "mime_type": "image/jpeg", "base64": "..."}
        For audio: {"type": "audio", "mime_type": "audio/mpeg", "base64": "..."}
        For files/videos: {"type": "file"|"video", "mime_type": "...", "filepath": "/path/to/file"}
        For errors: {"error": "description", "uri": "original_uri"}
    """
    try:
        result = get_media_attachment_content(attachment_uri, optimize_for_context)
        return result
    except Exception as e:
        logging.error(f"Error retrieving media attachment '{attachment_uri}': {e}")
        return {"error": str(e), "uri": attachment_uri}


def main():
    """Main entry point to run the MCP server."""
    logging.info("Starting Beeper MCP server in stdio mode...")
    # The server communicates over standard input/output
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
