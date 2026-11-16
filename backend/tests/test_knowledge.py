from geophysics_agent.knowledge.retriever import retrieve


def test_retriever_returns_source_metadata() -> None:
    results = retrieve("折射地震速度结构")

    assert results
    assert results[0].source.endswith(".pdf")
    assert results[0].verification_status
