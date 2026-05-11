document.addEventListener("alpine:init", function () {
  Alpine.data("LoadoutSelector", function () {
    return {
      inventory: [],
      slots: { 1: null, 2: null, 3: null, 4: null, 5: null },
      hints: [],
      submitted: false,
      loading: true,
      selectedSlot: null,

      async init() {
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
            for (const [slot, entry] of Object.entries(existingSlots)) {
              this.slots[parseInt(slot)] = entry;
            }
          }
          if (hintsData.success) this.hints = hintsData.data;
        } catch (e) {
          console.error("[atr26_game] Failed to load loadout data:", e);
        }
        this.loading = false;
      },

      openSlotPicker(slot) {
        this.selectedSlot = slot;
      },

      assignSelected(item) {
        if (this.selectedSlot === null) return;
        this.slots[this.selectedSlot] = {
          inventory_item: item,
        };
        this.selectedSlot = null;
      },

      removeFromSlot(slot) {
        this.slots[slot] = null;
      },

      async saveLoadout() {
        const slotData = {};
        for (const [slot, entry] of Object.entries(this.slots)) {
          if (entry && entry.inventory_item) {
            slotData[slot] = entry.inventory_item.id;
          }
        }

        try {
          await fetch("/atr26_game/api/loadout", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "CSRF-Token": window.init.csrfNonce,
            },
            body: JSON.stringify({ slots: slotData }),
          });
        } catch (e) {
          console.error("[atr26_game] Failed to save loadout:", e);
        }
      },

      async submitLoadout() {
        if (!confirm("Are you sure? Once submitted, your loadout cannot be changed.")) {
          return;
        }
        await this.saveLoadout();
        try {
          const resp = await fetch("/atr26_game/api/loadout/submit", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "CSRF-Token": window.init.csrfNonce,
            },
          });
          const data = await resp.json();
          if (data.success) {
            this.submitted = true;
          }
        } catch (e) {
          console.error("[atr26_game] Failed to submit loadout:", e);
        }
      },
    };
  });
});
