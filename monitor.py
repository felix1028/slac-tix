#!/usr/bin/env python3
import base64
import datetime
import fcntl
import json
from pathlib import Path
import random
import re
import subprocess
import sys
import time
import urllib.request

# November 2026 SLAC tour slots ordered chronologically from earliest to latest
SLOTS = [
    ("Nov 13 10:30 AM", "2004248881357"),
    ("Nov 13 1:00 PM",  "2004249348755"),
    ("Nov 20 10:30 AM", "2004249650658"),
    ("Nov 20 1:00 PM",  "2004250219359"),
]
DISCOVERY_URLS = [
    "https://www6.slac.stanford.edu/news-and-events/events/public-tours",
    "https://www.eventbrite.com/o/slac-communications-9991103564",
]
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
SERVER_DATA_RE = re.compile(r"window\.__SERVER_DATA__\s*=\s*(\{.*?\});\s*</script>", re.S)


def prompt_reservations() -> list[dict]:
    """Prompts for visitor details on startup and groups them into reservations of up to 2 tickets."""
    while True:
        raw = input("Total number of visitors (1-4) [2]: ").strip() or "2"
        if raw.isdigit() and 1 <= int(raw) <= 4:
            total = int(raw)
            break
        print("Please enter a number between 1 and 4.")

    visitors = []
    for i in range(1, total + 1):
        print(f"\n--- Visitor #{i} (must match government-issued photo ID) ---")
        first = input(f"  First name: ").strip()
        last = input(f"  Last name:  ").strip()
        email = input(f"  Email:      ").strip()
        phone = input(f"  Phone:      ").strip()
        visitors.append({"first": first, "last": last, "email": email, "phone": phone})

    reservations = []
    for idx in range(0, len(visitors), 2):
        group = visitors[idx : idx + 2]
        reservations.append({"buyer": group[0], "attendees": group})
    return reservations


def encode_payload(reservation: dict) -> str:
    raw = json.dumps(reservation, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def discover_slots() -> list[tuple[str, str]]:
    """Returns configured SLOTS plus any new Eventbrite IDs on SLAC's website or organizer page."""
    seen = {eid for _, eid in SLOTS}
    slots = list(SLOTS)
    for page_url in DISCOVERY_URLS:
        try:
            html = fetch(page_url)
            for eid in re.findall(r"eventbrite\.com/e/(?:[a-z0-9-]+-)?(\d{10,15})", html):
                if eid not in seen:
                    seen.add(eid)
                    slots.append((f"Discovered {eid}", eid))
        except Exception as exc:
            print(f"[WARN] Discovery failed on {page_url}: {exc}", flush=True)
    return slots


def has_available_tickets(eid: str, qty: int) -> bool:
    url = f"https://www.eventbrite.com/checkout-external?eid={eid}"
    html = fetch(url)
    match = SERVER_DATA_RE.search(html)
    if not match:
        return False
    data = json.loads(match.group(1))
    for ticket in data.get("tickets", []):
        status = ticket.get("on_sale_status")
        options = ticket.get("ticket_options_range") or []
        if status == "AVAILABLE" and qty in options:
            return True
    return False


def main(timeout_minutes: int = 15) -> None:
    lock_file = open("/tmp/slac_monitor.lock", "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("[INFO] monitor.py is already running in another process. Exiting.", flush=True)
        sys.exit(0)

    reservations = prompt_reservations()
    min_qty_needed = len(reservations[0]["attendees"])

    now = datetime.datetime.now()
    start_target = now.replace(hour=8, minute=57, second=0, microsecond=0)
    if now < start_target:
        wait_seconds = (start_target - now).total_seconds()
        print(f"\n[INFO] Standing by until 08:57:00 AM PT ({int(wait_seconds // 60)}m {int(wait_seconds % 60)}s)...", flush=True)
        time.sleep(wait_seconds)

    deadline = time.time() + (timeout_minutes * 60)
    slots = discover_slots()
    print(f"\n[INFO] Polling {len(slots)} SLAC slots for {len(reservations)} reservation(s)...", flush=True)

    profiles = [
        str(Path.home() / "Library/Application Support/Google/Chrome"),
        str(Path.home() / ".chrome-slac-pair2"),
    ]

    while time.time() < deadline:
        for label, eid in slots:
            try:
                if has_available_tickets(eid, min_qty_needed):
                    base = f"https://www.eventbrite.com/checkout-external?eid={eid}"
                    print(f"[LIVE] {label} ({eid}) is open! Launching Chrome...", flush=True)
                    for res, profile in zip(reservations, profiles):
                        b64 = encode_payload(res)
                        subprocess.Popen([
                            "open", "-na", "Google Chrome", "--args",
                            f"--user-data-dir={profile}", f"{base}#slac_payload={b64}",
                        ])
                    subprocess.Popen(["afplay", "/System/Library/Sounds/Glass.aiff"])
                    subprocess.Popen(["say", f"SLAC tickets live for {label}"])
                    return
            except Exception as exc:
                print(f"[WARN] {label} ({eid}): {exc}", flush=True)
        time.sleep(random.uniform(2.0, 3.5))

    print("[TIMEOUT] Polling window ended.", flush=True)


if __name__ == "__main__":
    main()
