"""LangChain tool to generate Grafana-compatible time ranges."""

from datetime import datetime, timedelta
import logging
from langchain.tools import tool

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@tool
def get_time_range(
    day: str = "today",
    start_date: str = None,
    end_date: str = None,
    last_n_days: int = None,
) -> str:
    """
    Generate a Grafana-compatible time range.
    Supports:
    - 'today', 'yesterday', or any specific date in 'YYYY-MM-DD' format (via 'day')
    - Custom range: provide 'start_date' and 'end_date' in 'YYYY-MM-DD' format
    - Relative range: provide 'last_n_days' (e.g., 7 for last 7 days)
    Returns a string like: 'From YYYY-MM-DD 00:00:00 To YYYY-MM-DD 23:59:59'
    """

    if last_n_days is not None:
        end = datetime.today()
        start = end - timedelta(days=last_n_days - 1)
        start_str = start.strftime("%Y-%m-%d") + " 00:00:00"
        end_str = end.strftime("%Y-%m-%d") + " 23:59:59"
        result = f"From {start_str} To {end_str}"
        return result

    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            logger.warning("❌ Invalid date format for start_date or end_date")
            return "Invalid date format. Use 'YYYY-MM-DD'."
        start_str = start.strftime("%Y-%m-%d") + " 00:00:00"
        end_str = end.strftime("%Y-%m-%d") + " 23:59:59"
        result = f"From {start_str} To {end_str}"
        return result

    # Fallback to single day logic
    if day.lower() == "today":
        date = datetime.today()
    elif day.lower() == "yesterday":
        date = datetime.today() - timedelta(days=1)
    else:
        try:
            date = datetime.strptime(day, "%Y-%m-%d")
        except ValueError:
            logger.warning("❌ Invalid date format passed to get_time_range")
            return "Invalid date format. Use 'YYYY-MM-DD'."

    start = date.strftime("%Y-%m-%d") + " 00:00:00"
    end = date.strftime("%Y-%m-%d") + " 23:59:59"
    result = f"From {start} To {end}"

    return result
