"""
Storage backends for the Object Primitive System.

This module contains storage adapters for different backends:
- TSV: Tab-separated values (human-readable, grep-able)
- FileSystem: Direct file storage
- SQLite: Embedded SQL database
- PostgreSQL: Production SQL database
- Redis: In-memory cache/store
- S3: Object storage
- Custom: Pluggable custom storage

Objects are stored with:
- Source code (current and all versions)
- Logs (self-logging, TSV format)
- Metadata (creation time, author, etc.)
- Data (state, if stateful)

Philosophy:
    Storage is swappable. Database goes evil? Swap it.
    TSV today, PostgreSQL tomorrow, ??? next year.
    The endpoint doesn't know or care where data lives.

    Start with TSV (simple, grep-able).
    Graduate to databases only when needed.
    Always be able to swap back.
"""

__all__ = [
    # To be implemented in Phase 3+
    # "TSVStorage",
    # "FileSystemStorage",
    # "SQLiteStorage",
    # "PostgreSQLStorage",
    # "RedisStorage",
]
