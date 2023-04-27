<div align="center">
  <h2 align="center">Line Beautifier</h2>

  <p align="center">
    A library for cleaning, optimizing, and standardizing hand-drawn lines on city maps
  </p>
</div>
<br />

**Table of Contents**
- [Example](#example)
- [How it Works](#how-it-works)
  - [Map Matching](#map-matching)
  - [Overlaps](#overlaps)
  - [Connecting LineStrings to Intersections](#connecting-linestrings-to-intersections)
  - [Splitting](#splitting)
  - [Shortening](#shortening)
  - [Removal](#removal)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgment](#acknowledgment)
- [Author](#author)


## Example

![Example](/examples/beautify.gif)

## How it Works

The optimization and standardization processes involves the following steps:
1. Drawn lines are matched to OSM street data.
2. Overlaps are removed, i.e. streets are only covered once.
3. Lines which started/ended only a few meters away from an intersection are connected to that intersection.
4. All lines are split at street intersections.
5. The start and end of a line is shortened at intersections to yield a unifrom appearance.
6. Lines smaller than a threshold are removed.

These steps are further explained below.

### Map Matching
Map matching is the problem of how to match recorded geographic coordinates to a logical model of the real world, typically using some form of Geographic Information System. The most common approach is to take recorded, serial location points (e.g. from GPS) and relate them to edges in an existing street graph (network).<sup>[[1]](https://en.wikipedia.org/wiki/Map_matching)</sup>

Our map matching approach takes a LineString and converts it to a sequence of points. This "GPS trajectory" is then mapped onto streets while finding the "most likely" path from start to end. Finally, the mapped points are connected and form a projected LineString.

![Map Matching](/examples/map_matching.gif)

Almost all modern implementations of the map matching problem follow this [Microsoft paper](https://infolab.usc.edu/csci587/Fall2016/papers/Hidden%20Markov%20Map%20Matching%20Through%20Noise%20and%20Sparseness.pdf). A Markov Hidden Model is used to find the "most likely" path through a graph (i.e. a path that maximizes a given probability distribution).

Here we are using an [open-source implementation](https://github.com/caomw/map_matching) for the map matching. This implementation performs the map matching on a given graph only. That means we have to supply road data in form of a graph by ourselves. We do this by querying OpenStreetMap (OSM) data and transforming it accordingly.

### Overlaps
Due to the projection of LineStrings to the same "source of truth", overlaps can be easily identified and removed:

![Overlaps](/examples/overlaps.gif)

### Connecting LineStrings to Intersections
If hand-drawn LineStrings start just before or after a street intersection, they are connected to this intersection:

![Connect](/examples/connect.gif)

### Splitting
All matched LineStrings are split at street intersections (note that this increases the total amount of LineStrings significantly):

![Splitting](/examples/split.gif)

### Shortening
Finally, LineStrings are shortened at each intersection to yield a standardized style:

![Shortening](/examples/shorten.gif)

### Removal
Lastly, short road segments are removed from the data. These result from either noise in the data or shortening an already short LineString. This improves UI interaction because tiny LineStrings will be hard to view and select.

![Shortening](/examples/removal.gif)

All of the above operations are performed on a graph to avoid floating point precision errors. That means LineStrings are mapped to "theoretical" edges of a graph. Overlaps, connections, splitting, etc. are performed on this graph. Only before the shortening operation, edges are transformed back to LineStrings.

## Getting Started

### Prerequisites
This project uses a number of Python packages. These can be conveniently installed using Python's package manager `pip`:
```
pip install numpy, requests, urllib3, python-intervals, shapely, pandas, geopandas, geopy, pyproj, boto3, tqdm, rtree, nose, argparse
```

### Installation
To get a local copy, simply clone this repository: `git clone https://github.com/mhubrich/line-beautifier.git`

## Usage
To run the package, simply execute `python optimize.py` in the command line with the following (optional) arguments:
- `--input`: path to the input file
- `--output`: path to the output file
- `--length`: sample interval to create measurements
- `--radius`: search radius for each measurement
- `--connect`: distance for connecting linestrings to OSM nodes
- `--shorten1`: amount in meters to shorten small linestrings
- `--shorten2`: amount in meters to shorten long linestrings
- `--shorten3`: threshold value for small/long linestrings
- `--threshold`: drops linestrings than given threshold in meters
- `--sparse`: split linestrings at driveways etc.
- `--color`: matched linestrings are colored
- `--silent`: suppresses all printed output

## Contributing
Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are greatly appreciated.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some amazing feature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
This project is licensed under the MIT License - see the `LICENSE` file for details.

## Acknowledgment
Shout-out to [@caomw](https://github.com/caomw) for providing the [map matching](https://github.com/caomw/map_matching) package, an open-source implementation of a map matching algorithm based on Hidden Markov Models.

## Author
[Markus Hubrich](https://github.com/mhubrich)
