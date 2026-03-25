from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from models import (
    NewsCache,
    ShareTemplateResponse,
    User
)
from auth import get_current_active_user
from services.achievement_service import check_and_unlock_achievements
from pydantic import BaseModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/share", tags=["Sharing"])


# Pydantic model for share generation
class ShareGenerationRequest(BaseModel):
    news_id: int
    platform: str = 'copy'
    use_roast_mode: bool = False

# 分享模板配置
SHARE_TEMPLATES = {
    'wechat': {
        'text': '刚刚看到一条有意思的新闻：{summary}\n\n来源：{source} | 查看详情：{url}',
        'platform': 'wechat'
    },
    'weibo': {
        'text': '#{topic}# {summary}\n\nvia Daily-News AI\n{url}',
        'platform': 'weibo'
    },
    'twitter': {
        'text': '📰 {summary}\n\nSource: {source}\n{url}\n\n#DailyNews #AI',
        'platform': 'twitter'
    },
    'copy': {
        'text': '新闻：{title}\n\n摘要：{summary}\n\n来源：{source}\n查看详情：{url}',
        'platform': 'copy'
    }
}


@router.post("/generate", response_model=ShareTemplateResponse)
async def generate_share_content(
    request: ShareGenerationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    生成优化的分享文案
    
    Args:
        request: 分享生成请求（包含 news_id, platform, use_roast_mode）
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        分享文案
    """
    news_id = request.news_id
    platform = request.platform
    use_roast_mode = request.use_roast_mode
    try:
        # 验证平台
        if platform not in SHARE_TEMPLATES:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的平台。支持的平臺: {', '.join(SHARE_TEMPLATES.keys())}"
            )
        
        # 获取新闻
        news = db.query(NewsCache).filter(NewsCache.id == news_id).first()
        if not news:
            raise HTTPException(
                status_code=404,
                detail="新闻不存在"
            )
        
        # 选择摘要（正常模式或吐槽模式）
        summary = news.summary_roast if (use_roast_mode and news.summary_roast) else news.summary
        
        # 获取模板
        template = SHARE_TEMPLATES[platform]
        
        # 生成分享文案
        share_text = template['text'].format(
            title=news.title,
            summary=summary,
            source=news.source or 'Daily-News',
            url=news.url,
            topic=news.topic
        )
        
        # 根据不同平台调整文案长度
        if platform == 'twitter':
            # Twitter有280字符限制，需要截断
            max_length = 280
            if len(share_text) > max_length:
                # 保留URL，截断摘要
                available_length = max_length - len(news.url) - 50  # 50是给其他固定文本的预留
                truncated_summary = summary[:available_length] + '…'
                share_text = template['text'].format(
                    title=news.title,
                    summary=truncated_summary,
                    source=news.source or 'Daily-News',
                    url=news.url,
                    topic=news.topic
                )
        
        logger.info(f"用户 {current_user.email} 生成分享文案，新闻: {news_id}, 平台: {platform}")
        
        return {
            "text": share_text,
            "url": news.url,
            "platform": platform
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成分享文案失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"生成分享文案失败: {str(e)}"
        )


@router.get("/platforms")
async def get_supported_platforms():
    """
    获取支持的分享平台列表
    
    Returns:
        平台列表
    """
    return {
        "platforms": [
            {
                "key": "wechat",
                "name": "微信",
                "icon": "💬"
            },
            {
                "key": "weibo",
                "name": "微博",
                "icon": "📝"
            },
            {
                "key": "twitter",
                "name": "Twitter",
                "icon": "🐦"
            },
            {
                "key": "copy",
                "name": "复制链接",
                "icon": "📋"
            }
        ]
    }


@router.post("/track")
async def track_share(
    news_id: int,
    platform: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    记录分享行为（用于统计和成就解锁）
    
    Args:
        news_id: 新闻ID
        platform: 分享平台
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        成功消息和解锁的成就
    """
    try:
        # 成就检测 - 分享相关成就
        unlocked_achievements = []
        try:
            unlocked = check_and_unlock_achievements(
                user_id=current_user.id,
                trigger_type='share',
                news_id=news_id,
                db=db
            )
            if unlocked:
                unlocked_achievements = unlocked
        except Exception as e:
            logger.error(f"成就检测失败: {str(e)}")
        
        logger.info(f"用户 {current_user.email} 分享新闻 {news_id} 到 {platform}")
        
        return {
            "message": "分享已记录",
            "news_id": news_id,
            "platform": platform,
            "unlocked_achievements": unlocked_achievements
        }
        
    except Exception as e:
        logger.error(f"记录分享失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"记录分享失败: {str(e)}"
        )
