document.addEventListener("alpine:init", function () {
  window.Alpine.data("LoadoutSelector", function () {
    return {
      inventory: [],
      slots: { 1: null, 2: null, 3: null, 4: null, 5: null },
      hints: [],
      submitted: false,
      loading: true,
      /** Pick a slot, then a weapon from the list (left highlight). */
      selectedSlot: null,
      /** Pick a weapon, then a slot (right highlight). */
      pendingItem: null,
      saveMessage: "",
      saveError: "",

      init() {
        this.reload();
      },

      async reload() {
        this.loading = true;
        this.saveMessage = "";
        this.saveError = "";
        try {
          const [invResp, loadoutResp, hintsResp] = await Promise.all([
            fetch("/atr26_game/api/inventory", { headers: { "CSRF-Token": window.init.csrfNonce } }),
            fetch("/atr26_game/api/loadout",   { headers: { "CSRF-Token": window.init.csrfNonce } }),
            fetch("/atr26_game/api/hints",     { headers: { "CSRF-Token": window.init.csrfNonce } }),
          ]);
          const invData     = await invResp.json();
          const loadoutData = await loadoutResp.json();
          const hintsData   = await hintsResp.json();

          if (invData.success) this.inventory = invData.data;
          if (loadoutData.success) {
            this.submitted = loadoutData.data.submitted;
            const existingSlots = loadoutData.data.slots;
            for (let s = 1; s <= 5; s++) this.slots[s] = null;
            for (const [slot, entry] of Object.entries(existingSlots)) {
              this.slots[parseInt(slot, 10)] = entry;
            }
          }
          if (hintsData.success) this.hints = hintsData.data;
        } catch (e) {
          console.error("[atr26_game] Failed to load loadout data:", e);
        }
        this.loading = false;
      },

      openSlotPicker(slot) {
        this.selectedSlot = this.selectedSlot === slot ? null : slot;
      },

      isAssigned(item) {
        return Object.values(this.slots).some(
          s => s && s.inventory_item && s.inventory_item.id === item.id
        );
      },

      slotOfItem(item) {
        for (const [slot, entry] of Object.entries(this.slots)) {
          if (entry && entry.inventory_item && entry.inventory_item.id === item.id)
            return slot;
        }
        return null;
      },

      assignSelected(item) {
        if (this.selectedSlot === null) return;
        if (this.isAssigned(item)) return;
        this.slots[this.selectedSlot] = { inventory_item: item };
        this.selectedSlot = null;
      },

      removeFromSlot(slot) {
        if (this.submitted) return;
        this.slots[slot] = null;
        if (this.selectedSlot === slot) this.selectedSlot = null;
      },

      clearAllSlots() {
        if (this.submitted) return;
        for (let s = 1; s <= 5; s++) this.slots[s] = null;
        this.selectedSlot = null;
        this.pendingItem = null;
      },

      weaponSprite(damage_type, rarity) {
        const t = (damage_type || "fire").toLowerCase();
        const r = (rarity || "common").toLowerCase();
        return `/plugins/atr26_game/assets/img/${t}_${r}.png`;
      },

      typeEmoji(type) {
        const m = { fire:"🔥", frost:"❄️", lightning:"⚡", poison:"☠️", arcane:"🔮" };
        return m[(type || "").toLowerCase()] || "⚔️";
      },

      rarityColor(rarity) {
        const m = { common:"#C39D81", uncommon:"#CCAA7A", rare:"#009dff", legendary:"#a0493c" };
        return m[(rarity || "").toLowerCase()] || "#7B2D21";
      },

      typeColor(type) {
        const m = { fire:"#a0493c", frost:"#009dff", lightning:"#CCAA7A", poison:"#7a9a4a", arcane:"#9a6ab0" };
        return m[(type || "").toLowerCase()] || "#C39D81";
      },

      damageRange(rarity) {
        const m = { common:"10 – 20", uncommon:"20 – 30", rare:"30 – 40", legendary:"40 – 50" };
        return m[(rarity || "").toLowerCase()] || "?";
      },

      async saveLoadout() {
        this.saveMessage = "";
        this.saveError = "";
        const slotData = {};
        for (const [slot, entry] of Object.entries(this.slots)) {
          if (entry && entry.inventory_item) slotData[slot] = entry.inventory_item.id;
        }
        try {
          const resp = await fetch("/atr26_game/api/loadout", {
            method: "POST",
            headers: { "Content-Type": "application/json", "CSRF-Token": window.init.csrfNonce },
            body: JSON.stringify({ slots: slotData }),
          });
          const data = await resp.json();
          if (data.success) {
            this.saveMessage = "Draft saved.";
            await this.reload();
          } else {
            this.saveError = data.error || "Save failed";
          }
        } catch (e) {
          console.error("[atr26_game] Failed to save loadout:", e);
          this.saveError = "Network error while saving.";
        }
      },

      clearLoadout() {
        this.slots = { 1: null, 2: null, 3: null, 4: null, 5: null };
      },

      async submitLoadout() {
        if (!confirm("Are you sure? Once submitted, your loadout cannot be changed.")) return;
        await this.saveLoadout();
        if (this.saveError) return;
        try {
          const resp = await fetch("/atr26_game/api/loadout/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json", "CSRF-Token": window.init.csrfNonce },
          });
          const data = await resp.json();
          if (data.success) this.submitted = true;
        } catch (e) {
          console.error("[atr26_game] Failed to submit loadout:", e);
          this.saveError = "Network error while submitting.";
        }
      },
    };
  });
});
