/**
 * ES: Controla apertura, cierre y foco de los diálogos del catálogo público.
 * EN: Controls opening, closing, and focus for public catalog dialogs.
 */
(function () {
  "use strict";

  /** ES: Abre únicamente un diálogo existente. EN: Opens only an existing dialog. */
  document.querySelectorAll("[data-open-part-dialog]").forEach(function (trigger) {
    trigger.addEventListener("click", function () {
      var dialog = document.getElementById(trigger.dataset.openPartDialog || "");
      if (dialog && typeof dialog.showModal === "function") dialog.showModal();
    });
  });

  /** ES: Cierra desde botones o clic directo en el fondo. EN: Closes from buttons or a direct backdrop click. */
  document.querySelectorAll(".part-public-dialog").forEach(function (dialog) {
    dialog.querySelectorAll("[data-close-part-dialog]").forEach(function (trigger) {
      trigger.addEventListener("click", function () { dialog.close(); });
    });
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) dialog.close();
    });
  });
}());
