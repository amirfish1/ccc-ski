#!/usr/bin/env python3
"""Hotel search for the Ski app: Google Hotels and Airbnb for one stay.

    python3 hotel_search.py search --checkin 2026-12-18 --checkout 2026-12-20 \
        --adults 2 --children 2 --child-age 7 --child-age 10 --area valley
    python3 hotel_search.py details <key> --checkin ... --checkout ...
    python3 hotel_search.py areas

`search` prints one JSON object: {"results": [{place, source, total, nightly,
link, cancel, ...}], "errors": [...]}. Prices are before taxes and fees.
`details` takes the "key" of a Google Hotels result and lists each booking
site's rate with its cancellation terms. Areas are defined in areas.json.

It uses the tools setup.py installs into .venv (stays and pyairbnb). It only
reads public search results: no login, no booking, no payment.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
VENV = HERE / ".venv"
VENV_BIN = VENV / ("Scripts" if (VENV / "Scripts").exists() else "bin")


def use_venv():
    """Re-run under the app's own Python so `python3 hotel_search.py` just works."""
    py = VENV_BIN / ("python.exe" if os.name == "nt" else "python")
    if not py.exists():
        sys.exit("The hotel search tools are not installed yet. Run: python3 setup.py")
    if Path(sys.prefix).resolve() != VENV.resolve():
        os.execv(str(py), [str(py), str(Path(__file__).resolve())] + sys.argv[1:])


def load_areas():
    data = json.loads((HERE / "areas.json").read_text(encoding="utf-8"))
    return data.get("areas", {}), data.get("default")


def stays_cli(args, timeout=150):
    exe = VENV_BIN / ("stays.exe" if os.name == "nt" else "stays")
    out = subprocess.run([str(exe)] + args + ["--format", "json"],
                         capture_output=True, text=True, timeout=timeout)
    try:
        data = json.loads(out.stdout)
    except ValueError:
        tail = [ln for ln in (out.stderr or out.stdout).splitlines() if ln.strip()]
        raise RuntimeError(tail[-1] if tail else "no answer from Google Hotels")
    if not data.get("success", True):
        raise RuntimeError(str(data.get("error") or "Google Hotels search failed"))
    return data


def guest_args(a):
    args = ["--check-in", a.checkin, "--check-out", a.checkout, "--adults", str(a.adults),
            "--currency", a.currency]
    if a.children:
        ages = list(a.child_age or [])
        ages += [10] * (a.children - len(ages))  # Google needs an age per child
        args += ["--children", str(a.children)]
        for age in ages[:a.children]:
            args += ["--child-age", str(age)]
    return args


def search_hotels(a, area, nights):
    args = ["search", area["query"]] + guest_args(a) + ["--max-results", "25"]
    if a.free_cancel:
        args.append("--free-cancellation")
    rows = []
    for h in stays_cli(args).get("hotels") or []:
        nightly = h.get("display_price")
        if nightly is None:
            continue
        rows.append({
            "place": h.get("name"),
            "source": "Google Hotels",
            "total": round(nightly * nights),
            "nightly": nightly,
            "link": "https://www.google.com/travel/search?q=" + quote(str(h.get("name") or "")),
            "cancel": "Free cancellation on at least one rate; run details for the date"
                      if a.free_cancel else None,
            "rating": h.get("overall_rating"),
            "key": h.get("entity_key"),
        })
    return rows


def search_airbnb(a, area, nights):
    import pyairbnb
    ne_lat, ne_lng, sw_lat, sw_lng = area["box"]
    try:
        found = pyairbnb.search_all(
            check_in=a.checkin, check_out=a.checkout,
            ne_lat=ne_lat, ne_long=ne_lng, sw_lat=sw_lat, sw_long=sw_lng,
            zoom_value=int(area.get("zoom", 12)), price_min=0, price_max=0,
            free_cancellation=bool(a.free_cancel), adults=a.adults, children=a.children,
            currency=a.currency, hash=pyairbnb.fetch_stays_search_hash())
    except Exception as e:
        if "429" in str(e):
            raise RuntimeError("Airbnb is refusing searches from this computer right now "
                               "(too many recent requests). Try again in an hour.")
        raise
    return airbnb_rows(found, a, nights)


def airbnb_rows(found, a, nights):
    """Airbnb's raw search rows -> the compact rows this tool prints."""
    rows, seen = [], set()
    for x in found:
        rid = str(x.get("room_id") or "")
        unit = (x.get("price") or {}).get("unit") or {}
        # "discount" is the price after discounts when there is one; both cover the whole stay.
        total = unit.get("discount") or unit.get("amount")
        if not rid or rid in seen or not total:
            continue
        seen.add(rid)
        pay = "; ".join(m.get("text", "") for m in x.get("paymentMessages") or [] if m.get("text"))
        rows.append({
            "place": x.get("name") or x.get("title"),
            "source": "Airbnb",
            "total": round(total),
            "nightly": round(total / nights),
            "link": "https://www.airbnb.com/rooms/%s?check_in=%s&check_out=%s&adults=%d&children=%d"
                    % (rid, a.checkin, a.checkout, a.adults, a.children),
            "cancel": "Free cancellation; read the exact date on the listing"
                      if a.free_cancel or "free cancellation" in pay.lower() else None,
            "pay": pay or None,
            "rating": (x.get("rating") or {}).get("value"),
            "kind": x.get("title"),
        })
    return rows


def cmd_search(a):
    areas, default = load_areas()
    name = a.area or default
    if name not in areas:
        sys.exit("Unknown area %r. Choose one of: %s" % (name, ", ".join(areas)))
    area = areas[name]
    nights = (date.fromisoformat(a.checkout) - date.fromisoformat(a.checkin)).days
    if nights < 1:
        sys.exit("Check-out must be after check-in.")
    results, errors = [], []
    for source, fn in (("hotels", search_hotels), ("airbnb", search_airbnb)):
        if a.source not in (source, "both"):
            continue
        try:
            results += fn(a, area, nights)
        except Exception as e:  # one source failing must not lose the other
            errors.append("%s: %s" % (source, str(e)[:200]))
    if a.max_nightly:
        results = [r for r in results if r["nightly"] <= a.max_nightly]
    results.sort(key=lambda r: r["total"])
    print(json.dumps({
        "checkin": a.checkin, "checkout": a.checkout, "nights": nights,
        "guests": {"adults": a.adults, "children": a.children},
        "area": area.get("label") or name,
        "prices": "before taxes and fees, in " + a.currency,
        "count": len(results), "results": results[:a.limit], "errors": errors,
    }, indent=1, ensure_ascii=False))


def cmd_details(a):
    data = stays_cli(["details", a.key, "--check-in", a.checkin, "--check-out", a.checkout,
                      "--currency", a.currency])
    h = data.get("hotel") or {}
    rates = []
    for room in h.get("rooms") or []:
        for r in room.get("rates") or []:
            rates.append({"room": room.get("name"), "site": r.get("provider"),
                          "nightly": r.get("price"), "cancel": r.get("cancellation"),
                          "taxes_included": r.get("includes_taxes_and_fees"),
                          "link": r.get("deeplink_url")})
    print(json.dumps({"place": h.get("name"), "address": h.get("address"), "phone": h.get("phone"),
                      "check_in_time": h.get("check_in_time"), "check_out_time": h.get("check_out_time"),
                      "rates": rates}, indent=1, ensure_ascii=False))


def cmd_areas(_):
    areas, default = load_areas()
    print(json.dumps({"default": default,
                      "areas": {k: v.get("label") for k, v in areas.items()}}, indent=1))


def main():
    p = argparse.ArgumentParser(description="Search Google Hotels and Airbnb for one stay.")
    sub = p.add_subparsers(dest="cmd", required=True)

    def stay(sp):
        sp.add_argument("--checkin", required=True, help="YYYY-MM-DD")
        sp.add_argument("--checkout", required=True, help="YYYY-MM-DD")
        sp.add_argument("--currency", default="USD")

    s = sub.add_parser("search", help="list places and prices for a stay")
    stay(s)
    s.add_argument("--adults", type=int, default=2)
    s.add_argument("--children", type=int, default=0)
    s.add_argument("--child-age", type=int, action="append", help="repeat once per child")
    s.add_argument("--area", help="a name from areas.json (default: its 'default')")
    s.add_argument("--source", choices=["hotels", "airbnb", "both"], default="both")
    s.add_argument("--free-cancel", action="store_true", help="only free-cancellation offers")
    s.add_argument("--max-nightly", type=float, help="drop anything above this per night")
    s.add_argument("--limit", type=int, default=20)
    s.set_defaults(fn=cmd_search)

    d = sub.add_parser("details", help="each booking site's rate and cancellation for one hotel")
    d.add_argument("key", help='the "key" of a Google Hotels result')
    stay(d)
    d.set_defaults(fn=cmd_details)

    sub.add_parser("areas", help="list the search areas").set_defaults(fn=cmd_areas)

    a = p.parse_args()
    if a.cmd != "areas":
        use_venv()
    a.fn(a)


if __name__ == "__main__":
    main()
