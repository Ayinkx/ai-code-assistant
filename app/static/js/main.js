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

  // Refresh the header notification badge (Phase 7 #156).
  function refreshNotificationBadge() {
    var badge = document.getElementById("notif-badge");
    if (!badge) return;
    fetch("/workspaces/api/notifications/count", { credentials: "same-origin" })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        var count = data && data.unread ? data.unread : 0;
        badge.hidden = count === 0;
        badge.textContent = count > 99 ? "99+" : String(count);
      })
      .catch(function () {
        // The count is a progressive enhancement; ignore failures.
      });
  }

  document.addEventListener("DOMContentLoaded", refreshNotificationBadge);
  setInterval(refreshNotificationBadge, 60000);
})();
