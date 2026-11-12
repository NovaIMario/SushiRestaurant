// Booking form: fill the time list for the chosen date and the guest list for the chosen kind.
// The server re-checks everything; this only makes the form pleasant to fill in.
(() => {
  const B = window.BOOKING;
  const form = document.getElementById("booking-form");
  const day = document.getElementById("day");
  const at = document.getElementById("at");
  const party = document.getElementById("party");
  const hint = document.getElementById("private-hint");
  const KEYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];  // Date.getDay() order

  const option = (value, text, selected) => {
    const o = document.createElement("option");
    o.value = value; o.textContent = text; o.selected = !!selected;
    return o;
  };

  function fillTimes() {
    const keep = at.value || at.dataset.selected;
    at.dataset.selected = "";
    at.replaceChildren();
    if (!day.value) { at.append(option("", B.pickText)); at.disabled = true; return; }
    const [y, m, d] = day.value.split("-").map(Number);
    let slots = B.slots[KEYS[new Date(y, m - 1, d).getDay()]] || [];
    if (day.value === B.today) {
      // Same rule as the server: at least 30 minutes' notice for a booking today.
      const now = new Date(), soon = new Date(now.getTime() + 30 * 60000);
      const cutoff = soon.toDateString() === now.toDateString()
        ? `${String(soon.getHours()).padStart(2, "0")}:${String(soon.getMinutes()).padStart(2, "0")}` : "24:00";
      slots = slots.filter(s => s >= cutoff);
    }
    if (!slots.length) { at.append(option("", B.closedText)); at.disabled = true; return; }
    at.disabled = false;
    slots.forEach(s => at.append(option(s, s, s === keep)));
  }

  function fillParty() {
    const kind = form.querySelector('input[name="kind"]:checked').value;
    const [lo, hi] = B.limits[kind];
    const keep = Number(party.value || party.dataset.selected);
    party.dataset.selected = "";
    party.replaceChildren();
    for (let n = lo; n <= hi; n++) party.append(option(n, n, n === keep));
    if (!party.value || keep < lo || keep > hi) party.value = String(kind === "table" ? Math.max(lo, 2) : lo);
    hint.hidden = kind !== "private";
  }

  day.addEventListener("change", fillTimes);
  form.querySelectorAll('input[name="kind"]').forEach(r => r.addEventListener("change", fillParty));
  fillTimes();
  fillParty();
})();
