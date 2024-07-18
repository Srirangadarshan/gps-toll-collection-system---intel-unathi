import signal
import sys
from flask import Flask, request, jsonify
from datetime import datetime
import geopy.distance
import networkx as nx
import osmnx as ox
import pandas as pd
from shapely.geometry import Point
import csv
import logging
from map import fetch_map_data
import threading
import queue

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Load the road network graph from file
center_lat, center_lon = 13.2129905, 77.5539951
buffer_km = 2.5
G, nh48_edges, other_edges = fetch_map_data(center_lat, center_lon, buffer_km)

# Load user data from CSV file
user_data = pd.read_csv("users.csv")

# Data structures
vehicle_gps_data = {}
gps_queue = queue.Queue()

# Locks for thread safety
data_lock = threading.Lock()

# Vehicle wallets with initial balances
vehicle_wallets = {str(row['vehicleNumber']): row['amount'] for _, row in user_data.iterrows()}  # Ensure vehicleNumber is a string
logging.debug(f"Vehicle wallets: {vehicle_wallets}")

@app.route('/gps', methods=['POST'])
def receive_gps():
    try:
        data = request.get_json()
        logging.debug(f"Received data: {data}")

        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        vehicle_id = data.get('vehicle_id')
        vehicle_id = str(vehicle_id)  # Ensure vehicle_id is a string
        logging.debug(f"Received vehicle_id: {vehicle_id}")
        timestamp = data.get('timestamp')
        longitude = data.get('longitude')
        latitude = data.get('latitude')

        if None in [vehicle_id, timestamp, longitude, latitude]:
            return jsonify({"error": "Missing data"}), 400

        with data_lock:
            if vehicle_id not in vehicle_gps_data:
                vehicle_gps_data[vehicle_id] = []
            vehicle_gps_data[vehicle_id].append((timestamp, longitude, latitude))

        gps_queue.put((vehicle_id, timestamp, longitude, latitude))

        return jsonify({"message": "GPS data received"}), 200

    except Exception as e:
        logging.error(f"Error processing GPS data: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

def process_gps_data():
    while True:
        vehicle_id, timestamp, longitude, latitude = gps_queue.get()
        logging.info(f"Processing GPS data for vehicle {vehicle_id}")

        with data_lock:
            data = vehicle_gps_data[vehicle_id]

            if len(data) < 2:
                gps_queue.task_done()
                continue

            previous_data = data[-2]
            current_data = data[-1]

            previous_point = (previous_data[2], previous_data[1])
            current_point = (current_data[2], current_data[1])

            # Check if the vehicle is on the national highway
            if not is_highway(previous_point, current_point):
                logging.warning(f"Vehicle {vehicle_id} is not on the national highway. Discarding GPS data.")
                gps_queue.task_done()
                continue

            distance = calculate_distance(previous_point, current_point)
            time_elapsed = calculate_time_elapsed(previous_data[0], current_data[0])
            speed = calculate_speed(distance, time_elapsed)

            highway_distance = distance if is_highway(previous_point, current_point) else 0
            overspeed_intervals = [(previous_data[0], current_data[0], speed)] if speed > 100 else []

            vehicle_type = get_vehicle_type(vehicle_id)
            distance_price = calculate_price_by_distance(distance)
            overspeed_price = calculate_price_for_overspeed(speed - 100) if speed > 100 else 0
            vehicle_type_price = calculate_price_by_vehicle_type(vehicle_type)
            peak_time_price = calculate_peak_time_price(timestamp)
            tax_price = 5.0
            road_type_price = 10.0

            total_price = (
                distance_price +
                overspeed_price +
                vehicle_type_price +
                road_type_price +
                peak_time_price +
                tax_price
            )

            if not deduct_from_wallet(vehicle_id, total_price):
                logging.warning(f"Insufficient funds for vehicle {vehicle_id}")
                gps_queue.task_done()
                continue

            save_data_to_csv(vehicle_id, timestamp, previous_point, current_point, distance, speed, highway_distance, distance_price, overspeed_price, vehicle_type_price, peak_time_price, tax_price, total_price)
            
            gps_queue.task_done()
            logging.info(f"Finished processing GPS data for vehicle {vehicle_id}")


def save_data_to_csv(vehicle_id, timestamp, start_gps, end_gps, total_distance, avg_speed, highway_distance, distance_price, overspeed_price, vehicle_type_price, peak_time_price, tax_price, total_price):
    logging.info(f"Saving data to CSV for vehicle {vehicle_id}")
    file_path = f"{vehicle_id}.csv"

    with open(file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            timestamp, start_gps, end_gps, total_distance,
            avg_speed, distance_price, overspeed_price,
            tax_price, peak_time_price, vehicle_type_price, total_price
            
        ])

def calculate_distance(start, end):
    return geopy.distance.geodesic(start, end).km

def calculate_time_elapsed(previous_timestamp, current_timestamp):
    previous_time = datetime.strptime(previous_timestamp, "%Y-%m-%d %H:%M:%S")
    current_time = datetime.strptime(current_timestamp, "%Y-%m-%d %H:%M:%S")
    return (current_time - previous_time).total_seconds() / 3600

def calculate_speed(distance, time_elapsed):
    return distance / time_elapsed if time_elapsed > 0 else 0

def is_highway(start, end):
    try:
        point1 = Point(start[1], start[0])
        point2 = Point(end[1], end[0])

        nearest_edge1 = ox.distance.nearest_edges(G, point1.x, point1.y)
        nearest_edge2 = ox.distance.nearest_edges(G, point2.x, point2.y)

        is_highway1 = nearest_edge1 in nh48_edges.index
        is_highway2 = nearest_edge2 in nh48_edges.index

        return is_highway1 and is_highway2
    except Exception as e:
        logging.error(f"Error determining highway status: {e}")
        return False

def calculate_price_by_distance(highway_distance):
    base_price_per_km = 0.1
    return highway_distance * base_price_per_km

def calculate_price_for_overspeed(overspeed_amount):
    return overspeed_amount * 0.2

def calculate_price_by_vehicle_type(vehicle_type):
    price_map = {
        "car": 20,
        "bus": 30,
        "truck": 40,
        "other": 10
    }
    return price_map.get(vehicle_type.lower(), 10)

def calculate_peak_time_price(start_time):
    start_hour = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").hour
    if 7 <= start_hour <= 9 or 17 <= start_hour <= 19:
        return 10.0
    return 0.0

# Updated function to deduct amount from vehicle wallet and update CSV
def deduct_from_wallet(vehicle_id, amount):
    if vehicle_id in vehicle_wallets:
        current_balance = vehicle_wallets[vehicle_id]
        if current_balance >= amount:
            logging.debug(f"Attempting to deduct {amount} from vehicle {vehicle_id}")
            new_balance = current_balance - amount
            vehicle_wallets[vehicle_id] = new_balance
            logging.info(f"Deducted {amount} from vehicle {vehicle_id}, new balance: {new_balance}")

            # Update the CSV file with the new balance
            update_csv_balance(vehicle_id, new_balance)

            return True
        else:
            logging.warning(f"Insufficient funds for vehicle {vehicle_id}: {current_balance}")
    else:
        logging.error(f"Vehicle ID {vehicle_id} not found in vehicle_wallets")
    return False

# Function to update CSV balance for vehicle after deduction
def update_csv_balance(vehicle_id, new_balance):
    logging.debug(f"Updating CSV balance for vehicle {vehicle_id} with new balance: {new_balance}")
    try:
        # Read the CSV file
        with open('users.csv', 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Update the balance for the specific vehicle
        for row in rows:
            if row[2] == str(vehicle_id):
                row[6] = "{:.2f}".format(new_balance)  

        # Write the updated rows back to the CSV file
        with open('users.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        logging.info(f"Updated CSV balance for vehicle {vehicle_id} successfully")
    except Exception as e:
        logging.error(f"Error updating CSV balance for vehicle {vehicle_id}: {e}")


def get_vehicle_type(vehicle_id):
    vehicle_type = user_data.loc[user_data['vehicleNumber'] == vehicle_id, 'vehicleType']
    if not vehicle_type.empty:
        return vehicle_type.values[0]
    return 'other'

def signal_handler(sig, frame):
    logging.info("Shutting down server...")
    gps_queue.join()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

threading.Thread(target=process_gps_data, daemon=True).start()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
