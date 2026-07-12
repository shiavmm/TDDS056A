from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import schemas, crud
from ..database import get_db

router = APIRouter(
    prefix="/trips",
    tags=["trips"]
)

@router.post("/", response_model=schemas.Trip, status_code=status.HTTP_201_CREATED)
def create_trip(trip: schemas.TripCreate, db: Session = Depends(get_db)):
    # Verify that the route exists
    db_route = crud.get_route(db=db, route_id=trip.route_id)
    if not db_route:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create trip. Route with ID {trip.route_id} does not exist"
        )
    return crud.create_trip(db=db, trip=trip)

@router.get("/", response_model=List[schemas.Trip])
def read_trips(status: Optional[str] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_trips(db=db, status=status, skip=skip, limit=limit)

@router.get("/{trip_id}", response_model=schemas.Trip)
def read_trip(trip_id: int, db: Session = Depends(get_db)):
    db_trip = crud.get_trip(db=db, trip_id=trip_id)
    if db_trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID {trip_id} not found"
        )
    return db_trip

@router.put("/{trip_id}", response_model=schemas.Trip)
def update_trip(trip_id: int, trip: schemas.TripUpdate, db: Session = Depends(get_db)):
    db_trip = crud.update_trip(db=db, trip_id=trip_id, trip_in=trip)
    if db_trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID {trip_id} not found"
        )
    return db_trip

@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(trip_id: int, db: Session = Depends(get_db)):
    success = crud.delete_trip(db=db, trip_id=trip_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID {trip_id} not found"
        )
    return None


# --- Real-Time Navigation / Tracking Endpoints ---

@router.post("/{trip_id}/navigation", response_model=schemas.NavigationUpdate, status_code=status.HTTP_201_CREATED)
def post_navigation_update(trip_id: int, update: schemas.NavigationUpdateCreate, db: Session = Depends(get_db)):
    db_trip = crud.get_trip(db=db, trip_id=trip_id)
    if not db_trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID {trip_id} not found"
        )
    # Ensure trip is active (or scheduled, auto-start it if active location ping is received)
    if db_trip.status == "scheduled":
        crud.update_trip(db=db, trip_id=trip_id, trip_in=schemas.TripUpdate(status="active"))
    
    return crud.create_navigation_update(db=db, trip_id=trip_id, update=update)

@router.get("/{trip_id}/navigation/latest", response_model=schemas.NavigationUpdate)
def read_latest_navigation(trip_id: int, db: Session = Depends(get_db)):
    db_trip = crud.get_trip(db=db, trip_id=trip_id)
    if not db_trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID {trip_id} not found"
        )
    db_update = crud.get_latest_navigation_update(db=db, trip_id=trip_id)
    if not db_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No navigation logs found for Trip with ID {trip_id}"
        )
    return db_update

@router.get("/{trip_id}/navigation/history", response_model=List[schemas.NavigationUpdate])
def read_navigation_history(trip_id: int, limit: int = 100, db: Session = Depends(get_db)):
    db_trip = crud.get_trip(db=db, trip_id=trip_id)
    if not db_trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID {trip_id} not found"
        )
    return crud.get_navigation_history(db=db, trip_id=trip_id, limit=limit)
