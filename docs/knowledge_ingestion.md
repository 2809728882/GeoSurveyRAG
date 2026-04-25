# 知识库入库方式

GeoSurveyRAG 支持两类知识来源：手动入库和爬虫自动更新。两类内容最终都会保存到 `data/knowledge`，再统一进入切片、向量化、检索和评测流程。

## 手动入库

适合录入内部项目经验、测绘质检规则、作业指导书摘要和运维知识。

API：

```bash
curl -X POST http://127.0.0.1:8000/admin/knowledge/manual \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"RTK 固定解检查规则\",\"category\":\"field-survey\",\"content\":\"RTK 外业采集前应检查固定解比例、PDOP、卫星数和差分延迟。\",\"rebuild\":true}"
```

CLI：

```powershell
python -m geosurvey_rag.knowledge_sources manual `
  --title "RTK 固定解检查规则" `
  --category "field-survey" `
  --content "RTK 外业采集前应检查固定解比例、PDOP、卫星数和差分延迟。"
```

保存位置：

```text
data/knowledge/manual/<category>/<title>.md
```

## 爬虫自动更新

适合同步公开网页、开放规范说明、EPSG 坐标系统说明、公开接口文档。

配置文件：

```text
data/sources/crawler_sources.json
```

默认来源包括：

- EPSG 4326 WGS84：默认启用。
- EPSG 3857 Web Mercator：默认启用。
- OGC GeoJSON Standard：默认关闭，可手动启用。
- OGC API Features：默认关闭，可手动启用。

来源管理 API：

```bash
curl http://127.0.0.1:8000/admin/knowledge/crawler-sources

curl -X POST http://127.0.0.1:8000/admin/knowledge/crawler-sources \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"EPSG 4490 CGCS2000\",\"url\":\"https://epsg.io/4490\",\"enabled\":true,\"tags\":[\"epsg\",\"cgcs2000\"]}"

curl -X PATCH http://127.0.0.1:8000/admin/knowledge/crawler-sources/ogc-geojson \
  -H "Content-Type: application/json" \
  -d "{\"enabled\":true}"

curl -X DELETE http://127.0.0.1:8000/admin/knowledge/crawler-sources/ogc-geojson
```

来源管理 CLI：

```powershell
python -m geosurvey_rag.knowledge_sources list-sources
python -m geosurvey_rag.knowledge_sources add-source --name "EPSG 4490 CGCS2000" --url "https://epsg.io/4490" --tag epsg --tag cgcs2000
python -m geosurvey_rag.knowledge_sources disable-source --id ogc-geojson
python -m geosurvey_rag.knowledge_sources enable-source --id ogc-geojson
python -m geosurvey_rag.knowledge_sources remove-source --id ogc-geojson
```

API：

```bash
curl -X POST http://127.0.0.1:8000/admin/knowledge/crawl \
  -H "Content-Type: application/json" \
  -d "{\"urls\":[\"https://epsg.io/3857\"],\"rebuild\":true}"
```

CLI：

```powershell
python -m geosurvey_rag.knowledge_sources crawl --url "https://epsg.io/3857"
```

保存位置：

```text
data/knowledge/crawler/<host>/<path>.md
```

## 自动更新器

运行时先爬虫同步，再检查知识库哈希，如果有变化则重建索引：

```powershell
python -m geosurvey_rag.index_updater --source data\knowledge --index data\index --interval 300 --crawl-first
```

Docker Compose 中的 `index-updater` 已默认启用 `--crawl-first`。

## 爬虫增强点

- 默认来源配置，开箱即可同步 EPSG 坐标系统页面。
- 支持手动添加、删除、启用、停用来源。
- 抓取结果记录 `content_sha1`、字符数、时间和错误状态。
- 抓取失败支持重试，正文过短会标记为失败，避免脏数据进入知识库。
