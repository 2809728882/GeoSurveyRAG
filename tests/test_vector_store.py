from geosurvey_rag.vector_store import JsonVectorStore, embed_dense


def test_vector_store_search(tmp_path) -> None:
    store = JsonVectorStore(tmp_path)
    store.add("survey.md", "无人机航测需要检查像控点、重叠度和空三精度", 0)
    store.add("llm.md", "RAG 系统需要关注召回命中率和答案忠实度", 0)
    store.save()

    loaded = JsonVectorStore(tmp_path).load()
    results = loaded.search("航测空三检查", top_k=1)

    assert len(results) == 1
    assert "无人机航测" in results[0][0].text


def test_dense_embedding_has_stable_dimension() -> None:
    vector = embed_dense("CGCS2000 坐标转换", dim=32)
    assert len(vector) == 32
    assert any(value != 0 for value in vector)
