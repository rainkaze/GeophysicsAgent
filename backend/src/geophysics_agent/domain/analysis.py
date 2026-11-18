"""确定性分析结果模型：单个方法的评估、外业设计与总体评估。

这些模型只由 ``analysis`` 包产生，**数值一律来自代码计算**，
大模型只负责读取其中的数字，不允许自行编造。
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from geophysics_agent.domain.enums import Method, Suitability


class AcquisitionParams(BaseModel):
    """采集参数建议：键为参数名，值为"数值+单位+依据"的可读字符串。"""

    items: dict[str, str] = Field(default_factory=dict)


class MethodAssessment(BaseModel):
    """单一方法在给定目标/介质/埋深/干扰下的确定性评估。"""

    method: Method
    method_cn: str
    max_depth_m: float = Field(description="经验最大探测深度（已乘目标尺寸修正）")
    depth_margin: float = Field(description="最大深度 / 设计埋深，>1 表示有余量")
    depth_check: str
    feasible: bool
    suitability: Suitability
    suitability_reason: str
    vertical_resolution_m: float | None = Field(
        default=None, description="垂向分辨率（m）；磁法无垂向分辨能力则为 None"
    )
    resolution_basis: str
    station_spacing_m: float | None = Field(
        default=None, description="点距/道距/电极距（m），用于工作量估算"
    )
    array_length_m: float | None = Field(default=None, description="排列长度（m），仅阵列类方法")
    relative_cost: str
    cost_index: float = Field(description="教学用相对成本指数，按每 100 m 测线计")
    acquisition: AcquisitionParams
    physics_basis: str
    deployment_requirement: str
    limitations: list[str] = Field(default_factory=list)
    interference_notes: list[str] = Field(default_factory=list)


class FieldDesign(BaseModel):
    """外业布置与工作量估算（由主方法与场地规模推导）。"""

    primary_method: Method | None = None
    main_line_length_m: float = 0.0
    line_count: int = 0
    cross_line_spacing_m: float | None = None
    total_line_km: float = 0.0
    station_count: int | None = None
    relative_cost_index: float = 0.0
    cost_band: str = "未评估"
    basis: list[str] = Field(default_factory=list, description="推导依据，逐条可追溯")


class AssessmentBundle(BaseModel):
    """一次评估的完整产物：八种方法 + 推荐主辅 + 外业设计 + 提示。"""

    target_cn: str
    medium_cn: str
    design_depth_m: float
    depth_range: str
    methods: dict[Method, MethodAssessment]
    recommended_primary: list[Method] = Field(default_factory=list)
    recommended_support: list[Method] = Field(default_factory=list)
    infeasible: list[Method] = Field(default_factory=list)
    design: FieldDesign
    warnings: list[str] = Field(default_factory=list)
    target_contrast: str = ""
    target_note: str = ""

    def ordered(self) -> list[MethodAssessment]:
        from geophysics_agent.domain.enums import METHOD_ORDER

        return [self.methods[method] for method in METHOD_ORDER if method in self.methods]
