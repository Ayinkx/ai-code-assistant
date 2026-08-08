// AI Code Assistant — Reviews: history, detail, project reviews, and config.
(function () {
  "use strict";

  var GH = window.GitHub;
  var SEVERITY_ORDER = ["critical", "high", "medium", "low", "informational"];

  function projectId() {
    var el = document.querySelector(".github-header");
    return el ? el.getAttribute("data-project-id") : null;
  }

  function reviewId() {
    var el = document.querySelector(".github-header");
    return el ? el.getAttribute("data-review-id") : null;
  }

  function severityClass(severity) {
    return "badge-severity-" + (SEVERITY_ORDER.indexOf(severity) >= 0 ? severity : "medium");
  }

  function badge(severity) {
    return '<span class="tag ' + severityClass(severity) + '">' + GH.escapeHtml(severity) + "</span>";
  }

  function sourceLabel(review) {
    if (review.source === "github_pr") {
      return review.owner + "/" + review.repo + " #" + (review.pr_number || "");
    }
    return review.kind + " review";
  }

  function statusLabel(review) {
    var cls = review.status === "completed" ? "tag-public" : review.status === "failed" ? "tag-private" : "";
    return '<span class="tag ' + cls + '">' + GH.escapeHtml(review.status) + "</span>";
  }

  function reviewCard(review) {
    var meta = sourceLabel(review);
    return (
      '<a class="issue-item" href="/reviews/' + review.id + '">' +
      '<div class="issue-item-title">' +
      statusLabel(review) + " " + GH.escapeHtml(meta) +
      "</div>" +
      '<div class="issue-item-sub">' +
      "kind " + GH.escapeHtml(review.kind) + " &middot; " +
      (review.findings_count || 0) + " findings &middot; " +
      GH.relativeDate(review.created_at) +
      "</div>" +
      "</a>"
    );
  }

  // ----- Quality dashboard strip ----------------------------------------

  function renderMetrics(metrics, container) {
    if (!container) return;
    var findings = metrics.findings || {};
    var parts = [
      "<div class='metric-card'>",
      "<span class='metric-value'>" + metrics.total_reviews + "</span>",
      "<span class='metric-label'>reviews</span>",
      "</div>",
      "<div class='metric-card'>",
      "<span class='metric-value'>" + (findings.total || 0) + "</span>",
      "<span class='metric-label'>findings</span>",
      "</div>",
      "<div class='metric-card'>",
      "<span class='metric-value'>" + (findings.high_risk || 0) + "</span>",
      "<span class='metric-label'>high risk</span>",
      "</div>",
      "<div class='metric-card'>",
      "<span class='metric-value'>" + (findings.unaddressed_high_risk || 0) + "</span>",
      "<span class='metric-label'>open high risk</span>",
      "</div>",
      "<div class='metric-card'>",
      "<span class='metric-value'>" + (findings.confirmed || 0) + "</span>",
      "<span class='metric-label'>confirmed</span>",
      "</div>",
    ];
    container.innerHTML = "<div class='metric-grid'>" + parts.join("") + "</div>";
  }

  function loadMetrics(container) {
    var pid = projectId();
    var url = "/reviews/api/metrics" + (pid ? "?project_id=" + encodeURIComponent(pid) : "");
    GH.api(url).then(function (metrics) {
      renderMetrics(metrics, container);
    }).catch(function () {
      container.innerHTML = '<p class="sidebar-empty">Quality metrics unavailable.</p>';
    });
  }

  // ----- Index / history -------------------------------------------------

  function loadReviewList(container, filter) {
    var params = [];
    if (filter) {
      if (filter.source) params.push("source=" + encodeURIComponent(filter.source));
      if (filter.kind) params.push("kind=" + encodeURIComponent(filter.kind));
      if (filter.project_id) params.push("project_id=" + encodeURIComponent(filter.project_id));
    }
    var url = "/reviews/api/reviews" + (params.length ? "?" + params.join("&") : "");
    GH.api(url).then(function (reviews) {
      container.innerHTML = "";
      if (!reviews.length) {
        container.innerHTML =
          '<p class="sidebar-empty">No reviews yet. Run a review from a project or a pull request.</p>';
        return;
      }
      reviews.forEach(function (review) {
        var el = document.createElement("div");
        el.innerHTML = reviewCard(review);
        container.appendChild(el.firstChild);
      });
    }).catch(function (error) {
      container.innerHTML = '<p class="sidebar-empty">Could not load reviews.</p>';
      GH.flashError(error.message);
    });
  }

  function initIndex() {
    var metricsEl = document.getElementById("metrics-strip");
    var listEl = document.getElementById("review-list");
    if (!listEl) return;
    loadMetrics(metricsEl);
    loadReviewList(listEl, null);
  }

  // ----- Detail ----------------------------------------------------------

  function findingsUrl(base) {
    var severity = document.getElementById("finding-severity");
    var confidence = document.getElementById("finding-confidence");
    var addressed = document.getElementById("finding-addressed");
    var params = [];
    if (severity && severity.value) params.push("severity=" + encodeURIComponent(severity.value));
    if (confidence && confidence.value) params.push("confidence=" + encodeURIComponent(confidence.value));
    if (addressed && addressed.value !== "") params.push("addressed=" + encodeURIComponent(addressed.value));
    return base + (params.length ? "?" + params.join("&") : "");
  }

  function summarySection(title, items) {
    if (!items || !items.length) return "";
    return (
      "<h4>" + GH.escapeHtml(title) + "</h4><ul>" +
      items.map(function (item) {
        return "<li>" + GH.renderMarkdownish(item) + "</li>";
      }).join("") +
      "</ul>"
    );
  }

  function findingCard(finding) {
    var location = finding.file ? GH.escapeHtml(finding.file) : "(whole repo)";
    if (finding.line != null) location += ":" + finding.line;
    var addressed = finding.addressed
      ? '<span class="tag tag-confirmed">addressed</span>'
      : '<span class="tag tag-suggestion">open</span>';
    return (
      '<div class="finding-card">' +
      '<div class="finding-header">' +
      badge(finding.severity) +
      " " + GH.escapeHtml(finding.category) +
      " <span class='finding-location'>" + location + "</span>" +
      '<button class="btn btn-ghost btn-sm finding-toggle" data-id="' + finding.id +
      '" data-addressed="' + (finding.addressed ? "0" : "1") + '" type="button">' +
      (finding.addressed ? "Reopen" : "Mark addressed") + "</button>" +
      "</div>" +
      "<p class='finding-confidence'>confidence: " + GH.escapeHtml(finding.confidence) + "</p>" +
      "<p>" + GH.renderMarkdownish(finding.explanation) + "</p>" +
      (finding.recommendation
        ? "<p class='finding-recommendation'><strong>Recommendation:</strong> " +
          GH.renderMarkdownish(finding.recommendation) + "</p>"
        : "") +
      "</div>"
    );
  }

  function loadFindings(reviewId) {
    var container = document.getElementById("finding-list");
    var countEl = document.getElementById("finding-count");
    container.innerHTML = '<p class="sidebar-empty">Loading findings...</p>';
    GH.api(findingsUrl("/reviews/api/reviews/" + reviewId + "/findings"))
      .then(function (findings) {
        container.innerHTML = "";
        if (countEl) countEl.textContent = findings.length + " finding" + (findings.length === 1 ? "" : "s");
        if (!findings.length) {
          container.innerHTML = '<p class="sidebar-empty">No findings match.</p>';
          return;
        }
        findings.slice().sort(function (a, b) {
          var ra = SEVERITY_ORDER.indexOf(a.severity);
          var rb = SEVERITY_ORDER.indexOf(b.severity);
          return (ra < 0 ? 99 : ra) - (rb < 0 ? 99 : rb);
        }).forEach(function (finding) {
          var el = document.createElement("div");
          el.innerHTML = findingCard(finding);
          container.appendChild(el.firstChild);
        });
      })
      .catch(function (error) {
        container.innerHTML = '<p class="sidebar-empty">Could not load findings.</p>';
        GH.flashError(error.message);
      });
  }

  function loadDetail() {
    var id = reviewId();
    var container = document.getElementById("review-detail");
    if (!container || !id) return;
    GH.api("/reviews/api/reviews/" + id).then(function (review) {
      var summary = review.summary || {};
      var title = review.source === "github_pr"
        ? review.owner + "/" + review.repo + " #" + (review.pr_number || "") + " — " + (review.pr_title || "")
        : review.kind + " review";
      container.innerHTML =
        '<div class="issue-detail-header">' +
        "<h2>" + GH.escapeHtml(title) + "</h2>" +
        '<div class="issue-meta">' +
        statusLabel(review) + " " + GH.escapeHtml(review.kind) + " &middot; " +
        (review.findings_count || 0) + " findings &middot; " + GH.relativeDate(review.created_at) +
        "</div>" +
        (review.error_message ? '<p class="flash flash-error">' + GH.escapeHtml(review.error_message) + "</p>" : "") +
        "</div>" +
        '<div class="analysis-output">' +
        summarySection("Overall assessment", summary.overall_assessment ? [summary.overall_assessment] : []) +
        summarySection("Important findings", summary.important_findings) +
        summarySection("Suggested improvements", summary.suggested_improvements) +
        summarySection("Testing recommendations", summary.testing_recommendations) +
        summarySection("Security concerns", summary.security_concerns) +
        summarySection("Performance concerns", summary.performance_concerns) +
        summarySection("Files affected", summary.files_affected) +
        (review.status === "failed" ? '<p class="sidebar-empty">This review did not complete.</p>' : "") +
        "</div>";
      loadFindings(id);
    }).catch(function (error) {
      container.innerHTML = '<p class="sidebar-empty">Could not load review.</p>';
      GH.flashError(error.message);
    });
  }

  function initDetail() {
    var deleteBtn = document.getElementById("delete-review");
    var id = reviewId();
    if (!document.getElementById("review-detail")) return;
    loadDetail();
    document.getElementById("finding-severity").addEventListener("change", function () { loadFindings(id); });
    document.getElementById("finding-confidence").addEventListener("change", function () { loadFindings(id); });
    document.getElementById("finding-addressed").addEventListener("change", function () { loadFindings(id); });
    document.addEventListener("click", function (event) {
      var toggle = event.target.closest(".finding-toggle");
      if (toggle) {
        GH.api("/reviews/api/reviews/findings/" + toggle.getAttribute("data-id"), {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ addressed: toggle.getAttribute("data-addressed") === "1" }),
        }).then(function () {
          loadFindings(id);
        }).catch(function (error) { GH.flashError(error.message); });
      }
    });
    if (deleteBtn) {
      deleteBtn.addEventListener("click", function () {
        if (!window.confirm("Delete this review and its findings?")) return;
        GH.api("/reviews/api/reviews/" + id, { method: "DELETE" })
          .then(function () { window.location.href = "/reviews/"; })
          .catch(function (error) { GH.flashError(error.message); });
      });
    }
  }

  // ----- Project reviews -------------------------------------------------

  function runReview(kind, statusEl) {
    var pid = projectId();
    statusEl.hidden = false;
    statusEl.textContent = "Running " + kind + " review...";
    GH.api("/reviews/api/reviews", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: "project", project_id: pid, kind: kind }),
    }).then(function (review) {
      statusEl.textContent = "";
      statusEl.hidden = true;
      if (review.status === "failed") {
        GH.flashError("Review failed: " + (review.error_message || "unknown error"));
      } else {
        window.location.href = "/reviews/" + review.id;
      }
    }).catch(function (error) {
      statusEl.hidden = false;
      statusEl.textContent = "";
      GH.flashError(error.message);
    });
  }

  function initProject() {
    var pid = projectId();
    var listEl = document.getElementById("review-list");
    if (!listEl) return;
    var metricsEl = document.getElementById("metrics-strip");
    loadMetrics(metricsEl);
    loadReviewList(listEl, { project_id: pid });
    var statusEl = document.getElementById("run-status");
    document.querySelectorAll(".review-run-buttons .btn").forEach(function (button) {
      button.addEventListener("click", function () {
        runReview(button.getAttribute("data-kind"), statusEl);
      });
    });
  }

  // ----- Config ----------------------------------------------------------

  function initConfig() {
    var pid = projectId();
    var saveBtn = document.getElementById("save-config");
    if (!saveBtn) return;
    GH.api("/reviews/api/projects/" + pid + "/config").then(function (config) {
      document.getElementById("cfg-enabled").value = config.enabled ? "1" : "0";
      var kinds = (config.kinds || "").split(",").map(function (k) { return k.trim(); });
      document.querySelectorAll("#cfg-kinds input[type=checkbox]").forEach(function (box) {
        box.checked = kinds.indexOf(box.value) >= 0;
      });
      document.getElementById("cfg-severity").value = config.severity_threshold || "low";
      document.getElementById("cfg-languages").value = config.languages || "";
      document.getElementById("cfg-security-focus").checked = !!config.security_focus;
      document.getElementById("cfg-performance-focus").checked = !!config.performance_focus;
      document.getElementById("cfg-testing-focus").checked = !!config.testing_focus;
      document.getElementById("cfg-max-files").value = config.max_files || "";
      document.getElementById("cfg-max-context").value = config.max_context_chars || "";
    }).catch(function (error) {
      GH.flashError(error.message);
    });

    saveBtn.addEventListener("click", function () {
      var kinds = [];
      document.querySelectorAll("#cfg-kinds input[type=checkbox]:checked").forEach(function (box) {
        kinds.push(box.value);
      });
      var payload = {
        enabled: document.getElementById("cfg-enabled").value === "1",
        kinds: kinds.join(","),
        severity_threshold: document.getElementById("cfg-severity").value,
        languages: document.getElementById("cfg-languages").value.trim(),
        security_focus: document.getElementById("cfg-security-focus").checked,
        performance_focus: document.getElementById("cfg-performance-focus").checked,
        testing_focus: document.getElementById("cfg-testing-focus").checked,
        max_files: parseInt(document.getElementById("cfg-max-files").value, 10),
        max_context_chars: parseInt(document.getElementById("cfg-max-context").value, 10),
      };
      var statusEl = document.getElementById("save-status");
      statusEl.textContent = "Saving...";
      GH.api("/reviews/api/projects/" + pid + "/config", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).then(function () {
        statusEl.textContent = "Saved.";
        setTimeout(function () { statusEl.textContent = ""; }, 3000);
      }).catch(function (error) {
        statusEl.textContent = "";
        GH.flashError(error.message);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (document.getElementById("review-list") && !projectId()) {
      initIndex();
    } else if (document.getElementById("review-detail")) {
      initDetail();
    } else if (document.getElementById("review-list") && projectId()) {
      initProject();
    } else if (document.getElementById("save-config")) {
      initConfig();
    }
  });
})();
