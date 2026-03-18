import { useState, useEffect } from 'react';
import { newsAPI } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  ExternalLink, 
  Sparkles, 
  Loader2, 
  RefreshCw, 
  Wand2,
  TrendingUp,
  Clock
} from 'lucide-react';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface PersonalizedNewsItem {
  id: number;
  title: string;
  summary: string;
  url: string;
  source: string | null;
  image_url: string | null;
  published_at: string | null;
  relevance_score: number;
  recommendation_reason: string;
  matched_topics: string[];
}

interface PersonalizedFeedProps {
  onNewsClick?: (newsId: number) => void;
  refreshTrigger?: number; // 用于触发刷新
}

export function PersonalizedFeed({ onNewsClick, refreshTrigger }: PersonalizedFeedProps) {
  const [recommendations, setRecommendations] = useState<PersonalizedNewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    loadRecommendations();
  }, [refreshTrigger]);

  const loadRecommendations = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await newsAPI.getPersonalizedRecommendations(10);
      setRecommendations(response.data.recommendations || []);
      setLastUpdated(new Date());
    } catch (err: any) {
      console.error('Failed to load personalized recommendations:', err);
      setError(err.response?.data?.detail || '加载个性化推荐失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取推荐原因图标
  const getReasonIcon = (reason: string) => {
    if (reason.includes('兴趣') || reason.includes('偏好')) {
      return <Wand2 className="h-3 w-3" />;
    }
    if (reason.includes('热度') || reason.includes('趋势')) {
      return <TrendingUp className="h-3 w-3" />;
    }
    if (reason.includes('时间') || reason.includes('最新')) {
      return <Clock className="h-3 w-3" />;
    }
    return <Sparkles className="h-3 w-3" />;
  };

  // 格式化相关度分数
  const formatRelevance = (score: number) => {
    if (score >= 0.8) return '高度相关';
    if (score >= 0.6) return '较为相关';
    return '可能感兴趣';
  };

  // 获取相关度颜色类
  const getRelevanceClass = (score: number) => {
    if (score >= 0.8) return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300';
    if (score >= 0.6) return 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300';
    return 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400';
  };

  if (loading && recommendations.length === 0) {
    return (
      <Card className="border-slate-200 dark:border-slate-700">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
              <Sparkles className="h-5 w-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <CardTitle className="text-lg">为你推荐</CardTitle>
              <CardDescription>基于您的阅读兴趣智能推荐</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <span className="ml-2 text-sm text-slate-500">正在分析您的兴趣...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error && recommendations.length === 0) {
    return (
      <Card className="border-slate-200 dark:border-slate-700">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
              <Sparkles className="h-5 w-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <CardTitle className="text-lg">为你推荐</CardTitle>
              <CardDescription>基于您的阅读兴趣智能推荐</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <p className="text-sm text-red-500 dark:text-red-400 mb-3">{error}</p>
            <Button variant="outline" size="sm" onClick={loadRecommendations}>
              <RefreshCw className="h-4 w-4 mr-2" />
              重试
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (recommendations.length === 0) {
    return (
      <Card className="border-slate-200 dark:border-slate-700">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
              <Sparkles className="h-5 w-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <CardTitle className="text-lg">为你推荐</CardTitle>
              <CardDescription>基于您的阅读兴趣智能推荐</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              开始阅读新闻，我们将为您推荐更多相关内容
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-slate-200 dark:border-slate-700">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
              <Sparkles className="h-5 w-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <CardTitle className="text-lg">为你推荐</CardTitle>
              <CardDescription className="text-xs">
                {lastUpdated && `更新于 ${format(lastUpdated, 'HH:mm', { locale: zhCN })}`}
              </CardDescription>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={loadRecommendations}
            disabled={loading}
            className="h-8 w-8"
            title="刷新推荐"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {recommendations.slice(0, 5).map((item) => (
          <div
            key={item.id}
            className="group p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 hover:border-purple-300 dark:hover:border-purple-700 hover:shadow-sm transition-all cursor-pointer"
            onClick={() => onNewsClick?.(item.id)}
          >
            <div className="flex gap-3">
              {item.image_url && (
                <img
                  src={item.image_url}
                  alt={item.title}
                  className="w-16 h-16 object-cover rounded-lg flex-shrink-0"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none';
                  }}
                />
              )}
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-medium text-slate-900 dark:text-slate-100 line-clamp-2 group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">
                  {item.title}
                </h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                  {item.summary}
                </p>
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${getRelevanceClass(item.relevance_score)}`}>
                    {getReasonIcon(item.recommendation_reason)}
                    {formatRelevance(item.relevance_score)}
                  </span>
                  {item.matched_topics.slice(0, 2).map((topic, idx) => (
                    <span
                      key={idx}
                      className="px-1.5 py-0.5 text-xs rounded bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex-shrink-0">
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="text-slate-400 hover:text-primary transition-colors"
                >
                  <ExternalLink className="h-4 w-4" />
                </a>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default PersonalizedFeed;
