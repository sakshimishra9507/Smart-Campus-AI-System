/* Developer-focused debugging dashboard; backend transport is injected. */
(function () {
  const steps = [
    ["agent.started","Agent started"],["agent.planning","Planning"],
    ["agent.searching","Searching repository"],["agent.inspecting_file","Inspecting file"],
    ["agent.hypothesis_created","Creating hypothesis"],["agent.testing","Testing hypothesis"],
    ["agent.root_cause_identified","Root cause identified"],["agent.patch_generated","Generating patch"],
    ["agent.waiting_for_approval","Waiting for approval"],["agent.patch_applied","Patch application"],
    ["agent.sandbox_started","Sandbox"],["agent.testing_completed","Running tests"],
    ["agent.validation_completed","Validation completed"],["agent.completed","Agent completed"],
    ["agent.failed","Agent failed"]
  ];
  window.createDebuggingDashboard = function(root, options) {
    options = options || {};
    const state = {events: []};
    root.innerHTML = '<div class="dev-dashboard">' +
      '<aside class="repo-explorer"><h3>Repository Explorer</h3><div data-panel="repo"></div></aside>' +
      '<main><header class="dashboard-header"><h2>Autonomous Debugger</h2><span data-status>Idle</span></header>' +
      '<section class="timeline" data-panel="timeline"></section>' +
      '<section class="dashboard-grid">' +
      '<article><h3>Investigation</h3><pre data-panel="investigation"></pre></article>' +
      '<article><h3>Root Cause</h3><pre data-panel="root"></pre></article>' +
      '<article><h3>Diff</h3><pre data-panel="diff"></pre></article>' +
      '<article><h3>Test Results</h3><pre data-panel="tests"></pre></article>' +
      '<article><h3>Git Status</h3><pre data-panel="git"></pre></article>' +
      '<article><h3>Audit Log</h3><pre data-panel="audit"></pre></article></section></main>' +
      '<aside class="code-viewer"><h3>Code Viewer</h3><pre data-panel="code"></pre></aside></div>';
    const panel = name => root.querySelector('[data-panel="'+name+'"]');
    function addEvent(event) {
      state.events.push(event);
      const item = document.createElement("div");
      item.className = "timeline-event";
      item.innerHTML = '<span class="timeline-dot"></span><div><strong>'+escape(event.event)+'</strong><small>'+new Date(event.timestamp*1000).toLocaleTimeString()+'</small><pre>'+escape(JSON.stringify(event.payload||{},null,2))+'</pre></div>';
      panel("timeline").appendChild(item);
      panel("audit").textContent = JSON.stringify(state.events, null, 2);
      panel("tests").textContent = JSON.stringify(event.payload?.test_results || {}, null, 2);
      panel("git").textContent = JSON.stringify(event.payload?.git_status || {}, null, 2);
      panel("root").textContent = JSON.stringify(event.payload?.root_cause || {}, null, 2);
      panel("investigation").textContent = JSON.stringify(event.payload?.investigation || {}, null, 2);
      panel("diff").textContent = event.payload?.diff || "";
      panel("code").textContent = event.payload?.code || "";
      root.querySelector("[data-status]").textContent = event.event.replace("agent.","");
    }
    return { addEvent, state, connect: options.connect || null };
  };
  function escape(v) { return String(v).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
})();
