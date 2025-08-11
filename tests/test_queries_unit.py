from mcp_beeper_texts.queries import extract_message_attachments, extract_message_text


def test_extract_message_text_plain_and_json():
    assert extract_message_text("hi", "TEXT") == "hi"
    assert extract_message_text('{"text":"hello"}', "TEXT") == "hello"
    assert extract_message_text('{"body":"b"}', "TEXT") == "b"

    # Non-text types fall back to placeholders when fields absent
    assert extract_message_text("{}", "FILE").startswith("[File:")
    assert extract_message_text("{}", "AUDIO").startswith("[Audio")


def test_extract_message_attachments_minimal():
    payload = (
        '{"attachments": [{"mimeType": "image/jpeg"}, {"mimetype": "audio/mpeg"}, {"mimeType": "application/pdf"}]}'
    )
    atts = extract_message_attachments(payload, "evt2")
    assert len(atts) == 3
    assert atts[0].type == "image"
    assert atts[1].type == "audio"
    assert atts[2].type == "file"
