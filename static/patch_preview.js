/* Patch review UI: preview first; approval/rejection are explicit actions. */
window.renderPatchPreview = function (container, patch, handlers) {
  if (!container || !patch) return;
  handlers = handlers || {};
  container.innerHTML = "";

  var title = document.createElement("h3");
  title.textContent = "Proposed Patch";
  container.appendChild(title);

  var status = document.createElement("div");
  status.className = "patch-status";
  status.textContent = "Status: " + (patch.status || "pending");
  container.appendChild(status);

  var pre = document.createElement("pre");
  pre.className = "patch-diff";
  pre.textContent = patch.diff || "";
  container.appendChild(pre);

  var rationale = document.createElement("p");
  rationale.textContent = patch.rationale || "";
  container.appendChild(rationale);

  if ((patch.status || "pending") === "pending") {
    var approve = document.createElement("button");
    approve.type = "button";
    approve.textContent = "Approve patch";
    approve.className = "patch-approve";
    approve.addEventListener("click", function () {
      if (handlers.approve) handlers.approve(patch.patch_id);
    });

    var reject = document.createElement("button");
    reject.type = "button";
    reject.textContent = "Reject patch";
    reject.className = "patch-reject";
    reject.addEventListener("click", function () {
      if (handlers.reject) handlers.reject(patch.patch_id);
    });
    container.appendChild(approve);
    container.appendChild(reject);
  }
};
