"""
=============================================================================
ECONOMIC CALENDAR — High-Impact News Event Tracker
=============================================================================
Maintains a hardcoded calendar of major US economic events (FOMC, CPI, NFP,
etc.) and determines when the bot should enter "Sniper Mode" (10-second
scan intervals) versus normal 15-minute cycles.

NO external API required — dates are maintained manually from publicly
available economic calendars (BLS, FED, etc.).

Methods expected by main.py:
  - fetch_calendar()                          → loads / refreshes events
  - get_upcoming_high_impact_events(minutes)  → list of upcoming events
  - generate_pre_event_bias(events)           → bias string for LLM
  - is_news_sniper_window()                   → True if near a high-impact event
=============================================================================
"""

from datetime import datetime, timedelta, timezone
from typing import Optional


# =============================================================================
# HIGH-IMPACT EVENT DEFINITIONS
# =============================================================================
# Each event: (month, day, hour_utc, minute_utc, name, impact)
# Times are in UTC. Update these quarterly from forexfactory.com or similar.
# =============================================================================

# 2026 Major US Economic Calendar (approximate — update as real dates are confirmed)
HIGH_IMPACT_EVENTS_2026 = [
    # ── AUGUST 2026 ──────────────────────────────────────────────────
    (8, 1,  12, 30, "NFP (Non-Farm Payrolls)",          "HIGH"),
    (8, 5,  14, 0,  "ISM Services PMI",                 "MEDIUM"),
    (8, 13, 12, 30, "CPI (Consumer Price Index)",       "HIGH"),
    (8, 14, 12, 30, "PPI (Producer Price Index)",       "MEDIUM"),
    (8, 27, 14, 0,  "Consumer Confidence Index",        "MEDIUM"),
    (8, 29, 12, 30, "GDP (Gross Domestic Product) Q2",  "HIGH"),

    # ── SEPTEMBER 2026 ───────────────────────────────────────────────
    (9, 4,  12, 30, "NFP (Non-Farm Payrolls)",          "HIGH"),
    (9, 10, 12, 30, "CPI (Consumer Price Index)",       "HIGH"),
    (9, 11, 12, 30, "PPI (Producer Price Index)",       "MEDIUM"),
    (9, 16, 18, 0,  "FOMC Interest Rate Decision",     "HIGH"),
    (9, 16, 18, 30, "FOMC Press Conference (Powell)",   "HIGH"),

    # ── OCTOBER 2026 ────────────────────────────────────────────────
    (10, 2,  12, 30, "NFP (Non-Farm Payrolls)",         "HIGH"),
    (10, 13, 12, 30, "CPI (Consumer Price Index)",      "HIGH"),
    (10, 14, 12, 30, "PPI (Producer Price Index)",      "MEDIUM"),
    (10, 29, 12, 30, "GDP (Gross Domestic Product) Q3", "HIGH"),

    # ── NOVEMBER 2026 ───────────────────────────────────────────────
    (11, 4,  18, 0,  "FOMC Interest Rate Decision",    "HIGH"),
    (11, 4,  18, 30, "FOMC Press Conference (Powell)",  "HIGH"),
    (11, 6,  12, 30, "NFP (Non-Farm Payrolls)",         "HIGH"),
    (11, 12, 12, 30, "CPI (Consumer Price Index)",      "HIGH"),
    (11, 13, 12, 30, "PPI (Producer Price Index)",      "MEDIUM"),

    # ── DECEMBER 2026 ───────────────────────────────────────────────
    (12, 4,  12, 30, "NFP (Non-Farm Payrolls)",         "HIGH"),
    (12, 10, 12, 30, "CPI (Consumer Price Index)",      "HIGH"),
    (12, 11, 12, 30, "PPI (Producer Price Index)",      "MEDIUM"),
    (12, 16, 18, 0,  "FOMC Interest Rate Decision",    "HIGH"),
    (12, 16, 18, 30, "FOMC Press Conference (Powell)",  "HIGH"),
]


class EconomicCalendar:
    """
    Tracks high-impact US economic events for Sniper Mode activation.

    The calendar is hardcoded (no API needed) and should be updated
    quarterly. The bot checks this calendar every loop iteration to
    decide if it should switch to 10-second high-frequency scanning.
    """

    # How many minutes before/after a high-impact event to enter Sniper Mode
    SNIPER_WINDOW_BEFORE_MINUTES = 0
    SNIPER_WINDOW_AFTER_MINUTES  = 60

    def __init__(self):
        self.events: list[dict] = []
        self._loaded = False

    def fetch_calendar(self):
        """
        Load the hardcoded calendar into memory.
        Call this once at startup.
        """
        now = datetime.now(timezone.utc)
        current_year = now.year

        self.events = []
        for month, day, hour, minute, name, impact in HIGH_IMPACT_EVENTS_2026:
            try:
                event_dt = datetime(current_year, month, day, hour, minute)
                self.events.append({
                    "datetime": event_dt,
                    "name":     name,
                    "impact":   impact,
                })
            except ValueError:
                # Skip invalid dates (e.g., Feb 30)
                continue

        # Sort by datetime
        self.events.sort(key=lambda e: e["datetime"])
        self._loaded = True

        # Count upcoming
        upcoming = [e for e in self.events if e["datetime"] > now]
        print(f"    [CALENDAR] Economic Calendar: {len(self.events)} events loaded, "
              f"{len(upcoming)} upcoming")

    def get_upcoming_high_impact_events(
        self, minutes_ahead: int = 60
    ) -> list[dict]:
        """
        Returns high-impact events happening within `minutes_ahead` from now.
        """
        if not self._loaded:
            return []

        now = datetime.now(timezone.utc)
        window_end = now + timedelta(minutes=minutes_ahead)

        upcoming = []
        for event in self.events:
            if event["impact"] != "HIGH":
                continue
            if now <= event["datetime"] <= window_end:
                mins_until = (event["datetime"] - now).total_seconds() / 60
                upcoming.append({
                    **event,
                    "minutes_until": round(mins_until, 1),
                })

        return upcoming

    def generate_pre_event_bias(
        self, upcoming_events: list[dict]
    ) -> Optional[str]:
        """
        Generate a bias warning string for the LLM based on upcoming events.
        Returns None if no upcoming events.
        """
        if not upcoming_events:
            return None

        lines = ["=== ⚠️ HIGH-IMPACT NEWS ALERT ==="]
        for event in upcoming_events:
            lines.append(
                f"  🔴 {event['name']} in ~{event['minutes_until']:.0f} minutes "
                f"(Impact: {event['impact']})"
            )

        lines.append(
            "\n⚠️ WARNING: Market will be extremely volatile. "
            "Widen stops or HOLD until the number is released. "
            "Do NOT enter a trade 15 minutes before the event unless "
            "you have a high-confidence directional bias from the data."
        )

        return "\n".join(lines)

    def is_news_sniper_window(self) -> bool:
        """
        Returns True if we are within the sniper window of ANY
        high-impact event (15 min before → 30 min after).
        This is checked every second in the main loop.
        """
        if not self._loaded:
            return False

        now = datetime.now(timezone.utc)

        for event in self.events:
            if event["impact"] != "HIGH":
                continue

            event_start = event["datetime"] - timedelta(
                minutes=self.SNIPER_WINDOW_BEFORE_MINUTES
            )
            event_end = event["datetime"] + timedelta(
                minutes=self.SNIPER_WINDOW_AFTER_MINUTES
            )

            if event_start <= now <= event_end:
                return True

        return False

    def get_next_event(self) -> Optional[dict]:
        """Get the next upcoming event (any impact level)."""
        if not self._loaded:
            return None

        now = datetime.now(timezone.utc)
        for event in self.events:
            if event["datetime"] > now:
                mins_until = (event["datetime"] - now).total_seconds() / 60
                return {**event, "minutes_until": round(mins_until, 1)}

        return None
