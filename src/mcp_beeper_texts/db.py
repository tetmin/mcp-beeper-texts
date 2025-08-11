import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator


def get_beeper_db_path() -> Path:
    """Find the Beeper application support directory.

    Returns:
        Path to the BeeperTexts directory

    Raises:
        FileNotFoundError: If Beeper directory is not found or not accessible
    """
    beeper_path = Path.home() / "Library" / "Application Support" / "BeeperTexts"

    if not beeper_path.exists():
        raise FileNotFoundError(
            f"Beeper directory not found at {beeper_path}. "
            "Please ensure Beeper Desktop is installed and has been run at least once."
        )

    if not beeper_path.is_dir():
        raise FileNotFoundError(f"Beeper path exists but is not a directory: {beeper_path}")

    return beeper_path


@asynccontextmanager
async def get_db_connection(db_name: str) -> AsyncGenerator[sqlite3.Connection, None]:
    """Get a connection to a Beeper database.

    Args:
        db_name: Name of the database file (e.g., 'account.db', 'index.db')

    Yields:
        sqlite3.Connection: Database connection

    Raises:
        FileNotFoundError: If the database file is not found
    """
    beeper_path = get_beeper_db_path()
    db_path = beeper_path / db_name

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row  # Enable column access by name
        yield conn
    finally:
        conn.close()


def get_platform_db_paths() -> list[Path]:
    """Discover all platform-specific megabridge.db files.

    Returns:
        List of paths to megabridge.db files
    """
    beeper_path = get_beeper_db_path()
    platform_dbs = []

    for item in beeper_path.iterdir():
        if item.is_dir() and item.name.startswith("local-"):
            megabridge_path = item / "megabridge.db"
            if megabridge_path.exists():
                platform_dbs.append(megabridge_path)

    return platform_dbs


def get_beeper_media_dir() -> Path:
    """Return the Beeper media directory.

    Uses the same base path discovery as databases to avoid duplicating logic.
    """
    return get_beeper_db_path() / "media"
