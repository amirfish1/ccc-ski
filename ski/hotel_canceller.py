#!/usr/bin/env python3
"""Hotel Canceller: warn before a booking stops being refundable.

Reads bookings.json: [{"hotel", "checkin", "checkout", "free_cancel_until"}]
(dates as YYYY-MM-DD, Pacific). Prints one JSON line for the app's routine
card; "alert" turns the card red and sends a notification.
"""
import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

WARN_DAYS = 3  # start warning this many days before the deadline

today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
bookings = json.loads((Path(__file__).parent / "bookings.json").read_text() or "[]")
urgent, later = [], []
for b in bookings:
    try:
        deadline = date.fromisoformat(str(b["free_cancel_until"]))
    except (KeyError, ValueError):
        continue
    left = (deadline - today).days
    if left < 0 or b.get("keep"):
        continue
    (urgent if left <= WARN_DAYS else later).append((left, b["hotel"], deadline))

fmt = lambda d: d.strftime("%a %b %-d")
if urgent:
    urgent.sort()
    lines = [f"{h}: free cancel ends {'today' if n == 0 else 'tomorrow' if n == 1 else 'in ' + str(n) + ' days'} ({fmt(d)})" for n, h, d in urgent]
    out = {"summary": "; ".join(lines), "alert": True,
           "notify": {"title": "Hotel Canceller: decide on " + urgent[0][1], "body": "; ".join(lines)}}
elif later:
    later.sort()
    n, h, d = later[0]
    out = {"summary": f"Nothing urgent. Next deadline: {h}, {fmt(d)} ({n} days)."}
else:
    out = {"summary": "No refundable bookings to watch yet."}
print(json.dumps(out))
