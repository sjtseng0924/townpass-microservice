from __future__ import annotations

import sys
from pathlib import Path

# When this script is executed directly (python scripts/init_default_user.py)
# the package root (backend/) may not be on sys.path. Ensure the project
# root is first on sys.path so `from app.config import settings` resolves.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.database import SessionLocal
from app.models import User


def init_default_user():
    """初始化預設使用者"""
    default_external_id = "7f3562f4-bb3f-4ec7-89b9-da3b4b5ff250"
    default_name = "Default User"
    
    db = SessionLocal()
    try:
        # 檢查是否已存在
        existing_user = db.query(User).filter(User.external_id == default_external_id).first()
        
        if existing_user:
            print(f"✅ 預設使用者已存在 (id: {existing_user.id}, external_id: {existing_user.external_id})")
            return True
        
        # 創建新使用者
        default_user = User(
            name=default_name,
            external_id=default_external_id
        )
        db.add(default_user)
        db.commit()
        db.refresh(default_user)
        
        print(f"預設使用者創建成功 (id: {default_user.id}, external_id: {default_user.external_id})")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"創建預設使用者失敗: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = init_default_user()
    sys.exit(0 if success else 1)

