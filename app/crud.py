from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from . import models, schemas

# --- Route CRUD ---

def create_route(db: Session, route: schemas.RouteCreate) -> models.Route:
    db_route = models.Route(
        name=route.name,
        start_location_name=route.start_location_name,
        end_location_name=route.end_location_name
    )
    db.add(db_route)
    db.commit()
    db.refresh(db_route)

    # Add waypoints
    for wp in route.waypoints:
        db_wp = models.Waypoint(
            route_id=db_route.id,
            latitude=wp.latitude,
            longitude=wp.longitude,
            sequence=wp.sequence,
            label=wp.label
        )
        db.add(db_wp)
    db.commit()
    db.refresh(db_route)
    return db_route

def get_route(db: Session, route_id: int) -> Optional[models.Route]:
    return db.query(models.Route).filter(models.Route.id == route_id).first()

def get_routes(db: Session, skip: int = 0, limit: int = 100) -> List[models.Route]:
    return db.query(models.Route).offset(skip).limit(limit).all()

def update_route(db: Session, route_id: int, route_in: schemas.RouteCreate) -> Optional[models.Route]:
    db_route = get_route(db, route_id)
    if not db_route:
        return None
    
    # Update base fields
    db_route.name = route_in.name
    db_route.start_location_name = route_in.start_location_name
    db_route.end_location_name = route_in.end_location_name
    
    # Delete old waypoints
    db.query(models.Waypoint).filter(models.Waypoint.route_id == route_id).delete()
    
    # Re-insert new waypoints
    for wp in route_in.waypoints:
        db_wp = models.Waypoint(
            route_id=route_id,
            latitude=wp.latitude,
            longitude=wp.longitude,
            sequence=wp.sequence,
            label=wp.label
        )
        db.add(db_wp)
        
    db.commit()
    db.refresh(db_route)
    return db_route

def delete_route(db: Session, route_id: int) -> bool:
    db_route = get_route(db, route_id)
    if not db_route:
        return False
    db.delete(db_route)
    db.commit()
    return True


# --- Trip CRUD ---

def create_trip(db: Session, trip: schemas.TripCreate) -> models.Trip:
    db_trip = models.Trip(
        driver_name=trip.driver_name,
        route_id=trip.route_id,
        departure_time=trip.departure_time,
        total_seats=trip.total_seats,
        available_seats=trip.total_seats,  # Initially all seats are available
        status="scheduled"
    )
    db.add(db_trip)
    db.commit()
    db.refresh(db_trip)
    return db_trip

def get_trip(db: Session, trip_id: int) -> Optional[models.Trip]:
    return db.query(models.Trip).filter(models.Trip.id == trip_id).first()

def get_trips(db: Session, status: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[models.Trip]:
    query = db.query(models.Trip)
    if status:
        query = query.filter(models.Trip.status == status)
    return query.offset(skip).limit(limit).all()

def update_trip(db: Session, trip_id: int, trip_in: schemas.TripUpdate) -> Optional[models.Trip]:
    db_trip = get_trip(db, trip_id)
    if not db_trip:
        return None
    
    update_data = trip_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_trip, field, value)
        
    db.commit()
    db.refresh(db_trip)
    return db_trip

def delete_trip(db: Session, trip_id: int) -> bool:
    db_trip = get_trip(db, trip_id)
    if not db_trip:
        return False
    db.delete(db_trip)
    db.commit()
    return True


# --- RideRequest CRUD ---

def create_ride_request(db: Session, request: schemas.RideRequestCreate) -> models.RideRequest:
    db_request = models.RideRequest(
        passenger_name=request.passenger_name,
        pickup_latitude=request.pickup_latitude,
        pickup_longitude=request.pickup_longitude,
        pickup_name=request.pickup_name,
        dropoff_latitude=request.dropoff_latitude,
        dropoff_longitude=request.dropoff_longitude,
        dropoff_name=request.dropoff_name,
        requested_seats=request.requested_seats,
        status="pending"
    )
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request

def get_ride_request(db: Session, request_id: int) -> Optional[models.RideRequest]:
    return db.query(models.RideRequest).filter(models.RideRequest.id == request_id).first()

def get_ride_requests(db: Session, status: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[models.RideRequest]:
    query = db.query(models.RideRequest)
    if status:
        query = query.filter(models.RideRequest.status == status)
    return query.offset(skip).limit(limit).all()

def update_ride_request(db: Session, request_id: int, request_in: schemas.RideRequestUpdate) -> Optional[models.RideRequest]:
    db_request = get_ride_request(db, request_id)
    if not db_request:
        return None
    
    update_data = request_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_request, field, value)
        
    db.commit()
    db.refresh(db_request)
    return db_request

def delete_ride_request(db: Session, request_id: int) -> bool:
    db_request = get_ride_request(db, request_id)
    if not db_request:
        return False
    db.delete(db_request)
    db.commit()
    return True


# --- Navigation Update CRUD ---

def create_navigation_update(db: Session, trip_id: int, update: schemas.NavigationUpdateCreate) -> models.NavigationUpdate:
    db_update = models.NavigationUpdate(
        trip_id=trip_id,
        current_latitude=update.current_latitude,
        current_longitude=update.current_longitude,
        speed=update.speed,
        heading=update.heading,
        current_waypoint_index=update.current_waypoint_index
    )
    db.add(db_update)
    db.commit()
    db.refresh(db_update)
    return db_update

def get_navigation_history(db: Session, trip_id: int, limit: int = 100) -> List[models.NavigationUpdate]:
    return (
        db.query(models.NavigationUpdate)
        .filter(models.NavigationUpdate.trip_id == trip_id)
        .order_by(desc(models.NavigationUpdate.timestamp))
        .limit(limit)
        .all()
    )

def get_latest_navigation_update(db: Session, trip_id: int) -> Optional[models.NavigationUpdate]:
    return (
        db.query(models.NavigationUpdate)
        .filter(models.NavigationUpdate.trip_id == trip_id)
        .order_by(desc(models.NavigationUpdate.timestamp))
        .first()
    )
