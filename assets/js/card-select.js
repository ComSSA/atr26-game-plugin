(function () {
  if (!window.location.pathname.includes("/challenges")) {
    return;
  }

  if (window.__atr26GameLootHooked) {
    return;
  }
  window.__atr26GameLootHooked = true;

  function showGameToast(message, variant) {
    variant = variant || "info";
    var wrap = document.createElement("div");
    wrap.className = "alert alert-" + variant + " shadow atr26-game-toast";
    wrap.setAttribute("role", "status");
    wrap.textContent = message;
    wrap.style.cssText =
      "position:fixed;bottom:1.25rem;right:1.25rem;z-index:20000;max-width:22rem;margin:0;font-size:0.95rem;";
    document.body.appendChild(wrap);
    setTimeout(function () {
      wrap.classList.add("fade", "show");
    }, 10);
    setTimeout(function () {
      wrap.remove();
    }, 9000);
  }

  function parseAttemptBody(body) {
    if (!body) {
      return null;
    }
    if (typeof body === "string") {
      try {
        var parsed = JSON.parse(body);
        return parsed.challenge_id != null ? parseInt(parsed.challenge_id, 10) : null;
      } catch (e) {
        try {
          return parseInt(new URLSearchParams(body).get("challenge_id"), 10) || null;
        } catch (e2) {
          return null;
        }
      }
    }
    if (typeof body === "object" && body.challenge_id != null) {
      return parseInt(body.challenge_id, 10);
    }
    return null;
  }

  async function handleAttemptResponse(response, requestBody) {
    var cloned = response.clone();
    try {
      var data = await cloned.json();
      if (data.success && data.data && data.data.status === "correct") {
        var challengeId = parseAttemptBody(requestBody);
        if (challengeId) {
          scheduleCardSelection(challengeId);
        } else {
          console.warn("[atr26_game] Correct solve but could not read challenge_id from request body");
        }
      }
    } catch (e) {
      // Not JSON — ignore
    }
  }

  function wrapFetchLike(fn) {
    if (typeof fn !== "function" || fn.__atr26Wrapped) {
      return fn;
    }
    var wrapped = async function (url, options) {
      var response = await fn.apply(this, arguments);
      var urlStr = typeof url === "string" ? url : url && url.url ? url.url : "";
      if (urlStr.indexOf("/api/v1/challenges/attempt") !== -1) {
        await handleAttemptResponse(response, options && options.body);
      }
      return response;
    };
    wrapped.__atr26Wrapped = true;
    return wrapped;
  }

  /** CTFd.fetch is bound before plugin scripts run; we must wrap CTFd.fetch, not only window.fetch. */
  function patchCtfdFetch() {
    if (!window.CTFd || !window.CTFd.fetch || window.CTFd.fetch.__atr26Wrapped) {
      return;
    }
    window.CTFd.fetch = wrapFetchLike(window.CTFd.fetch);
  }

    renderModal(offer);
  }

  var EMOJIS      = { fire:"🔥", frost:"❄️", lightning:"⚡", poison:"☠️", arcane:"🔮" };
  var TYPE_COLORS = { fire:"#a0493c", frost:"#009dff", lightning:"#CCAA7A", poison:"#7a9a4a", arcane:"#9a6ab0" };
  var DMG_RANGES  = { common:"10 – 20", uncommon:"20 – 30", rare:"30 – 40", legendary:"40 – 50" };

  function buildCardHtml(weapon, side) {
    const t = (weapon.damage_type || "fire").toLowerCase();
    const r = (weapon.rarity || "common").toLowerCase();
    const spriteSrc  = `/plugins/atr26_game/assets/img/${t}_${r}.png`;
    const typeColor  = TYPE_COLORS[t] || "#C39D81";
    const dmgRange   = DMG_RANGES[r]  || "?";
    const emoji      = EMOJIS[t]      || "⚔️";
    const descHtml   = weapon.description
      ? `<p class="atr26-detail-desc">${esc(weapon.description)}</p>` : "";

    return `
      <button class="atr26-weapon-card atr26-card-${esc(side)}"
              data-weapon-id="${esc(String(weapon.id))}"
              aria-pressed="false">

        <div class="atr26-card-image">
          <img src="${esc(spriteSrc)}" alt="${esc(weapon.name)}"
               style="image-rendering:crisp-edges;image-rendering:pixelated"
               onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
          <div class="atr26-card-emoji" style="display:none">${esc(emoji)}</div>
        </div>

        <div class="atr26-card-body">
          <div class="atr26-card-name">${esc(weapon.name)}</div>
          <div class="atr26-card-rarity rarity-${esc(r)}">${esc(weapon.rarity)}</div>
          <div class="atr26-card-damage">DMG: ${esc(String(weapon.min_damage))}–${esc(String(weapon.max_damage))}</div>
        </div>

        <div class="atr26-card-detail">
          <div class="atr26-detail-badges">
            <span class="atr26-card-rarity rarity-${esc(r)}"
                  style="border:1px solid currentColor;padding:.1rem .5rem;border-radius:2px;
                         font-size:.65rem;letter-spacing:1px;text-transform:uppercase">${esc(weapon.rarity)}</span>
            <span style="color:${esc(typeColor)};border:1px solid currentColor;padding:.1rem .5rem;
                         border-radius:2px;font-size:.65rem;text-transform:uppercase">${esc(emoji)} ${esc(weapon.damage_type)}</span>
          </div>
          <div class="atr26-detail-stats">
            <div class="atr26-detail-stat">
              <div class="atr26-detail-label">DMG Range</div>
              <div class="atr26-detail-value" style="font-size:1.1rem">${esc(String(weapon.min_damage))}–${esc(String(weapon.max_damage))}</div>
            </div>
            <div class="atr26-detail-divider"></div>
            <div class="atr26-detail-stat">
              <div class="atr26-detail-label">Rarity Range</div>
              <div class="atr26-detail-range">${esc(dmgRange)}</div>
            </div>
          </div>
          ${descHtml}
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

  patchCtfdFetch();
  document.addEventListener("DOMContentLoaded", patchCtfdFetch);
  setTimeout(patchCtfdFetch, 0);

  function sleep(ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  }

  function waitUntilVisible() {
    if (!document.hidden) {
      return Promise.resolve();
    }
    return new Promise(function (resolve) {
      function onVis() {
        if (!document.hidden) {
          document.removeEventListener("visibilitychange", onVis);
          resolve();
        }
      }
      document.addEventListener("visibilitychange", onVis);
    });
  }

      try {
        await window.CTFd.fetch("/atr26_game/api/card-select", {
  function removeExistingOverlays() {
    document.querySelectorAll(".atr26-card-overlay").forEach(function (el) {
      el.remove();
    });
  }

  function scheduleCardSelection(challengeId) {
    function kickoff() {
      setTimeout(function () {
        showCardSelection(challengeId);
      }, 800);
    }
    if (document.hidden) {
      document.addEventListener(
        "visibilitychange",
        function onceVisible() {
          if (document.hidden) return;
          document.removeEventListener("visibilitychange", onceVisible);
          kickoff();
        },
        { passive: true }
      );
      return;
    }
    kickoff();
  }

  async function showCardSelection(challengeId) {
    await waitUntilVisible();

    var csrfToken = window.init && window.init.csrfNonce ? window.init.csrfNonce : "";
    var lastErr = null;
    var innerFetch = window.CTFd && window.CTFd.fetch ? window.CTFd.fetch : window.fetch.bind(window);

    for (var attempt = 0; attempt < 6; attempt++) {
      if (document.hidden) {
        await waitUntilVisible();
      }
      try {
        var resp = await innerFetch("/atr26_game/api/card-offer", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "CSRF-Token": csrfToken,
          },
          body: JSON.stringify({ challenge_id: challengeId }),
        });
        var result = await resp.json();
        if (result.success && result.data && result.data.weapon_a && result.data.weapon_b) {
          removeExistingOverlays();
          renderCardOverlay(result.data, challengeId);
          return;
        }
        if (resp.status === 409 && result.retry) {
          lastErr = result.error;
          await sleep(350 + attempt * 150);
          continue;
        }
        var errMsg = result.error || result.message || "Unknown error";
        console.warn("[atr26_game] Card offer not shown:", resp.status, errMsg);
        showGameToast(
          "No weapon pick for this solve: " +
            errMsg +
            ". If you expected loot: use Admin → ATR26 → Seed weapons, and tag the challenge with loot:easy|medium|hard.",
          "warning"
        );
        return;
      } catch (e) {
        console.error("[atr26_game] Card offer error:", e);
        showGameToast("Could not load weapon offer (network or server error).", "warning");
        return;
      }
    }
    if (lastErr) {
      console.warn("[atr26_game] Card offer gave up:", lastErr);
      showGameToast("Weapon offer not ready after retries. Try Inventory in a moment.", "warning");
    }
  }

  function renderCardOverlay(offer, challengeId) {
    var overlay = document.createElement("div");
    overlay.className = "atr26-card-overlay";
    overlay.innerHTML =
      '<div class="atr26-card-selection-container">' +
      '<h2 class="atr26-card-selection-title">Choose Your Weapon</h2>' +
      '<div class="atr26-card-selection-cards">' +
      renderCard(offer.weapon_a, "a") +
      renderCard(offer.weapon_b, "b") +
      "</div></div>";

    document.body.appendChild(overlay);
    requestAnimationFrame(function () {
      overlay.classList.add("active");
    });

    overlay.querySelectorAll(".atr26-selectable-card").forEach(function (card) {
      card.addEventListener("click", function () {
        var pick = this.dataset.pick;
        selectCard(challengeId, pick, overlay);
      });
    });
  }

  function renderCard(weapon, side) {
    if (!weapon) return "";
    var dmg = weapon.rolled_damage != null ? weapon.rolled_damage : "";
    return (
      '<div class="atr26-selectable-card atr26-card-' +
      side +
      '" data-pick="' +
      side +
      '" style="border-color: ' +
      (weapon.card_border_color || "#808080") +
      '">' +
      '<div class="atr26-card-icon">' +
      (weapon.icon_path
        ? '<img src="' +
          String(weapon.icon_path).replace(/"/g, "&quot;") +
          '" alt="' +
          String(weapon.name || "").replace(/</g, "") +
          '">'
        : '<i class="fas fa-sword"></i>') +
      "</div>" +
      '<div class="atr26-card-body">' +
      "<h5 class=\"atr26-card-name\">" +
      String(weapon.name || "").replace(/</g, "") +
      "</h5>" +
      '<span class="atr26-card-rarity rarity-' +
      String(weapon.rarity || "common") +
      '">' +
      String(weapon.rarity || "") +
      "</span>" +
      '<span class="atr26-card-damage-type">' +
      String(weapon.damage_type || "") +
      "</span>" +
      "<p class=\"atr26-card-desc\">" +
      String(weapon.description || "").replace(/</g, "") +
      "</p>" +
      '<div class="atr26-card-damage">DMG: ' +
      dmg +
      "</div></div></div>"
    );
  }

  async function selectCard(challengeId, pick, overlay) {
    try {
      var csrfToken = window.init && window.init.csrfNonce ? window.init.csrfNonce : "";
      var innerFetch = window.CTFd && window.CTFd.fetch ? window.CTFd.fetch : window.fetch.bind(window);
      var resp = await innerFetch("/atr26_game/api/card-select", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "CSRF-Token": csrfToken,
        },
        body: JSON.stringify({
          challenge_id: challengeId,
          pick: pick,
        }),
      });
      var result = await resp.json();

      if (!result.success) {
        console.warn("[atr26_game] Card select failed:", result.error || result);
        showGameToast(result.error || "Could not add weapon to inventory.", "danger");
      } else {
        showGameToast("Weapon saved — open Inventory from the menu.", "success");
      }

      const selectedWeapon = selectedWeaponId === offer.weapon_a.id ? offer.weapon_a : offer.weapon_b;
      showClaimSuccess(selectedWeapon, overlay, offer.challenge_id);
    });
  }

  var CLAIM_EMOJIS = { fire:"🔥", frost:"❄️", lightning:"⚡", poison:"☠️", arcane:"🔮" };

  function showClaimSuccess(weapon, overlay, challengeId) {
    const modal = overlay.querySelector(".atr26-modal");
    const t = (weapon.damage_type || "fire").toLowerCase();
    const r = (weapon.rarity || "common").toLowerCase();
    const spriteSrc = "/plugins/atr26_game/assets/img/" + t + "_" + r + ".png";
    const emoji = CLAIM_EMOJIS[t] || "⚔️";

    modal.innerHTML = `
      <div class="atr26-claim-success">
        <div class="atr26-success-glow"></div>
        <div class="atr26-success-card">
          <div class="atr26-card-image">
            <img src="${esc(spriteSrc)}" alt="${esc(weapon.name)}"
                 style="image-rendering:crisp-edges;image-rendering:pixelated"
                 onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
            <div class="atr26-card-emoji" style="display:none">${esc(emoji)}</div>
          </div>
        </div>
        <div class="atr26-success-label">Added to Inventory</div>
        <div class="atr26-success-name rarity-${esc(r)}">${esc(weapon.name)}</div>
        <p class="atr26-modal-subtitle">Weapon added to inventory!</p>
      </div>`;

    setTimeout(function () {
      overlay.classList.add("closing");
      setTimeout(function () {
        overlay.remove();
        _summaryCache = null;
        _applyBadges();
        if (challengeId) _injectModalClaim(challengeId);
      }, 280);
    }, 3000);
  }

  // Deduplication guard — prevents double-firing if multiple hooks catch the same solve.
  var _recentSolves = {};
  function _onCorrectSolve(challengeId) {
    var now = Date.now();
    if (_recentSolves[challengeId] && now - _recentSolves[challengeId] < 3000) return;
    _recentSolves[challengeId] = now;
    _summaryCache = null; // force fresh fetch so badges reflect the new solve
    console.log("[atr26] correct solve detected, challengeId:", challengeId);
    setTimeout(function () { showCardSelection(challengeId); }, 150);
  }

  // Primary hook: CTFd.pages.challenge.submitChallenge returns the result directly.
  function _hookSubmitChallenge() {
    if (
      !window.CTFd ||
      !window.CTFd.pages ||
      !window.CTFd.pages.challenge ||
      typeof window.CTFd.pages.challenge.submitChallenge !== "function" ||
      window.CTFd.pages.challenge.submitChallenge._atr26
    ) return false;

    var _orig = window.CTFd.pages.challenge.submitChallenge;
    window.CTFd.pages.challenge.submitChallenge = async function (challengeId, submission) {
      console.log("[atr26] wrapper called, challengeId:", challengeId);
      var result = await _orig.apply(this, arguments);
      console.log("[atr26] result status:", result && result.data && result.data.status);
      if (result && result.data && result.data.status === "correct") {
        _onCorrectSolve(challengeId);
      }
      return result;
    };
    window.CTFd.pages.challenge.submitChallenge._atr26 = true;
    console.log("[atr26] submitChallenge hook installed");
    return true;
  }

  console.log("[atr26] card-select.js loaded, CTFd available:", !!(window.CTFd));

  // Poll until CTFd.pages.challenge.submitChallenge is available, then wrap it once.
  var _pollAttempts = 0;
  var _pollInterval = setInterval(function () {
    _pollAttempts++;
    if (_hookSubmitChallenge() || _pollAttempts >= 200) {
      if (_pollAttempts >= 200 && !window.CTFd?.pages?.challenge?.submitChallenge?._atr26) {
        console.warn("[atr26] poll timed out — hook NOT installed. CTFd:", window.CTFd);
      }
      clearInterval(_pollInterval);
    }
  }, 50);

  // On every page load, re-show any unclaimed offers so a refresh doesn't lose them.
  async function checkPendingOffers() {
    if (!window.CTFd || !window.CTFd.fetch) return;
    try {
      const resp = await window.CTFd.fetch("/atr26_game/api/pending-offers", { method: "GET" });
      const result = await resp.json();
      if (result.success && result.data && result.data.length > 0) {
        renderModal(result.data[0]);
      }
    } catch (e) {
      console.error("[atr26] pending offers check error:", e);
    }
  }


  window._atr26ShowOffer = renderModal;

  // ── Activity summary & challenge claim badges ────────────────────────────
  var _summaryCache = null; // { [challengeId]: { offer, challenge_name } }

  async function _loadSummary() {
    if (_summaryCache !== null) return _summaryCache;
    _summaryCache = {};
    try {
      var resp = await fetch("/atr26_game/api/activity-summary", {
        credentials: "same-origin",
        headers: { "CSRF-Token": (window.init && window.init.csrfNonce) || "" },
      });
      var data = await resp.json();
      if (data.success) {
        data.data.forEach(function (row) {
          _summaryCache[row.offer.challenge_id] = row;
        });
      }
    } catch (e) {
      console.error("[atr26] summary fetch error", e);
    }
    return _summaryCache;
  }

  function _stampBadge(el, row) {
    if (el.querySelector(".atr26-chall-badge")) return;
    if (getComputedStyle(el).position === "static") el.style.position = "relative";
    var badge = document.createElement("div");
    badge.className = "atr26-chall-badge " + (row.offer.selected ? "claimed" : "unclaimed");
    badge.textContent = row.offer.selected ? "✓ Claimed" : "⚠ Weapon Not Claimed";
    el.appendChild(badge);
  }

  async function _applyBadges() {
    var summary = await _loadSummary();
    document.querySelectorAll("button.challenge-button").forEach(function (el) {
      var cid = parseInt(el.value || el.getAttribute("value"), 10);
      if (!cid || isNaN(cid)) return;
      var row = summary[cid];
      if (!row) return;
      var existing = el.querySelector(".atr26-chall-badge");
      if (existing) existing.remove();
      _stampBadge(el, row);
    });
  }

  function _injectModalClaim(cid) {
    var modal = document.getElementById("challenge-window");
    if (!modal) return;
    _loadSummary().then(function (summary) {
      var row = summary[cid];
      var prev = modal.querySelector(".atr26-modal-claim-wrap");
      if (prev) prev.remove();
      if (!row) return;

      var wrap = document.createElement("div");
      wrap.className = "atr26-modal-claim-wrap";
      if (row.offer.selected) {
        wrap.innerHTML = '<div class="atr26-modal-claimed">&#10003; Weapon Claimed</div>';
      } else {
        var btn = document.createElement("button");
        btn.className = "atr26-modal-claim-btn";
        btn.textContent = "⚔ Claim Weapon";
        btn.addEventListener("click", function () { renderModal(row.offer); });
        wrap.appendChild(btn);
      }

      var body = modal.querySelector(".modal-body");
      if (body) body.appendChild(wrap);
    });
  }

  // #challenge-window is shown programmatically (no relatedTarget on the event).
  // Priority for challenge ID:
  //   1. Hidden input #challenge-id (server-rendered inside the modal, most reliable)
  //   2. Alpine.store("challenge").data.id
  //   3. URL hash (#ChallengeName-<id>)
  document.addEventListener("shown.bs.modal", function (e) {
    if (e.target.id !== "challenge-window") return;
    var modal = e.target;
    var cid = 0;

    // Most reliable: the server-rendered hidden input inside the modal content
    var hiddenInput = modal.querySelector("#challenge-id, .challenge-id");
    if (hiddenInput) cid = parseInt(hiddenInput.value, 10);

    if (!cid || isNaN(cid)) {
      try { cid = Alpine.store("challenge").data.id; } catch (err) {}
    }
    if (!cid || isNaN(cid)) {
      var m = window.location.hash.match(/-(\d+)$/);
      if (m) cid = parseInt(m[1], 10);
    }

    if (!cid || isNaN(cid)) return;
    _injectModalClaim(cid);
  });

  // Watch for challenge cards rendered after page load (CTFd fetches them async via Alpine x-for)
  var _badgeObserver = new MutationObserver(function (mutations) {
    var found = false;
    mutations.forEach(function (m) {
      if (found) return;
      m.addedNodes.forEach(function (node) {
        if (found || node.nodeType !== 1) return;
        if (
          (node.classList && node.classList.contains("challenge-button")) ||
          (node.querySelector && node.querySelector("button.challenge-button"))
        ) found = true;
      });
    });
    if (found) setTimeout(_applyBadges, 100);
  });
  _badgeObserver.observe(document.body, { childList: true, subtree: true });

  // Initial pass — and re-run at 2s in case Alpine is still loading challenges
  setTimeout(_applyBadges, 1000);
  setTimeout(_applyBadges, 2500);

  // Dev helper: window.__atr26Test(challengeId?) — trigger the modal directly.
  window.__atr26Test = function (challengeId) {
    showCardSelection(challengeId == null ? 0 : challengeId);
  };

  // Debug: expose hook state
  window.__atr26Debug = function () {
    console.log("CTFd:", window.CTFd);
    console.log("submitChallenge:", window.CTFd && window.CTFd.pages && window.CTFd.pages.challenge && window.CTFd.pages.challenge.submitChallenge);
    console.log("hook installed:", !!(window.CTFd && window.CTFd.pages && window.CTFd.pages.challenge && window.CTFd.pages.challenge.submitChallenge && window.CTFd.pages.challenge.submitChallenge._atr26));
  };
})();
