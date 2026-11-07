// ==UserScript==
// @name         SLAC Eventbrite Checkout Assistant
// @namespace    http://tampermonkey.net/
// @version      2.0
// @match        https://www.eventbrite.com/checkout-external*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function () {
  "use strict";

  // Capture base64-encoded visitor payload from URL hash and persist across waiting-room redirects
  const hashMatch = location.hash.match(/slac_payload=([A-Za-z0-9_-]+)/);
  if (hashMatch) {
    const b64 = hashMatch[1].replace(/-/g, "+").replace(/_/g, "/");
    sessionStorage.setItem("slac_payload_json", atob(b64));
  }

  const rawPayload = sessionStorage.getItem("slac_payload_json");
  if (!rawPayload) return;

  const { buyer: BUYER, attendees: ATTENDEES } = JSON.parse(rawPayload);
  const TICKET_QTY = ATTENDEES.length;

  function setReactValue(el, value) {
    if (!el || el.value === String(value)) return;
    const proto = el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
    if (setter) setter.call(el, String(value));
    else el.value = String(value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.dispatchEvent(new Event("blur", { bubbles: true }));
  }

  function step() {
    // Step 1: On the ticket-selection screen, increment stepper to TICKET_QTY (if + button is enabled), then click Register
    const isTicketScreen = document.querySelector('[data-spec="checkout-widget-tickets-page"], [data-testid="eds-stepper"]');
    if (isTicketScreen) {
      const addBtn = document.querySelector('button[data-testid="eds-stepper-increase-button"], button[aria-label="Increase"]');
      const countEl = document.querySelector('[data-testid="eds-stepper-quantity"]');
      const currentQty = countEl ? parseInt(countEl.textContent || countEl.getAttribute("aria-valuenow") || "1", 10) : 1;
      const canIncrease = addBtn && !addBtn.disabled && addBtn.getAttribute("aria-disabled") !== "true";

      if (currentQty < TICKET_QTY && canIncrease) {
        addBtn.click();
        return;
      }

      const proceedBtn = document.querySelector('button[data-testid="eds-modal__primary-button"], button[data-spec="eds-modal__primary-button"]');
      if (proceedBtn && !proceedBtn.disabled && !proceedBtn.dataset.clicked) {
        proceedBtn.dataset.clicked = "1";
        proceedBtn.click();
      }
      return;
    }

    // Step 2: Populate Buyer + per-Attendee inputs
    const inputs = document.querySelectorAll("input:not([type='hidden'])");
    if (!inputs.length) return;

    setReactValue(document.querySelector('input[name*="buyer"][name*="first_name"], input[id*="buyer"][id*="first_name"]'), BUYER.first);
    setReactValue(document.querySelector('input[name*="buyer"][name*="last_name"], input[id*="buyer"][id*="last_name"]'), BUYER.last);
    setReactValue(document.querySelector('input[name*="buyer"][name*="email"], input[id*="buyer"][id*="email"]'), BUYER.email);
    setReactValue(document.querySelector('input[name*="confirmEmail"], input[id*="confirmEmail"]'), BUYER.email);

    const firsts = document.querySelectorAll('input[name*="first_name"]:not([name*="buyer"])');
    const lasts = document.querySelectorAll('input[name*="last_name"]:not([name*="buyer"])');
    const emails = document.querySelectorAll('input[name*="email"]:not([name*="buyer"]):not([name*="confirm"])');
    const phones = document.querySelectorAll('input[type="tel"], input[name*="phone"]');

    ATTENDEES.forEach((att, i) => {
      if (firsts[i]) setReactValue(firsts[i], att.first);
      if (lasts[i]) setReactValue(lasts[i], att.last);
      if (emails[i]) setReactValue(emails[i], att.email);
      if (phones[i]) setReactValue(phones[i], att.phone);
    });

    // Step 3: Check SLAC safety/waiver/ID/age checkboxes & radios (skip marketing & copyBilling checkboxes)
    document.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
      const label = (cb.closest("label")?.textContent || document.querySelector(`label[for="${cb.id}"]`)?.textContent || "").toLowerCase();
      const isMarketingOrCopy = /marketing|optin|copybilling/i.test(cb.name + cb.id) || /marketing|newsletter|keep me updated|promotions|eventbrite emails/i.test(label);
      if (!isMarketingOrCopy && (cb.required || /waiver|safety|agree|id|12|18|shoe|bag|acknowledge|terms/i.test(label))) {
        if (!cb.checked) cb.click();
      }
    });

    document.querySelectorAll('input[type="radio"]').forEach((rb) => {
      const label = (rb.closest("label")?.textContent || document.querySelector(`label[for="${rb.id}"]`)?.textContent || "").trim();
      if (/^(yes|i agree|i acknowledge|18\+|adult)/i.test(label) && !rb.checked) {
        rb.click();
      }
    });

    // Step 4: Immediate (0ms) single-fire submit once attendee fields are populated
    const submitBtn = Array.from(document.querySelectorAll('button[type="submit"], button[data-spec="eds-modal__primary-button"]')).find(
      (b) => /register|complete order|place order/i.test((b.textContent || "").trim()) && !b.disabled
    );
    if (submitBtn && !submitBtn.dataset.submitted && firsts.length >= 1 && firsts[0].value) {
      submitBtn.dataset.submitted = "1";
      submitBtn.click();
    }
  }

  setInterval(step, 250);
})();
