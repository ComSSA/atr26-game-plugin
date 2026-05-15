/**
 * inventory.js — minimal update to existing Inventory Alpine component.
 * Adds: sprite resolution, emoji fallback, detail modal, damage display.
 */
document.addEventListener("alpine:init", function () {
  window.Alpine.data("Inventory", function () {
    return {
      items:   [],
      loading: true,

      async init() {
        try {
          const r    = await fetch("/atr26_game/api/inventory", {
            headers: { "CSRF-Token": (window.init && window.init.csrfNonce) || "" },
          });
          const data = await r.json();
          if (data.success) this.items = data.data;
        } catch (e) {
          console.error("[atr26] inventory load failed", e);
        }
        this.loading = false;
      },

      // Auto sprite: /plugins/atr26_game/assets/img/<type>_<rarity>.png
      weaponSprite(damage_type, rarity) {
        const t = (damage_type || "fire").toLowerCase();
        const r = (rarity || "common").toLowerCase();
        return `/plugins/atr26_game/assets/img/${t}_${r}.png`;
      },

      typeEmoji(type) {
        const m = { fire:"🔥", frost:"❄️", lightning:"⚡", poison:"☠️", arcane:"🔮" };
        return m[(type || "").toLowerCase()] || "⚔️";
      },

      typeColor(type) {
        const m = { fire:"#a0493c", frost:"#009dff", lightning:"#CCAA7A", poison:"#7a9a4a", arcane:"#9a6ab0" };
        return m[(type || "").toLowerCase()] || "#C39D81";
      },

      rarityColor(rarity) {
        const m = { common:"#C39D81", uncommon:"#CCAA7A", rare:"#009dff", legendary:"#a0493c" };
        return m[(rarity || "").toLowerCase()] || "#7B2D21";
      },

      damageRange(rarity) {
        const m = { common:"10 – 20", uncommon:"20 – 30", rare:"30 – 40", legendary:"40 – 50" };
        return m[(rarity || "").toLowerCase()] || "?";
      },
    };
  });
});
