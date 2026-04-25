const question = document.querySelector("#question");
const answer = document.querySelector("#answer");
const sources = document.querySelector("#sources");

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
  const data = await postJson("/admin/knowledge/crawl", {
    urls,
    rebuild: true,
  });
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
  const data = await postJson("/admin/knowledge/crawl-and-chat", {
    urls,
    question: question.value,
    top_k: 4,
  });
  answer.textContent = data.answer;
  renderSources(data.sources);
  sources.textContent += `\n\n爬虫结果：${JSON.stringify(data.crawl, null, 2)}`;
});

document.querySelector("#statusBtn").addEventListener("click", async () => {
  const response = await fetch("/admin/index/status");
  const data = await response.json();
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
