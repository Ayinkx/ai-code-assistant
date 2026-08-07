// AI Code Assistant — workspaces list page
// Creates new workspaces from the modal form.

(function () {
  "use strict";

  function getCsrf() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.content;
    var input = document.querySelector('input[name="csrf_token"]');
    return input ? input.value : "";
  }

  function flashError(message) {
    var el = document.createElement("div");
    el.className = "flash flash-error";
    el.textContent = message;
    var main = document.querySelector(".main-content");
    (main || document.body).prepend(el);
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

  document.addEventListener("DOMContentLoaded", function () {
    var modal = document.getElementById("workspace-modal");
    var nameEl = document.getElementById("ws-name");
    var descEl = document.getElementById("ws-description");
    var createBtn = document.getElementById("create-workspace");

    document.getElementById("new-workspace").addEventListener("click", function () {
      modal.hidden = false;
      nameEl.focus();
    });

    modal.querySelectorAll(".modal-close").forEach(function (btn) {
      btn.addEventListener("click", function () {
        modal.hidden = true;
      });
    });

    modal.addEventListener("click", function (event) {
      if (event.target === modal) modal.hidden = true;
    });

    function createWorkspace() {
      var name = nameEl.value.trim();
      if (!name) {
        nameEl.focus();
        return;
      }
      createBtn.disabled = true;
      api("/workspaces/api/workspaces", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name, description: descEl.value.trim() }),
      })
        .then(function (workspace) {
          window.location.href = "/workspaces/" + workspace.id;
        })
        .catch(function (error) {
          flashError(error.message);
          createBtn.disabled = false;
        });
    }

    createBtn.addEventListener("click", createWorkspace);
    nameEl.addEventListener("keydown", function (event) {
      if (event.key === "Enter") createWorkspace();
    });
  });
})();
