from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import schemas, crud
from ..database import get_db
from ..utils import match_trip_to_request

router = APIRouter(
    prefix="/matching",
    tags=["matching"]
)

@router.get("/request/{request_id}", response_model=schemas.MatchResponse)
def get_matches_for_request(
    request_id: int,
    max_distance_km: float = 2.0,
    db: Session = Depends(get_db)
):
    """
    Finds all active or scheduled trips whose routes match the passenger's request constraints.
    - passenger pickup must be within `max_distance_km` of some route waypoint i.
    - passenger dropoff must be within `max_distance_km` of some route waypoint j.
    - sequence index of waypoint i must be less than sequence index of waypoint j (i < j).
    - trip must have enough available seats.
    """
    # Fetch the ride request
    ride_request = crud.get_ride_request(db=db, request_id=request_id)
    if not ride_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ride request with ID {request_id} not found"
        )
    
    # Retrieve all trips (filtering for active or scheduled occurs in the matching logic)
    all_trips = crud.get_trips(db=db, limit=200)
    
    matches = []
    for trip in all_trips:
        match_detail = match_trip_to_request(trip=trip, request=ride_request, max_distance_km=max_distance_km)
        if match_detail:
            matches.append(match_detail)
            
    # Sort matches by combined distance (best match first)
    matches.sort(key=lambda m: m["pickup_distance_km"] + m["dropoff_distance_km"])
    
    return {
        "ride_request": ride_request,
        "matches": matches
    }
