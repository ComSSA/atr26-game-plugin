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

  if (!window.__atr26GameFetchPatched) {
    window.__atr26GameFetchPatched = true;
    var originalFetch = window.fetch.bind(window);
    window.fetch = wrapFetchLike(originalFetch);
  }

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

      if (result.success && result.data && result.data.hint) {
        showHintReveal(result.data.hint, overlay);
      } else {
        closeOverlay(overlay);
      }
    } catch (e) {
      console.error("[atr26_game] Card select error:", e);
      showGameToast("Network error while choosing weapon.", "danger");
      closeOverlay(overlay);
    }
  }

  function showHintReveal(hint, overlay) {
    var container = overlay.querySelector(".atr26-card-selection-container");
    container.innerHTML =
      '<div class="atr26-hint-reveal">' +
      "<h2>Hint Unlocked!</h2>" +
      '<div class="atr26-hint-content">' +
      String(hint.hint_content || "").replace(/</g, "") +
      "</div>" +
      '<p class="text-muted mt-3">This hint is now available in your Loadout page.</p>' +
      '<button type="button" class="btn btn-primary atr26-hint-close">Continue</button>' +
      "</div>";
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
