const map = document.querySelector("#map");
const drawLayer = document.querySelector("#drawLayer");
const mapStatus = document.querySelector("#mapStatus");
const question = document.querySelector("#question");
const answer = document.querySelector("#answer");
const sources = document.querySelector("#sources");
const points = [];

function svgPoint(event) {
  const rect = map.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * 1000;
  const y = ((event.clientY - rect.top) / rect.height) * 620;
  const lon = 111.15 + (x / 1000) * 0.5;
  const lat = 30.45 + ((620 - y) / 620) * 0.42;
  return { x, y, lon: Number(lon.toFixed(6)), lat: Number(lat.toFixed(6)) };
}

function render() {
  drawLayer.innerHTML = "";
  if (points.length >= 3) {
    const polygon = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
    polygon.setAttribute("points", points.map((p) => `${p.x},${p.y}`).join(" "));
    polygon.setAttribute("class", "area");
    drawLayer.appendChild(polygon);
  }
  if (points.length >= 2) {
    const line = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    line.setAttribute("points", points.map((p) => `${p.x},${p.y}`).join(" "));
    line.setAttribute("class", "line");
    drawLayer.appendChild(line);
  }
  points.forEach((p, index) => {
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", p.x);
    circle.setAttribute("cy", p.y);
    circle.setAttribute("r", 8);
    circle.setAttribute("class", "point");
    drawLayer.appendChild(circle);

    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", p.x + 12);
    label.setAttribute("y", p.y - 12);
    label.setAttribute("font-size", "18");
    label.setAttribute("fill", "#1f2a37");
    label.textContent = `${index + 1}`;
    drawLayer.appendChild(label);
  });
  mapStatus.textContent = points.length
    ? points.map((p, i) => `${i + 1}: (${p.lon}, ${p.lat})`).join("  ")
    : "点击地图添加点，系统会按宜昌附近经纬度范围模拟坐标。";
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

map.addEventListener("click", (event) => {
  points.push(svgPoint(event));
  render();
});

document.querySelector("#clearBtn").addEventListener("click", () => {
  points.length = 0;
  render();
});

document.querySelector("#distanceBtn").addEventListener("click", async () => {
  if (points.length < 2) return;
  const result = await postJson("/tool/distance", {
    points: points.map((p) => [p.lon, p.lat]),
    unit: "m",
  });
  mapStatus.textContent = `折线距离：${result.distance} ${result.unit}`;
});

document.querySelector("#areaBtn").addEventListener("click", async () => {
  if (points.length < 3) return;
  const result = await postJson("/tool/area", {
    polygon: points.map((p) => [p.lon, p.lat]),
    unit: "ha",
  });
  mapStatus.textContent = `闭合面积：${result.area} ${result.unit}`;
});

document.querySelector("#askBtn").addEventListener("click", async () => {
  answer.textContent = "检索知识库中...";
  sources.textContent = "";
  const data = await postJson("/chat", {
    question: question.value,
    top_k: 4,
    use_tools: true,
  });
  answer.textContent = data.answer;
  sources.textContent = data.sources
    .map((item) => `来源：${item.source}\n分数：${item.score}\n片段：${item.text.slice(0, 120)}...`)
    .join("\n\n");
});

document.querySelector("#statusBtn").addEventListener("click", async () => {
  const response = await fetch("/admin/index/status");
  const data = await response.json();
  answer.textContent = JSON.stringify(data.manifest, null, 2);
});

document.querySelector("#manualBtn").addEventListener("click", async () => {
  const title = document.querySelector("#manualTitle").value.trim();
  const content = document.querySelector("#manualContent").value.trim();
  if (!title || !content) return;
  answer.textContent = "Manual knowledge ingesting...";
  const data = await postJson("/admin/knowledge/manual", {
    title,
    content,
    category: "webgis-demo",
    rebuild: true,
  });
  answer.textContent = JSON.stringify(data, null, 2);
});

document.querySelector("#crawlBtn").addEventListener("click", async () => {
  const url = document.querySelector("#crawlUrl").value.trim();
  if (!url) return;
  answer.textContent = "Crawler ingesting...";
  const data = await postJson("/admin/knowledge/crawl", {
    urls: [url],
    rebuild: true,
  });
  answer.textContent = JSON.stringify(data, null, 2);
});

document.querySelector("#addSourceBtn").addEventListener("click", async () => {
  const name = document.querySelector("#sourceName").value.trim();
  const url = document.querySelector("#sourceUrl").value.trim();
  if (!url) return;
  answer.textContent = "Adding crawler source...";
  const data = await postJson("/admin/knowledge/crawler-sources", {
    name,
    url,
    enabled: true,
    tags: ["manual-added"],
    description: "Added from WebGIS admin panel",
  });
  answer.textContent = JSON.stringify(data, null, 2);
});

document.querySelector("#listSourcesBtn").addEventListener("click", async () => {
  const response = await fetch("/admin/knowledge/crawler-sources");
  const data = await response.json();
  answer.textContent = JSON.stringify(data, null, 2);
});

render();
