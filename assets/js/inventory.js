document.addEventListener("alpine:init", function () {
  Alpine.data("Inventory", function () {
    return {
      items: [],
      loading: true,

      async init() {
        try {
          const response = await fetch("/atr26_game/api/inventory", {
            headers: { "CSRF-Token": window.init.csrfNonce },
          });
          const data = await response.json();
          if (data.success) {
            this.items = data.data;
          }
        } catch (e) {
          console.error("[atr26_game] Failed to load inventory:", e);
        }
        this.loading = false;
      },
    };
  });
});
