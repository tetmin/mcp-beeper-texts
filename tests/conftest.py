import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image


@pytest.fixture()
def dummy_beeper_env():
    """Create a tiny BeeperTexts directory with minimal databases and media.

    Patches get_beeper_db_path() so the code under test reads these files.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # media directory with a small JPEG image
        media_dir = root / "media"
        media_dir.mkdir(parents=True)
        img_path = media_dir / "pic.jpg"
        Image.new("RGB", (10, 10), color="red").save(img_path, "JPEG", quality=80)

        # index.db with minimal schema and a couple messages
        index_db = root / "index.db"
        conn = sqlite3.connect(str(index_db))
        c = conn.cursor()
        c.execute("CREATE TABLE threads (threadID TEXT PRIMARY KEY, thread TEXT, timestamp INTEGER)")
        c.execute("CREATE TABLE breadcrumbs (id TEXT PRIMARY KEY, lastOpenTime INTEGER)")
        c.execute(
            """
            CREATE TABLE mx_room_messages (
                roomID TEXT,
                senderContactID TEXT,
                message TEXT,
                timestamp INTEGER,
                isSentByMe INTEGER,
                type TEXT,
                inReplyToID TEXT,
                eventID TEXT,
                hsOrder INTEGER
            )
            """
        )

        # One chat with title and two messages (one from me, one from contact with attachment)
        c.execute(
            "INSERT INTO threads VALUES (?, ?, ?)",
            (
                "!room:whatsapp.com",
                '{"title":"Tiny Chat","isLowPriority":0,"extra":{"tags": []}}',
                0,
            ),
        )
        c.execute("INSERT INTO breadcrumbs VALUES (?, ?)", ("!room:whatsapp.com", 0))

        c.execute(
            "INSERT INTO mx_room_messages VALUES (?,?,?,?,?,?,?,?,?)",
            (
                "!room:whatsapp.com",
                "user",
                '{"text":"hello"}',
                1_000,
                1,
                "TEXT",
                None,
                "evt1",
                1,
            ),
        )
        c.execute(
            "INSERT INTO mx_room_messages VALUES (?,?,?,?,?,?,?,?,?)",
            (
                "!room:whatsapp.com",
                "@contact:beeper.com",
                '{"text":"world","attachments":[{"mimeType":"image/jpeg","url":"' + str(img_path) + '"}]}',
                2_000,
                0,
                "TEXT",
                None,
                "evt2",
                2,
            ),
        )

        conn.commit()
        conn.close()

        # local-whatsapp/megabridge.db for optional name resolution/community checks
        plat_dir = root / "local-whatsapp"
        plat_dir.mkdir()
        mega = plat_dir / "megabridge.db"
        mc = sqlite3.connect(str(mega))
        mc.execute("CREATE TABLE portal (mxid TEXT, other_user_id TEXT, room_type TEXT, parent_id TEXT)")
        mc.execute("CREATE TABLE ghost (id TEXT, name TEXT)")
        mc.execute(
            "INSERT INTO portal VALUES (?,?,?,?)",
            ("!room:whatsapp.com", "ghost123", "group", None),
        )
        mc.execute("INSERT INTO ghost VALUES (?,?)", ("ghost123", "Contact Name"))
        mc.commit()
        mc.close()

        with patch("mcp_beeper_texts.db.get_beeper_db_path", return_value=root):
            yield root
