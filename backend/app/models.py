from sqlalchemy import Column, Integer, String, Boolean, Float, JSON, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    external_id = Column(String(255), nullable=True, unique=True, index=True)  # Flutter Account.id (UUID)


class TestRecord(Base):
    __tablename__ = "test_records"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)


class RoadSegment(Base):
    __tablename__ = "road_segments"

    id = Column(Integer, primary_key=True, index=True)
    osmid = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=True, index=True)
    highway = Column(String(50), nullable=True, index=True)
    lanes = Column(String(50), nullable=True)
    oneway = Column(Boolean, nullable=True)
    length_m = Column(Float, nullable=True)
    properties = Column(JSON, nullable=True)
    geometry = Column(JSON, nullable=False)

class ConstructionNotice(Base):
    __tablename__ = "construction_notices"
    id = Column(Integer, primary_key=True, index=True)
    start_date = Column(Date, nullable=True)  # 起始日期
    end_date = Column(Date, nullable=True)    # 結束日期
    name = Column(String(500), nullable=False) # 工程名稱
    type = Column(String(200), nullable=True)  # 工程類型
    unit = Column(String(200), nullable=True)  # 執行單位
    road = Column(String(500), nullable=True)  # 道路/地點
    url = Column(String(1000), nullable=True)  # 詳細資訊連結
    geometry = Column(JSON, nullable=True)     # GeoJSON 格式的幾何資料（Point 點座標）

class Favorite(Base):
    __tablename__ = "favorites"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 基本欄位
    type = Column(String(20), nullable=False)  # 'place', 'road', 'route'
    name = Column(String(500), nullable=False)
    address = Column(String(1000), nullable=True)
    lon = Column(Float, nullable=True)  # 經度
    lat = Column(Float, nullable=True)  # 緯度
    
    # 地點類型 (place) 的額外欄位
    # 使用 JSON 存儲地點的完整信息（如 id, name, addr 等）
    place_data = Column(JSON, nullable=True)
    
    # 道路類型 (road) 的欄位
    road_name = Column(String(500), nullable=True)
    road_search_name = Column(String(500), nullable=True)
    road_osmids = Column(JSON, nullable=True)  # 存儲 osmid 數組
    road_distance_threshold = Column(Float, nullable=True, default=15.0)  # 預設 15 公尺
    
    # 路線類型 (route) 的欄位
    route_start = Column(String(500), nullable=True)
    route_end = Column(String(500), nullable=True)
    route_start_coords = Column(JSON, nullable=True)  # {lon, lat}
    route_end_coords = Column(JSON, nullable=True)  # {lon, lat}
    route_distance = Column(Float, nullable=True)  # 路線距離（公尺）
    route_duration = Column(Float, nullable=True)  # 路線時間（秒）
    route_feature_collection = Column(JSON, nullable=True)  # GeoJSON FeatureCollection
    route_distance_threshold = Column(Float, nullable=True, default=50.0)  # 預設 50 公尺
    
    # 施工資訊（收藏時收集的附近施工點）
    recommendations = Column(JSON, nullable=True)  # 存儲施工資訊數組
    
    # 通知相關欄位
    notification_enabled = Column(Boolean, nullable=False, default=False)
    distance_threshold = Column(Float, nullable=False, default=100.0)  # 通知距離閾值（公尺），預設 100m
    
    # 時間戳
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)