# SLAC Public Tour Ticket Assistant — User Guide

Automated detection and browser checkout for **SLAC National Accelerator Laboratory** public tours on Eventbrite (released the **first Friday of each month at 9:00:00 AM PT**, maximum 2 tickets per reservation).

## Files

- **[monitor.py](monitor.py)** — Prompts you interactively on startup for the number of visitors (1–4) and each visitor's legal name, email, and phone number. Groups them into reservations of up to 2 tickets, waits until `8:57:00 AM PT`, and polls SLAC's tour slots in chronological order (`Earliest` → `Latest`). As soon as a slot has available tickets, it passes each reservation's payload via URL hash (`#slac_payload=<base64>`) into separate Chrome profiles (`Pair 1` and `Pair 2`).
- **[autofill.user.js](autofill.user.js)** — Generic Tampermonkey userscript containing **zero personal information**. Reads `#slac_payload=<base64>` from the URL hash, selects the required ticket quantity (`1` or `2`), clicks `Register`, populates Buyer and Attendee fields, checks required SLAC waivers, and clicks the final `Register` button immediately (`0ms`).

---

## 1. One-Time Setup (Install Generic Userscript Once)

Because [autofill.user.js](autofill.user.js) contains no hardcoded personal data, you only need to install it once in each Chrome profile and never edit it again:

1. **Profile 1 (Regular Chrome):**
   - Install [Tampermonkey](https://chromewebstore.google.com/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo).
   - Open `chrome://extensions`, click **Details** on Tampermonkey, and toggle **Allow User Scripts** (or **Developer mode** in the top right) **ON**.
   - Click the Tampermonkey icon → **Create a new script**, paste [autofill.user.js](autofill.user.js), and press `Cmd + S` to save.

2. **Profile 2 (Isolated Second Chrome Window — only needed if booking 3–4 tickets):**
   - Open the second Chrome profile from Terminal:
     ```bash
     open -na "Google Chrome" --args --user-data-dir="$HOME/.chrome-slac-pair2" "https://chromewebstore.google.com/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo"
     ```
   - Install Tampermonkey, enable **Allow User Scripts** in `chrome://extensions`, and save [autofill.user.js](autofill.user.js).

---

## 2. Running on Release Day (First Friday of the Month)

Run this in Terminal from the project directory anytime on Friday morning before `9:00:00 AM PT`:

```bash
/usr/bin/caffeinate -dims -t 6600 /usr/bin/python3 monitor.py
```

1. **Enter Visitor Details When Prompted:**
   - Enter the total number of visitors (`1` to `4`).
   - Enter each visitor's **First Name**, **Last Name** (must match the physical government-issued REAL ID or passport presented at the SLAC gate), **Email**, and **Phone**.
2. **Leave Laptop Open & Chrome Windows Open:**
   - `monitor.py` keeps your Mac awake (`caffeinate`), waits until `8:57:00 AM PT`, and polls every 2–3.5 seconds until tickets open at `9:00:00 AM PT`.
   - When tickets go live, Chrome opens automatically and fills out the checkout form from your startup inputs.
