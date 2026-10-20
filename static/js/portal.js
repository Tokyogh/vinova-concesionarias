/* ES: Implementa interacción de navegador para static/js/portal; backend conserva la autoridad. */
/* EN: Implements browser interaction for static/js/portal; the backend remains authoritative. */
(() => {
  /* ES: Los eventos siguientes controlan el drawer y restauran foco sin decidir autorización. */
  /* EN: The following events control the drawer and restore focus without deciding authorization. */
  const body = document.body;
  if (!body.classList.contains("portal-body")) return;

  /* ES: Los eventos siguientes controlan el drawer y restauran foco sin decidir autorización. */
  /* EN: The following events control the drawer and restore focus without deciding authorization. */
  const openButton = document.querySelector("[data-portal-sidebar-open]");
  const closeButtons = document.querySelectorAll("[data-portal-sidebar-close]");
  const sidebar = document.querySelector("#portal-sidebar");
  const sidebarMedia = window.matchMedia("(max-width: 980px)");

  const setOpen = (open, restoreFocus = true) => {
    const drawerMode = sidebarMedia.matches;
    const effectiveOpen = drawerMode && open;
    body.classList.toggle("portal-sidebar-open", effectiveOpen);
    openButton?.setAttribute("aria-expanded", String(effectiveOpen));
    if (drawerMode) sidebar?.setAttribute("aria-hidden", String(!effectiveOpen));
    else sidebar?.removeAttribute("aria-hidden");
    if (effectiveOpen) sidebar?.querySelector("a")?.focus();
    else if (restoreFocus) openButton?.focus();
  };

  openButton?.addEventListener("click", () => setOpen(true));
  closeButtons.forEach((button) => button.addEventListener("click", () => setOpen(false)));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && body.classList.contains("portal-sidebar-open")) setOpen(false);
  });
  sidebarMedia.addEventListener("change", () => setOpen(false, false));
  setOpen(false, false);

  const active = sidebar?.querySelector("[aria-current='page']");
  active?.scrollIntoView({block: "nearest"});

  /* ES: Formatea códigos emitidos sin decidir su validez ni estado de canje. */
  /* EN: Formats issued codes without deciding their validity or redemption state. */
  const formatVnvCode = (value) => {
    const compact = String(value || "").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 19);
    const payload = compact.startsWith("VNV") ? compact.slice(3) : compact;
    const groups = payload.match(/.{1,4}/g) || [];
    return ["VNV", ...groups].join("-").slice(0, 23);
  };
  document.querySelectorAll("[data-vnv-code]").forEach((input) => {
    input.addEventListener("input", () => {
      const cursor = input.selectionStart ?? input.value.length;
      const alphanumericBeforeCursor = input.value.slice(0, cursor).replace(/[^A-Z0-9]/gi, "").length;
      const formatted = formatVnvCode(input.value);
      input.value = formatted;
      let target = formatted.length;
      let seen = 0;
      for (let index = 0; index < formatted.length; index += 1) {
        if (/[A-Z0-9]/.test(formatted[index])) seen += 1;
        if (seen >= alphanumericBeforeCursor) {
          target = index + 1;
          break;
        }
      }
      input.setSelectionRange(target, target);
    });
  });

  const dialog = document.querySelector("#portal-detail-dialog");
  const dialogBody = dialog?.querySelector("[data-portal-dialog-body]");
  const closeDialog = () => dialog?.close();
  dialog?.querySelector("[data-portal-dialog-close]")?.addEventListener("click", closeDialog);
  dialog?.addEventListener("click", (event) => {
    if (event.target === dialog) closeDialog();
  });

  const bindTabs = (scope = document) => {
    const tablist = scope.querySelector("[data-portal-tabs]");
    if (!tablist) return;
    const tabs = [...tablist.querySelectorAll("[role='tab']")];
    const panels = [...scope.querySelectorAll("[role='tabpanel']")];
    const activate = (tab) => {
      tabs.forEach((candidate) => {
        const selected = candidate === tab;
        candidate.setAttribute("aria-selected", String(selected));
        candidate.tabIndex = selected ? 0 : -1;
      });
      panels.forEach((panel) => { panel.hidden = panel.id !== tab.getAttribute("aria-controls"); });
    };
    tabs.forEach((tab) => tab.addEventListener("click", () => activate(tab)));
  };

  document.addEventListener("click", async (event) => {
    const link = event.target.closest("[data-portal-modal]");
    if (!link || !dialog || !dialogBody || typeof dialog.showModal !== "function") return;
    event.preventDefault();
    dialogBody.innerHTML = '<div class="portal-dialog-loading" role="status">Cargando detalle…</div>';
    dialog.showModal();
    try {
      const response = await fetch(link.href, {headers: {"X-Requested-With": "XMLHttpRequest"}});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const page = new DOMParser().parseFromString(await response.text(), "text/html");
      const heading = page.querySelector(".portal-heading h1");
      const content = page.querySelector(".portal-content");
      if (!content) throw new Error("missing portal content");
      dialogBody.innerHTML = `<header class="portal-dialog-heading"><span class="eyebrow">Mi vehículo</span><h2 id="portal-dialog-title"></h2></header>${content.innerHTML}`;
      dialogBody.querySelector("#portal-dialog-title").textContent = heading?.textContent || "Detalle del vehículo";
      bindTabs(dialogBody);
      dialog.querySelector("[data-portal-dialog-close]")?.focus();
    } catch (_error) {
      window.location.assign(link.href);
    }
  });

  bindTabs();
})();
