import shapely
import numpy as np
import pandas as pd
import geopandas as gpd
import intervals as I
from shapely.geometry import Point, LineString
from functools import partial

from map_matching.utils import dist_m, length_in_meters
from map_matcher.road_routing import AdHocNode


class Node(object):
    def __init__(self, node, edge_id, location):
        self.edge_id = edge_id
        self.location = location
        if isinstance(node, int) or isinstance(node, np.int64):
            self.id = node
            self.adhoc = False
        else:
            self.id = node.edge_id
            self.adhoc = True

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        if self.id != other.id:
            return False
        if self.adhoc and self.location != other.location:
            return False
        return True

    def __lt__(self, other):
        if not other:
            return True
        if not isinstance(other, Node):
            return True
        return self.location < other.location

    def __gt__(self, other):
        if not other:
            return True
        if not isinstance(other, Node):
            return True
        return self.location > other.location


class Path(object):
    def __init__(self, start, end):
        self.path = [(start, end)]
        self.start = start
        self.end = end

    def add_first(self, start, end):
        self.path.insert(0, (start, end))
        self.start = start

    def add_last(self, start, end):
        self.path.append((start, end))
        self.end = end


def list_edges(df, edges):
    """Creates a DataFrame consisting of Edge objects found in `df`.
      Arguments:
        df: GeoDataFrame. Contains column `path`, created by our map matching.
        edges: GeoDataFrame. Edges used in the map matching (see osm.convert.py).
      Returns:
        DataFrame: Contains all edges found in `df`.
    """
    if 'path' not in df.columns:
        raise ValueError('DataFrame is expected to have column "path".')
    way_id, edge_id, start, end = [], [], [], []
    for _, row in df.iterrows():
        for e in row['path']:
            way_id.append(edges.loc[e.id, 'way_id'])
            edge_id.append(e.id)
            if e.reversed:
                start.append(Node(e.end_node, e.id, e.end_node.location \
                                  if isinstance(e.end_node, AdHocNode) else 0))
                end.append(Node(e.start_node, e.id, e.start_node.location \
                                if isinstance(e.start_node, AdHocNode) else 1))
            else:
                start.append(Node(e.start_node, e.id, e.start_node.location \
                                  if isinstance(e.start_node, AdHocNode) else 0))
                end.append(Node(e.end_node, e.id, e.end_node.location \
                                if isinstance(e.end_node, AdHocNode) else 1))
    return pd.DataFrame({'way_id': way_id,
                         'edge_id': edge_id,
                         'start': start,
                         'end': end})


def combine_edges(df, sparse=False):
    way_id, edge_id, start, end = [], [], [], []
    for name, group in df.groupby(['way_id', 'edge_id']):
        intervals = I.empty()
        for _, row in group.iterrows():
            intervals = intervals | I.closed(row['start'], row['end'])
        if not sparse:
            intervals = intervals.enclosure()
        for interval in intervals:
            way_id.append(name[0])
            edge_id.append(name[1])
            start.append(interval.lower)
            end.append(interval.upper)
    return pd.DataFrame({'way_id': way_id,
                         'edge_id': edge_id,
                         'start': start,
                         'end': end})


def _interpolate_node(node, edges, pos, threshold):
    """If `node` is not AdHoc, returns the closest start/end node of an edge
      in `edges` within a distance of `threshold` meters.
    """
    if not node.adhoc:
        return node
    lon1 = edges.loc[node.edge_id, pos + '_p'].x
    lat1 = edges.loc[node.edge_id, pos + '_p'].y
    p = edges.loc[node.edge_id, 'geometry'].interpolate(node.location,
                                                        normalized=True)
    lon2, lat2 = p.x, p.y
    if dist_m(lon1, lat1, lon2, lat2) < threshold:
        return Node(edges.loc[node.edge_id, pos], node.edge_id,
                    0 if pos == 'source' else 1)
    else:
        return node


def interpolate_edges(df, edges, threshold=10.):
    """Connects the start and end of an edge to closest node within a
      distance of `threshold` meters.
      Typically, `df` is a DataFrame resulting from call `combine_edges`.
    """
    interpolate_start = partial(_interpolate_node, edges=edges,
                                                   threshold=threshold,
                                                   pos='source')
    interpolate_end = partial(_interpolate_node, edges=edges,
                                                 threshold=threshold,
                                                 pos='target')
    df.loc[:, 'start'] = df.loc[:, 'start'].apply(interpolate_start)
    df.loc[:, 'end'] = df.loc[:, 'end'].apply(interpolate_end)
    return df


def connect_edges(df):
    """All edges with the same `way_id` are tried to be connected.
      Typically, `df` is a DataFrame resulting from call `interpolate_edges`.
      Returns:
        lines: List. Contains Path objects for all connected paths found.
    """
    lines = []
    for name, group in df.groupby('way_id'):
        paths = []
        for _, row in group.iterrows():
            flag = True
            for p in paths:
                if row['end'] == p.start:
                    p.add_first(row['start'], row['end'])
                    flag = False
                    break
                elif row['start'] == p.end:
                    p.add_last(row['start'], row['end'])
                    flag = False
                    break
            if flag:
                paths.append(Path(row['start'], row['end']))
        lines += paths
    return lines


def _is_intersection(node, edges):
    """Returns True if `node` is a real street intersection."""
    if node.adhoc:
        return False
    if node.id == edges.loc[node.edge_id, 'source']:
        return edges.loc[node.edge_id, 'source_inter']
    return edges.loc[node.edge_id, 'target_inter']


def _to_point(node, edges):
    """Converts a node to a Point object (lon/lat)."""
    if node.adhoc:
        return edges.loc[node.edge_id, 'geometry'].interpolate(node.location,
                                                               normalized=True)
    if node.id == edges.loc[node.edge_id, 'source']:
        return edges.loc[node.edge_id, 'source_p']
    return edges.loc[node.edge_id, 'target_p']


def _get_points(nodes, edges):
    """Converts a list of nodes to a list of Point objects."""
    return [_to_point(n, edges) for n in nodes]


def split_at_intersection(lines, edges):
    """All Paths in `lines` are split at real street intersections.
      Typically, `lines` is a List of Paths resulting from call `connect_edges`.
      Returns:
        DataFrame: Linesegments in form of list of nodes.
    """
    nodes_lst = []
    for p in lines:
        nodes = [p.start] + [e[1] for e in p.path]
        split = [0]
        split += map(lambda x: 1+x[0],
                     filter(lambda x: _is_intersection(x[1], edges),
                            enumerate(nodes[1:])))
        if split[-1] != len(nodes) - 1:
            split.append(len(nodes) - 1)
        for i in range(len(split) - 1):
            nodes_lst.append(nodes[split[i]:split[i+1]+1])
    return pd.DataFrame({'nodes': nodes_lst})


def _shorten_linestring(linestring, dist_small, dist_long, threshold):
    """Shortens the given linestring at its beginning."""
    length = length_in_meters(linestring)
    dist = dist_small if length < threshold else dist_long
    if length <= dist or dist <= 0:
        return linestring
    checkpoints = [linestring.project(Point(p), normalized=True) \
                   for p in linestring.coords]
    index = np.argmin([dist/length >= c for c in checkpoints])
    p = linestring.interpolate(dist/length, normalized=True)
    return LineString([(p.x, p.y)] + linestring.coords[index:])


def _reverse_linestring(linestring):
    """Reverses the ordering of the nodes of the given LineString."""
    return LineString(linestring.coords[::-1])


def to_linestring(df, edges, shorten_small=1.,
                             shorten_long=5.,
                             threshold=20.):
    """Converts sequences of nodes to LineString objects and shortens them.
      If the LineString is shorter than `threshold`, it gets trimmed by
      `shorten_small`. Otherwise `shorten_long` is used.
      Typically, `df` is a DataFrame resulting from call `split_at_intersection`.
    """
    geometries = []
    for _, row in df.iterrows():
        linestring = LineString(_get_points(row['nodes'], edges))
        if _is_intersection(row['nodes'][0], edges):
            linestring = _shorten_linestring(linestring, shorten_small,
                                             shorten_long, threshold)
        if _is_intersection(row['nodes'][-1], edges):
            r_linestring = _reverse_linestring(linestring)
            s_linestring = _shorten_linestring(r_linestring, shorten_small,
                                               shorten_long, threshold)
            linestring = _reverse_linestring(s_linestring)
        geometries.append(linestring)
    return gpd.GeoDataFrame({'geometry': geometries})


def remove_short_linestrings(df, threshold=5.):
    """Removes geometries with length smaller than `threshold`."""
    drop = []
    for i, row in df.iterrows():
        if length_in_meters(row['geometry']) < threshold:
            drop.append(i)
    return df.drop(drop)
