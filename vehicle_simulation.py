import networkx as nx
import random
import time
import threading
import requests
import csv
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import osmnx as ox
from shapely.geometry import Point
from datetime import datetime
from map import fetch_map_data

# Load the road network graph from file
center_lat, center_lon = 13.2129905, 77.5539951
buffer_km = 2.5
G, nh48_edges, _ = fetch_map_data(center_lat, center_lon, buffer_km) 

# Load user data from CSV file
user_data = pd.read_csv("users.csv")

class Vehicle:
    def __init__(self, vehicle_number, start_node, end_node, G, speed):
        self.vehicle_number = vehicle_number
        self.start_node = start_node
        self.end_node = end_node
        self.current_node = start_node
        self.speed = speed  # Speed in nodes per second
        self.path = self.calculate_path(G)
        self.position_index = 0

    def calculate_path(self, G):
        try:
            return nx.shortest_path(G, source=self.start_node, target=self.end_node, weight='length')
        except nx.NetworkXNoPath:
            print(f"No path between {self.start_node} and {self.end_node}")
            return []

    def move(self):
        if self.position_index < len(self.path) - 1:
            self.position_index += 1
            self.current_node = self.path[self.position_index]

    def get_current_gps(self, G):
        node_data = G.nodes[self.current_node]
        return Point(node_data['x'], node_data['y'])

    def send_gps_to_server(self, gps_data):
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            x, y = gps_data.coords[0]  # Extract x and y coordinates from Point object

            url = 'http://localhost:5000/gps'
            payload = {
                'vehicle_id': str(self.vehicle_number),
                'timestamp': timestamp,
                'longitude': float(x),
                'latitude': float(y)
            }

            print(f"Sending payload: {payload}")  # Debug print

            response = requests.post(url, json=payload)
            response.raise_for_status()  # Raise HTTPError for bad response status

            try:
                server_response = response.json()
                print(f"Vehicle {self.vehicle_number}: Time {timestamp}, GPS ({x}, {y}), Server Response: {server_response}")
            except ValueError as e:
                print(f"Vehicle {self.vehicle_number}: Time {timestamp}, GPS ({x}, {y}), Invalid JSON Response: {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"Vehicle {self.vehicle_number}: Time {timestamp}, GPS ({x}, {y}), Request Exception: {e}")

        except Exception as e:
            print(f"Vehicle {self.vehicle_number}: Time {timestamp}, GPS ({x}, {y}), Unexpected Error: {e}")


# Initialize CSV file


# Read vehicle numbers from user data
vehicle_numbers = user_data['vehicleNumber'].tolist()
num_vehicles = len(vehicle_numbers)
vehicles = []

# Randomly select start and end nodes from the nodes in the network
nodes_list = list(G.nodes)
for i in range(num_vehicles):
    start_node = random.choice(nodes_list)
    end_node = random.choice(nodes_list)
    speed = random.uniform(0.5, 2.0)  # Random speed between 0.5 and 2.0 nodes per second
    
    vehicle_number = vehicle_numbers[i]
    
    vehicle = Vehicle(vehicle_number, start_node, end_node, G, speed)
    vehicles.append(vehicle)

def simulate_movement(vehicle, G):
    while vehicle.position_index < len(vehicle.path) - 1:
        try:
            vehicle.move()
            gps_data = vehicle.get_current_gps(G)  # Retrieve GPS data as Point object
            vehicle.send_gps_to_server(gps_data)
        except Exception as e:
            print(f"Vehicle {vehicle.vehicle_number} encountered an error: {e}")
        finally:
            time.sleep(1 / vehicle.speed)  # Sleep time adjusted by speed

threads = []
for vehicle in vehicles:
    t = threading.Thread(target=simulate_movement, args=(vehicle, G))
    threads.append(t)
    t.start()

# Visualization setup 
fig, ax = plt.subplots(figsize=(10, 10))
nh48_edges.plot(ax=ax, linewidth=2, edgecolor='red', label='Doddaballapur Road')
edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
edges.plot(ax=ax, linewidth=1, edgecolor='blue')
node_data = ox.graph_to_gdfs(G, nodes=True, edges=False)[['x', 'y']].to_numpy()
sc = ax.scatter([], [], color='red', s=100, zorder=5,label = "vehicles")

def update(frame):
    positions = []
    for vehicle in vehicles:
        gps_data = vehicle.get_current_gps(G)
        positions.append((gps_data.x, gps_data.y))
    sc.set_offsets(positions)
    
    # Add title, xlabel, ylabel, and legend
    ax.set_title('Vehicle Simulation on Road Network')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.legend(['Doddaballapur national highway'])
    
    
    return sc,

ani = animation.FuncAnimation(fig, update, frames=range(100), interval=1000, blit=True)

plt.show()

for t in threads:
    t.join()


