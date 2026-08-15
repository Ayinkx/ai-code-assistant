// AI Code Assistant — invitation landing page
// Accept or decline a workspace invitation through the token endpoint.

(function () {
  "use strict";

  var TOKEN = window.INVITE_TOKEN || "";
  var EMAIL_OK = window.INVITE_EMAIL_OK === true;

  function getCsrf() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.content;
    var input = document.querySelector('input[name="csrf_token"]');
    return input ? input.value : "";
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

  function flash(message, category) {
    var status = document.getElementById("invite-status");
    status.hidden = false;
    status.textContent = message;
    status.style.color = category === "error" ? "#fca5a5" : "#6ee7b7";
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!EMAIL_OK) return;
    var accept = document.getElementById("accept-btn");
    var decline = document.getElementById("decline-btn");
    if (accept) {
      accept.addEventListener("click", function () {
        accept.disabled = true;
        api("/workspaces/api/invitations/" + encodeURIComponent(TOKEN) + "/accept", {
          method: "POST",
        })
          .then(function (data) {
            var ws = data.membership ? data.membership.workspace_id : null;
            flash("You joined the workspace!", "success");
            setTimeout(function () {
              window.location.href = ws ? "/workspaces/" + ws + "/members" : "/workspaces/";
            }, 800);
          })
          .catch(function (error) {
            flash(error.message, "error");
            accept.disabled = false;
          });
      });
    }
    if (decline) {
      decline.addEventListener("click", function () {
        if (!confirm("Decline this invitation?")) return;
        decline.disabled = true;
        api("/workspaces/api/invitations/" + encodeURIComponent(TOKEN) + "/decline", {
          method: "POST",
        })
          .then(function () {
            flash("Invitation declined.", "success");
            setTimeout(function () { window.location.reload(); }, 800);
          })
          .catch(function (error) {
            flash(error.message, "error");
            decline.disabled = false;
          });
      });
    }
  });
})();
