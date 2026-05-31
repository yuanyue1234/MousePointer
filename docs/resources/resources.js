const grid = document.getElementById("resourceGrid");
const statusPanel = document.getElementById("statusPanel");

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;"
  }[char]));
}

function renderEmpty(data) {
  statusPanel.textContent = data && data.note ? data.note : "No resources have been published yet.";
  grid.innerHTML = "";
}

function renderResources(data) {
  const items = Array.isArray(data.items) ? data.items : [];
  if (!items.length) {
    renderEmpty(data);
    return;
  }

  statusPanel.textContent = `Resources: ${items.length}. Updated: ${data.updated || "unknown"}.`;
  grid.innerHTML = items.map((item) => {
    const tags = Array.isArray(item.tags) ? item.tags : [];
    const preview = escapeHtml(item.preview || "../images/app-icon.png");
    const name = escapeHtml(item.name || "Untitled resource");
    const description = item.description ? `<p>${escapeHtml(item.description)}</p>` : "";
    const size = item.size ? `<p>${escapeHtml(item.size)}</p>` : "";
    const tagHtml = tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("");
    const download = item.download
      ? `<a class="download-link" href="${escapeHtml(item.download)}" target="_blank" rel="noreferrer">Download</a>`
      : "";
    return `
      <article class="resource-card">
        <img src="${preview}" alt="${name} preview">
        <h2>${name}</h2>
        ${description}
        ${size}
        ${tagHtml ? `<div class="tag-row">${tagHtml}</div>` : ""}
        ${download}
      </article>
    `;
  }).join("");
}

fetch("./resources.json", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
  })
  .then(renderResources)
  .catch((error) => {
    statusPanel.textContent = `Failed to load resource catalog: ${error.message}`;
  });
