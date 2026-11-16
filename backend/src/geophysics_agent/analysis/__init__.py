"""确定性分析层：方法元数据、课程数据表、物理关系、评估器与外业设计。

本包不调用任何大模型，所有输出可复现、可单测。
"""

from geophysics_agent.analysis.calculator import assess, depth_check, max_depth_of
from geophysics_agent.analysis.design import build_design

__all__ = ["assess", "build_design", "depth_check", "max_depth_of"]
