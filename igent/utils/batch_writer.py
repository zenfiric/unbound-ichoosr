"""Batch file writer for improved I/O performance.

Instead of writing to files after each registration, accumulate writes
and flush in batches. This reduces disk I/O overhead significantly.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

import aiofiles


class BatchWriter:
    """Accumulates file writes and flushes in batches.

    Example:
        >>> writer = BatchWriter(batch_size=5)
        >>> writer.append('matches.json', {'id': '123', 'data': ...})
        >>> writer.append('matches.json', {'id': '124', 'data': ...})
        >>> await writer.flush()  # Writes both at once
    """

    def __init__(self, batch_size: int = 5):
        """Initialize batch writer.

        Args:
            batch_size: Number of writes to accumulate before auto-flush
        """
        self.batch_size = batch_size
        self._pending_writes: dict[str, list[dict[str, Any]]] = {}
        self._write_counts: dict[str, int] = {}

    def append(self, filepath: str, data: dict[str, Any]) -> None:
        """Add data to pending writes for a file.

        Args:
            filepath: Path to the file
            data: Data to append
        """
        if filepath not in self._pending_writes:
            self._pending_writes[filepath] = []
            self._write_counts[filepath] = 0

        self._pending_writes[filepath].append(data)
        self._write_counts[filepath] += 1

    async def should_flush(self, filepath: str | None = None) -> bool:
        """Check if we should flush based on batch size.

        Args:
            filepath: Optional specific file to check, or None for any file

        Returns:
            True if any file has reached batch_size
        """
        if filepath:
            return self._write_counts.get(filepath, 0) >= self.batch_size

        return any(count >= self.batch_size for count in self._write_counts.values())

    async def flush(self, filepath: str | None = None) -> int:
        """Write all pending data to disk.

        Args:
            filepath: Optional specific file to flush, or None to flush all

        Returns:
            Number of records written
        """
        files_to_flush = [filepath] if filepath else list(self._pending_writes.keys())

        total_written = 0

        for file_path in files_to_flush:
            if file_path not in self._pending_writes:
                continue

            pending_data = self._pending_writes[file_path]
            if not pending_data:
                continue

            # Read existing data
            path = Path(file_path)
            existing_data = []

            if path.exists():
                async with aiofiles.open(path, "r") as f:
                    content = await f.read()
                    if content.strip():
                        existing_data = json.loads(content)

            # Ensure it's a list
            if not isinstance(existing_data, list):
                existing_data = []

            # Append pending data
            existing_data.extend(pending_data)

            # Write back
            path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(path, "w") as f:
                await f.write(json.dumps(existing_data, indent=2))

            total_written += len(pending_data)

            # Clear pending for this file
            self._pending_writes[file_path] = []
            self._write_counts[file_path] = 0

        return total_written

    async def flush_all(self) -> int:
        """Flush all pending writes.

        Returns:
            Total number of records written
        """
        return await self.flush()

    def get_pending_count(self, filepath: str | None = None) -> int:
        """Get count of pending writes.

        Args:
            filepath: Optional specific file, or None for total

        Returns:
            Number of pending writes
        """
        if filepath:
            return len(self._pending_writes.get(filepath, []))

        return sum(len(data) for data in self._pending_writes.values())

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - auto flush."""
        await self.flush_all()


class AutoFlushBatchWriter(BatchWriter):
    """BatchWriter that auto-flushes when batch size is reached.

    Example:
        >>> async with AutoFlushBatchWriter(batch_size=3) as writer:
        ...     writer.append('file.json', {'id': 1})
        ...     writer.append('file.json', {'id': 2})
        ...     writer.append('file.json', {'id': 3})  # Auto-flushes here
        ...     writer.append('file.json', {'id': 4})
        ... # Final flush on exit
    """

    def append(self, filepath: str, data: dict[str, Any]) -> None:
        """Add data and auto-flush if batch size reached.

        Args:
            filepath: Path to the file
            data: Data to append
        """
        super().append(filepath, data)

        # Schedule auto-flush if batch size reached (don't await)
        if self._write_counts[filepath] >= self.batch_size:
            asyncio.create_task(self.flush(filepath))
