/* Read-only debugging timeline renderer. The backend may supply DebuggingResult.timeline. */
window.renderDebuggingTimeline = function (container, events) {
  if (!container) return;
  container.innerHTML = "";
  (events || []).forEach(function (event) {
    var item = document.createElement("div");
    item.className = "debug-timeline-item";
    var title = document.createElement("strong");
    title.textContent = event.name;
    var time = document.createElement("time");
    time.textContent = event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : "";
    item.appendChild(title);
    item.appendChild(time);
    if (event.payload) {
      var detail = document.createElement("span");
      detail.textContent = JSON.stringify(event.payload);
      item.appendChild(detail);
    }
    container.appendChild(item);
  });
};
