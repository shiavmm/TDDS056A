import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    start_location_name = Column(String)
    end_location_name = Column(String)

    # Relationships
    waypoints = relationship("Waypoint", back_populates="route", cascade="all, delete-orphan", order_by="Waypoint.sequence")
    trips = relationship("Trip", back_populates="route", cascade="all, delete-orphan")

class Waypoint(Base):
    __tablename__ = "waypoints"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id", ondelete="CASCADE"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    sequence = Column(Integer, nullable=False)
    label = Column(String, nullable=True)

    # Relationships
    route = relationship("Route", back_populates="waypoints")

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    driver_name = Column(String, index=True)
    route_id = Column(Integer, ForeignKey("routes.id", ondelete="CASCADE"), nullable=False)
    departure_time = Column(DateTime, nullable=False)
    total_seats = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)
    status = Column(String, default="scheduled")  # scheduled, active, completed, cancelled

    # Relationships
    route = relationship("Route", back_populates="trips")
    navigation_updates = relationship("NavigationUpdate", back_populates="trip", cascade="all, delete-orphan")
    ride_requests = relationship("RideRequest", back_populates="matched_trip")

class RideRequest(Base):
    __tablename__ = "ride_requests"

    id = Column(Integer, primary_key=True, index=True)
    passenger_name = Column(String, index=True)
    pickup_latitude = Column(Float, nullable=False)
    pickup_longitude = Column(Float, nullable=False)
    pickup_name = Column(String, nullable=False)
    dropoff_latitude = Column(Float, nullable=False)
    dropoff_longitude = Column(Float, nullable=False)
    dropoff_name = Column(String, nullable=False)
    requested_seats = Column(Integer, default=1)
    status = Column(String, default="pending")  # pending, matched, completed, cancelled
    matched_trip_id = Column(Integer, ForeignKey("trips.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    matched_trip = relationship("Trip", back_populates="ride_requests")

class NavigationUpdate(Base):
    __tablename__ = "navigation_updates"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    current_latitude = Column(Float, nullable=False)
    current_longitude = Column(Float, nullable=False)
    speed = Column(Float, nullable=True)  # in km/h
    heading = Column(Float, nullable=True)  # in degrees (0-360)
    current_waypoint_index = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)

    # Relationships
    trip = relationship("Trip", back_populates="navigation_updates")
