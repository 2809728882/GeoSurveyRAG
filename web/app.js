const answer = document.querySelector("#answer");
const sources = document.querySelector("#sources");
const taskStage = document.querySelector("#taskStage");
const crawlTotal = document.querySelector("#crawlTotal");
const crawlSuccess = document.querySelector("#crawlSuccess");
const crawlFailed = document.querySelector("#crawlFailed");
const crawlStatusList = document.querySelector("#crawlStatusList");
let activeSource = "url";

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

function parseUrls(value) {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter((item) => item.startsWith("http://") || item.startsWith("https://"));
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

function setStage(stage, items = []) {
  taskStage.textContent = stage;
  crawlTotal.textContent = String(items.length);
  crawlSuccess.textContent = "0";
  crawlFailed.textContent = "0";
  crawlStatusList.innerHTML = items.length
    ? items.map((item) => `<div class="status-item pending"><span>等待</span><code>${item}</code></div>`).join("")
    : "暂无任务。";
}

function renderOperation(data) {
  answer.textContent = JSON.stringify(data, null, 2);
  sources.textContent = "";
}

function renderSources(items = []) {
  sources.textContent = items
    .map((item) => `来源：${item.source}\n分数：${item.score}\n片段：${item.text.slice(0, 160)}...`)
    .join("\n\n");
}

function renderCrawlStatus(crawl) {
  const results = crawl?.results || [];
  const successCount = results.filter((item) => item.ok).length;
  taskStage.textContent = successCount === results.length ? "爬取完成" : "部分失败";
  crawlTotal.textContent = String(results.length);
  crawlSuccess.textContent = String(successCount);
  crawlFailed.textContent = String(results.length - successCount);
  crawlStatusList.innerHTML = results.length
    ? results
        .map((item) => {
          const cls = item.ok ? "success" : "failed";
          const label = item.ok ? "成功" : "失败";
          const detail = item.ok
            ? `${item.chars || 0} 字符 · ${item.path || ""}`
            : item.error || "未知错误";
          return `<div class="status-item ${cls}"><span>${label}</span><code>${item.url}</code><small>${detail}</small></div>`;
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
          const detail = item.ok
            ? `${item.chars || 0} 字符 · ${item.knowledge_path || ""}`
            : item.error || "未知错误";
          return `<div class="status-item ${cls}"><span>${label}</span><code>${item.filename}</code><small>${detail}</small></div>`;
        })
        .join("")
    : "没有返回上传结果。";
}

async function updateKnowledge() {
  sources.textContent = "";
  if (activeSource === "url") {
    const urls = parseUrls(document.querySelector("#crawlUrls").value);
    if (!urls.length) {
      answer.textContent = "请先粘贴至少一个 http/https URL。";
      return null;
    }
    answer.textContent = "正在爬取资料、写入知识库并重建索引...";
    setStage("爬取中", urls);
    const data = await postJson("/admin/knowledge/crawl", { urls, rebuild: true });
    renderCrawlStatus(data.crawl);
    renderOperation(data);
    return data;
  }

  if (activeSource === "file") {
    const fileInput = document.querySelector("#uploadFiles");
    if (!fileInput.files.length) {
      answer.textContent = "请选择至少一个文件。";
      return null;
    }
    const names = Array.from(fileInput.files).map((file) => file.name);
    answer.textContent = "正在解析文件、写入知识库并重建索引...";
    setStage("上传解析中", names);
    const formData = new FormData();
    for (const file of fileInput.files) formData.append("files", file);
    formData.append("category", document.querySelector("#uploadCategory").value.trim() || "uploads");
    formData.append("rebuild", "true");
    const data = await postForm("/admin/knowledge/upload", formData);
    renderUploadStatus(data);
    renderOperation(data);
    return data;
  }

  const title = document.querySelector("#manualTitle").value.trim();
  const content = document.querySelector("#manualContent").value.trim();
  if (!title || !content) {
    answer.textContent = "请填写标题和内容。";
    return null;
  }
  answer.textContent = "正在手动入库并重建索引...";
  setStage("手动入库中", [title]);
  const data = await postJson("/admin/knowledge/manual", {
    title,
    content,
    category: "webgis-demo",
    rebuild: true,
  });
  taskStage.textContent = "入库完成";
  crawlSuccess.textContent = "1";
  renderOperation(data);
  return data;
}

async function askCurrentKnowledge() {
  answer.textContent = "正在检索当前知识库并调用模型...";
  sources.textContent = "";
  taskStage.textContent = "问答生成中";
  const data = await postJson("/chat", {
    question: document.querySelector("#question").value,
    top_k: 4,
    use_tools: true,
  });
  taskStage.textContent = "回答完成";
  answer.textContent = data.answer;
  renderSources(data.sources);
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => setActiveSource(tab.dataset.source));
});

document.querySelector("#updateKnowledgeBtn").addEventListener("click", updateKnowledge);

document.querySelector("#crawlAskBtn").addEventListener("click", async () => {
  const updated = await updateKnowledge();
  if (updated) await askCurrentKnowledge();
});

document.querySelector("#askBtn").addEventListener("click", askCurrentKnowledge);

document.querySelector("#statusBtn").addEventListener("click", async () => {
  const response = await fetch("/admin/index/status");
  const data = await response.json();
  taskStage.textContent = "索引状态";
  renderOperation(data);
});

document.querySelector("#addSourceBtn").addEventListener("click", async () => {
  const name = document.querySelector("#sourceName").value.trim();
  const url = document.querySelector("#sourceUrl").value.trim();
  if (!url) {
    answer.textContent = "请填写来源 URL。";
    return;
  }
  taskStage.textContent = "添加来源";
  const data = await postJson("/admin/knowledge/crawler-sources", {
    name,
    url,
    enabled: true,
    tags: ["manual-added"],
    description: "Added from WebGIS admin panel",
  });
  renderOperation(data);
});

document.querySelector("#listSourcesBtn").addEventListener("click", async () => {
  const response = await fetch("/admin/knowledge/crawler-sources");
  const data = await response.json();
  taskStage.textContent = "来源列表";
  renderOperation(data);
});
