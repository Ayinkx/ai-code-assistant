// AI Code Assistant — notifications inbox
// List, mark-read, mark-all-read, and preferences for the current user.

(function () {
  "use strict";

  var PAGE = 1;
  var PER_PAGE = 20;

  function getCsrf() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.content;
    var input = document.querySelector('input[name="csrf_token"]');
    return input ? input.value : "";
  }

  function flash(message, category) {
    var stack = document.querySelector(".flash-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "flash-stack";
      var main = document.querySelector(".main-content");
      (main || document.body).prepend(stack);
    }
    var el = document.createElement("div");
    el.className = "flash flash-" + (category || "info");
    el.textContent = message;
    stack.appendChild(el);
    setTimeout(function () { el.remove(); }, 6000);
  }

  function api(url, options) {
    options = options || {};
    options.headers = Object.assign({}, options.headers || {}, {
      "X-CSRFToken": getCsrf(),
    });
    return fetch(url, options).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) {
          var error = new Error(data && data.error ? data.error : "Request failed (" + response.status + ").");
          throw error;
        }
        return data;
      });
    });
  }

  function escapeHtml(value) {
    var div = document.createElement("div");
    div.textContent = value == null ? "" : String(value);
    return div.innerHTML;
  }

  function formatTime(iso) {
    if (!iso) return "";
    return new Date(iso).toLocaleString();
  }

  function refreshBadge() {
    fetch("/workspaces/api/notifications/count", { credentials: "same-origin" })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        var badge = document.getElementById("notif-badge");
        if (!badge) return;
        var count = data && data.unread ? data.unread : 0;
        badge.hidden = count === 0;
        badge.textContent = count > 99 ? "99+" : String(count);
      })
      .catch(function () {});
  }

  function loadNotifications() {
    var list = document.getElementById("notification-list");
    api("/workspaces/api/notifications?page=" + PAGE + "&per_page=" + PER_PAGE)
      .then(function (data) {
        if (!data.items.length) {
          list.innerHTML = '<p class="empty-note">You have no notifications.</p>';
          return;
        }
        var html = "";
        data.items.forEach(function (n) {
          var title = (n.payload && n.payload.title) || n.type;
          var meta = n.actor_username ? "From " + n.actor_username + " &middot; " : "";
          meta += formatTime(n.created_at);
          var link = n.link ? ' <a class="notification-link" href="' + escapeHtml(n.link) + '">Open</a>' : "";
          var markBtn = n.is_read
            ? ""
            : '<button class="btn btn-ghost btn-sm notif-read" data-id="' + n.id + '" type="button">Mark read</button>';
          html +=
            '<div class="notification-row' + (n.is_read ? "" : " unread") + '">' +
            '<div class="notification-info">' +
            "<div>" +
            '<div class="notification-title">' + escapeHtml(title) + link + "</div>" +
            '<div class="notification-meta">' + meta + "</div>" +
            "</div>" +
            "</div>" +
            '<div class="notification-actions">' + markBtn + "</div>" +
            "</div>";
        });
        list.innerHTML = html;
        if (data.total > data.items.length) {
          var pager = document.createElement("div");
          pager.className = "pager";
          pager.innerHTML =
            '<button id="prev-page" class="btn btn-ghost btn-sm" type="button" disabled>Previous</button>' +
            '<span class="field-hint">Page ' + data.page + " of " + Math.max(1, Math.ceil(data.total / data.per_page)) + "</span>" +
            '<button id="next-page" class="btn btn-ghost btn-sm" type="button"' + (data.page * data.per_page >= data.total ? " disabled" : "") + ">Next</button>";
          list.appendChild(pager);
          document.getElementById("prev-page").disabled = data.page <= 1;
          document.getElementById("prev-page").addEventListener("click", function () {
            PAGE -= 1;
            loadNotifications();
          });
          document.getElementById("next-page").addEventListener("click", function () {
            PAGE += 1;
            loadNotifications();
          });
        }

        list.querySelectorAll(".notif-read").forEach(function (btn) {
          btn.addEventListener("click", function () {
            api("/workspaces/api/notifications/" + btn.dataset.id + "/read", { method: "POST" })
              .then(function () { loadNotifications(); refreshBadge(); })
              .catch(function (error) { flash(error.message, "error"); });
          });
        });
      })
      .catch(function (error) {
        list.innerHTML = '<p class="empty-note">' + escapeHtml(error.message) + "</p>";
      });
  }

  function loadPreferences() {
    var toggles = document.querySelectorAll(".pref-toggle");
    api("/workspaces/api/notifications/preferences")
      .then(function (prefs) {
        toggles.forEach(function (toggle) {
          toggle.checked = !!prefs[toggle.dataset.key];
          toggle.addEventListener("change", function () {
            var update = {};
            update[toggle.dataset.key] = toggle.checked;
            api("/workspaces/api/notifications/preferences", {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(update),
            })
              .then(function () {})
              .catch(function (error) {
                flash(error.message, "error");
                toggle.checked = !toggle.checked;
              });
          });
        });
      })
      .catch(function (error) {
        flash(error.message, "error");
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadNotifications();
    loadPreferences();
    document.getElementById("mark-all-read").addEventListener("click", function () {
      api("/workspaces/api/notifications/read-all", { method: "POST" })
        .then(function () { loadNotifications(); refreshBadge(); })
        .catch(function (error) { flash(error.message, "error"); });
    });
  });
})();
