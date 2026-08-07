// AI Code Assistant — GitHub issue detail page with AI analysis
(function () {
  "use strict";

  var GH = window.GitHub;
  var crumbs = document.querySelector(".github-header h1").textContent;
  var match = crumbs.match(/\/([^/]+)\/([^/]+)\s*\/\s*Issues\s*\/\s*#\d+/);
  var OWNER = match ? match[1] : "";
  var REPO = match ? match[2] : "";
  var NUMBER = null;
  var numberMatch = crumbs.match(/#(\d+)/);
  if (numberMatch) NUMBER = numberMatch[1];

  var detailEl = document.getElementById("issue-detail");
  var analysisEl = document.getElementById("issue-analysis");

  function render(issue) {
    var labels = (issue.labels || []).map(function (label) {
      return '<span class="tag">' + GH.escapeHtml(label) + "</span>";
    }).join(" ");
    detailEl.innerHTML =
      '<div class="issue-detail-header">' +
      '<h2>#' + issue.number + " " + GH.escapeHtml(issue.title) + "</h2>" +
      '<div class="issue-meta">' + labels + " " +
      '<span class="tag ' + (issue.state === "open" ? "tag-public" : "tag-private") + '">' + GH.escapeHtml(issue.state) + "</span> " +
      GH.escapeHtml(issue.author || "") + " opened " + GH.relativeDate(issue.created_at) +
      (issue.comments ? " &middot; " + issue.comments + " comments" : "") +
      "</div>" +
      "</div>" +
      '<div class="issue-body">' + GH.renderMarkdownish(issue.body) + "</div>";
  }

  function load(analyze) {
    detailEl.innerHTML = '<p class="sidebar-empty">Loading issue...</p>';
    var url = "/github/api/repos/" + encodeURIComponent(OWNER) + "/" + encodeURIComponent(REPO) +
      "/issues/" + NUMBER + (analyze ? "?analyze=1" : "");
    GH.api(url).then(function (issue) {
      render(issue);
      if (issue.analysis) {
        GH.renderAnalysis(analysisEl, issue.analysis.analysis);
      }
    }).catch(function (error) {
      detailEl.innerHTML = '<p class="sidebar-empty">Could not load issue.</p>';
      GH.flashError(error.message);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!detailEl) return;
    load(false);
    document.getElementById("analyze-issue").addEventListener("click", function () {
      analysisEl.hidden = false;
      analysisEl.innerHTML = '<p class="sidebar-empty">Analyzing issue...</p>';
      GH.api("/github/api/repos/" + encodeURIComponent(OWNER) + "/" + encodeURIComponent(REPO) +
        "/issues/" + NUMBER + "?analyze=1")
        .then(function (issue) {
          GH.renderAnalysis(analysisEl, issue.analysis.analysis);
        })
        .catch(function (error) {
          analysisEl.innerHTML = "";
          GH.flashError(error.message);
        });
    });
  });
})();
