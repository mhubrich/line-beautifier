import numpy as np
import pyproj


GEOD = pyproj.Geod(ellps='WGS84')


def length_in_meters(linestring):
    """Returns the length of the given LineString in meters."""
    length = 0.
    for i in range(len(linestring.coords) - 1):
        length += dist_m(linestring.coords[i][0], linestring.coords[i][1],
                         linestring.coords[i+1][0], linestring.coords[i+1][1])
    return length


def linestring_to_sequence(linestring, interval):
    """Returns a list of Points obtained from a LineString split at every
      `interval` segment. The start and end points of the LineString are
      guaranteed to be included in the list.
    """
    length = length_in_meters(linestring)
    return [linestring.interpolate(0)] + \
           [linestring.interpolate(interval/length * i, normalized=True) \
               for i in range(1, int(np.ceil(length/interval)))] + \
           [linestring.interpolate(1, normalized=True)]


def dist_m(lon1, lat1, lon2, lat2):
    """Returns the distance between both points in meters."""
    return GEOD.inv(lon1, lat1, lon2, lat2)[2]


def shift(lon, lat, deg, dist):
    """Shifts a point by a given distance (meters) into a direction (degrees)."""
    return GEOD.fwd(lon, lat, deg, dist)[:2]
