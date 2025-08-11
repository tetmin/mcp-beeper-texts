from typing import List, Literal, Optional

from pydantic import BaseModel, Field

# Use Literal type instead of enum for better MCP compatibility
ChatLabel = Literal["all", "inbox", "archive", "favourite", "unread"]


class Reaction(BaseModel):
    """A reaction to a message."""

    emoji: str
    sender_name: str
    timestamp: str = Field(description="ISO 8601 formatted timestamp")


class MessageAttachment(BaseModel):
    """Attachment metadata for a message."""

    uri: str = Field(description="URI to retrieve attachment content via get_media_attachment tool")
    type: str = Field(description="Attachment type: 'image', 'audio', 'video', 'file'")
    mime_type: str = Field(description="MIME type like 'image/jpeg', 'video/mp4'")
    duration: Optional[float] = Field(None, description="Audio/video duration in seconds")


class Message(BaseModel):
    """A message in Beeper."""

    sender_name: str
    text: str
    timestamp: str = Field(description="ISO 8601 formatted timestamp")
    message_type: str = "text"
    in_reply_to: Optional[str] = None
    reactions: List[Reaction] = Field(default_factory=list)
    attachments: List[MessageAttachment] = Field(
        default_factory=list,
        description="Media attachments - use get_media_attachment tool to retrieve content",
    )


class Chat(BaseModel):
    """A group or DM chat/conversation in Beeper."""

    chat_id: str
    name: str
    platform: str
    unread: bool = False
    last_activity: str = Field(description="ISO 8601 formatted timestamp")
    total_messages: int = 0
    participants: List[str] = Field(default_factory=list)
    recent_messages: List[Message] = Field(default_factory=list)


class ChatSearchResult(BaseModel):
    """Search result containing found messages with context."""

    chat: Chat
    messages: List[Message] = Field(default_factory=list, description="Found messages with surrounding context")
