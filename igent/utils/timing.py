"""Detailed timing utilities for performance measurement."""

import time
from contextlib import contextmanager


class Timer:
    """Hierarchical timer for detailed performance tracking.

    Example:
        >>> timer = Timer("workflow")
        >>> with timer.section("phase1"):
        ...     with timer.section("ai_conversation"):
        ...         await call_ai()
        ...     with timer.section("file_write"):
        ...         await write_file()
        >>> print(timer.get_summary())
        {
            'workflow_total': 50.5,
            'phase1_total': 35.2,
            'phase1_ai_conversation': 34.1,
            'phase1_file_write': 1.1
        }
    """

    def __init__(self, name: str = "root"):
        self.name = name
        self.timings: dict[str, float] = {}
        self.current_path: list[str] = []
        self._section_starts: dict[str, float] = {}

    @contextmanager
    def section(self, section_name: str):
        """Time a section of code.

        Args:
            section_name: Name of the section being timed

        Yields:
            None
        """
        # Build hierarchical key
        self.current_path.append(section_name)
        key = "_".join(self.current_path)

        # Start timing
        start_time = time.time()
        self._section_starts[key] = start_time

        try:
            yield
        finally:
            # Record elapsed time
            elapsed = time.time() - start_time
            self.timings[key] = elapsed
            self.current_path.pop()

    def get_summary(self) -> dict[str, float]:
        """Get timing summary with all measurements.

        Returns:
            Dictionary mapping section names to elapsed seconds
        """
        return self.timings.copy()

    def get_total(self, prefix: str = "") -> float:
        """Get total time for sections matching prefix.

        Args:
            prefix: Only sum sections starting with this prefix

        Returns:
            Total seconds for matching sections
        """
        if not prefix:
            return sum(self.timings.values())

        return sum(
            time_val for key, time_val in self.timings.items() if key.startswith(prefix)
        )

    def format_summary(self, indent: int = 2) -> str:
        """Format timing summary as readable text.

        Args:
            indent: Number of spaces per indentation level

        Returns:
            Formatted timing summary
        """
        lines = [f"Timing Summary for '{self.name}':"]

        # Group by hierarchy
        sorted_keys = sorted(self.timings.keys())

        for key in sorted_keys:
            elapsed = self.timings[key]
            level = key.count("_")
            indent_str = " " * (indent * level)
            section_name = key.split("_")[-1]
            lines.append(f"{indent_str}{section_name}: {elapsed:.3f}s")

        return "\n".join(lines)

    def reset(self):
        """Clear all timing data."""
        self.timings.clear()
        self.current_path.clear()
        self._section_starts.clear()


class GlobalTimer:
    """Global timer accessible from anywhere in the codebase.

    This allows adding timing measurements without passing timer objects
    through the entire call stack.

    Example:
        >>> from igent.utils.timing import global_timer
        >>> with global_timer.section("my_function"):
        ...     do_work()
        >>> print(global_timer.get_summary())
    """

    _instance: Timer | None = None

    @classmethod
    def get_timer(cls) -> Timer:
        """Get or create the global timer instance."""
        if cls._instance is None:
            cls._instance = Timer("global")
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset the global timer."""
        if cls._instance is not None:
            cls._instance.reset()

    @classmethod
    def section(cls, section_name: str):
        """Context manager for timing a section.

        Args:
            section_name: Name of the section

        Returns:
            Context manager
        """
        return cls.get_timer().section(section_name)

    @classmethod
    def get_summary(cls) -> dict[str, float]:
        """Get timing summary.

        Returns:
            Dictionary of timing measurements
        """
        return cls.get_timer().get_summary()

    @classmethod
    def format_summary(cls) -> str:
        """Get formatted timing summary.

        Returns:
            Formatted string
        """
        return cls.get_timer().format_summary()


# Convenience instance
global_timer = GlobalTimer()
