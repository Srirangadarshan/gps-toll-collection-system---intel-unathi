import osmnx as ox
import contextily as ctx
import matplotlib.pyplot as plt
from shapely.geometry import Point
import geopandas as gpd
import pickle

def fetch_map_data(center_lat, center_lon, buffer_km):
    # Fetch road network data from OSM
    G = ox.graph_from_point((center_lat, center_lon), dist=buffer_km*1000, network_type='all')

    # Convert the graph to a GeoDataFrame
    edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
    nodes = ox.graph_to_gdfs(G, nodes=True, edges=False)

    # Flatten the 'name' field
    edges['name'] = edges['name'].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)

    # Adjust the filtering logic based on the correct identification of NH48
    nh48_edges = edges[edges['name'].str.contains('Doddaballapur Road', case=False, na=False)]
    other_edges = edges[~edges['name'].str.contains('Doddaballapur Road', case=False, na=False)]

    return G, nh48_edges, other_edges

def plot_map(G, nh48_edges, other_edges, toll_point, center_lat, center_lon, buffer_km):
    # Plot the road network with basemap
    fig, ax = plt.subplots(figsize=(10, 10))

    # Plot NH48 and other roads with different colors
    nh48_edges.plot(ax=ax, linewidth=1.5, edgecolor='red', label='Doddaballapur Road')
    other_edges.plot(ax=ax, linewidth=1, edgecolor='blue', label="other road")

    # Plot the toll point as a green block
    gpd.GeoSeries([toll_point]).plot(ax=ax, color='green', markersize=320, marker='s', label='Toll Point')

    # Set the extent of the map
    buffer_deg = buffer_km / 111.32  # Convert km to degrees (approximation)
    ax.set_xlim(center_lon - buffer_deg, center_lon + buffer_deg)
    ax.set_ylim(center_lat - buffer_deg, center_lat + buffer_deg)

    # Add the basemap using OpenStreetMap
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, crs=nh48_edges.crs.to_string())

    plt.legend()
    plt.show()

    # Save the network graph using pickle
    with open("network_graph.pkl", "wb") as f:
        pickle.dump(G, f)
