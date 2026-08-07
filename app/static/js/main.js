// AI Code Assistant — client-side helpers
// Phase 1: minimal, progressive enhancement. Future phases add the editor,
// chat UI, and real-time features here.

(function () {
  "use strict";

  // Auto-dismiss flash messages after a short delay.
  document.addEventListener("DOMContentLoaded", function () {
    var flashes = document.querySelectorAll(".flash");
    flashes.forEach(function (flash) {
      setTimeout(function () {
        flash.style.transition = "opacity .4s ease";
        flash.style.opacity = "0";
        setTimeout(function () {
          flash.remove();
        }, 400);
      }, 4000);
    });
  });
})();
