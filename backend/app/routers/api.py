import json
import traceback

from fastapi import APIRouter, Depends, Query, Response, status, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Dict, Any
from ..database import get_db
from .. import models, schemas
from ..config import settings
from ..services.construction_scraper import get_construction_geojson, update_construction_geojson_file
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter()

# test for echo
@router.post("/echo")
def echo(payload: dict):
    return {"you sent": payload}

@router.get("/hello")
def hello():
    return {"message": "Hello, Taipei Hackathon!"}

@router.get("/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).order_by(models.User.id).all()

@router.post("/users", response_model=schemas.UserOut)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    u = models.User(name=payload.name)
    db.add(u); db.commit(); db.refresh(u); return u


# TestRecord endpoints
@router.get("/test_records", response_model=list[schemas.TestOut])
def list_test_records(db: Session = Depends(get_db)):
    return db.query(models.TestRecord).order_by(models.TestRecord.id).all()


@router.post("/test_records", response_model=schemas.TestOut)
def create_test_record(payload: schemas.TestCreate, db: Session = Depends(get_db)):
    tr = models.TestRecord(title=payload.title, description=payload.description)
    db.add(tr)
    db.commit()
    db.refresh(tr)
    return tr


@router.get("/road_segments/suggest")
def suggest_road_segments(
    q: str = Query(..., min_length=1, description="Keyword to match road segment names"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    stmt = (
        select(models.RoadSegment.name)
        .where(models.RoadSegment.name.isnot(None))
        .where(models.RoadSegment.name.ilike(f"%{q}%"))
        .distinct()
        .order_by(models.RoadSegment.name.asc())
        .limit(limit)
    )
    names = db.execute(stmt).scalars().all()
    return {"items": names}


@router.get("/road_segments/search")
def search_road_segments(
    name: str = Query(..., min_length=1, description="Full road name to search"),
    db: Session = Depends(get_db),
):
    segments = (
        db.query(models.RoadSegment)
        .filter(models.RoadSegment.name == name)
        .order_by(models.RoadSegment.id.asc())
        .all()
    )

    features = []
    for seg in segments:
        geometry = seg.geometry or {}
        properties = seg.properties or {}
        if isinstance(properties, str):
            try:
                properties = json.loads(properties)
            except Exception:
                properties = {"raw_properties": properties}
        if isinstance(geometry, str):
            try:
                geometry = json.loads(geometry)
            except Exception:
                geometry = None
        if not geometry:
            continue

        # Merge basic columns into properties for popup usage
        merged_props = {
            **({} if not isinstance(properties, dict) else properties),
            "name": seg.name,
            "highway": seg.highway,
            "lanes": seg.lanes,
            "oneway": seg.oneway,
            "length_m": seg.length_m,
            "osmid": seg.osmid,
        }
        features.append({
            "type": "Feature",
            "properties": merged_props,
            "geometry": geometry,
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }

@router.get("/construction/geojson", response_model=Dict[str, Any])
def get_construction_data(response: Response):
    """Get construction data as GeoJSON from file. If file doesn't exist, update it first."""
    geojson = get_construction_geojson(settings.CONSTRUCTION_GEOJSON_PATH)
    
    # If file doesn't exist, try to update it first
    if geojson is None:
        logger.info("Construction GeoJSON file not found, attempting to update...")
        try:
            # Ensure data directory exists
            data_dir = os.path.dirname(settings.CONSTRUCTION_GEOJSON_PATH)
            os.makedirs(data_dir, exist_ok=True)
            
            # Try to update the file
            success = update_construction_geojson_file(settings.CONSTRUCTION_GEOJSON_PATH)
            if success:
                # Read the newly created file
                geojson = get_construction_geojson(settings.CONSTRUCTION_GEOJSON_PATH)
                if geojson is not None:
                    logger.info("Successfully updated and loaded construction data")
                    return geojson
            
            # If update failed or file still doesn't exist
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"error": "Construction data not available and update failed"}
        except Exception as e:
            logger.error(f"Error updating construction data: {e}", exc_info=True)
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"error": f"Failed to update construction data: {str(e)}"}
    
    return geojson


@router.get("/construction/update", response_model=Dict[str, Any])
def manual_update():
    """Manual trigger for construction data update (for testing/admin)"""
    try:
        # Ensure data directory exists
        data_dir = os.path.dirname(settings.CONSTRUCTION_GEOJSON_PATH)
        os.makedirs(data_dir, exist_ok=True)
        
        success = update_construction_geojson_file(settings.CONSTRUCTION_GEOJSON_PATH)
        if success:
            geojson = get_construction_geojson(settings.CONSTRUCTION_GEOJSON_PATH)
            feature_count = len(geojson['features']) if geojson else 0
            return {
                "status": "success",
                "message": "Construction data updated successfully",
                "feature_count": feature_count
            }
        else:
            return {"status": "error", "message": "Failed to update construction data"}
    except Exception as e:
        logger.error(f"Manual update failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


# Construction Notices endpoints
@router.get("/construction/notices", response_model=list[schemas.ConstructionNoticeOut])
def list_construction_notices(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """獲取施工通知列表"""
    notices = db.query(models.ConstructionNotice).offset(skip).limit(limit).all()
    return notices


@router.get("/construction/notices/update", response_model=Dict[str, Any])
def update_construction_notices_endpoint(
    db: Session = Depends(get_db),
    max_pages: int = None,
    clear_existing: bool = True
):
    """手動觸發更新施工通知資料（爬取並保存）"""
    from ..services.notice_contruction import update_construction_notices
    try:
        result = update_construction_notices(db, max_pages=max_pages, clear_existing=clear_existing)
        return result
    except Exception as e:
        logger.error(f"Update construction notices failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


# Favorite endpoints
@router.get("/favorites", response_model=list[schemas.FavoriteOut])
def list_favorites(
    user_id: int = Query(None, description="User ID (internal)"),
    external_id: str = Query(None, description="External User ID (UUID from Flutter)"),
    db: Session = Depends(get_db)
):
    """獲取用戶的收藏列表"""
    # 如果提供了 external_id，先查找對應的 user_id
    if external_id and not user_id:
        user = db.query(models.User).filter(models.User.external_id == external_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User with external_id {external_id} not found")
        user_id = user.id
    elif not user_id:
        raise HTTPException(status_code=400, detail="Either user_id or external_id must be provided")
    
    favorites = (
        db.query(models.Favorite)
        .filter(models.Favorite.user_id == user_id)
        .order_by(models.Favorite.added_at.desc())
        .all()
    )
    return favorites


@router.post("/favorites", response_model=schemas.FavoriteOut)
def create_favorite(
    payload: schemas.FavoriteCreate,
    external_id: str = Query(None, description="External User ID (UUID from Flutter)"),
    db: Session = Depends(get_db)
):
    """創建收藏"""
    try:
        # 如果提供了 external_id，先查找或創建用戶
        if external_id:
            user = db.query(models.User).filter(models.User.external_id == external_id).first()
            if not user:
                # 如果用戶不存在，創建新用戶
                user = models.User(name="Default User", external_id=external_id)
                db.add(user)
                db.commit()
                db.refresh(user)
            payload.user_id = user.id
        elif not payload.user_id:
            raise HTTPException(status_code=400, detail="Either user_id in payload or external_id query parameter must be provided")
        
        # 檢查用戶是否存在
        user = db.query(models.User).filter(models.User.id == payload.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User with id {payload.user_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_favorite (user lookup): {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    # 檢查是否已存在相同的收藏（根據 type 和 name 或 id）
    existing = None
    if payload.type == 'place' and payload.place_data and payload.place_data.get('id'):
        # 查詢所有該用戶的 place 類型收藏，然後在 Python 中過濾
        place_favorites = (
            db.query(models.Favorite)
            .filter(
                models.Favorite.user_id == payload.user_id,
                models.Favorite.type == 'place'
            )
            .all()
        )
        for fav in place_favorites:
            if fav.place_data and fav.place_data.get('id') == payload.place_data.get('id'):
                existing = fav
                break
    elif payload.type == 'road' and payload.road_name:
        # 對於道路，使用 road_name 和 road_osmids 來判斷
        existing = (
            db.query(models.Favorite)
            .filter(
                models.Favorite.user_id == payload.user_id,
                models.Favorite.type == 'road',
                models.Favorite.road_name == payload.road_name
            )
            .first()
        )
    elif payload.type == 'route' and payload.route_start and payload.route_end:
        existing = (
            db.query(models.Favorite)
            .filter(
                models.Favorite.user_id == payload.user_id,
                models.Favorite.type == 'route',
                models.Favorite.route_start == payload.route_start,
                models.Favorite.route_end == payload.route_end
            )
            .first()
        )
    
    if existing:
        # 如果已存在，更新它
        for key, value in payload.model_dump(exclude={'user_id'}).items():
            if value is not None:
                setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    
    # 創建新的收藏
    try:
        favorite = models.Favorite(**payload.model_dump())
        db.add(favorite)
        db.commit()
        db.refresh(favorite)
        return favorite
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating favorite: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to create favorite: {str(e)}")


@router.get("/favorites/{favorite_id}", response_model=schemas.FavoriteOut)
def get_favorite(
    favorite_id: int,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """獲取單個收藏"""
    favorite = (
        db.query(models.Favorite)
        .filter(
            models.Favorite.id == favorite_id,
            models.Favorite.user_id == user_id
        )
        .first()
    )
    if not favorite:
        raise HTTPException(status_code=404, detail=f"Favorite with id {favorite_id} not found")
    return favorite


@router.put("/favorites/{favorite_id}", response_model=schemas.FavoriteOut)
def update_favorite(
    favorite_id: int,
    payload: schemas.FavoriteUpdate,
    user_id: int = Query(None, description="User ID (internal)"),
    external_id: str = Query(None, description="External User ID (UUID from Flutter)"),
    db: Session = Depends(get_db)
):
    """更新收藏（主要用於更新通知設置）"""
    # 如果提供了 external_id，先查找對應的 user_id
    if external_id and not user_id:
        user = db.query(models.User).filter(models.User.external_id == external_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User with external_id {external_id} not found")
        user_id = user.id
    elif not user_id:
        raise HTTPException(status_code=400, detail="Either user_id or external_id must be provided")
    
    favorite = (
        db.query(models.Favorite)
        .filter(
            models.Favorite.id == favorite_id,
            models.Favorite.user_id == user_id
        )
        .first()
    )
    if not favorite:
        raise HTTPException(status_code=404, detail=f"Favorite with id {favorite_id} not found")
    
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(favorite, key, value)
    
    db.commit()
    db.refresh(favorite)
    return favorite


@router.delete("/favorites/{favorite_id}")
def delete_favorite(
    favorite_id: int,
    user_id: int = Query(None, description="User ID (internal)"),
    external_id: str = Query(None, description="External User ID (UUID from Flutter)"),
    db: Session = Depends(get_db)
):
    """刪除收藏"""
    # 如果提供了 external_id，先查找對應的 user_id
    if external_id and not user_id:
        user = db.query(models.User).filter(models.User.external_id == external_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User with external_id {external_id} not found")
        user_id = user.id
    elif not user_id:
        raise HTTPException(status_code=400, detail="Either user_id or external_id must be provided")
    
    favorite = (
        db.query(models.Favorite)
        .filter(
            models.Favorite.id == favorite_id,
            models.Favorite.user_id == user_id
        )
        .first()
    )
    if not favorite:
        raise HTTPException(status_code=404, detail=f"Favorite with id {favorite_id} not found")
    
    db.delete(favorite)
    db.commit()
    return {"status": "success", "message": "Favorite deleted"}