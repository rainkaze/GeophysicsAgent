import pytest
from pydantic import ValidationError

from geophysics_agent.api.routes import health
from geophysics_agent.domain.schemas import RecommendRequest


def test_health_endpoint() -> None:
    assert health() == {"status": "ok"}


def test_recommend_validates_short_input() -> None:
    with pytest.raises(ValidationError):
        RecommendRequest(message="短")
