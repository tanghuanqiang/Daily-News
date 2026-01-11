import requests
import feedparser
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from database import settings
import logging
import hashlib
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsFetcher:
    """Multi-source news fetcher with fallback support"""
    
    def __init__(self, custom_rss_feeds: List[Dict] = None):
        self.gnews_api_key = settings.GNEWS_API_KEY
        self.newsdata_api_key = settings.NEWSDATA_API_KEY
        
        # RSS Feed sources as fallback
        self.rss_feeds = {
            "科技": [
                "https://www.theverge.com/rss/index.xml",
                "https://techcrunch.com/feed/",
                "https://www.wired.com/feed/rss",
                "https://www.engadget.com/rss.xml",
            ],
            "AI": [
                "https://www.artificialintelligence-news.com/feed/",
                "https://www.technologyreview.com/feed/",
                "https://www.vox.com/rss/index.xml",
                "https://www.reddit.com/r/artificial.rss",
            ],
            "财经": [
                "https://www.economist.com/business/rss.xml",
                "https://www.marketwatch.com/rss/topstories",
                "https://finance.yahoo.com/rss/topstories",
                "https://www.bloomberg.com/feeds/news.rss",
            ],
            "股市": [
                "https://finance.yahoo.com/rss/finance/rssindex",
                "https://www.cnbc.com/id/100003114/device/rss/rss.html",
            ],
            "国际时事": [
                "https://feeds.bbci.co.uk/news/world/rss.xml",
                "https://www.nytimes.com/svc/collections/v1/publish/https://www.nytimes.com/section/world/rss.xml",
                "https://www.reddit.com/r/worldnews.rss",
                "https://www.vox.com/rss/index.xml",
            ],
            "国际": [
                "https://feeds.bbci.co.uk/news/world/rss.xml",
                "https://www.reddit.com/r/worldnews.rss",
            ],
            "科学": [
                "https://www.nature.com/nature.rss",
                "https://www.science.org/rss/news_current.xml",
                # removed unstable scientificamerican feed, keep Nature/Science/ScienceDaily
                "https://www.sciencedaily.com/rss/all.xml",
            ],
            "娱乐": [
                "https://www.theguardian.com/uk/culture/rss",
                "https://www.indiewire.com/feed/rss",
                "https://www.variety.com/feed/",
            ],
            "体育": [
                "https://www.espn.com/espn/rss/news",
                "https://feeds.bbci.co.uk/sport/rss.xml",
                "https://sports.yahoo.com/rss/",
                "https://www.cbssports.com/rss/headlines/",
            ],
            "搞笑": [
                "https://www.theonion.com/rss",
                "https://www.boredpanda.com/feed/",
                "https://www.cheezburger.com/rss",
            ],
            "奇闻": [
                "https://nypost.com/feed/",
                "https://www.mirror.co.uk/news/rss.xml",
                "https://www.telegraph.co.uk/news/rss.xml",
                "https://www.nytimes.com/services/xml/rss/nyt/HomePage.xml",
            ],
            # 中文技术/编程/开发者社区（强烈推荐）- 每个RSS源作为独立主题
            "阮一峰的网络日志": [
                "https://www.ruanyifeng.com/blog/atom.xml",
            ],
            "酷壳 CoolShell": [
                "https://coolshell.cn/feed",
            ],
            "美团技术团队": [
                "https://tech.meituan.com/feed",
            ],
            "少数派（数字生产力）": [
                "https://sspai.com/feed",
            ],
            "玉伯的博客/蚂蚁体验": [
                "https://www.yuque.com/yubo/blog/rss",
            ],
            "粥里有勺糖": [
                "https://www.zhihu.com/people/shao-nian-ge-xing-68-13/posts/rss",
            ],
            "黑泽的博客": [
                "https://heizex.com/feed",
            ],
            "独立开发者周刊": [
                "https://indiehackers.feeds.cn/rss",
            ]
        }
        
        # Add custom RSS feeds if provided
        if custom_rss_feeds:
            for feed in custom_rss_feeds:
                if feed.get('is_active'):
                    topic = feed.get('topic')
                    feed_url = feed.get('feed_url')
                    if topic and feed_url:
                        if topic not in self.rss_feeds:
                            self.rss_feeds[topic] = []
                        if feed_url not in self.rss_feeds[topic]:
                            self.rss_feeds[topic].append(feed_url)
    
    def fetch_news(self, topic: str, max_articles: int = 8) -> List[Dict]:
        """
        Fetch news for a topic from multiple sources
        Returns list of news items with title, url, source, published_at, content
        """
        articles = []
        
        # Try GNews API first
        if self.gnews_api_key and self.gnews_api_key != "":
            try:
                articles = self._fetch_from_gnews(topic, max_articles)
                if articles:
                    logger.info(f"Fetched {len(articles)} articles from GNews for topic: {topic}")
                    return articles
            except Exception as e:
                logger.error(f"GNews API error for {topic}: {str(e)}")
        
        # Try NewsData.io API
        if self.newsdata_api_key and self.newsdata_api_key != "":
            try:
                articles = self._fetch_from_newsdata(topic, max_articles)
                if articles:
                    logger.info(f"Fetched {len(articles)} articles from NewsData for topic: {topic}")
                    return articles
            except Exception as e:
                logger.error(f"NewsData API error for {topic}: {str(e)}")
        
        # Fallback to RSS feeds
        try:
            articles = self._fetch_from_rss(topic, max_articles)
            if articles:
                logger.info(f"Fetched {len(articles)} articles from RSS for topic: {topic}")
                return articles
        except Exception as e:
            logger.error(f"RSS fetch error for {topic}: {str(e)}")
        
        # If all sources fail, return a default article
        logger.warning(f"No articles found for topic: {topic}, returning default article")
        return [{
            "title": f"暂无{topic}相关新闻",
            "url": "",
            "source": "系统消息",
            "published_at": datetime.now(),
            "content": f"我们正在努力为您获取{topic}相关新闻，请稍后刷新重试。",
            "image_url": None
        }]
    
    def _fetch_from_gnews(self, topic: str, max_articles: int) -> List[Dict]:
        """Fetch from GNews API"""
        url = "https://gnews.io/api/v4/search"
        params = {
            "q": topic,
            "lang": "zh",  # Chinese, change to "en" for English
            "country": "cn",  # China, change to "us" for USA
            "max": max_articles,
            "apikey": self.gnews_api_key,
            "sortby": "publishedAt"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for item in data.get("articles", [])[:max_articles]:
                articles.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "source": item.get("source", {}).get("name", "GNews"),
                    "published_at": self._parse_datetime(item.get("publishedAt")),
                    "content": item.get("description", ""),
                    "image_url": item.get("image")
                })
            return articles
        except Exception as e:
            logger.error(f"GNews fetch error: {str(e)}")
            return []
    
    def _fetch_from_newsdata(self, topic: str, max_articles: int) -> List[Dict]:
        """Fetch from NewsData.io API"""
        url = "https://newsdata.io/api/1/news"
        params = {
            "apikey": self.newsdata_api_key,
            "q": topic,
            "language": "zh,en",
            "size": max_articles
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for item in data.get("results", [])[:max_articles]:
                articles.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "source": item.get("source_id", "NewsData"),
                    "published_at": self._parse_datetime(item.get("pubDate")),
                    "content": item.get("description", "") or item.get("content", ""),
                    "image_url": item.get("image_url")
                })
            return articles
        except Exception as e:
            logger.error(f"NewsData fetch error: {str(e)}")
            return []
    
    def _generate_entry_id(self, feed_url: str, entry) -> str:
        """Generate unique entry ID from feed_url + guid/link"""
        # Try guid first, then link, then id
        guid = entry.get("id") or entry.get("guid") or entry.get("link", "")
        
        if not guid:
            # Last resort: use title + url hash
            title = entry.get("title", "")
            url = entry.get("link", "")
            guid = f"{title}:{url}"
        
        # Create hash from feed_url + guid
        combined = f"{feed_url}:{guid}"
        entry_id = hashlib.sha256(combined.encode('utf-8')).hexdigest()
        return entry_id
    
    def _fetch_from_rss(self, topic: str, max_articles: int) -> List[Dict]:
        """Fetch from RSS feeds (fallback)"""
        articles = []
        
        # Find relevant RSS feeds for the topic
        feeds = self.rss_feeds.get(topic, [])
        
        # If no exact match, use all feeds and filter by keyword
        if not feeds:
            feeds = [feed for feed_list in self.rss_feeds.values() for feed in feed_list]
        
        # Try all feeds, not just the first 3
        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                if not hasattr(feed, 'entries') or not feed.entries:
                    continue
                
                for entry in feed.entries[:max_articles]:
                    # Don't filter by topic keyword, keep all articles
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    
                    # Skip empty articles
                    if not title and not summary:
                        continue
                    
                    # Generate unique entry ID
                    entry_id = self._generate_entry_id(feed_url, entry)
                    
                    articles.append({
                        "title": title,
                        "url": entry.get("link", ""),
                        "source": feed.feed.get("title", "RSS Feed"),
                        "published_at": self._parse_datetime(entry.get("published")),
                        "content": summary,
                        "image_url": self._extract_image_from_entry(entry),
                        "entry_id": entry_id,  # Add entry_id for RSS articles
                        "feed_url": feed_url  # Add feed_url for tracking
                    })
                    
                    if len(articles) >= max_articles:
                        break
                
                if len(articles) >= max_articles:
                    break
                    
            except Exception as e:
                logger.error(f"RSS feed error for {feed_url}: {str(e)}")
                continue
        
        # If still no articles, use a default article
        if not articles:
            articles.append({
                "title": f"暂无{topic}相关新闻",
                "url": "",
                "source": "系统消息",
                "published_at": datetime.now(),
                "content": f"我们正在努力为您获取{topic}相关新闻，请稍后刷新重试。",
                "image_url": None,
                "entry_id": None,  # Default article has no entry_id
                "feed_url": None
            })
        
        return articles[:max_articles]
    
    def _extract_image_from_entry(self, entry) -> Optional[str]:
        """Extract image URL from RSS entry"""
        # Try media:content
        if hasattr(entry, 'media_content') and entry.media_content:
            return entry.media_content[0].get('url')
        
        # Try media:thumbnail
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            return entry.media_thumbnail[0].get('url')
        
        # Try enclosures
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if 'image' in enclosure.get('type', ''):
                    return enclosure.get('url')
        
        return None
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse various datetime formats"""
        if not date_str:
            return None
        
        try:
            # ISO format (GNews)
            if 'T' in date_str and 'Z' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
            # Try common formats
            from dateutil import parser
            return parser.parse(date_str)
        except:
            return None


# Deduplicate articles by URL
def deduplicate_articles(articles: List[Dict]) -> List[Dict]:
    """Remove duplicate articles based on URL"""
    seen_urls = set()
    unique_articles = []
    
    for article in articles:
        url = article.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)
    
    return unique_articles
