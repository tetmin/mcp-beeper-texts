import base64
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image

from .models import Chat, ChatLabel, ChatSearchResult, Message, MessageAttachment

# Message types for queries that return messages (shorter list)
MESSAGE_TYPES_RETURN = ("TEXT", "IMAGE", "VIDEO", "AUDIO", "FILE", "CONTACT")

# Extended message types for counting and broader queries
MESSAGE_TYPES_EXTENDED = MESSAGE_TYPES_RETURN + ("STICKER", "LOCATION")

# SQL placeholders for message type filters
MESSAGE_TYPES_RETURN_SQL = "', '".join(MESSAGE_TYPES_RETURN)
MESSAGE_TYPES_EXTENDED_SQL = "', '".join(MESSAGE_TYPES_EXTENDED)


def nanoseconds_to_iso(timestamp_ns: int) -> str:
    """Convert timestamp to ISO 8601 string."""
    try:
        if timestamp_ns > 1e15:  # Microseconds or nanoseconds
            timestamp_s = timestamp_ns / (1_000_000_000 if timestamp_ns > 1e18 else 1_000_000)
        elif timestamp_ns > 1e12:  # Milliseconds
            timestamp_s = timestamp_ns / 1_000
        else:  # Already in seconds
            timestamp_s = timestamp_ns
        return datetime.fromtimestamp(timestamp_s).isoformat()
    except (ValueError, OSError):
        return datetime.now().isoformat()


def resolve_platform_from_room_id(room_id: str) -> str:
    """Extract platform from room ID."""
    room_id_lower = room_id.lower()
    for key, platform in {
        "whatsapp": "WhatsApp",
        "telegram": "Telegram",
        "signal": "Signal",
        "linkedin": "LinkedIn",
        "discord": "Discord",
        "slack": "Slack",
        "facebook": "Facebook",
        "instagram": "Instagram",
        "imessage": "iMessage",
        "twitter": "Twitter",
    }.items():
        if key in room_id_lower:
            return platform
    return "Beeper" if "beeper.local" in room_id else "Unknown"


def get_contact_name(
    sender_id: str,
    room_id: str,
    is_from_me: bool = False,
    index_conn: sqlite3.Connection = None,
) -> str:
    """Get contact name from thread participants."""
    if is_from_me:
        return "Me"

    if index_conn:
        try:
            thread_cursor = index_conn.execute(
                "SELECT json_extract(thread, '$.participants.items') as participants FROM threads WHERE threadID = ?",
                (room_id,),
            )
            thread_row = thread_cursor.fetchone()
            if thread_row and thread_row["participants"]:
                participants = json.loads(thread_row["participants"])
                for participant in participants:
                    if participant.get("id") == sender_id:
                        return participant.get("fullName", sender_id)
        except (sqlite3.Error, json.JSONDecodeError):
            pass

    return sender_id


def extract_message_attachments(message_json: str, message_id: str) -> List[MessageAttachment]:
    """Extract minimal attachment metadata (URI, type, mime, filename, caption, duration).

    We intentionally avoid parsing image/video dimensions or file sizes to keep this light.
    """
    if not message_json:
        return []

    try:
        data = json.loads(message_json)
    except json.JSONDecodeError:
        return []

    items = data.get("attachments") or []
    if not isinstance(items, list):
        return []

    def infer_type(mime: str) -> str:
        mime = mime or "application/octet-stream"
        return next((t for t in ("image", "audio", "video") if mime.startswith(f"{t}/")), "file")

    return [
        MessageAttachment(
            uri=f"beeper://attachment/{message_id}/{i}",
            type=infer_type((att or {}).get("mimeType") or (att or {}).get("mimetype")),
            mime_type=((att or {}).get("mimeType") or (att or {}).get("mimetype") or "application/octet-stream"),
            duration=(att or {}).get("duration"),
        )
        for i, att in enumerate(items)
        if isinstance(att, dict)
    ]


def process_image_for_context(file_path: Path, max_dimension: int = 1568) -> Dict[str, Any]:
    """Resize image to max edge <= max_dimension, return base64 JPEG."""
    if not file_path.exists():
        raise ValueError(f"Image file not found: {file_path}")

    try:
        with Image.open(file_path) as img:
            ow, oh = img.size
            scale = min(max_dimension / max(ow, oh), 1.0)
            if scale < 1.0:
                img = img.resize((int(ow * scale), int(oh * scale)), Image.Resampling.LANCZOS)

            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            from io import BytesIO

            buf = BytesIO()
            img.save(buf, format="JPEG", quality=85, optimize=True)
            image_bytes = buf.getvalue()

        return {
            "type": "image",
            "mime_type": "image/jpeg",
            "base64": base64.b64encode(image_bytes).decode("utf-8"),
        }
    except Exception as e:
        raise ValueError(f"Error processing image: {e}")


def process_binary_attachment(
    file_path: Path, *, mime_type: str, att_type: str, filename: Optional[str] = None
) -> Dict[str, Any]:
    """Base64-encode a binary file (e.g., audio)."""
    if not file_path.exists():
        raise ValueError(f"File not found: {file_path}")

    try:
        data = file_path.read_bytes()
        return {
            "type": att_type,
            "mime_type": mime_type,
            "base64": base64.b64encode(data).decode("utf-8"),
            "filename": filename,
        }
    except Exception as e:
        raise ValueError(f"Error processing binary attachment: {e}")


def get_media_attachment_content(attachment_uri: str, optimize_for_context: bool = True) -> Dict[str, Any]:
    """Retrieve media by URI: base64 for images (with optional resize) and audio, filepath for others."""
    from .db import get_beeper_db_path, get_beeper_media_dir

    if not attachment_uri.startswith("beeper://attachment/"):
        raise ValueError("Invalid attachment URI format - must start with beeper://attachment/")

    try:
        message_id, idx = attachment_uri[len("beeper://attachment/") :].rsplit("/", 1)
        attachment_index = int(idx)
    except Exception:
        raise ValueError("Invalid attachment URI format - missing or bad index")

    db_path = get_beeper_db_path() / "index.db"
    if not db_path.exists():
        return {"error": f"Database not found: {db_path}", "uri": attachment_uri}

    try:
        with sqlite3.connect(str(db_path)) as index_conn:
            index_conn.row_factory = sqlite3.Row
            row = index_conn.execute(
                "SELECT roomID, message FROM mx_room_messages WHERE eventID = ?",
                (message_id,),
            ).fetchone()
            if not row or not row["message"]:
                return {
                    "error": f"Message not found or empty: {message_id}",
                    "uri": attachment_uri,
                }

            data = json.loads(row["message"]) if isinstance(row["message"], str) else {}
            items = data.get("attachments") or []
            if not isinstance(items, list) or not (0 <= attachment_index < len(items)):
                return {"error": "Attachment index out of range", "uri": attachment_uri}

            att = items[attachment_index] or {}
            mime = att.get("mimeType") or att.get("mimetype") or "application/octet-stream"
            filename = att.get("fileName") or att.get("filename")

            att_type = next(
                (t for t in ("image", "audio", "video") if mime.startswith(f"{t}/")),
                "file",
            )

            # URL extraction with minimal mapping
            url = att.get("srcURL") or att.get("url") or att.get("href")
            media_id_fallback = att.get("id") or att.get("mxc")
            if not url and not media_id_fallback:
                return {"error": "Attachment has no URL", "uri": attachment_uri}

            # data:image/* case
            lower_url = (url or "").lower()
            if url and lower_url.startswith("data:image/") and ";base64," in url:
                try:
                    mime_prefix = url.split(":", 1)[1].split(";", 1)[0]
                    b64 = url.split(",", 1)[1]
                    return {"type": "image", "mime_type": mime_prefix, "base64": b64}
                except Exception:
                    pass

            file_path: Optional[Path] = None
            # Direct file path cases
            if url and lower_url.startswith("file://"):
                p = Path(url[7:])
                file_path = p if p.exists() else None
            elif url:
                p = Path(url)
                file_path = p if p.exists() else None

            # Fallback: search media dir by last path segment or media id
            if not file_path:
                candidate = None
                if url:
                    candidate = url.rsplit("/", 1)[-1].split("?", 1)[0]
                if not candidate:
                    candidate = media_id_fallback

                if candidate:
                    media_dir = get_beeper_media_dir()
                    # Prefer exact match; fallback to contains
                    found = next((p for p in media_dir.rglob(candidate)), None)
                    if not found:
                        found = next((p for p in media_dir.rglob(f"*{candidate}*")), None)
                    file_path = found

            if file_path and file_path.exists():
                try:
                    if att_type == "image" and optimize_for_context:
                        return process_image_for_context(file_path)
                    if att_type in ("image", "audio"):
                        return process_binary_attachment(
                            file_path,
                            mime_type=mime,
                            att_type=att_type,
                            filename=filename,
                        )
                    return {
                        "type": att_type,
                        "mime_type": mime,
                        "filepath": str(file_path),
                    }
                except Exception as e:
                    return {
                        "error": f"Failed to process media file: {e}",
                        "uri": attachment_uri,
                    }

            # Not found on disk: return minimal metadata
            return {
                "error": "Media file not found on disk",
                "type": att_type,
                "mime_type": mime,
                "attachment_url": url,
                "uri": attachment_uri,
            }
    except Exception as e:
        return {"error": f"Database error: {e}", "uri": attachment_uri}


def extract_message_text(message_input: str, message_type: str) -> str:
    """Extract human-readable text from message payloads.

    Accepts either a JSON string (Beeper message payload) or a plain string
    (already-extracted text). Falls back to reasonable placeholders by type.
    """
    if not message_input:
        return ""

    upper_type = (message_type or "TEXT").upper()
    looks_like_json = isinstance(message_input, str) and message_input.lstrip().startswith(("{", "["))

    data = None
    if looks_like_json:
        try:
            data = json.loads(message_input)
        except json.JSONDecodeError:
            data = None

    # If we don't have a dict payload, treat input as plain text
    if not isinstance(data, dict):
        return message_input if upper_type == "TEXT" else (message_input or f"[{upper_type}]")

    if upper_type == "TEXT":
        return data.get("body", data.get("text", ""))
    if upper_type in ("IMAGE", "VIDEO"):
        return data.get("text", data.get("body", f"[{upper_type.title()}]"))
    if upper_type == "AUDIO":
        url = data.get("url", "")
        return f"[Audio: {url}]" if url else "[Audio message]"
    if upper_type == "FILE":
        filename = data.get("filename", "file")
        url = data.get("url", "")
        return f"[File: {filename} - {url}]" if url else f"[File: {filename}]"
    if upper_type == "LOCATION":
        geo = data.get("geo_uri", "")
        return f"[Location: {geo}]" if geo else "[Location]"
    if upper_type == "CONTACT":
        name = data.get("display_name", "Contact")
        return f"[Contact: {name}]"
    if upper_type == "STICKER":
        url = data.get("url", "")
        return f"[Sticker: {url}]" if url else "[Sticker]"
    return data.get("body", data.get("text", f"[{upper_type}]"))


def get_chat_name(thread_title: str, chat_id: str, platform_dbs: List[Path]) -> str:
    """Resolve chat name from title or platform databases."""
    if thread_title:
        return thread_title

    # For DMs, get contact name
    platform = resolve_platform_from_room_id(chat_id).lower()
    for db_path in platform_dbs:
        if platform in db_path.parent.name:
            try:
                with sqlite3.connect(str(db_path)) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute(
                        "SELECT other_user_id FROM portal WHERE mxid = ? AND other_user_id IS NOT NULL",
                        (chat_id,),
                    )
                    row = cursor.fetchone()
                    if row:
                        ghost_cursor = conn.execute(
                            "SELECT name FROM ghost WHERE id = ? AND name != ''",
                            (row["other_user_id"],),
                        )
                        ghost_row = ghost_cursor.fetchone()
                        if ghost_row and ghost_row["name"]:
                            return ghost_row["name"]
            except sqlite3.Error:
                continue

    # Fallback to room ID cleanup
    return chat_id.split(":")[0][1:] if chat_id.startswith("!") and ":" in chat_id else chat_id


def _build_message_from_row(
    row: sqlite3.Row,
    chat_id: str,
    index_conn: sqlite3.Connection,
    message_col: str = "message",
    type_col: str = "type",
) -> Message:
    """Build Message object from database row - shared helper function."""
    sender_name = get_contact_name(row["sender_id"], chat_id, bool(row["is_from_me"]), index_conn)
    text = extract_message_text(row[message_col], row[type_col])

    # Extract attachments if message has eventID and message JSON
    attachments = []
    if "eventID" in row.keys() and row[message_col]:
        try:
            # Use eventID as message_id for attachment URIs
            message_id = row["eventID"] if row["eventID"] else f"msg_{row['timestamp']}"
            attachments = extract_message_attachments(row[message_col], message_id)
        except Exception:
            # If attachment extraction fails, continue without attachments
            # print(f"Attachment extraction failed: {e}")  # Debug - uncomment if needed
            pass

    return Message(
        sender_name=sender_name,
        text=text,
        timestamp=nanoseconds_to_iso(row["timestamp"]),
        message_type=row[type_col].lower(),
        in_reply_to=row["in_reply_to"] if "in_reply_to" in row.keys() else None,
        reactions=[],
        attachments=attachments,
    )


def _get_context_messages(
    chat_id: str,
    timestamp: int,
    index_conn: sqlite3.Connection,
    context_window: int = 3600000,  # 1 hour in milliseconds
    limit: int = 20,
) -> List[Message]:
    """Get context messages around a specific timestamp - shared helper function."""
    context_query = f"""
    SELECT senderContactID as sender_id, message, timestamp, isSentByMe as is_from_me, 
           type, inReplyToID as in_reply_to, eventID
    FROM mx_room_messages
    WHERE roomID = ? AND type IN ('{MESSAGE_TYPES_RETURN_SQL}')
    AND message IS NOT NULL
    AND timestamp BETWEEN ? AND ?
    ORDER BY timestamp ASC
    LIMIT ?
    """

    context_cursor = index_conn.execute(
        context_query,
        (chat_id, timestamp - context_window, timestamp + context_window, limit),
    )

    context_messages = []
    for ctx_row in context_cursor.fetchall():
        message = _build_message_from_row(ctx_row, chat_id, index_conn, "message", "type")
        context_messages.append(message)

    return context_messages


def _build_chat_from_id(
    chat_id: str,
    platform_dbs: List[Path],
    index_conn: sqlite3.Connection,
    last_activity: Optional[str] = None,
) -> Chat:
    """Build Chat object from chat_id - shared helper function."""
    platform = resolve_platform_from_room_id(chat_id)

    # Get chat info
    chat_cursor = index_conn.execute(
        "SELECT json_extract(thread, '$.title') as thread_title FROM threads WHERE threadID = ?",
        (chat_id,),
    )
    chat_row = chat_cursor.fetchone()
    thread_title = chat_row["thread_title"] if chat_row else None
    chat_name = get_chat_name(thread_title, chat_id, platform_dbs)

    # Get total message count for this chat
    msg_count_cursor = index_conn.execute(
        f"SELECT COUNT(*) as total FROM mx_room_messages WHERE roomID = ? AND type IN ('{MESSAGE_TYPES_EXTENDED_SQL}')",
        (chat_id,),
    )
    msg_count_row = msg_count_cursor.fetchone()
    total_messages = msg_count_row["total"] if msg_count_row else 0

    # Use provided last_activity or default
    activity = last_activity if last_activity else nanoseconds_to_iso(0)

    return Chat(
        chat_id=chat_id,
        name=chat_name,
        platform=platform,
        last_activity=activity,
        total_messages=total_messages,
        recent_messages=[],
    )


def fetch_messages(
    index_conn: sqlite3.Connection,
    platform_dbs: List[Path],
    chat_id: str,
    limit: int = 50,
    before: Optional[str] = None,
    after: Optional[str] = None,
) -> List[Message]:
    """Fetch messages with text extraction."""
    query = f"""
    SELECT senderContactID as sender_id, message, timestamp, isSentByMe as is_from_me, 
           type as message_type, inReplyToID as in_reply_to, eventID
    FROM mx_room_messages
    WHERE roomID = ? AND type IN ('{MESSAGE_TYPES_RETURN_SQL}')
    AND message IS NOT NULL
    """
    params = [chat_id]

    # Add date filters if provided
    for date_param, operator in [(after, ">"), (before, "<")]:
        if date_param:
            try:
                dt = datetime.fromisoformat(date_param.replace("Z", "+00:00"))
                ms_timestamp = int(dt.timestamp() * 1_000)
                query += f" AND timestamp {operator} ?"
                params.append(ms_timestamp)
            except ValueError:
                pass

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor = index_conn.execute(query, params)
    messages = []

    for row in cursor.fetchall():
        message = _build_message_from_row(row, chat_id, index_conn, "message", "message_type")
        messages.append(message)

    return messages


def search_messages(
    index_conn: sqlite3.Connection,
    platform_dbs: List[Path],
    query: str,
    chat_id: Optional[str] = None,
    limit: int = 25,
    include_context: bool = True,
) -> List[ChatSearchResult]:
    """Search messages using index.db only."""
    sql_query = f"""
    SELECT roomID as chat_id, senderContactID as sender_id, 
           json_extract(message, '$.text') as text, timestamp, eventID, 
           json_extract(message, '$.extra.type') as message_type
    FROM mx_room_messages
    WHERE json_extract(message, '$.text') LIKE ? 
    AND json_extract(message, '$.text') IS NOT NULL
    AND type IN ('{MESSAGE_TYPES_RETURN_SQL}')
    """
    params = [f"%{query}%"]

    if chat_id:
        sql_query += " AND roomID = ?"
        params.append(chat_id)

    sql_query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor = index_conn.execute(sql_query, params)
    results = []

    for row in cursor.fetchall():
        chat_id = row["chat_id"]

        # Create main message using helper function
        # We need to construct a row-like object with the expected column names
        message_row = {
            "sender_id": row["sender_id"],
            "message": row["text"],  # Use the extracted text
            "timestamp": row["timestamp"],
            "is_from_me": row["sender_id"] == "user" or ("@" in row["sender_id"] and "beeper.com" in row["sender_id"]),
            "type": row["message_type"] or "TEXT",
        }
        message = _build_message_from_row(message_row, chat_id, index_conn, "message", "type")

        # Get context messages around the match
        messages = [message]  # Start with the matched message
        if include_context:
            match_ts = row["timestamp"]
            # Include a small window of context messages around the match
            context_messages = _get_context_messages(
                chat_id,
                match_ts,
                index_conn,
                context_window=3600000,  # 1 hour in milliseconds
                limit=10,
            )

            # Use context messages if found, otherwise keep just the match
            messages = context_messages if context_messages else [message]

        # Build Chat object using helper function
        chat = _build_chat_from_id(chat_id, platform_dbs, index_conn, message.timestamp)

        results.append(
            ChatSearchResult(
                chat=chat,
                messages=messages,
            )
        )

    return results


def apply_inbox_filters(
    rows: List[sqlite3.Row], index_conn: sqlite3.Connection, platform_dbs: List[Path]
) -> List[sqlite3.Row]:
    """Apply inbox-specific post-query filters."""
    if not index_conn or not rows:
        return rows

    filtered_rows = []
    for row in rows:
        chat_id = row["chat_id"]

        # Skip system chats
        if chat_id.endswith((":beeper.local", ":beeper.com")):
            continue

        is_archived_upto = row["is_archived_upto"] is not None
        is_favorited = row["tags"] and "favourite" in row["tags"]

        # Favorites are always in inbox regardless of archive status
        if is_favorited:
            filtered_rows.append(row)
            continue

        # If not archived in UI, it's in inbox
        if not is_archived_upto:
            filtered_rows.append(row)
            continue

        # Get isArchivedUpToOrder from thread data
        thread_cursor = index_conn.execute(
            """
            SELECT json_extract(thread, '$.extra.isArchivedUpToOrder') as archived_up_to_order
            FROM threads WHERE threadID = ?
        """,
            (chat_id,),
        )
        thread_row = thread_cursor.fetchone()

        if not thread_row:
            continue

        archived_up_to_order = thread_row["archived_up_to_order"]

        # If no isArchivedUpToOrder is set, include in inbox
        if archived_up_to_order is None:
            filtered_rows.append(row)
            continue

        # Get latest non-HIDDEN message hsOrder
        latest_msg_cursor = index_conn.execute(
            """
            SELECT MAX(hsOrder) as latest_hs_order
            FROM mx_room_messages
            WHERE roomID = ? AND type != 'HIDDEN'
        """,
            (chat_id,),
        )
        latest_msg_row = latest_msg_cursor.fetchone()

        if not latest_msg_row or latest_msg_row["latest_hs_order"] is None:
            continue

        latest_hs_order = latest_msg_row["latest_hs_order"]

        # Include in inbox if latest message hsOrder is greater than archived order
        # This means new activity occurred after the archive action
        if latest_hs_order > archived_up_to_order:
            filtered_rows.append(row)

    return filtered_rows


def check_community(chat_id: str, platform_dbs: List[Path]) -> bool:
    """Check if the chat is a community."""
    for db_path in platform_dbs:
        if "whatsapp" in db_path.parent.name:
            try:
                with sqlite3.connect(str(db_path)) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute(
                        "SELECT room_type, parent_id FROM portal WHERE mxid = ?",
                        (chat_id,),
                    )
                    row = cursor.fetchone()
                    if row:
                        return row["room_type"] == "space" or row["parent_id"] is not None
            except sqlite3.Error:
                pass
            break
    return False


def fetch_chats(
    index_conn: sqlite3.Connection,
    platform_dbs: List[Path],
    label: ChatLabel = "inbox",
    include_low_priority: bool = False,
    limit: int = 25,
    recent_messages_limit: int = 3,
    sort_by: str = "latest_message",
    max_participants: int = 10,
) -> List[Chat]:
    """Fetch enriched chats with proper filtering and metadata."""

    # Build base query
    base_query = """
    SELECT 
        t.threadID as chat_id,
        COALESCE(b.lastOpenTime, 0) as last_open_time,
        json_extract(t.thread, '$.title') as thread_title,
        json_extract(t.thread, '$.participants') as participants_json,
        json_extract(t.thread, '$.type') as thread_type,
        json_extract(t.thread, '$.isLowPriority') as is_low_priority,
        json_extract(t.thread, '$.isMarkedUnread') as is_marked_unread,
        json_extract(t.thread, '$.extra.isArchivedUpto') as is_archived_upto,
        json_extract(t.thread, '$.extra.tags') as tags,
        (SELECT MAX(timestamp)
         FROM mx_room_messages
         WHERE roomID = t.threadID
           AND type IN ('{MESSAGE_TYPES_RETURN_SQL}')
        ) as last_message_time,
        (SELECT COUNT(*)
         FROM mx_room_messages
         WHERE roomID = t.threadID
           AND type IN ('{MESSAGE_TYPES_EXTENDED_SQL}')
        ) as total_messages
    FROM threads t
    LEFT JOIN breadcrumbs b ON t.threadID = b.id
    """

    # Add label-specific conditions
    conditions = []
    if label == "inbox":
        conditions.append("json_extract(t.thread, '$.isLowPriority') = 0")
    elif label == "archive":
        conditions.extend(
            [
                "json_extract(t.thread, '$.extra.isArchivedUpto') IS NOT NULL",
                "json_extract(t.thread, '$.extra.tags') NOT LIKE '%favourite%'",
            ]
        )
        if not include_low_priority:
            conditions.append("json_extract(t.thread, '$.isLowPriority') = 0")
    elif label == "favourite":
        conditions.append("json_extract(t.thread, '$.extra.tags') LIKE '%favourite%'")
        if not include_low_priority:
            conditions.append("json_extract(t.thread, '$.isLowPriority') = 0")
    elif not include_low_priority and label in ["all", "unread"]:
        conditions.append("json_extract(t.thread, '$.isLowPriority') = 0")

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    # Add sorting
    sort_clauses = {
        # In SQLite, NULLS LAST is not supported; use COALESCE for deterministic ordering
        "latest_message": "COALESCE(last_message_time, b.lastOpenTime, 0) DESC",
        "last_active": "b.lastOpenTime DESC",
        "name": "json_extract(t.thread, '$.title') ASC",
    }
    base_query += f" ORDER BY {sort_clauses.get(sort_by, sort_clauses['latest_message'])}"

    # Apply limit for non-inbox queries
    if label != "inbox":
        base_query += " LIMIT ?"

    # Execute query
    index_conn.row_factory = sqlite3.Row
    params = [limit] if label != "inbox" else []
    cursor = index_conn.execute(base_query, params)
    rows = cursor.fetchall()

    # Apply inbox filters
    if label == "inbox":
        rows = apply_inbox_filters(rows, index_conn, platform_dbs)

    chats = []
    for row in rows:
        chat_id = row["chat_id"]
        platform = resolve_platform_from_room_id(chat_id)
        last_open_time = row["last_open_time"] or 0

        # Determine if group (chat_name resolution happens in helper function)
        thread_type = row["thread_type"]
        is_group = thread_type == "group" if thread_type else ("@g.us" in chat_id or "group" in chat_id.lower())

        # Skip WhatsApp communities in inbox
        if label == "inbox" and is_group and platform.lower() == "whatsapp":
            if check_community(chat_id, platform_dbs):
                continue

        # Get recent messages
        recent_messages = []
        if recent_messages_limit > 0:
            msg_cursor = index_conn.execute(
                f"""
                SELECT senderContactID as sender_id, message, timestamp, isSentByMe as is_from_me, type, eventID
                FROM mx_room_messages 
                WHERE roomID = ? AND type IN ('{MESSAGE_TYPES_RETURN_SQL}')
                AND message IS NOT NULL
                ORDER BY timestamp DESC LIMIT ?
            """,
                (chat_id, recent_messages_limit),
            )

            for msg_row in reversed(msg_cursor.fetchall()):  # Chronological order
                message = _build_message_from_row(msg_row, chat_id, index_conn, "message", "type")

                # Truncate for preview
                if len(message.text) > 100:
                    message.text = message.text[:100] + "..."

                recent_messages.append(message)

        last_activity_timestamp = row["last_message_time"] or last_open_time

        # Check if chat is marked as unread
        unread = bool(row["is_marked_unread"])

        # Get participants ordered by activity level
        participants = []
        if is_group and max_participants > 0:
            participant_cursor = index_conn.execute(
                f"""
                SELECT senderContactID, COUNT(*) as message_count
                FROM mx_room_messages 
                WHERE roomID = ? AND type IN ('{MESSAGE_TYPES_RETURN_SQL}')
                AND senderContactID IS NOT NULL
                GROUP BY senderContactID
                ORDER BY message_count DESC
                LIMIT ?
            """,
                (chat_id, max_participants),
            )

            for p_row in participant_cursor.fetchall():
                sender_id = p_row["senderContactID"]
                is_sender_me = sender_id == "user" or ("@" in sender_id and "beeper.com" in sender_id)
                contact_name = get_contact_name(sender_id, chat_id, is_sender_me, index_conn)

                participants.append(contact_name)

        # Build Chat object using helper function
        chat = _build_chat_from_id(
            chat_id,
            platform_dbs,
            index_conn,
            nanoseconds_to_iso(last_activity_timestamp),
        )

        # Add additional properties that aren't in the helper
        chat.unread = unread
        chat.participants = participants
        chat.recent_messages = recent_messages
        chats.append(chat)

    # Apply final limit for inbox
    if label == "inbox":
        chats = chats[:limit]

    return chats


def search_chats_by_name(
    index_conn: sqlite3.Connection,
    platform_dbs: List[Path],
    query: str,
    label: str = "all",
    limit: int = 25,
) -> List[Chat]:
    """Search chats by name including contact name resolution for DMs."""
    # Use fetch_chats to get all chats with full metadata, then filter by name
    # Set a higher limit for fetching since we'll filter down
    fetch_limit = limit * 3  # Fetch more chats to account for filtering

    all_chats = fetch_chats(
        index_conn=index_conn,
        platform_dbs=platform_dbs,
        label=label,
        include_low_priority=False,
        limit=fetch_limit,
        recent_messages_limit=3,
        sort_by="latest_message",
        max_participants=10,
    )

    # Filter chats by name match (case insensitive)
    matching_chats = []
    query_lower = query.lower()

    for chat in all_chats:
        if query_lower in chat.name.lower():
            matching_chats.append(chat)

            # Stop when we have enough matches
            if len(matching_chats) >= limit:
                break

    return matching_chats


def get_messages_by_person(
    index_conn: sqlite3.Connection,
    platform_dbs: List[Path],
    person_name: str,
    limit: int = 50,
    platform: Optional[str] = None,
    chat_type: Optional[str] = None,
    days_back: Optional[int] = None,
    include_context: bool = False,
) -> List[ChatSearchResult]:
    """Get all messages sent by a specific person across all chats."""

    # Step 1: Find all senderContactIDs that match the person name
    # Get unique sender IDs and their representative chat (for name resolution)
    unique_senders_query = f"""
    SELECT DISTINCT senderContactID, roomID
    FROM mx_room_messages 
    WHERE senderContactID IS NOT NULL 
    AND senderContactID != 'user'
    AND type IN ('{MESSAGE_TYPES_EXTENDED_SQL}')
    """

    sender_cursor = index_conn.execute(unique_senders_query)
    matching_sender_ids = []
    person_name_lower = person_name.lower()

    # Resolve each sender ID to a name and check for matches
    for row in sender_cursor.fetchall():
        sender_id = row["senderContactID"]
        room_id = row["roomID"]

        # Use existing get_contact_name function to resolve name
        resolved_name = get_contact_name(sender_id, room_id, False, index_conn)

        if person_name_lower in resolved_name.lower():
            matching_sender_ids.append(sender_id)

    if not matching_sender_ids:
        return []  # No matching contacts found

    # Step 2: Build the messages query with filters
    messages_query = f"""
    SELECT roomID as chat_id, senderContactID as sender_id,
           json_extract(message, '$.text') as text, timestamp, eventID,
           json_extract(message, '$.extra.type') as message_type, type,
           message, isSentByMe as is_from_me, inReplyToID as in_reply_to
    FROM mx_room_messages
    WHERE senderContactID IN ({",".join("?" * len(matching_sender_ids))})
    AND type IN ('{MESSAGE_TYPES_EXTENDED_SQL}')
    """

    params = matching_sender_ids[:]

    # Add platform filter
    if platform:
        messages_query += " AND roomID LIKE ?"
        params.append(f"%{platform.lower()}%")

    # Add time filter
    if days_back:
        from datetime import datetime, timedelta

        cutoff_time = datetime.now() - timedelta(days=days_back)
        cutoff_ms = int(cutoff_time.timestamp() * 1_000)
        messages_query += " AND timestamp > ?"
        params.append(cutoff_ms)

    messages_query += " ORDER BY timestamp DESC"

    # Step 3: Execute query and group results by chat
    cursor = index_conn.execute(messages_query, params)
    chat_messages = {}  # chat_id -> list of messages

    for row in cursor.fetchall():
        chat_id = row["chat_id"]

        # Apply chat_type filter
        if chat_type:
            is_group_chat = "group" in chat_id.lower() or "@g.us" in chat_id
            if chat_type == "dm" and is_group_chat:
                continue
            elif chat_type == "group" and not is_group_chat:
                continue

        if chat_id not in chat_messages:
            chat_messages[chat_id] = []

        # Create message object using helper function
        message = _build_message_from_row(row, chat_id, index_conn, "message", "type")

        chat_messages[chat_id].append(message)

        # Limit messages per chat
        if len(chat_messages[chat_id]) >= limit:
            break

    # Step 4: Build ChatSearchResult objects using existing patterns
    results = []

    for chat_id, messages in chat_messages.items():
        # Build Chat object using helper function
        last_activity = messages[0].timestamp if messages else None
        chat = _build_chat_from_id(chat_id, platform_dbs, index_conn, last_activity)

        # Add context messages if requested
        final_messages = messages
        if include_context and messages:
            # Use the timestamp of the first message to get context around it
            first_msg_timestamp = int(
                datetime.fromisoformat(messages[0].timestamp.replace("Z", "+00:00")).timestamp() * 1_000
            )
            context_messages = _get_context_messages(chat_id, first_msg_timestamp, index_conn)
            final_messages = context_messages if context_messages else messages

        results.append(
            ChatSearchResult(
                chat=chat,
                messages=final_messages,
            )
        )

    return results
