import json
import numpy as np
import geopandas as gpd

from shapely.geometry import Point, LineString
from collections import defaultdict


def _helper(ways, node_count, del_way_ids, n, id1, id2, ind):
    """Helper function to reduce code in `merge_ways`."""
    for x in ways[id2]['ref']:
        ways[x] = ways[id1]
    ways[id2] = ways[id1]
    ways[id1]['ref'] += [id2] + ways[id2]['ref']
    del node_count[n][1]
    del_way_ids.add(id2)


# TODO function needs refactoring
def merge_ways(ways, node_count):
    """Merges ways which are not an intersection but are broken up in OSM."""
    del_way_ids = set([])
    for n in node_count:
        # the second evaluation accounts for closed roundabouts
        # with way['nodes'][0] == way['nodes'][-1]
        if len(node_count[n]) == 2 and node_count[n][0] != node_count[n][1]:
            id1, id2 = node_count[n]
            if (ways[id1]['nodes'][0] == n or ways[id1]['nodes'][-1] == n) and \
               (ways[id2]['nodes'][0] == n or ways[id2]['nodes'][-1] == n):
                if not 'ref' in ways[id1]:
                    ways[id1]['ref'] = []
                if not 'ref' in ways[id2]:
                    ways[id2]['ref'] = []
                if ways[id1]['nodes'][0] == n and ways[id2]['nodes'][0] == n:
                    ways[id1]['nodes'] = ways[id1]['nodes'][::-1] + ways[id2]['nodes'][1:]
                    _helper(ways, node_count, del_way_ids, n, id1, id2, 1)
                elif ways[id1]['nodes'][-1] == n and ways[id2]['nodes'][-1] == n:
                    ways[id1]['nodes'] += ways[id2]['nodes'][:-1][::-1]
                    _helper(ways, node_count, del_way_ids, n, id1, id2, 1)
                elif ways[id2]['nodes'][0] == n and ways[id1]['nodes'][0] != n:
                    ways[id1]['nodes'] += ways[id2]['nodes'][1:]
                    _helper(ways, node_count, del_way_ids, n, id1, id2, 1)
                else:
                    ways[id2]['nodes'] += ways[id1]['nodes'][1:]
                    _helper(ways, node_count, del_way_ids, n, id2, id1, 0)
    for id in del_way_ids:
        del ways[id]
    return ways, node_count


def load_osm(data):
    """Takes OSM data as input and converts it to a GeoDataFrame.
      Arguments:
        data: Dict or String. The OSM data in JSON format. If String, a JSON
          file at this location is tried to be openend.
      Returns:
        df: GeoDataFrame. Contains all edges found in `data`.
    """
    if isinstance(data, str):
        data = json.load(open(data, 'r'))
    if not isinstance(data, dict):
        raise ValueError('Argument `data` is expected to be a dictionary.')
    nodes, ways = {}, {}
    node_count = defaultdict(list)
    for obj in data['elements']:
        if obj['type'] == 'node':
            nodes[obj['id']] = obj
        else:
            ways[obj['id']] = obj
            for n in obj['nodes']:
                node_count[n].append(obj['id'])
    # this step accounts for "broken up" OSM streets
    ways, node_count = merge_ways(ways, node_count)
    geom, source, target, source_p, target_p = [], [], [], [], []
    source_inter, target_inter, way_id = [], [], []
    for w in ways.values():
        for i in range(len(w['nodes']) - 1):
            s = w['nodes'][i]
            t = w['nodes'][i+1]
            sp = Point(nodes[s]['lon'], nodes[s]['lat'])
            tp = Point(nodes[t]['lon'], nodes[t]['lat'])
            geom.append(LineString((sp, tp)))
            source.append(s)
            target.append(t)
            source_p.append(sp)
            target_p.append(tp)
            source_inter.append(len(node_count[s]) > 1)
            target_inter.append(len(node_count[t]) > 1)
            way_id.append(w['id'])
    df =  gpd.GeoDataFrame({'geometry': geom,
                            'source': source,
                            'target': target,
                            'source_p': source_p,
                            'target_p': target_p,
                            'source_inter': source_inter,
                            'target_inter': target_inter,
                            'way_id': way_id,
                            'id': np.arange(len(geom), dtype=np.int32)})
    df.set_index('id', drop=False, inplace=True)
    return df
