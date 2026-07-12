from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import List, Optional
from datetime import datetime

# --- Waypoint Schemas ---
class WaypointBase(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude of the waypoint")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude of the waypoint")
    sequence: int = Field(..., ge=0, description="Sequence order of the waypoint in the route")
    label: Optional[str] = Field(None, description="Optional name/label for the waypoint")

class WaypointCreate(WaypointBase):
    pass

class Waypoint(WaypointBase):
    id: int
    route_id: int

    model_config = ConfigDict(from_attributes=True)


# --- Route Schemas ---
class RouteBase(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the route")
    start_location_name: str = Field(..., min_length=1, description="Name of starting location")
    end_location_name: str = Field(..., min_length=1, description="Name of ending location")

class RouteCreate(RouteBase):
    waypoints: List[WaypointCreate] = Field(..., min_length=2, description="Route must contain at least a start and end waypoint")

    @model_validator(mode="after")
    def validate_waypoint_sequences(self):
        # Sort waypoints by sequence to check consistency
        sorted_wps = sorted(self.waypoints, key=lambda w: w.sequence)
        
        # Verify sequences are continuous starting from 0 (e.g. 0, 1, 2...)
        for idx, wp in enumerate(sorted_wps):
            if wp.sequence != idx:
                raise ValueError(f"Waypoint sequences must be continuous starting from 0. Expected sequence {idx}, got {wp.sequence}")
        return self


class Route(RouteBase):
    id: int
    waypoints: List[Waypoint]

    model_config = ConfigDict(from_attributes=True)


# --- Trip Schemas ---
class TripBase(BaseModel):
    driver_name: str = Field(..., min_length=1, description="Name of the driver")
    departure_time: datetime = Field(..., description="Scheduled departure time")
    total_seats: int = Field(..., ge=1, description="Total passenger capacity")

class TripCreate(TripBase):
    route_id: int = Field(..., description="ID of the Route associated with this trip")

class TripUpdate(BaseModel):
    departure_time: Optional[datetime] = None
    available_seats: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, pattern="^(scheduled|active|completed|cancelled)$")

class Trip(TripBase):
    id: int
    route_id: int
    available_seats: int
    status: str
    route: Route

    model_config = ConfigDict(from_attributes=True)


# --- Ride Request Schemas ---
class RideRequestBase(BaseModel):
    passenger_name: str = Field(..., min_length=1, description="Name of the passenger")
    pickup_latitude: float = Field(..., ge=-90.0, le=90.0)
    pickup_longitude: float = Field(..., ge=-180.0, le=180.0)
    pickup_name: str = Field(..., min_length=1, description="Name of the pickup location")
    dropoff_latitude: float = Field(..., ge=-90.0, le=90.0)
    dropoff_longitude: float = Field(..., ge=-180.0, le=180.0)
    dropoff_name: str = Field(..., min_length=1, description="Name of the dropoff location")
    requested_seats: int = Field(1, ge=1, description="Number of seats requested")

class RideRequestCreate(RideRequestBase):
    pass

class RideRequestUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(pending|matched|completed|cancelled)$")
    matched_trip_id: Optional[int] = None

class RideRequest(RideRequestBase):
    id: int
    status: str
    matched_trip_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)


# --- Navigation Update Schemas ---
class NavigationUpdateBase(BaseModel):
    current_latitude: float = Field(..., ge=-90.0, le=90.0)
    current_longitude: float = Field(..., ge=-180.0, le=180.0)
    speed: Optional[float] = Field(None, ge=0.0, description="Speed in km/h")
    heading: Optional[float] = Field(None, ge=0.0, le=360.0, description="Heading in degrees")
    current_waypoint_index: Optional[int] = Field(None, ge=0, description="Index of the last reached waypoint")

class NavigationUpdateCreate(NavigationUpdateBase):
    pass

class NavigationUpdate(NavigationUpdateBase):
    id: int
    trip_id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Matching Schemas ---
class MatchedTripDetail(BaseModel):
    trip: Trip
    pickup_distance_km: float = Field(..., description="Distance from requested pickup to closest waypoint")
    dropoff_distance_km: float = Field(..., description="Distance from requested dropoff to closest waypoint")
    pickup_waypoint_seq: int = Field(..., description="Sequence of waypoint matched for pickup")
    dropoff_waypoint_seq: int = Field(..., description="Sequence of waypoint matched for dropoff")

class MatchResponse(BaseModel):
    ride_request: RideRequest
    matches: List[MatchedTripDetail]
