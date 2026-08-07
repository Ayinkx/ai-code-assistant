// AI Code Assistant — GitHub repository browser
// Loads and filters the connected user's repositories.

(function () {
  "use strict";

  var GH = window.GitHub;
  var listEl = document.getElementById("repo-list");
  var searchEl = document.getElementById("repo-search");

  function render(repos) {
    listEl.innerHTML = "";
    if (!repos.length) {
      listEl.innerHTML = '<p class="sidebar-empty">No repositories found. Your GitHub account may need the <code>repo</code> scope.</p>';
      return;
    }
    repos.forEach(function (repo) {
      var card = document.createElement("div");
      card.className = "repo-card";
      var visibility = repo.private ? '<span class="tag tag-private">private</span>' : '<span class="tag tag-public">public</span>';
      var language = repo.language ? '<span class="repo-language">' + GH.escapeHtml(repo.language) + "</span>" : "";
      var description = repo.description
        ? '<p class="repo-description">' + GH.escapeHtml(repo.description) + "</p>"
        : "";
      card.innerHTML =
        '<div class="repo-card-header">' +
        '<a class="repo-name" href="/github/repos/' + encodeURIComponent(repo.full_name.split("/")[0]) + "/" + encodeURIComponent(repo.full_name.split("/")[1]) + '">' +
        GH.escapeHtml(repo.full_name) + "</a> " + visibility +
        "</div>" +
        description +
        '<div class="repo-card-meta">' + language +
        '<span class="repo-updated">Updated ' + GH.relativeDate(repo.updated_at) + "</span>" +
        "</div>";
      listEl.appendChild(card);
    });
  }

  function refresh() {
    var query = searchEl.value.trim();
    var url = "/github/api/repos" + (query ? "?q=" + encodeURIComponent(query) : "");
    GH.api(url).then(render).catch(function (error) {
      if (error.kind === "not_connected") {
        listEl.innerHTML = '<p class="sidebar-empty">Connect your GitHub account first.</p>';
      } else {
        listEl.innerHTML = '<p class="sidebar-empty">Could not load repositories.</p>';
        GH.flashError(error.message);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!listEl || !searchEl) return;
    refresh();
    searchEl.addEventListener("input", refresh);
  });
})();
