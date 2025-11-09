import json
import logging
import math
from typing import Dict, Set
from datetime import datetime, date
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..database import SessionLocal
from .. import models

logger = logging.getLogger(__name__)

router = APIRouter()

# 儲存活躍的 WebSocket 連接
# key: external_id, value: WebSocket
active_connections: Dict[str, WebSocket] = {}


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """計算兩點之間的距離（米）使用 Haversine 公式"""
    R = 6371000  # 地球半徑（米）
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def get_favorite_coordinates(favorite: models.Favorite) -> list[tuple[float, float]]:
    """從收藏中提取座標點列表"""
    coordinates = []
    
    if favorite.type == 'place':
        # 地點類型：使用 lat/lon
        if favorite.lat is not None and favorite.lon is not None:
            coordinates.append((favorite.lat, favorite.lon))
    elif favorite.type == 'road':
        # 道路類型：需要從 road_osmids 查詢道路段座標
        # 這裡簡化處理，如果有 lat/lon 就使用
        if favorite.lat is not None and favorite.lon is not None:
            coordinates.append((favorite.lat, favorite.lon))
        # TODO: 可以從 road_osmids 查詢道路段的所有座標點
    elif favorite.type == 'route':
        # 路線類型：使用起點和終點
        if favorite.route_start_coords:
            coords = favorite.route_start_coords
            if isinstance(coords, dict) and 'lat' in coords and 'lon' in coords:
                coordinates.append((coords['lat'], coords['lon']))
        if favorite.route_end_coords:
            coords = favorite.route_end_coords
            if isinstance(coords, dict) and 'lat' in coords and 'lon' in coords:
                coordinates.append((coords['lat'], coords['lon']))
        # TODO: 可以從 route_feature_collection 提取路線上的所有點
    
    return coordinates


def check_construction_near_favorites(user_id: int, db: Session) -> list[dict]:
    """檢查用戶收藏地點附近的施工情況"""
    # 獲取用戶所有啟用了通知的收藏
    favorites = (
        db.query(models.Favorite)
        .filter(
            models.Favorite.user_id == user_id,
            models.Favorite.notification_enabled == True
        )
        .all()
    )
    
    if not favorites:
        return []
    
    # 獲取當前正在進行的施工通知
    today = date.today()
    construction_notices = (
        db.query(models.ConstructionNotice)
        .filter(
            models.ConstructionNotice.start_date <= today,
            or_(
                models.ConstructionNotice.end_date >= today,
                models.ConstructionNotice.end_date.is_(None)
            )
        )
        .all()
    )
    
    logger.debug(f"User {user_id}: Found {len(favorites)} favorites with notifications enabled, {len(construction_notices)} ongoing constructions")
    
    alerts = []
    
    for favorite in favorites:
        favorite_coords = get_favorite_coordinates(favorite)
        if not favorite_coords:
            logger.debug(f"User {user_id}: Favorite {favorite.id} ({favorite.name}) has no coordinates")
            continue
        
        threshold_meters = favorite.distance_threshold or 100.0
        
        for construction in construction_notices:
            if not construction.geometry:
                continue
            
            # 從 geometry 中提取座標
            geometry = construction.geometry
            if isinstance(geometry, dict) and geometry.get('type') == 'Point':
                coords = geometry.get('coordinates')
                if isinstance(coords, list) and len(coords) >= 2:
                    con_lon = float(coords[0])
                    con_lat = float(coords[1])
                    
                    # 檢查是否在收藏地點的閾值範圍內
                    for fav_lat, fav_lon in favorite_coords:
                        distance = haversine_distance_meters(fav_lat, fav_lon, con_lat, con_lon)
                        
                        if distance <= threshold_meters:
                            alerts.append({
                                'favorite_id': favorite.id,
                                'favorite_name': favorite.name,
                                'favorite_type': favorite.type,
                                'construction_id': construction.id,
                                'construction_name': construction.name,
                                'construction_road': construction.road,
                                'construction_type': construction.type,
                                'distance_meters': round(distance),
                                'start_date': construction.start_date.isoformat() if construction.start_date else None,
                                'end_date': construction.end_date.isoformat() if construction.end_date else None,
                                'url': construction.url,
                            })
                            logger.info(
                                f"User {user_id}: Found nearby construction - "
                                f"Favorite '{favorite.name}' (id={favorite.id}) has construction "
                                f"'{construction.name}' (id={construction.id}) at {round(distance)}m"
                            )
                            break  # 找到匹配就跳出內層循環
    
    if alerts:
        logger.info(f"User {user_id}: Generated {len(alerts)} alerts")
    return alerts


@router.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket, external_id: str = Query(...)):
    """WebSocket 端點，用於接收施工通知推送"""
    await websocket.accept()
    
    # 驗證用戶
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.external_id == external_id).first()
        if not user:
            await websocket.close(code=1008, reason="User not found")
            return
        
        user_id = user.id
        
        # 儲存連接
        if external_id in active_connections:
            # 如果已有連接，關閉舊的
            try:
                await active_connections[external_id].close()
            except:
                pass
        
        active_connections[external_id] = websocket
        logger.info(f"WebSocket connected: external_id={external_id}, user_id={user_id}")
        
        # 發送連接成功訊息
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connection established",
            "user_id": user_id
        })
        
        # 保持連接並處理訊息
        try:
            while True:
                # 接收客戶端訊息（用於心跳或控制）
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except:
                    pass
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: external_id={external_id}")
        finally:
            # 清理連接
            if external_id in active_connections and active_connections[external_id] == websocket:
                del active_connections[external_id]
            db.close()
    except Exception as e:
        logger.error(f"WebSocket error for external_id={external_id}: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
        db.close()


async def send_construction_alert(external_id: str, alerts: list[dict]):
    """向指定用戶發送施工警報"""
    if external_id not in active_connections:
        return False
    
    websocket = active_connections[external_id]
    try:
        await websocket.send_json({
            "type": "construction_alert",
            "alerts": alerts,
            "timestamp": datetime.now().isoformat()
        })
        return True
    except Exception as e:
        logger.error(f"Failed to send alert to {external_id}: {e}")
        # 連接可能已斷開，清理
        if external_id in active_connections:
            del active_connections[external_id]
        return False


async def check_and_notify_all_users():
    """檢查所有在線用戶的收藏地點並發送通知"""
    if not active_connections:
        logger.debug("No active WebSocket connections, skipping check")
        return
    
    logger.info(f"Checking notifications for {len(active_connections)} online users")
    
    db = SessionLocal()
    try:
        # 獲取所有在線用戶的 external_id 和對應的 user_id
        online_users = []
        for external_id in list(active_connections.keys()):
            user = db.query(models.User).filter(models.User.external_id == external_id).first()
            if user:
                online_users.append((external_id, user.id))
            else:
                logger.warning(f"User with external_id={external_id} not found in database")
        
        logger.info(f"Found {len(online_users)} valid online users")
        
        for external_id, user_id in online_users:
            try:
                alerts = check_construction_near_favorites(user_id, db)
                if alerts:
                    success = await send_construction_alert(external_id, alerts)
                    if success:
                        logger.info(f"✓ Successfully sent {len(alerts)} alerts to user {external_id} (user_id={user_id})")
                    else:
                        logger.warning(f"✗ Failed to send alerts to user {external_id} (user_id={user_id})")
                else:
                    logger.debug(f"No alerts for user {external_id} (user_id={user_id})")
            except Exception as e:
                logger.error(f"Error checking user {external_id} (user_id={user_id}): {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Error in check_and_notify_all_users: {e}", exc_info=True)
    finally:
        db.close()

