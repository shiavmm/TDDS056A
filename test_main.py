import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from app.database import Base, get_db
from app.main import app

# Set up test database (isolated test.db)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test.db"):
        try:
            os.remove("./test.db")
        except PermissionError:
            pass  # Windows might lock it temporarily

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to the Carpooling" in response.json()["message"]

def test_routes_crud():
    # Create
    route_data = {
        "name": "Route A-to-D",
        "start_location_name": "Location A",
        "end_location_name": "Location D",
        "waypoints": [
            {"latitude": 10.0, "longitude": 10.0, "sequence": 0, "label": "Start A"},
            {"latitude": 10.1, "longitude": 10.1, "sequence": 1, "label": "Checkpoint B"},
            {"latitude": 10.2, "longitude": 10.2, "sequence": 2, "label": "Checkpoint C"},
            {"latitude": 10.3, "longitude": 10.3, "sequence": 3, "label": "End D"}
        ]
    }
    response = client.post("/routes/", json=route_data)
    assert response.status_code == 201
    res_json = response.json()
    assert res_json["name"] == "Route A-to-D"
    assert len(res_json["waypoints"]) == 4
    route_id = res_json["id"]

    # Read All
    response = client.get("/routes/")
    assert response.status_code == 200
    assert len(response.json()) == 1

    # Read One
    response = client.get(f"/routes/{route_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Route A-to-D"

    # Update
    updated_route_data = {
        "name": "Route A-to-D Modified",
        "start_location_name": "Location A Modified",
        "end_location_name": "Location D Modified",
        "waypoints": [
            {"latitude": 10.0, "longitude": 10.0, "sequence": 0, "label": "Start A"},
            {"latitude": 10.5, "longitude": 10.5, "sequence": 1, "label": "New Waypoint E"},
            {"latitude": 10.3, "longitude": 10.3, "sequence": 2, "label": "End D"}
        ]
    }
    response = client.put(f"/routes/{route_id}", json=updated_route_data)
    assert response.status_code == 200
    assert response.json()["name"] == "Route A-to-D Modified"
    assert len(response.json()["waypoints"]) == 3

    # Delete
    response = client.delete(f"/routes/{route_id}")
    assert response.status_code == 204
    # Ensure it is gone
    response = client.get(f"/routes/{route_id}")
    assert response.status_code == 404

def test_route_validation_error():
    # Bad sequence (missing sequence 1)
    route_data = {
        "name": "Invalid Route",
        "start_location_name": "A",
        "end_location_name": "C",
        "waypoints": [
            {"latitude": 10.0, "longitude": 10.0, "sequence": 0, "label": "Start"},
            {"latitude": 10.2, "longitude": 10.2, "sequence": 2, "label": "End"}
        ]
    }
    response = client.post("/routes/", json=route_data)
    assert response.status_code == 422  # Unprocessable Entity

def test_trips_crud():
    # 1. Create a route first
    route_data = {
        "name": "Test Route",
        "start_location_name": "Start",
        "end_location_name": "End",
        "waypoints": [
            {"latitude": 10.0, "longitude": 10.0, "sequence": 0},
            {"latitude": 11.0, "longitude": 11.0, "sequence": 1}
        ]
    }
    route_res = client.post("/routes/", json=route_data).json()
    route_id = route_res["id"]

    # 2. Create Trip
    trip_data = {
        "driver_name": "Alice",
        "departure_time": "2026-07-15T08:00:00",
        "total_seats": 4,
        "route_id": route_id
    }
    response = client.post("/trips/", json=trip_data)
    assert response.status_code == 201
    trip_res = response.json()
    assert trip_res["driver_name"] == "Alice"
    assert trip_res["available_seats"] == 4
    assert trip_res["status"] == "scheduled"
    trip_id = trip_res["id"]

    # 3. Read Trip
    response = client.get(f"/trips/{trip_id}")
    assert response.status_code == 200
    assert response.json()["driver_name"] == "Alice"

    # 4. Update Trip status
    response = client.put(f"/trips/{trip_id}", json={"status": "active"})
    assert response.status_code == 200
    assert response.json()["status"] == "active"

    # 5. Delete Trip
    response = client.delete(f"/trips/{trip_id}")
    assert response.status_code == 204

def test_realtime_navigation_logs():
    # Create Route and Trip
    route_data = {
        "name": "Nav Route",
        "start_location_name": "Start",
        "end_location_name": "End",
        "waypoints": [
            {"latitude": 10.0, "longitude": 10.0, "sequence": 0},
            {"latitude": 11.0, "longitude": 11.0, "sequence": 1}
        ]
    }
    route_id = client.post("/routes/", json=route_data).json()["id"]
    trip_id = client.post("/trips/", json={
        "driver_name": "Bob",
        "departure_time": "2026-07-15T08:00:00",
        "total_seats": 4,
        "route_id": route_id
    }).json()["id"]

    # Check latest navigation: should be 404 since no pings sent yet
    response = client.get(f"/trips/{trip_id}/navigation/latest")
    assert response.status_code == 404

    # Post real-time navigation update
    nav_ping = {
        "current_latitude": 10.05,
        "current_longitude": 10.05,
        "speed": 60.5,
        "heading": 45.0,
        "current_waypoint_index": 0
    }
    response = client.post(f"/trips/{trip_id}/navigation", json=nav_ping)
    assert response.status_code == 201
    assert response.json()["current_latitude"] == 10.05
    assert response.json()["speed"] == 60.5

    # Check if trip status auto-updated to active
    trip_res = client.get(f"/trips/{trip_id}").json()
    assert trip_res["status"] == "active"

    # Verify latest location matches ping
    latest = client.get(f"/trips/{trip_id}/navigation/latest").json()
    assert latest["current_latitude"] == 10.05

    # Post another ping
    client.post(f"/trips/{trip_id}/navigation", json={
        "current_latitude": 10.10,
        "current_longitude": 10.10,
        "speed": 55.0,
        "heading": 46.0,
        "current_waypoint_index": 0
    })

    # Read history (limit 5)
    history = client.get(f"/trips/{trip_id}/navigation/history?limit=5").json()
    assert len(history) == 2
    # Verify descending ordering: latest ping should be first
    assert history[0]["current_latitude"] == 10.10
    assert history[1]["current_latitude"] == 10.05

def test_carpool_matching_algorithm():
    # 1. Create a driver route (Route goes straight along coordinates (10, 10) -> (10.2, 10.2) -> (10.4, 10.4) -> (10.6, 10.6))
    # Distance between waypoints is ~31 km (10.0->10.2 at latitude 10)
    route_data = {
        "name": "Driver Route A-B-C-D",
        "start_location_name": "A",
        "end_location_name": "D",
        "waypoints": [
            {"latitude": 10.0, "longitude": 10.0, "sequence": 0, "label": "Point A"},
            {"latitude": 10.2, "longitude": 10.2, "sequence": 1, "label": "Point B"},
            {"latitude": 10.4, "longitude": 10.4, "sequence": 2, "label": "Point C"},
            {"latitude": 10.6, "longitude": 10.6, "sequence": 3, "label": "Point D"}
        ]
    }
    route_id = client.post("/routes/", json=route_data).json()["id"]

    # 2. Create Trip Offer with 3 available seats
    trip_id = client.post("/trips/", json={
        "driver_name": "Driver Dave",
        "departure_time": "2026-07-15T09:00:00",
        "total_seats": 3,
        "route_id": route_id
    }).json()["id"]

    # 3. Create a MATCHING passenger request
    # Pickup is very close to Point B (10.2, 10.2) -> (10.205, 10.205) is ~780m away
    # Dropoff is very close to Point C (10.4, 10.4) -> (10.395, 10.395) is ~780m away
    # Since B (sequence 1) comes before C (sequence 2), this is chronologically valid.
    matching_request = {
        "passenger_name": "Passenger Peter",
        "pickup_latitude": 10.205,
        "pickup_longitude": 10.205,
        "pickup_name": "Near Point B",
        "dropoff_latitude": 10.395,
        "dropoff_longitude": 10.395,
        "dropoff_name": "Near Point C",
        "requested_seats": 2
    }
    req_res_1 = client.post("/requests/", json=matching_request).json()
    request_1_id = req_res_1["id"]

    # Check match endpoint
    matches = client.get(f"/matching/request/{request_1_id}?max_distance_km=2.0").json()["matches"]
    assert len(matches) == 1
    assert matches[0]["trip"]["id"] == trip_id
    assert matches[0]["pickup_waypoint_seq"] == 1
    assert matches[0]["dropoff_waypoint_seq"] == 2
    assert matches[0]["pickup_distance_km"] < 1.0
    assert matches[0]["dropoff_distance_km"] < 1.0

    # 4. Create a NON-MATCHING passenger request (Chronologically reversed)
    # Pickup is near Point C (sequence 2), dropoff near Point B (sequence 1)
    reversed_request = {
        "passenger_name": "Passenger Rebecca",
        "pickup_latitude": 10.395,
        "pickup_longitude": 10.395,
        "pickup_name": "Near Point C",
        "dropoff_latitude": 10.205,
        "dropoff_longitude": 10.205,
        "dropoff_name": "Near Point B",
        "requested_seats": 1
    }
    request_2_id = client.post("/requests/", json=reversed_request).json()["id"]
    matches_2 = client.get(f"/matching/request/{request_2_id}?max_distance_km=2.0").json()["matches"]
    # Should not match because driver is going B -> C, passenger wants C -> B
    assert len(matches_2) == 0

    # 5. Create a NON-MATCHING request (too far from route)
    far_request = {
        "passenger_name": "Passenger Far",
        "pickup_latitude": 12.000,
        "pickup_longitude": 12.000,
        "pickup_name": "Far Away",
        "dropoff_latitude": 10.395,
        "dropoff_longitude": 10.395,
        "dropoff_name": "Near Point C",
        "requested_seats": 1
    }
    request_3_id = client.post("/requests/", json=far_request).json()["id"]
    matches_3 = client.get(f"/matching/request/{request_3_id}?max_distance_km=2.0").json()["matches"]
    assert len(matches_3) == 0

    # 6. Create request asking for too many seats (4 seats required, only 3 available)
    high_seats_request = {
        "passenger_name": "Passenger Heavy",
        "pickup_latitude": 10.205,
        "pickup_longitude": 10.205,
        "pickup_name": "Near Point B",
        "dropoff_latitude": 10.395,
        "dropoff_longitude": 10.395,
        "dropoff_name": "Near Point C",
        "requested_seats": 4
    }
    request_4_id = client.post("/requests/", json=high_seats_request).json()["id"]
    matches_4 = client.get(f"/matching/request/{request_4_id}?max_distance_km=2.0").json()["matches"]
    assert len(matches_4) == 0

def test_seat_deduction_and_release():
    # 1. Setup route & trip with 3 seats
    route_data = {
        "name": "Simple Route",
        "start_location_name": "A",
        "end_location_name": "B",
        "waypoints": [
            {"latitude": 10.0, "longitude": 10.0, "sequence": 0},
            {"latitude": 10.1, "longitude": 10.1, "sequence": 1}
        ]
    }
    route_id = client.post("/routes/", json=route_data).json()["id"]
    trip_id = client.post("/trips/", json={
        "driver_name": "Driver Sam",
        "departure_time": "2026-07-15T09:00:00",
        "total_seats": 3,
        "route_id": route_id
    }).json()["id"]

    # 2. Create Ride Request requesting 2 seats
    req_id = client.post("/requests/", json={
        "passenger_name": "Pam",
        "pickup_latitude": 10.0,
        "pickup_longitude": 10.0,
        "pickup_name": "A",
        "dropoff_latitude": 10.1,
        "dropoff_longitude": 10.1,
        "dropoff_name": "B",
        "requested_seats": 2
    }).json()["id"]

    # 3. Match Request with Trip (PUT request update status=matched, matched_trip_id=trip_id)
    response = client.put(f"/requests/{req_id}", json={
        "status": "matched",
        "matched_trip_id": trip_id
    })
    assert response.status_code == 200
    assert response.json()["status"] == "matched"
    assert response.json()["matched_trip_id"] == trip_id

    # Verify trip seats decremented from 3 to 1
    trip_res = client.get(f"/trips/{trip_id}").json()
    assert trip_res["available_seats"] == 1

    # 4. Attempt to match ANOTHER request asking for 2 seats (only 1 left)
    req_fail_id = client.post("/requests/", json={
        "passenger_name": "Failing",
        "pickup_latitude": 10.0,
        "pickup_longitude": 10.0,
        "pickup_name": "A",
        "dropoff_latitude": 10.1,
        "dropoff_longitude": 10.1,
        "dropoff_name": "B",
        "requested_seats": 2
    }).json()["id"]
    
    response = client.put(f"/requests/{req_fail_id}", json={
        "status": "matched",
        "matched_trip_id": trip_id
    })
    assert response.status_code == 400
    assert "Not enough seats" in response.json()["detail"]

    # 5. Cancel Pam's ride request, verify seats restored back to 3
    client.put(f"/requests/{req_id}", json={
        "status": "cancelled",
        "matched_trip_id": None
    })
    trip_res_new = client.get(f"/trips/{trip_id}").json()
    assert trip_res_new["available_seats"] == 3
