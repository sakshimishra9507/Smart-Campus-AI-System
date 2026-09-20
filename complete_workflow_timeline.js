/* Full debugging workflow timeline. */
(function () {
  const labels = [
    ["problem_reported", "User Problem"],
    ["planning", "Planner"],
    ["repository_analysis", "Repository Intelligence"],
    ["code_searching", "Code Search"],
    ["debugging", "Debugger"],
    ["root_cause_identified", "Root Cause"],
    ["fix_proposed", "Fixer"],
    ["patch_generated", "Diff"],
    ["approval_required", "User Approval"],
    ["patch_applied", "Patch Application"],
    ["sandbox_started", "Sandbox"],
    ["tests_completed", "Tests"],
    ["validation_completed", "Validation"],
    ["final_report", "Final Report"]
  ];

  window.renderCompleteDebuggingTimeline = function (container, events) {
    if (!container) return;
    const byName = new Map((events || []).map(e => [e.event, e]));
    container.innerHTML = "";
    labels.forEach(([name, label]) => {
      const event = byName.get(name);
      const item = document.createElement("div");
      item.className = "workflow-timeline-item " + (event ? "completed" : "pending");
      item.innerHTML =
        '<div class="workflow-timeline-marker">' + (event ? "✓" : "○") + "</div>" +
        '<div class="workflow-timeline-content"><strong>' + label + "</strong>" +
        (event ? '<pre>' + escapeHtml(JSON.stringify(event.payload || {}, null, 2)) + "</pre>" : "") +
        "</div>";
      container.appendChild(item);
    });
  };

  function escapeHtml(value) {
    return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
})();
