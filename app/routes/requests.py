from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import schemas, crud
from ..database import get_db

router = APIRouter(
    prefix="/requests",
    tags=["requests"]
)

@router.post("/", response_model=schemas.RideRequest, status_code=status.HTTP_201_CREATED)
def create_ride_request(request: schemas.RideRequestCreate, db: Session = Depends(get_db)):
    return crud.create_ride_request(db=db, request=request)

@router.get("/", response_model=List[schemas.RideRequest])
def read_ride_requests(status: Optional[str] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_ride_requests(db=db, status=status, skip=skip, limit=limit)

@router.get("/{request_id}", response_model=schemas.RideRequest)
def read_ride_request(request_id: int, db: Session = Depends(get_db)):
    db_request = crud.get_ride_request(db=db, request_id=request_id)
    if db_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ride request with ID {request_id} not found"
        )
    return db_request

@router.put("/{request_id}", response_model=schemas.RideRequest)
def update_ride_request(request_id: int, request: schemas.RideRequestUpdate, db: Session = Depends(get_db)):
    db_request = crud.get_ride_request(db=db, request_id=request_id)
    if db_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ride request with ID {request_id} not found"
        )
    
    old_status = db_request.status
    old_trip_id = db_request.matched_trip_id
    requested_seats = db_request.requested_seats
    
    # Store temporary changes to request
    new_status = request.status if request.status is not None else old_status
    new_trip_id = request.matched_trip_id if request.matched_trip_id is not None else old_trip_id
    
    # Validation / Seat updates before applying database modifications
    if old_trip_id != new_trip_id:
        # Free seats in old trip if it was previously matched
        if old_trip_id and old_status == "matched":
            trip_old = crud.get_trip(db=db, trip_id=old_trip_id)
            if trip_old:
                crud.update_trip(db=db, trip_id=old_trip_id, trip_in=schemas.TripUpdate(
                    available_seats=trip_old.available_seats + requested_seats
                ))
        
        # Deduct seats in new trip if it is now matched
        if new_trip_id and new_status == "matched":
            trip_new = crud.get_trip(db=db, trip_id=new_trip_id)
            if not trip_new:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Matched Trip with ID {new_trip_id} not found"
                )
            if trip_new.available_seats < requested_seats:
                # Revert seats on old trip since we threw an exception
                if old_trip_id and old_status == "matched":
                    trip_old = crud.get_trip(db=db, trip_id=old_trip_id)
                    if trip_old:
                        crud.update_trip(db=db, trip_id=old_trip_id, trip_in=schemas.TripUpdate(
                            available_seats=trip_old.available_seats - requested_seats
                        ))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Not enough seats available in matched Trip {new_trip_id}. Required: {requested_seats}, Available: {trip_new.available_seats}"
                )
            crud.update_trip(db=db, trip_id=new_trip_id, trip_in=schemas.TripUpdate(
                available_seats=trip_new.available_seats - requested_seats
            ))
            
    elif old_status != new_status:
        # Trip remains same, only status changed
        if new_trip_id:
            trip = crud.get_trip(db=db, trip_id=new_trip_id)
            if trip:
                if old_status == "matched" and new_status != "matched":
                    # Unmatched: Restore seats to the trip
                    crud.update_trip(db=db, trip_id=new_trip_id, trip_in=schemas.TripUpdate(
                        available_seats=trip.available_seats + requested_seats
                    ))
                elif old_status != "matched" and new_status == "matched":
                    # Matched: Deduct seats from the trip
                    if trip.available_seats < requested_seats:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Not enough seats available in matched Trip {new_trip_id}. Required: {requested_seats}, Available: {trip.available_seats}"
                        )
                    crud.update_trip(db=db, trip_id=new_trip_id, trip_in=schemas.TripUpdate(
                        available_seats=trip.available_seats - requested_seats
                    ))
                    
    # Safely perform the update on the request row
    return crud.update_ride_request(db=db, request_id=request_id, request_in=request)

@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ride_request(request_id: int, db: Session = Depends(get_db)):
    db_request = crud.get_ride_request(db=db, request_id=request_id)
    if db_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ride request with ID {request_id} not found"
        )
    
    # If the deleted request was matched, release its seats back to the trip
    if db_request.status == "matched" and db_request.matched_trip_id:
        trip = crud.get_trip(db=db, trip_id=db_request.matched_trip_id)
        if trip:
            crud.update_trip(db=db, trip_id=db_request.matched_trip_id, trip_in=schemas.TripUpdate(
                available_seats=trip.available_seats + db_request.requested_seats
            ))
            
    crud.delete_ride_request(db=db, request_id=request_id)
    return None
