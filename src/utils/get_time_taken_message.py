"""Time and performance utilities"""

import time


def get_time_taken_message(start_time: float) -> str:
    """Returns a message showing how long the operation took"""
    elapsed = int(time.perf_counter() - start_time)
    minutes, seconds = divmod(elapsed, 60)
    time_str = (
        f"{minutes} minute{'s' if minutes != 1 else ''} " if minutes else ""
    ) + f"{seconds} second{'s' if seconds != 1 else ''}"

    return f"🤖 Time taken for this response: {time_str}"