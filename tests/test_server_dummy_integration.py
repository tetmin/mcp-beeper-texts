import pytest

from mcp_beeper_texts.server import (
    get_media_attachment,
    get_messages,
    list_chats,
    search_message_contents,
)


@pytest.mark.asyncio
async def test_server_tools_against_dummy_db(dummy_beeper_env):
    chats = await list_chats(limit=5)
    assert len(chats) >= 1
    chat = chats[0]
    assert chat.chat_id
    assert chat.name

    msgs = await get_messages(chat_id="!room:whatsapp.com", limit=10)
    assert len(msgs) == 2
    assert msgs[0].text

    results = await search_message_contents(query="hello", limit=5)
    assert isinstance(results, list)
    assert any(r.chat.chat_id == "!room:whatsapp.com" for r in results)

    # Attachment content fetch from known uri
    att_uri = "beeper://attachment/evt2/0"
    media = await get_media_attachment(att_uri)
    assert media.get("type") in {"image", "audio", "video", "file"}
    # for image we expect base64
    if media.get("type") == "image":
        assert "base64" in media
