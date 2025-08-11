import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_beeper_texts.db import (
    get_beeper_db_path,
    get_db_connection,
    get_platform_db_paths,
)


def test_get_beeper_db_path_not_found():
    """Test get_beeper_db_path when directory doesn't exist."""
    with patch("pathlib.Path.home") as mock_home:
        mock_home.return_value = Path("/nonexistent")

        with pytest.raises(FileNotFoundError) as exc_info:
            get_beeper_db_path()

        assert "Beeper directory not found" in str(exc_info.value)


def test_get_beeper_db_path_success():
    """Test get_beeper_db_path with valid directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        beeper_dir = Path(tmpdir) / "Library" / "Application Support" / "BeeperTexts"
        beeper_dir.mkdir(parents=True)

        with patch("pathlib.Path.home", return_value=Path(tmpdir)):
            result = get_beeper_db_path()
            assert result == beeper_dir


@pytest.mark.asyncio
async def test_get_db_connection_not_found():
    """Test get_db_connection with non-existent database."""
    with patch("mcp_beeper_texts.db.get_beeper_db_path") as mock_path:
        mock_path.return_value = Path("/nonexistent")

        with pytest.raises(FileNotFoundError):
            async with get_db_connection("test.db"):
                pass


@pytest.mark.asyncio
async def test_get_db_connection_success():
    """Test get_db_connection with valid database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Create a simple test database
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()

        with patch("mcp_beeper_texts.db.get_beeper_db_path") as mock_path:
            mock_path.return_value = Path(tmpdir)

            async with get_db_connection("test.db") as connection:
                assert isinstance(connection, sqlite3.Connection)
                # Test row factory is set
                cursor = connection.execute("SELECT 1 as test_col")
                row = cursor.fetchone()
                assert row["test_col"] == 1


def test_get_platform_db_paths():
    """Test get_platform_db_paths discovery."""
    with tempfile.TemporaryDirectory() as tmpdir:
        beeper_dir = Path(tmpdir)

        # Create platform directories with megabridge.db files
        platforms = ["local-whatsapp", "local-telegram", "local-signal"]
        expected_paths = []

        for platform in platforms:
            platform_dir = beeper_dir / platform
            platform_dir.mkdir()
            db_path = platform_dir / "megabridge.db"
            db_path.touch()
            expected_paths.append(db_path)

        # Create a directory without megabridge.db (should be ignored)
        (beeper_dir / "local-empty").mkdir()

        with patch("mcp_beeper_texts.db.get_beeper_db_path") as mock_path:
            mock_path.return_value = beeper_dir

            result = get_platform_db_paths()
            assert len(result) == 3
            assert all(path in result for path in expected_paths)
