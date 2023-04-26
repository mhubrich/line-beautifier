# mapillary/map_matching

Open-source implementation of a map matching algorithm based on
Hidden Markov Models.

Source: https://github.com/mapillary/map_matching

(Note that `shortest_path.py` was edited to fix a bug which broke the library.)


## Information

This implementation does pure map matching only, i.e. the underlaying map
structure (Google Maps, OSM, TomTom, etc.) has to be provided. Essentially,
it maps a sequence of points to the most likely edges of a graph.
