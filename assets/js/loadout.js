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
            fetch("/atr26_game/api/inventory", {
              headers: { "CSRF-Token": window.init.csrfNonce },
            }),
            fetch("/atr26_game/api/loadout", {
              headers: { "CSRF-Token": window.init.csrfNonce },
            }),
            fetch("/atr26_game/api/hints", {
              headers: { "CSRF-Token": window.init.csrfNonce },
            }),
          ]);

          const invData = await invResp.json();
          const loadoutData = await loadoutResp.json();
          const hintsData = await hintsResp.json();

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

      isInventoryInAnySlot(itemId) {
        for (let s = 1; s <= 5; s++) {
          const e = this.slots[s];
          if (e && e.inventory_item && e.inventory_item.id === itemId) return s;
        }
        return null;
      },

      onSlotClick(slot) {
        if (this.submitted) return;
        if (this.pendingItem) {
          this.assignWeaponToSlot(slot, this.pendingItem);
          this.pendingItem = null;
          this.selectedSlot = null;
          return;
        }
        this.selectedSlot = this.selectedSlot === slot ? null : slot;
      },

      onInventoryClick(item) {
        if (this.submitted || !item.weapon) return;
        if (this.selectedSlot !== null) {
          this.assignWeaponToSlot(this.selectedSlot, item);
          this.selectedSlot = null;
          this.pendingItem = null;
          return;
        }
        this.pendingItem =
          this.pendingItem && this.pendingItem.id === item.id ? null : item;
      },

      assignWeaponToSlot(slot, item) {
        this.slots[slot] = { inventory_item: item };
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

      async saveLoadout() {
        this.saveMessage = "";
        this.saveError = "";
        const slotData = {};
        for (const [slot, entry] of Object.entries(this.slots)) {
          if (entry && entry.inventory_item) {
            slotData[slot] = entry.inventory_item.id;
          }
        }

        try {
          const resp = await fetch("/atr26_game/api/loadout", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "CSRF-Token": window.init.csrfNonce,
            },
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

      async submitLoadout() {
        if (!confirm("Submit and lock this loadout? You cannot change it after.")) {
          return;
        }
        await this.saveLoadout();
        if (this.saveError) return;
        try {
          const resp = await fetch("/atr26_game/api/loadout/submit", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "CSRF-Token": window.init.csrfNonce,
            },
            body: "{}",
          });
          const data = await resp.json();
          if (data.success) {
            this.submitted = true;
            this.saveMessage = "Loadout submitted and locked.";
            await this.reload();
          } else {
            this.saveError = data.error || "Submit failed";
          }
        } catch (e) {
          console.error("[atr26_game] Failed to submit loadout:", e);
          this.saveError = "Network error while submitting.";
        }
      },
    };
  });
});
