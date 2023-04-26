import numpy as np
from shapely.geometry import LineString, Polygon

from .utils import dist_m, shift
from map_matcher.map_matching import Candidate, MapMatching
from map_matcher.utils import Edge, Measurement
from map_matcher.road_routing import AdHocNode


# TODO come up with reasonable defaults
DEFAULT_BETA = 5.0
DEFAULT_SIGMA_Z = 4.07
DEFAULT_SEARCH_RADIUS = 20


def to_circle(p, radius, n=36):
    """Returns a circle-like polygon with center `p`."""
    return Polygon([shift(p.x, p.y, i * (360./n), radius) for i in range(n)])


def query_candidates(idx, edges, sequence, search_radius):
    """Creates Candidate objects for each Point in `sequence`.
      Considers only edges within a distance of `search_radius`.
    """
    # TODO print warning if no edge within distance of `search_radius`
    candidates = []
    for i, p in enumerate(sequence):
        measurement = Measurement(id=i, lon=p.x, lat=p.y)
        p_buffered = to_circle(p, search_radius)
        for eid in list(idx.intersection(p_buffered.bounds)):
            e = edges.loc[eid]
            if e.geometry.intersects(p_buffered):
                length = dist_m(e.geometry.coords[0][0], e.geometry.coords[0][1],
                                e.geometry.coords[1][0], e.geometry.coords[1][1])
                edge = Edge(id=e.id,
                            start_node=e.source,
                            end_node=e.target,
                            cost=length,
                            reverse_cost=length)
                location = e.geometry.project(p, normalized=True)
                p_on_edge = e.geometry.interpolate(location, normalized=True)
                distance = dist_m(p.x, p.y, p_on_edge.x, p_on_edge.y)
                candidate = Candidate(measurement=measurement, edge=edge,
                                      location=location, distance=distance)
                candidates.append(candidate)
    return candidates


def query_candidate_edges(candidates):
    """Returns a list of all unique edges used in the set of candidates."""
    return list(set([candidate.edge for candidate in candidates]))


def build_road_network(edges):
    """Construct the bidirectional road graph given a list of edges."""
    graph = {}
    for edge in edges:
        graph.setdefault(edge.start_node, []).append(edge)
        graph.setdefault(edge.end_node, []).append(edge.reversed_edge())
    return graph


def map_match(idx, edges, sequence, search_radius=DEFAULT_SEARCH_RADIUS,
              beta=DEFAULT_BETA, sigma=DEFAULT_SIGMA_Z):
    """Performs the map matchig algorithm.
      Points in `sequence` are mapped to `edges`.
    """
    candidates = query_candidates(idx, edges, sequence, search_radius)
    candidate_edges = query_candidate_edges(candidates)
    network = build_road_network(candidate_edges)
    matcher = MapMatching(network.get, max_route_distance=float('inf'),
                                       beta=beta, sigma_z=sigma)
    return list(matcher.offline_match(candidates))
