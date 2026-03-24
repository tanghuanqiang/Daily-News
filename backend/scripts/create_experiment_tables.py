#!/usr/bin/env python3
"""
创建A/B测试平台相关数据库表
- experiments: 实验配置表
- experiment_variants: 实验版本表
- user_experiment_assignments: 用户实验分配表
- experiment_results: 实验结果表
- experiment_events: 实验事件表
"""

import sys
import os
from pathlib import Path

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database import engine, Base
from models import Experiment, ExperimentVariant, UserExperimentAssignment, ExperimentResult, ExperimentEvent
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_experiment_tables():
    """创建A/B测试平台相关表"""
    try:
        logger.info("开始创建A/B测试平台数据库表...")
        
        # 创建所有表（只创建不存在的表）
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ 数据库表创建成功！")
        logger.info("  - experiments (实验配置表)")
        logger.info("  - experiment_variants (实验版本表)")
        logger.info("  - user_experiment_assignments (用户实验分配表)")
        logger.info("  - experiment_results (实验结果表)")
        logger.info("  - experiment_events (实验事件表)")
        
        return True
        
    except Exception as e:
        logger.error(f"创建数据库表失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = create_experiment_tables()
    if success:
        logger.info("\n🎉 A/B测试平台数据库表创建完成！")
        logger.info("\n下一步：")
        logger.info("1. 实现实验分流算法")
        logger.info("2. 实现实验配置管理")
        logger.info("3. 实现结果统计服务")
        logger.info("4. 创建实验结果仪表板")
    else:
        logger.error("\n❌ 数据库表创建失败")
        sys.exit(1)
