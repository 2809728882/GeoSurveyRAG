const question = document.querySelector("#question");
const answer = document.querySelector("#answer");
const sources = document.querySelector("#sources");
const crawlStage = document.querySelector("#crawlStage");
const crawlTotal = document.querySelector("#crawlTotal");
const crawlSuccess = document.querySelector("#crawlSuccess");
const crawlFailed = document.querySelector("#crawlFailed");
const crawlStatusList = document.querySelector("#crawlStatusList");

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

function renderSources(items = []) {
  sources.textContent = items
    .map((item) => `来源：${item.source}\n分数：${item.score}\n片段：${item.text.slice(0, 160)}...`)
    .join("\n\n");
}

function renderOperation(data) {
  answer.textContent = JSON.stringify(data, null, 2);
  sources.textContent = "";
}

function setCrawlStage(stage, urls = []) {
  crawlStage.textContent = stage;
  crawlTotal.textContent = String(urls.length);
  crawlSuccess.textContent = "0";
  crawlFailed.textContent = "0";
  crawlStatusList.innerHTML = urls.length
    ? urls.map((url) => `<div class="status-item pending"><span>等待</span><code>${url}</code></div>`).join("")
    : "暂无爬取任务。";
}

function renderCrawlStatus(crawl) {
  const results = crawl?.results || [];
  const successCount = results.filter((item) => item.ok).length;
  crawlStage.textContent = successCount === results.length ? "爬取完成" : "部分失败";
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

async function postForm(url, formData) {
  const response = await fetch(url, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

document.querySelector("#askBtn").addEventListener("click", async () => {
  answer.textContent = "正在检索当前知识库并调用模型...";
  sources.textContent = "";
  const data = await postJson("/chat", {
    question: question.value,
    top_k: 4,
    use_tools: true,
  });
  answer.textContent = data.answer;
  renderSources(data.sources);
});

document.querySelector("#crawlBtn").addEventListener("click", async () => {
  const urls = parseUrls(document.querySelector("#crawlUrls").value);
  if (!urls.length) {
    answer.textContent = "请先粘贴至少一个 http/https URL。";
    return;
  }
  answer.textContent = "正在爬取资料、写入知识库并重建索引...";
  setCrawlStage("爬取中", urls);
  const data = await postJson("/admin/knowledge/crawl", {
    urls,
    rebuild: true,
  });
  renderCrawlStatus(data.crawl);
  renderOperation(data);
});

document.querySelector("#crawlAskBtn").addEventListener("click", async () => {
  const urls = parseUrls(document.querySelector("#crawlUrls").value);
  if (!urls.length) {
    answer.textContent = "请先粘贴至少一个 http/https URL。";
    return;
  }
  answer.textContent = "正在爬取资料、更新知识库，并基于新知识回答...";
  sources.textContent = "";
  setCrawlStage("爬取中", urls);
  const data = await postJson("/admin/knowledge/crawl-and-chat", {
    urls,
    question: question.value,
    top_k: 4,
  });
  renderCrawlStatus(data.crawl);
  answer.textContent = data.answer;
  renderSources(data.sources);
  sources.textContent += `\n\n爬虫结果：${JSON.stringify(data.crawl, null, 2)}`;
});

document.querySelector("#statusBtn").addEventListener("click", async () => {
  const response = await fetch("/admin/index/status");
  const data = await response.json();
  renderOperation(data);
});

document.querySelector("#uploadBtn").addEventListener("click", async () => {
  const fileInput = document.querySelector("#uploadFiles");
  if (!fileInput.files.length) {
    answer.textContent = "请选择至少一个文件。";
    return;
  }
  const formData = new FormData();
  for (const file of fileInput.files) {
    formData.append("files", file);
  }
  formData.append("category", document.querySelector("#uploadCategory").value.trim() || "uploads");
  formData.append("rebuild", "true");
  answer.textContent = "正在解析文件、写入知识库并重建索引...";
  const data = await postForm("/admin/knowledge/upload", formData);
  renderOperation(data);
});

document.querySelector("#manualBtn").addEventListener("click", async () => {
  const title = document.querySelector("#manualTitle").value.trim();
  const content = document.querySelector("#manualContent").value.trim();
  if (!title || !content) {
    answer.textContent = "请填写标题和内容。";
    return;
  }
  answer.textContent = "正在手动入库并重建索引...";
  const data = await postJson("/admin/knowledge/manual", {
    title,
    content,
    category: "webgis-demo",
    rebuild: true,
  });
  renderOperation(data);
});

document.querySelector("#addSourceBtn").addEventListener("click", async () => {
  const name = document.querySelector("#sourceName").value.trim();
  const url = document.querySelector("#sourceUrl").value.trim();
  if (!url) {
    answer.textContent = "请填写来源 URL。";
    return;
  }
  answer.textContent = "正在添加爬虫来源...";
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
  renderOperation(data);
});
