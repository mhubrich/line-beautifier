import os
import json
import argparse
import pandas as pd
import geopandas as gpd

import graph.ops
from map_matching.map_matching import map_geolocations


COLOR_MODIFIED = '#4CAF50'
COLOR_UNMODIFIED = '#F44336'
COLOR_POLYGONS = '#555555'
STROKE_WIDTH = 3.


def load_geolocations(path):
    """Loads a GeoJSON file from a given path."""
    return gpd.read_file(path)


def save_geolocations(df, path):
    """Saves a GeoDataFrame to a given path."""
    try:
        json.dump(json.loads(df.to_json()), open(path, 'w'))
    except UnicodeDecodeError:
        # Needed for special characters (workaround for now)
        json.dump(json.loads(df.to_json(encoding='latin-1')), open(path, 'w'))


def merge_geolocations(df_unmodified, df_modified,
                       columns=['geometry', 'modified']):
    """Concatenates two GeoDataFrames."""
    return pd.concat([df_unmodified[columns],
                        df_modified[columns]
                     ], ignore_index=True)

def optimize(path_in,
             path_out=None,
             sequence_interval=5.,
             search_radius=20.,
             connect_dist=5.,
             shorten_dist_small=1.,
             shorten_dist_long=5.,
             shorten_dist_threshold=20.,
             length_threshold=5.,
             sparse=False,
             color=False,
             verbose=True):
    """Performs the geolocation optimization for LineStrings.
      Arguments:
        path_in: String. Path to the input GeoJSON file.
        path_out: String or None. Path to the output file. If None, the cleaned
          up file is saved at the same location as the input file, plus the
          suffix `_cleaned.geojson`.
        sequence_interval: Float. Interval for splitting linestrings.
        search_radius: Float. Consider only streets within this distance.
        connect_dist: Float. Distance for connecting linestrings to OSM nodes.
        shorten_dist_small: Float. Amount of which to shorten small linestrings.
        shorten_dist_long: Float. Amount of which to shorten long linestrings.
        shorten_dist_threshold: Float. Decision value for small/long LineStrings.
        length_threshold: Float. Remove LineStrings smaller than this value.
        sparse: Boolean. Whether to split LineStrings at driveways etc.
        color: Boolean. Whether to colour matched LineStrings.
        verbose: Boolean. Whether to print progress and unmatched LineStrings.
    """
    geolocations = load_geolocations(path_in)
    df_mapped, edges = map_geolocations(geolocations, sequence_interval,
                                        search_radius, verbose)
    df_unmodified = df_mapped[df_mapped.modified == False]
    df_modified = df_mapped[df_mapped.modified == True]
    df = graph.ops.list_edges(df_modified, edges)
    df = graph.ops.combine_edges(df, sparse)
    df = graph.ops.interpolate_edges(df, edges, connect_dist)
    lines = graph.ops.connect_edges(df)
    df = graph.ops.split_at_intersection(lines, edges)
    df = graph.ops.to_linestring(df, edges, shorten_dist_small,
                                            shorten_dist_long,
                                            shorten_dist_threshold)
    df = graph.ops.remove_short_linestrings(df, length_threshold)
    df['modified'] = True
    df_final = merge_geolocations(df_unmodified, df,
                                  ['geometry', 'modified'])
    if color:
        df_final.loc[:, 'stroke-width'] = STROKE_WIDTH
        df_final.loc[:, 'stroke'] = COLOR_POLYGONS
        df_final.loc[df_final.modified == True, 'stroke'] = COLOR_MODIFIED
        loc_unmodified_linestrings = (df_final.modified == False) & \
                                     (df_final.geom_type == 'LineString')
        df_final.loc[loc_unmodified_linestrings, 'stroke'] = COLOR_UNMODIFIED
    if not path_out:
        path_out = os.path.splitext(path_in)[0] + '_optimized.geojson'
    save_geolocations(df_final, path_out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', required=True, type=str,
                        help='path to the input file')
    parser.add_argument('--output', '-o', required=False, type=str,
                        default=None,
                        help='path to the output file')
    parser.add_argument('--length', '-l', required=False, type=float,
                        default=5.,
                        help='sample interval to create measurements')
    parser.add_argument('--radius', '-r', required=False, type=float,
                        default=20.,
                        help='search radius for each measurement')
    parser.add_argument('--connect', '-c', required=False, type=float,
                        default=5.,
                        help='distance for connecting linestrings to OSM nodes')
    parser.add_argument('--shorten1', '-sS', required=False, type=float,
                        default=1.,
                        help='amount of which to shorten small linestrings')
    parser.add_argument('--shorten2', '-sL', required=False, type=float,
                        default=5.,
                        help='amount of which to shorten long linestrings')
    parser.add_argument('--shorten3', '-sT', required=False, type=float,
                        default=20.,
                        help='threshold value for small/long LineStrings')
    parser.add_argument('--threshold', '-t', required=False, type=float,
                        default=5.,
                        help='drop LineStrings smaller than this')
    parser.add_argument('--sparse', '-SP', required=False, type=bool,
                        default=False,
                        help='split LineStrings at driveways etc.')
    parser.add_argument('--color', '-C', required=False, action='store_true',
                        help='matched linestrings are coloured')
    parser.add_argument('--silent', '-S', required=False, action='store_true',
                        help='suppresses all printed output')
    args = parser.parse_args()
    optimize(path_in=args.input,
             path_out=args.output,
             sequence_interval=args.length,
             search_radius=args.radius,
             connect_dist=args.connect,
             shorten_dist_small=args.shorten1,
             shorten_dist_long=args.shorten2,
             shorten_dist_threshold=args.shorten3,
             length_threshold=args.threshold,
             sparse=args.sparse,
             color=args.color,
             verbose=not args.silent)
