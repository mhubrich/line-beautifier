import geopandas as gpd
from tqdm import tqdm
from rtree import index

from osm.query_overpass import query_overpass
from osm.convert import load_osm
from .map_match import map_match, DEFAULT_BETA, DEFAULT_SIGMA_Z
from .utils import linestring_to_sequence


class PathBrokenException(Exception):
    """Raises when a path between two Candidates is broken."""


def build_rtee(df):
    """Builds an R-Tree of the given geometries in `df`."""
    if 'id' not in df.columns:
        raise ValueError('DataFrame is expected to have column "id".')
    if 'geometry' not in df.columns:
        raise ValueError('DataFrame is expected to have column "geometry".')
    idx = index.Index()
    for _, row in df.iterrows():
        idx.insert(row['id'], row['geometry'].bounds)
    return idx


def _verify_matched_path(candidates, sequence, tol=0.95):
    """Verifies if there is a connected path of consecutive candidates."""
    # There must be at least two Candidate objects: start and end of LineString
    if len(candidates) < 2:
        raise PathBrokenException('Number of candidates is smaller than 2.')
    # For each Measurement (see map_match.py) there must be a matched candidate
    if len(candidates) < len(sequence) * tol:
        raise PathBrokenException('Not all Measurements could be matched.')
    # Check if path between consecutive candidates was found
    for i in range(len(candidates) - 1, 0, -1):
        if candidates[i-1] not in candidates[i].path:
            raise PathBrokenException('Candidate path is broken.')
        # TODO We might get away with path = [], commenting this out for now
        # if len(candidates[i].path[candidates[i-1]]) == 0:
        #     raise PathBrokenException('Candidate path is broken.')


def build_path(candidates):
    """Returns the path from the last to the first candidate."""
    path = []
    for i in range(len(candidates) - 1, 0, -1):
        path += candidates[i].path[candidates[i-1]]
    return path


def map_geolocations(geolocations,
                     sequence_interval=5.,
                     search_radius=20.,
                     verbose=True):
    """The given geometries are matched to OSM data.
      Note that only LineStrings are matched.
      Arguments:
        geolocations: GeoDataFrame. The given geometries.
        sequence_interval: Float. Interval for splitting linestrings.
        search_radius: Float. Consider only streets within this distance.
        verbose: Boolean. Whether to print progress and unmatched LineStrings.
      Returns:
         mapped_geoms: GeoDataFrame. Contains `path` with matched edges.
         edges: GeoDataFrame. The edges downloaded from OSM.
    """
    if 'geometry' not in geolocations.columns:
        raise ValueError('DataFrame is expected to have column "geometry".')
    mapped_geoms = geolocations.copy()
    mapped_geoms.loc[:, 'modified'] = False
    mapped_geoms.loc[:, 'path'] = None
    bounds = (geolocations.bounds.minx.min(), geolocations.bounds.miny.min(),
              geolocations.bounds.maxx.max(), geolocations.bounds.maxy.max())
    map = query_overpass(bounds)
    edges = load_osm(map)
    idx = build_rtee(edges)
    unmatched_lines = []
    linestrings = mapped_geoms[mapped_geoms.geom_type == 'LineString']
    for i, row in tqdm(linestrings.iterrows(), total=len(linestrings),
                                               disable=not verbose):
        sequence = linestring_to_sequence(row['geometry'], sequence_interval)
        candidates = map_match(idx, edges, sequence, search_radius,
                               beta=DEFAULT_BETA, sigma=DEFAULT_SIGMA_Z)
        try:
            _verify_matched_path(candidates, sequence)
            mapped_geoms.at[i, 'path'] = build_path(candidates)
            mapped_geoms.loc[i, 'modified'] = True
        except PathBrokenException:
            unmatched_lines.append(row['geometry'])
            if verbose:
                tqdm.write('No match found for geometry %d/%d'
                           % (i+1, len(mapped_geoms)))
    if len(unmatched_lines) > 0 and verbose:
        print('\nUnmatched LineStrings:')
        print(gpd.GeoDataFrame({'geometry': unmatched_lines}).to_json())
    return mapped_geoms, edges
