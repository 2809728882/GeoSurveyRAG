import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from geosurvey_rag import api
from geosurvey_rag import knowledge_sources
from geosurvey_rag.agent import GeoAgent
from geosurvey_rag.evaluation import evaluate
from geosurvey_rag.ingestion import build_index, split_text
from geosurvey_rag.rag import RagPipeline
from geosurvey_rag.retrieval import HybridRetriever
from geosurvey_rag.tools.geodesy import (
    geodesic_distance,
    haversine_distance,
    polygon_area_lambert,
    transform_coordinate,
    wkt_bbox,
)
from geosurvey_rag.vector_store import JsonVectorStore, FaissVectorStore, create_vector_store


@pytest.fixture
def client(tmp_path, monkeypatch):
    source = tmp_path / "knowledge"
    source.mkdir()
    (source / "gnss.md").write_text(
        "GNSS 单点定位使用 RINEX 伪距、广播星历和最小二乘解算钟差。", encoding="utf-8"
    )
    build_index(source, tmp_path / "index")
    monkeypatch.setattr(api, "rag", RagPipeline(tmp_path / "index"))
    configured = replace(api.settings, knowledge_dir=source, index_dir=tmp_path / "index")
    monkeypatch.setattr(api, "settings", configured)
    monkeypatch.setattr(knowledge_sources, "settings", configured)
    monkeypatch.chdir(tmp_path)
    with TestClient(api.app) as value:
        yield value


@pytest.mark.parametrize("backend", ["json", "faiss"])
def test_hybrid_roundtrip_and_source_filter(tmp_path, backend):
    if backend == "faiss":
        pytest.importorskip("faiss")
    directory = tmp_path / "测绘知识库"
    store = JsonVectorStore(directory) if backend == "json" else FaissVectorStore(directory)
    store.add("gnss.md", "GNSS 单点定位读取 RINEX，计算广播星历和卫星钟差", 0)
    store.add("uav.md", "无人机航测检查像控点与重叠度", 0)
    store.save()
    retriever = HybridRetriever(store.load())
    assert retriever.search("GNSS RINEX 钟差", 1)[0][0].source == "gnss.md"
    assert retriever.search("番茄意大利面烹饪食谱") == []
    assert retriever.search("GNSS RINEX", source_filter="uav.md") == []
    assert len(retriever.search("GNSS RINEX", 100)) == 1


def test_no_evidence_does_not_call_model(tmp_path):
    pipeline = RagPipeline(tmp_path)

    class MustNotCall:
        def generate(self, **kwargs):
            raise AssertionError("empty evidence called LLM")

    pipeline.llm = MustNotCall()
    answer, sources = pipeline.answer("番茄意大利面烹饪食谱")
    assert not sources and "没有匹配" in answer


def test_exact_epsg_identifier_survives_long_document_threshold(tmp_path):
    store = JsonVectorStore(tmp_path)
    store.add(
        "coordinate.md", "测绘资料需要整理归档。" * 100 + "WebGIS 使用 EPSG:3857 Web Mercator。", 0
    )
    result = HybridRetriever(store).search("WebGIS 为什么常用 EPSG:3857？")
    assert result and result[0][0].source == "coordinate.md"


def test_context_citations_and_relative_paths(tmp_path):
    source = tmp_path / "knowledge"
    source.mkdir()
    (source / "rtk.md").write_text("RTK 外业需要检查固定解和差分延迟。", encoding="utf-8")
    build_index(source, tmp_path / "index")
    pipeline = RagPipeline(tmp_path / "index")

    class Capture:
        def generate(self, question, context, tool_summary):
            assert "[1] 来源：rtk.md" in context
            return "检查差分延迟 [1]"

    pipeline.llm = Capture()
    answer, sources = pipeline.answer("RTK 差分延迟")
    assert "[1]" in answer and sources[0].citation_id == "[1]"
    assert sources[0].source == "rtk.md"


@pytest.mark.parametrize("size,overlap", [(0, 0), (10, 10), (10, -1)])
def test_invalid_chunk_configuration(size, overlap):
    with pytest.raises(ValueError):
        split_text("test", size, overlap)


def test_geodesic_reference_and_antipodes():
    assert geodesic_distance([(0, 0), (1, 0)])["distance"] == pytest.approx(111319.491, abs=0.001)
    assert haversine_distance([(0, 0), (180, 0)])["distance"] > 20_000_000
    assert geodesic_distance([(179.9, 0), (-179.9, 0)], "km")["distance"] == pytest.approx(
        22.264, abs=0.001
    )


def test_area_units_orientation_and_antimeridian():
    points = [(0, 0), (1, 0), (1, 1), (0, 1)]
    area = polygon_area_lambert(points)["area"]
    assert area == pytest.approx(12308778361.469, abs=0.01)
    assert polygon_area_lambert(points[::-1])["area"] == area
    assert polygon_area_lambert(points + [points[0]])["area"] == area
    assert polygon_area_lambert(points, "ha")["area"] == pytest.approx(area / 10000, abs=0.0001)
    assert polygon_area_lambert([(179, 0), (-179, 0), (-179, 1), (179, 1)])["area"] > area


@pytest.mark.parametrize(
    "polygon", [[(0, 0), (1, 1), (0, 1), (1, 0)], [(0, 0)] * 3, [(0, 0), (1, 1), (2, 2)]]
)
def test_invalid_polygons(polygon):
    with pytest.raises(ValueError):
        polygon_area_lambert(polygon)


def test_transform_roundtrip():
    value = transform_coordinate(111.3, 30.7)
    back = transform_coordinate(value["x"], value["y"], 3857, 4326)
    assert back["x"] == pytest.approx(111.3, abs=1e-6)
    assert back["y"] == pytest.approx(30.7, abs=1e-6)


@pytest.mark.parametrize("wkt", ["random 0 0 2 3", "POINT EMPTY", "POLYGON((0 0,1 1,0 1,1 0,0 0))"])
def test_invalid_wkt(wkt):
    with pytest.raises(ValueError):
        wkt_bbox(wkt)


def test_wkt_scientific_notation_and_srid():
    result = wkt_bbox("SRID=4326;LINESTRING(-1e1 2, 4 -3e0)")
    assert result["min_x"] == -10 and result["min_y"] == -3
    assert result["epsg_hint"] == "EPSG:4326"


def test_agent_transform_and_wkt_sentence():
    calls = GeoAgent().maybe_run_tools("把（111.3，30.7）从 EPSG:4326 转为 EPSG:3857")
    assert calls[0].name == "transform_coordinate"
    assert calls[0].result["x"] > 12_000_000
    calls = GeoAgent().maybe_run_tools("请计算 POINT(1e1 2) 的边界框，谢谢")
    assert calls[0].result["min_x"] == 10
    calls = GeoAgent().maybe_run_tools("距离 (200,30) 到 (111,30)")
    assert "error" in calls[0].result


@pytest.mark.parametrize(
    "endpoint,payload,status",
    [
        ("/tool/distance", {"points": [[200, 0], [0, 0]]}, 422),
        ("/tool/distance", {"points": [[0, 0], [1, 0]], "unit": "feet"}, 422),
        ("/tool/area", {"polygon": [[0, 0], [1, 1], [0, 1], [1, 0]]}, 400),
        ("/tool/transform", {"x": 0, "y": 90}, 400),
        ("/tool/transform", {"x": 0, "y": 0, "to_epsg": 99999999}, 400),
        ("/tool/wkt-bbox", {"wkt": "random 1 2 3 4"}, 400),
        ("/chat", {"question": "   "}, 422),
        ("/chat", {"question": "测试", "mode": "typo"}, 422),
    ],
)
def test_api_invalid_inputs(client, endpoint, payload, status):
    assert client.post(endpoint, json=payload).status_code == status


def test_chat_and_health(client):
    data = client.post("/chat", json={"question": "GNSS RINEX 钟差", "mode": "local"}).json()
    assert data["retrieval_status"] == "matched" and data["sources"][0]["citation_id"] == "[1]"
    assert client.get("/health").json()["index_ready"] is True
    data = client.post("/chat", json={"question": "番茄意大利面烹饪食谱"}).json()
    assert data["sources"] == [] and data["retrieval_status"] == "no_evidence"
    result = client.post("/tool/distance", json={"points": [[0, 0], [1, 0]]}).json()
    assert result["method"] == "wgs84_geodesic"


def test_upload_rebuild_and_partial_failure(client):
    result = client.post(
        "/admin/knowledge/upload",
        files=[
            (
                "files",
                (
                    "rtk.md",
                    "RTK 固定解检查包括差分延迟和卫星数量。".encode("utf-8"),
                    "text/markdown",
                ),
            ),
            ("files", ("broken.pdf", b"not a pdf", "application/pdf")),
        ],
    )
    assert result.status_code == 200
    data = result.json()
    assert data["ok"] and data["index"]["updated"]
    assert data["uploaded"][0]["ok"] and not data["uploaded"][1]["ok"]
    answer = client.post("/chat", json={"question": "RTK 固定解差分延迟", "mode": "local"}).json()
    assert any("uploads/" in source["source"] for source in answer["sources"])


def test_manual_ingestion_and_rebuild(client):
    response = client.post(
        "/admin/knowledge/manual",
        json={
            "title": "全站仪检核",
            "content": "全站仪作业前需要检查对中整平、测站定向与后视检核。",
            "category": "field",
        },
    )
    assert response.status_code == 200 and response.json()["index"]["updated"]
    data = client.post("/chat", json={"question": "全站仪对中整平", "mode": "local"}).json()
    assert any("manual/" in source["source"] for source in data["sources"])


def test_evaluation_distinguishes_answer_and_evidence(tmp_path):
    store = create_vector_store(tmp_path / "index", api.settings.vector_backend)
    store.add("gnss.md", "RINEX " * 20 + "常见测绘数据格式。" * 50 + "钟差", 0)
    store.save()
    cases = [
        {"question": "RINEX", "expected_terms": ["钟差"], "expected_sources": ["gnss.md"]},
        {"question": "番茄意大利面烹饪食谱", "expect_no_evidence": True},
    ]
    path = tmp_path / "eval.json"
    path.write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")
    result = evaluate(path, index_dir=tmp_path / "index")
    assert result["source_hit_rate"] == 1 and result["mrr"] == 1
    assert result["term_coverage"] == 1 and result["answer_term_coverage"] == 0
    assert result["no_evidence_rate"] == 1
