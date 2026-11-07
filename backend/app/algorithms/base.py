from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
import math


@dataclass(frozen=True)
class AlgorithmSpec:
    algorithm_id: str
    name: str
    version: str
    parameters: dict
    required_weight_semantics: str
    supported_graph_types: tuple = ('DiGraph',)
    execution_method: str = 'compute(graph, resolved_parameters)'
    result_schema: str = 'fnb.node-scores.v1'


@dataclass
class Computation:
    scores: dict
    metrics: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


@dataclass
class AlgorithmResult:
    algorithm_id: str
    algorithm_name: str
    algorithm_version: str
    dataset_id: str | None
    dataset_version: str | None
    period: str | None
    graph_sha256: str | None
    parameters: dict
    status: str
    scores: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    error: dict | None = None
    schema_version: str = 'fnb.node-scores.v1'
    experiment_id: str | None = None

    def top(self, n):
        if type(n) is not int or n < 1:
            raise ValueError('Top-N must be a positive integer.')
        return self.scores[:n]

    def to_dict(self):
        def safe(value):
            if isinstance(value, dict):
                return {str(k): safe(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [safe(v) for v in value]
            if isinstance(value, float) and not math.isfinite(value):
                return repr(value)  # Invalid request values remain inspectable in error results.
            if value is None or isinstance(value, (str, int, float, bool)):
                return value
            return repr(value)
        return safe(dict(asdict(self), top_nodes={str(n): self.top(n) for n in (5, 10, 20)}))


class Algorithm(ABC):
    spec: AlgorithmSpec

    def resolve(self, parameters):
        unknown = set(parameters) - set(self.spec.parameters)
        if unknown:
            raise ValueError(f'Unknown parameters: {sorted(unknown)}')
        return dict(self.spec.parameters, **parameters)

    def validate_graph_parameters(self, graph, parameters):
        """Optional parameter constraints that depend on the validated graph size."""

    @abstractmethod
    def compute(self, graph, parameters) -> Computation:
        """Receive a structurally and attribute-read-only snapshot."""


def positive_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be a finite positive number.')


def boolean(value, name):
    if type(value) is not bool:
        raise ValueError(f'{name} must be boolean.')
