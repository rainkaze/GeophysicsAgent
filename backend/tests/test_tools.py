from geophysics_agent.tools.geophysical_lookup import geophysical_param_lookup


def test_parameter_tool_returns_method_comparison() -> None:
    result = geophysical_param_lookup("土层液化", "软土", 20)

    assert result["ok"] is True
    assert result["normalized"]["depth_m"] == 20
    assert "GPR" in result["methods"]
    assert result["disclaimer"]


def test_parameter_tool_rejects_unknown_medium() -> None:
    result = geophysical_param_lookup("溶洞", "火星", 10)

    assert result["ok"] is False
    assert "error" in result
