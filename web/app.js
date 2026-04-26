const answer = document.querySelector("#answer");
const sources = document.querySelector("#sources");
const taskStage = document.querySelector("#taskStage");
const crawlTotal = document.querySelector("#crawlTotal");
const crawlSuccess = document.querySelector("#crawlSuccess");
const crawlFailed = document.querySelector("#crawlFailed");
const crawlStatusList = document.querySelector("#crawlStatusList");
const sourceList = document.querySelector("#sourceList");
const documentList = document.querySelector("#documentList");
const searchUrlBox = document.querySelector("#searchUrlBox");
let activeSource = "url";

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function parseUrls(value) {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => {
      if (item.startsWith("http://") || item.startsWith("https://")) return item;
      if (item.includes(".") && !/\s/.test(item)) return `https://${item}`;
      return "";
    })
    .filter(Boolean);
}

function setActiveSource(source) {
  activeSource = source;
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.source === source);
  });
  document.querySelectorAll(".source-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `source-${source}`);
  });
  setStage("待开始");
}

function setMode(mode) {
  document.querySelectorAll(".mode-card").forEach((card) => {
    card.classList.toggle("active", card.querySelector("input").value === mode);
  });
  searchUrlBox.classList.toggle("hidden", mode !== "knowledge_ai_search");
}

function currentMode() {
  return document.querySelector('input[name="answerMode"]:checked').value;
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function postForm(url, formData) {
  const response = await fetch(url, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function patchJson(url, payload) {
  const response = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function deleteJson(url) {
  const response = await fetch(url, { method: "DELETE" });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function setStage(stage, items = []) {
  taskStage.textContent = stage;
  crawlTotal.textContent = String(items.length);
  crawlSuccess.textContent = "0";
  crawlFailed.textContent = "0";
  crawlStatusList.innerHTML = items.length
    ? items.map((item) => `<div class="status-item pending"><span>等待</span><code>${escapeHtml(item)}</code></div>`).join("")
    : "暂无任务。";
}

function renderOperation(data) {
  answer.textContent = JSON.stringify(data, null, 2);
}

function renderAnswer(text) {
  answer.innerHTML = escapeHtml(text || "没有返回回答。")
    .split(/\n{2,}/)
    .map((block) => `<p>${block.replace(/\n/g, "<br />")}</p>`)
    .join("");
}

function renderSources(items = []) {
  sources.innerHTML = items.length
    ? items
        .map(
          (item, index) => `
            <div class="source-item">
              <strong>${index + 1}. ${escapeHtml(item.source)}</strong>
              <span>匹配度：${escapeHtml(item.score)}</span>
              <p>${escapeHtml(item.text.slice(0, 220))}${item.text.length > 220 ? "..." : ""}</p>
            </div>
          `,
        )
        .join("")
    : "暂无引用。";
}

function renderCrawlStatus(crawl) {
  const results = crawl?.results || [];
  const successCount = results.filter((item) => item.ok).length;
  taskStage.textContent = !results.length ? "无爬取任务" : successCount === results.length ? "爬取完成" : "部分失败";
  crawlTotal.textContent = String(results.length);
  crawlSuccess.textContent = String(successCount);
  crawlFailed.textContent = String(results.length - successCount);
  crawlStatusList.innerHTML = results.length
    ? results
        .map((item) => {
          const cls = item.ok ? "success" : "failed";
          const label = item.ok ? "成功" : "失败";
          const shownUrl = item.final_url && item.final_url !== item.url ? `${item.url} -> ${item.final_url}` : item.url;
          const detail = item.ok
            ? `${item.title || "未识别标题"} · ${item.chars || 0} 字符 · ${item.content_type || "unknown"} · ${item.path || ""}`
            : item.error || "未知错误";
          return `<div class="status-item ${cls}"><span>${label}</span><code>${escapeHtml(shownUrl)}</code><small>${escapeHtml(detail)}</small></div>`;
        })
        .join("")
    : "没有返回爬取结果。";
}

function renderUploadStatus(data) {
  const results = data.uploaded || [];
  const successCount = results.filter((item) => item.ok).length;
  taskStage.textContent = successCount === results.length ? "上传完成" : "部分失败";
  crawlTotal.textContent = String(results.length);
  crawlSuccess.textContent = String(successCount);
  crawlFailed.textContent = String(results.length - successCount);
  crawlStatusList.innerHTML = results.length
    ? results
        .map((item) => {
          const cls = item.ok ? "success" : "failed";
          const label = item.ok ? "成功" : "失败";
          const detail = item.ok ? `${item.chars || 0} 字符 · ${item.knowledge_path || ""}` : item.error || "未知错误";
          return `<div class="status-item ${cls}"><span>${label}</span><code>${escapeHtml(item.filename)}</code><small>${escapeHtml(detail)}</small></div>`;
        })
        .join("")
    : "没有返回上传结果。";
}

async function updateKnowledge() {
  sources.textContent = "";
  if (activeSource === "url") {
    const urls = parseUrls(document.querySelector("#crawlUrls").value);
    setStage("爬取中", urls.length ? urls : ["默认启用来源"]);
    answer.textContent = "正在爬取资料、写入知识库并重建索引...";
    const data = await postJson("/admin/knowledge/crawl", { urls: urls.length ? urls : null, rebuild: true });
    renderCrawlStatus(data.crawl);
    await loadKnowledgeDocuments();
    return data;
  }

  if (activeSource === "file") {
    const fileInput = document.querySelector("#uploadFiles");
    if (!fileInput.files.length) {
      answer.textContent = "请先选择至少一个文件。";
      return null;
    }
    const names = Array.from(fileInput.files).map((file) => file.name);
    setStage("上传解析中", names);
    answer.textContent = "正在解析文件、写入知识库并重建索引...";
    const formData = new FormData();
    for (const file of fileInput.files) formData.append("files", file);
    formData.append("category", document.querySelector("#uploadCategory").value.trim() || "uploads");
    formData.append("rebuild", "true");
    const data = await postForm("/admin/knowledge/upload", formData);
    renderUploadStatus(data);
    await loadKnowledgeDocuments();
    return data;
  }

  const title = document.querySelector("#manualTitle").value.trim();
  const content = document.querySelector("#manualContent").value.trim();
  if (!title || !content) {
    answer.textContent = "请填写标题和内容。";
    return null;
  }
  setStage("手动入库中", [title]);
  answer.textContent = "正在手动入库并重建索引...";
  const data = await postJson("/admin/knowledge/manual", {
    title,
    content,
    category: "webgis-demo",
    rebuild: true,
  });
  taskStage.textContent = "入库完成";
  crawlSuccess.textContent = "1";
  await loadKnowledgeDocuments();
  return data;
}

async function askCurrentKnowledge() {
  const mode = currentMode();
  const question = document.querySelector("#question").value.trim();
  if (!question) {
    answer.textContent = "请先输入问题。";
    return;
  }
  const urls = parseUrls(document.querySelector("#searchUrls").value);
  const modeLabel = {
    local: "纯本地知识库匹配",
    knowledge_ai: "知识库 + AI",
    knowledge_ai_search: "知识库 + AI + 联网采集",
  }[mode];
  answer.textContent = `正在使用“${modeLabel}”模式处理...`;
  sources.textContent = "";
  taskStage.textContent = mode === "knowledge_ai_search" ? "联网采集中" : "问答生成中";
  const data = await postJson("/chat", {
    question,
    top_k: 4,
    use_tools: mode !== "local",
    mode,
    urls: mode === "knowledge_ai_search" && urls.length ? urls : null,
  });
  if (data.crawl) renderCrawlStatus(data.crawl);
  taskStage.textContent = "回答完成";
  renderAnswer(data.answer);
  renderSources(data.sources);
  if (data.crawl) await loadKnowledgeDocuments();
}

async function loadKnowledgeDocuments() {
  const response = await fetch("/admin/knowledge/documents");
  const data = await response.json();
  documentList.innerHTML = data.documents?.length
    ? data.documents
        .map(
          (item) => `
            <div class="doc-item">
              <strong>${escapeHtml(item.title)}</strong>
              <span>${escapeHtml(item.source_type)} · ${escapeHtml(item.size_kb)} KB · ${escapeHtml(item.modified_at)}</span>
              <code>${escapeHtml(item.relative_path)}</code>
            </div>
          `,
        )
        .join("")
    : "当前知识库暂无文档。";
}

async function loadCrawlerSources() {
  const response = await fetch("/admin/knowledge/crawler-sources");
  const data = await response.json();
  sourceList.innerHTML = data.sources?.length
    ? data.sources
        .map(
          (item) => `
            <div class="source-row">
              <div>
                <strong>${escapeHtml(item.name)}</strong>
                <code>${escapeHtml(item.url)}</code>
                <small>${escapeHtml(item.description || "暂无描述")}</small>
              </div>
              <div class="row-actions">
                <button data-toggle-source="${escapeHtml(item.id)}" data-enabled="${item.enabled ? "false" : "true"}">
                  ${item.enabled ? "停用" : "启用"}
                </button>
                <button data-delete-source="${escapeHtml(item.id)}">删除</button>
              </div>
            </div>
          `,
        )
        .join("")
    : "暂无来源数据。";
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => setActiveSource(tab.dataset.source));
});

document.querySelectorAll('input[name="answerMode"]').forEach((input) => {
  input.addEventListener("change", () => setMode(input.value));
});

document.querySelector("#updateKnowledgeBtn").addEventListener("click", async () => {
  try {
    const data = await updateKnowledge();
    if (data) renderOperation(data);
  } catch (error) {
    answer.textContent = `操作失败：${error.message}`;
    taskStage.textContent = "失败";
  }
});

document.querySelector("#crawlAskBtn").addEventListener("click", async () => {
  try {
    const updated = await updateKnowledge();
    if (updated) await askCurrentKnowledge();
  } catch (error) {
    answer.textContent = `操作失败：${error.message}`;
    taskStage.textContent = "失败";
  }
});

document.querySelector("#askBtn").addEventListener("click", async () => {
  try {
    await askCurrentKnowledge();
  } catch (error) {
    answer.textContent = `回答失败：${error.message}`;
    taskStage.textContent = "失败";
  }
});

document.querySelector("#statusBtn").addEventListener("click", async () => {
  const response = await fetch("/admin/index/status");
  const data = await response.json();
  taskStage.textContent = "索引状态";
  renderOperation(data);
});

document.querySelector("#refreshDocsBtn").addEventListener("click", loadKnowledgeDocuments);

document.querySelector("#addSourceBtn").addEventListener("click", async () => {
  const name = document.querySelector("#sourceName").value.trim();
  const url = document.querySelector("#sourceUrl").value.trim();
  if (!url) {
    answer.textContent = "请填写来源 URL。";
    return;
  }
  const data = await postJson("/admin/knowledge/crawler-sources", {
    name,
    url,
    enabled: true,
    tags: ["manual-added"],
    description: "从 Web 管理界面添加",
  });
  taskStage.textContent = "来源已添加";
  renderOperation(data);
  await loadCrawlerSources();
});

document.querySelector("#listSourcesBtn").addEventListener("click", loadCrawlerSources);

sourceList.addEventListener("click", async (event) => {
  const toggleButton = event.target.closest("[data-toggle-source]");
  if (toggleButton) {
    await patchJson(`/admin/knowledge/crawler-sources/${toggleButton.dataset.toggleSource}`, {
      enabled: toggleButton.dataset.enabled === "true",
    });
    await loadCrawlerSources();
    return;
  }
  const deleteButton = event.target.closest("[data-delete-source]");
  if (deleteButton && confirm("确认删除这个爬虫来源吗？不会删除已入库文档。")) {
    await deleteJson(`/admin/knowledge/crawler-sources/${deleteButton.dataset.deleteSource}`);
    await loadCrawlerSources();
  }
});

setMode(currentMode());
loadCrawlerSources();
loadKnowledgeDocuments();
