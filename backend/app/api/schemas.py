from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class Selection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    dataset: str = Field(min_length=1, max_length=100)
    period: str = Field(min_length=1, max_length=20)


class AlgorithmRequest(Selection):
    algorithm_id: Literal['strength','betweenness','pagerank','debtrank']
    parameters: dict[str, Any] = Field(default_factory=dict)


class Case(BaseModel):
    model_config = ConfigDict(extra='forbid')
    case_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,60}$')
    algorithm_id: Literal['strength','betweenness','pagerank','debtrank']
    parameters: dict[str, Any] = Field(default_factory=dict)


class BenchmarkRequest(Selection):
    algorithms: list[Case] = Field(min_length=1,max_length=8)
    repeat_count: int = Field(default=5,ge=5,le=20)
    random_seed: int = Field(default=42,ge=0,le=2**32-1)
    algorithm_timeout_seconds: float = Field(default=20,ge=.1,le=120)


class StressRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    dataset: str = Field(min_length=1,max_length=100)
    periods: list[str] = Field(min_length=1,max_length=4)
    shocked_nodes: list[str] = Field(min_length=1,max_length=20)
    shock_magnitudes: list[float] = Field(min_length=1,max_length=6)
