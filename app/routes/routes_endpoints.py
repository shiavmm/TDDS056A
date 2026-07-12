from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, crud
from ..database import get_db

router = APIRouter(
    prefix="/routes",
    tags=["routes"]
)

@router.post("/", response_model=schemas.Route, status_code=status.HTTP_201_CREATED)
def create_route(route: schemas.RouteCreate, db: Session = Depends(get_db)):
    return crud.create_route(db=db, route=route)

@router.get("/", response_model=List[schemas.Route])
def read_routes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_routes(db=db, skip=skip, limit=limit)

@router.get("/{route_id}", response_model=schemas.Route)
def read_route(route_id: int, db: Session = Depends(get_db)):
    db_route = crud.get_route(db=db, route_id=route_id)
    if db_route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route with ID {route_id} not found"
        )
    return db_route

@router.put("/{route_id}", response_model=schemas.Route)
def update_route(route_id: int, route: schemas.RouteCreate, db: Session = Depends(get_db)):
    db_route = crud.update_route(db=db, route_id=route_id, route_in=route)
    if db_route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route with ID {route_id} not found"
        )
    return db_route

@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(route_id: int, db: Session = Depends(get_db)):
    success = crud.delete_route(db=db, route_id=route_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route with ID {route_id} not found"
        )
    return None
