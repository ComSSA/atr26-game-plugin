(function () {
  if (!window.location.pathname.includes("/challenges")) return;

  const originalFetch = window.fetch;
  window.fetch = async function (...args) {
    const response = await originalFetch.apply(this, args);

    const url = typeof args[0] === "string" ? args[0] : args[0]?.url;
    if (url && url.includes("/api/v1/challenges/attempt")) {
      const cloned = response.clone();
      try {
        const data = await cloned.json();
        if (data.success && data.data && data.data.status === "correct") {
          const body = args[1]?.body;
          let challengeId = null;
          if (body) {
            try {
              const parsed = JSON.parse(body);
              challengeId = parsed.challenge_id;
            } catch (e) {
              const formData = new URLSearchParams(body);
              challengeId = formData.get("challenge_id");
            }
          }
          if (challengeId) {
            setTimeout(function () {
              showCardSelection(parseInt(challengeId));
            }, 800);
          }
        }
      } catch (e) {
        // Not JSON or parse error — ignore
      }
    }

    return response;
  };

  async function showCardSelection(challengeId) {
    try {
      const csrfToken = window.init?.csrfNonce || "";
      const resp = await originalFetch("/atr26_game/api/card-offer", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "CSRF-Token": csrfToken,
        },
        body: JSON.stringify({ challenge_id: challengeId }),
      });
      const result = await resp.json();

      if (!result.success || !result.data) return;

      const offer = result.data;
      renderCardOverlay(offer);
    } catch (e) {
      console.error("[atr26_game] Card offer error:", e);
    }
  }

  function renderCardOverlay(offer) {
    const overlay = document.createElement("div");
    overlay.className = "atr26-card-overlay";
    overlay.innerHTML = `
      <div class="atr26-card-selection-container">
        <h2 class="atr26-card-selection-title">Choose Your Weapon</h2>
        <div class="atr26-card-selection-cards">
          ${renderCard(offer.weapon_a, "a")}
          ${renderCard(offer.weapon_b, "b")}
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
    requestAnimationFrame(function () {
      overlay.classList.add("active");
    });

    overlay.querySelectorAll(".atr26-selectable-card").forEach(function (card) {
      card.addEventListener("click", function () {
        const weaponId = parseInt(this.dataset.weaponId);
        selectCard(offer.id, weaponId, overlay);
      });
    });
  }

  function renderCard(weapon, side) {
    if (!weapon) return "";
    return `
      <div class="atr26-selectable-card atr26-card-${side}"
           data-weapon-id="${weapon.id}"
           style="border-color: ${weapon.card_border_color}">
        <div class="atr26-card-icon">
          ${weapon.icon_path ? `<img src="${weapon.icon_path}" alt="${weapon.name}">` : '<i class="fas fa-sword"></i>'}
        </div>
        <div class="atr26-card-body">
          <h5 class="atr26-card-name">${weapon.name}</h5>
          <span class="atr26-card-rarity rarity-${weapon.rarity}">${weapon.rarity}</span>
          <span class="atr26-card-damage-type">${weapon.damage_type}</span>
          <p class="atr26-card-desc">${weapon.description}</p>
          <div class="atr26-card-damage">DMG: ${weapon.base_damage}</div>
        </div>
      </div>
    `;
  }

  async function selectCard(offerId, weaponId, overlay) {
    try {
      const csrfToken = window.init?.csrfNonce || "";
      const resp = await originalFetch("/atr26_game/api/card-select", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "CSRF-Token": csrfToken,
        },
        body: JSON.stringify({
          offer_id: offerId,
          selected_weapon_id: weaponId,
        }),
      });
      const result = await resp.json();

      if (result.success && result.data && result.data.hint) {
        showHintReveal(result.data.hint, overlay);
      } else {
        closeOverlay(overlay);
      }
    } catch (e) {
      console.error("[atr26_game] Card select error:", e);
      closeOverlay(overlay);
    }
  }

  function showHintReveal(hint, overlay) {
    const container = overlay.querySelector(".atr26-card-selection-container");
    container.innerHTML = `
      <div class="atr26-hint-reveal">
        <h2>Hint Unlocked!</h2>
        <div class="atr26-hint-content">${hint.hint_content}</div>
        <p class="text-muted mt-3">This hint is now available in your Loadout page.</p>
        <button class="btn btn-primary atr26-hint-close">Continue</button>
      </div>
    `;
    container.querySelector(".atr26-hint-close").addEventListener("click", function () {
      closeOverlay(overlay);
    });
  }

  function closeOverlay(overlay) {
    overlay.classList.remove("active");
    setTimeout(function () {
      overlay.remove();
    }, 300);
  }
})();
