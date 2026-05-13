(function () {
  "use strict";

  // Pick 2 distinct items from pool at random.
  function pickTwo(pool) {
    if (!pool || pool.length < 2) return (pool || []).slice(0, 2);
    const copy = pool.slice();
    const i1 = Math.floor(Math.random() * copy.length);
    const item1 = copy.splice(i1, 1)[0];
    const item2 = copy[Math.floor(Math.random() * copy.length)];
    return [item1, item2];
  }

  function esc(str) {
    const d = document.createElement("div");
    d.appendChild(document.createTextNode(str == null ? "" : String(str)));
    return d.innerHTML;
  }

  function buildCardHtml(item) {
    const imageHtml = item.image
      ? `<img src="${esc(item.image)}" alt="${esc(item.name)}">`
      : `<div class="loot-card-placeholder"></div>`;
    return `
      <button class="loot-card" data-item-id="${esc(item.id)}" aria-pressed="false">
        <div class="loot-card-image">${imageHtml}</div>
        <div class="loot-card-body">
          <h3 class="loot-card-name">${esc(item.name)}</h3>
          <p class="loot-card-desc">${esc(item.description)}</p>
        </div>
      </button>`;
  }

  function showLootModal(challengeId) {
    const pool = window.lootPool;
    if (!pool || pool.length < 2) return;

    const items = pickTwo(pool);
    let selectedItemId = null;

    const overlay = document.createElement("div");
    overlay.id = "loot-modal-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-labelledby", "loot-modal-title");

    overlay.innerHTML = `
      <div class="loot-modal">
        <h2 id="loot-modal-title" class="loot-title">Choose Your Reward</h2>
        <p class="loot-subtitle">Pick one item to claim from this solve</p>
        <div class="loot-cards">
          ${items.map(buildCardHtml).join("")}
        </div>
        <button id="loot-claim-btn" class="loot-claim-btn" disabled>Claim</button>
      </div>`;

    document.body.appendChild(overlay);

    const cards = overlay.querySelectorAll(".loot-card");

    cards.forEach(function (card) {
      card.addEventListener("click", function () {
        cards.forEach(function (c) {
          c.classList.remove("selected", "dimmed");
          c.setAttribute("aria-pressed", "false");
        });
        card.classList.add("selected");
        card.setAttribute("aria-pressed", "true");
        cards.forEach(function (c) {
          if (c !== card) c.classList.add("dimmed");
        });
        selectedItemId = card.dataset.itemId;
        document.getElementById("loot-claim-btn").disabled = false;
      });
    });

    document.getElementById("loot-claim-btn").addEventListener("click", async function () {
      if (!selectedItemId) return;
      const btn = document.getElementById("loot-claim-btn");
      btn.disabled = true;
      btn.textContent = "Claiming…";
      try {
        await window.CTFd.fetch("/api/v1/loot/claim", {
          method: "POST",
          body: JSON.stringify({ challenge_id: challengeId, item_id: selectedItemId }),
        });
      } catch (err) {
        console.error("[loot] Claim request failed:", err);
      }
      overlay.remove();
    });
  }

  // page.js (defer, earlier in DOM) sets window.CTFd before this deferred script runs.
  const orig = window.CTFd.pages.challenge.submitChallenge;
  window.CTFd.pages.challenge.submitChallenge = async function (challengeId, submission) {
    const response = await orig(challengeId, submission);
    if (response && response.data && response.data.status === "correct") {
      showLootModal(challengeId);
    }
    return response;
  };

  // Dev helper: window.__lootTest(challengeId?) — trigger the modal directly.
  window.__lootTest = function (challengeId) {
    showLootModal(challengeId == null ? 0 : challengeId);
  };
})();
