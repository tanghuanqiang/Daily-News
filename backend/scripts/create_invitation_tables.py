#!/usr/bin/env python3
"""
创建邀请系统相关数据库表
- invitation_codes: 邀请码表
- user_invitation_stats: 用户邀请统计表
"""

import sys
import os
from pathlib import Path

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database import engine, Base
from models import InvitationCode, UserInvitationStats
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_invitation_tables():
    """创建邀请系统相关表"""
    try:
        logger.info("开始创建邀请系统数据库表...")
        
        # 创建所有表（只创建不存在的表）
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ 数据库表创建成功！")
        logger.info("  - invitation_codes (邀请码表)")
        logger.info("  - user_invitation_stats (用户邀请统计表)")
        
        return True
        
    except Exception as e:
        logger.error(f"创建数据库表失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = create_invitation_tables()
    if success:
        logger.info("\n🎉 邀请系统数据库表创建完成！")
        logger.info("\n下一步：")
        logger.info("1. 实现邀请码生成API")
        logger.info("2. 实现邀请码使用逻辑")
        logger.info("3. 集成邀请奖励到成就系统")
    else:
        logger.error("\n❌ 数据库表创建失败")
        sys.exit(1)
