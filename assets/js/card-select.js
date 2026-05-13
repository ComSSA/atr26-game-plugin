(function () {
  "use strict";

  // Escape user-supplied strings before inserting into innerHTML.
  function esc(str) {
    const d = document.createElement("div");
    d.appendChild(document.createTextNode(str == null ? "" : String(str)));
    return d.innerHTML;
  }

  async function showCardSelection(challengeId) {
    let offer;
    try {
      const resp = await window.CTFd.fetch("/atr26_game/api/card-offer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ challenge_id: challengeId }),
      });
      const result = await resp.json();
      if (!result.success || !result.data) return;
      offer = result.data;
    } catch (e) {
      console.error("[atr26_game] Card offer error:", e);
      return;
    }

    renderModal(offer);
  }

  function buildCardHtml(weapon, side) {
    const imageHtml = weapon.icon_path
      ? `<img src="${esc(weapon.icon_path)}" alt="${esc(weapon.name)}">`
      : `<div class="atr26-card-placeholder"></div>`;
    return `
      <button class="atr26-weapon-card atr26-card-${esc(side)}"
              data-weapon-id="${esc(String(weapon.id))}"
              style="border-color: ${esc(weapon.card_border_color)}"
              aria-pressed="false">
        <div class="atr26-card-image">${imageHtml}</div>
        <div class="atr26-card-body">
          <h3 class="atr26-card-name">${esc(weapon.name)}</h3>
          <span class="atr26-card-rarity rarity-${esc(weapon.rarity)}">${esc(weapon.rarity)}</span>
          <span class="atr26-card-damage-type">${esc(weapon.damage_type)}</span>
          <p class="atr26-card-desc">${esc(weapon.description)}</p>
          <div class="atr26-card-damage">DMG: ${esc(String(weapon.base_damage))}</div>
        </div>
      </button>`;
  }

  function renderModal(offer) {
    let selectedWeaponId = null;

    const overlay = document.createElement("div");
    overlay.id = "atr26-modal-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-labelledby", "atr26-modal-title");

    overlay.innerHTML = `
      <div class="atr26-modal">
        <h2 id="atr26-modal-title" class="atr26-modal-title">Choose Your Weapon</h2>
        <p class="atr26-modal-subtitle">Pick one weapon to claim from this solve</p>
        <div class="atr26-weapon-cards">
          ${buildCardHtml(offer.weapon_a, "a")}
          ${buildCardHtml(offer.weapon_b, "b")}
        </div>
        <button id="atr26-claim-btn" class="atr26-claim-btn" disabled>Claim</button>
      </div>`;

    document.body.appendChild(overlay);

    const cards = overlay.querySelectorAll(".atr26-weapon-card");
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
        selectedWeaponId = parseInt(card.dataset.weaponId, 10);
        document.getElementById("atr26-claim-btn").disabled = false;
      });
    });

    document.getElementById("atr26-claim-btn").addEventListener("click", async function () {
      if (!selectedWeaponId) return;
      const btn = this;
      btn.disabled = true;
      btn.textContent = "Claiming…";

      let hint = null;
      try {
        const resp = await window.CTFd.fetch("/atr26_game/api/card-select", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            offer_id: offer.id,
            selected_weapon_id: selectedWeaponId,
          }),
        });
        const result = await resp.json();
        if (result.success && result.data && result.data.hint) {
          hint = result.data.hint;
        }
      } catch (e) {
        console.error("[atr26_game] Card select error:", e);
      }

      if (hint) {
        showHintReveal(hint, overlay);
      } else {
        closeOverlay(overlay);
      }
    });
  }

  function showHintReveal(hint, overlay) {
    const modal = overlay.querySelector(".atr26-modal");
    modal.innerHTML = `
      <div class="atr26-hint-reveal">
        <h2 class="atr26-modal-title">Hint Unlocked!</h2>
        <div class="atr26-hint-content">${esc(hint.hint_content)}</div>
        <p class="atr26-modal-subtitle">This hint is now available in your Loadout page.</p>
        <button class="atr26-claim-btn atr26-hint-close">Continue</button>
      </div>`;
    modal.querySelector(".atr26-hint-close").addEventListener("click", function () {
      closeOverlay(overlay);
    });
  }

  function closeOverlay(overlay) {
    overlay.classList.add("closing");
    setTimeout(function () { overlay.remove(); }, 280);
  }

  // Hook into CTFd's challenge submission so the modal fires on any correct solve.
  if (
    window.CTFd &&
    window.CTFd.pages &&
    window.CTFd.pages.challenge &&
    typeof window.CTFd.pages.challenge.submitChallenge === "function"
  ) {
    const orig = window.CTFd.pages.challenge.submitChallenge;
    window.CTFd.pages.challenge.submitChallenge = async function (challengeId, submission) {
      const response = await orig(challengeId, submission);
      if (response && response.data && response.data.status === "correct") {
        setTimeout(function () { showCardSelection(challengeId); }, 600);
      }
      return response;
    };
  }

  // Dev helper: window.__atr26Test(challengeId?) — trigger the modal directly.
  window.__atr26Test = function (challengeId) {
    showCardSelection(challengeId == null ? 0 : challengeId);
  };
})();
