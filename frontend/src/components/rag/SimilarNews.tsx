import { useState, useEffect } from 'react';
import { newsAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { ExternalLink, Sparkles, Loader2, ChevronDown, ChevronUp } from 'lucide-react';

interface SimilarNewsItem {
  id: number;
  title: string;
  summary: string;
  url: string;
  source: string | null;
  published_at: string | null;
  similarity_score: number;
  matched_keywords: string[];
}

interface SimilarNewsProps {
  newsId: number;
  onNewsClick?: (newsId: number) => void;
}

export function SimilarNews({ newsId, onNewsClick }: SimilarNewsProps) {
  const [similarNews, setSimilarNews] = useState<SimilarNewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);

  useEffect(() => {
    // 只有展开时才加载数据
    if (isExpanded && !hasLoaded) {
      loadSimilarNews();
    }
  }, [isExpanded, newsId]);

  const loadSimilarNews = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await newsAPI.getSimilarNews(newsId, 5);
      setSimilarNews(response.data.similar_news || []);
      setHasLoaded(true);
    } catch (err: any) {
      console.error('Failed to load similar news:', err);
      setError(err.response?.data?.detail || '加载相似新闻失败');
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  // 格式化相似度分数
  const formatSimilarity = (score: number) => {
    return `${Math.round(score * 100)}%`;
  };

  // 获取相似度颜色
  const getSimilarityColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600 dark:text-green-400';
    if (score >= 0.6) return 'text-blue-600 dark:text-blue-400';
    return 'text-slate-500 dark:text-slate-400';
  };

  return (
    <div className="mt-4 border-t border-slate-200 dark:border-slate-700 pt-4">
      <Button
        variant="ghost"
        size="sm"
        onClick={toggleExpand}
        className="w-full flex items-center justify-between text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
      >
        <span className="flex items-center gap-2">
          <Sparkles className="h-4 w-4" />
          <span className="text-sm font-medium">相关推荐</span>
        </span>
        {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </Button>

      {isExpanded && (
        <div className="mt-3 space-y-3">
          {loading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span className="ml-2 text-sm text-slate-500">正在查找相关新闻...</span>
            </div>
          ) : error ? (
            <p className="text-sm text-red-500 dark:text-red-400 text-center py-4">{error}</p>
          ) : similarNews.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-4">
              暂无相关新闻推荐
            </p>
          ) : (
            similarNews.map((item) => (
              <div
                key={item.id}
                className="group p-3 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors cursor-pointer"
                onClick={() => onNewsClick?.(item.id)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <h5 className="text-sm font-medium text-slate-900 dark:text-slate-100 line-clamp-2 group-hover:text-primary transition-colors">
                      {item.title}
                    </h5>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                      {item.summary}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      {item.source && (
                        <span className="text-xs text-slate-400">{item.source}</span>
                      )}
                      {item.matched_keywords.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {item.matched_keywords.slice(0, 3).map((keyword, idx) => (
                            <span
                              key={idx}
                              className="px-1.5 py-0.5 text-xs rounded bg-primary/10 text-primary"
                            >
                              {keyword}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2 flex-shrink-0">
                    <span className={`text-xs font-medium ${getSimilarityColor(item.similarity_score)}`}>
                      {formatSimilarity(item.similarity_score)}
                    </span>
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="text-primary hover:text-primary/80"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default SimilarNews;
