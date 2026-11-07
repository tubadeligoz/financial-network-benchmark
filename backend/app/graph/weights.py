import math
import networkx as nx
from typing import Protocol


class WeightView(Protocol):
    """Future pure derived-weight layer; must not overwrite source exposure.

    Distance and capacity are distinct attributes, never automatic exposure aliases.
    Source exposures must remain unchanged.
    """

    name: str

    def derive(self, exposure: float, source_metadata: dict) -> float: ...


def inverse_exposure_view(graph, scale=1.0):
    """A separate distance-only graph, d=c/exposure; never edit source attributes."""
    if isinstance(scale, bool) or not isinstance(scale, (int, float)) or not math.isfinite(scale) or scale <= 0:
        raise ValueError('Distance scale must be finite and positive.')
    view = nx.DiGraph()
    view.add_nodes_from(sorted(graph))
    for source, target, attrs in sorted(graph.edges(data=True)):
        value = attrs.get('exposure')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError('Inverse exposure requires finite positive weights.')
        distance = scale / value
        if not math.isfinite(distance) or distance <= 0:
            raise ValueError('Inverse exposure distance underflows or overflows.')
        view.add_edge(source, target, distance=distance)
    return nx.freeze(view)
