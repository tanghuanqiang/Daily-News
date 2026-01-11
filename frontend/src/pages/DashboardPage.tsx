import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { newsAPI, preferencesAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { RefreshCw, Settings, LogOut, Moon, Sun, Loader2, ExternalLink, Newspaper, Sparkles, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { useToast } from '@/components/ui/use-toast';

interface NewsItem {
  id: number;
  title: string;
  summary: string;
  summary_roast: string | null;
  url: string;
  source: string | null;
  image_url: string | null;
  published_at: string | null;
  date: string;
  is_read?: boolean;  // 用户是否已读
}

interface TopicNews {
  topic: string;
  news_items: NewsItem[];
  last_updated: string;
  roast_mode: boolean;
}

interface RefreshResult {
  topic: string;
  status: 'refreshing' | 'skipped' | 'completed' | 'failed';
  reason?: string;
  message?: string;
  remaining_seconds?: number;
  last_refreshed_at?: string;
}

export default function DashboardPage() {
  const [topics, setTopics] = useState<TopicNews[]>([]);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshStatus, setRefreshStatus] = useState<RefreshResult[]>([]);
  const [darkMode, setDarkMode] = useState(false);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const refreshToastRef = useRef<{ id: string; update: (props: any) => void; dismiss: () => void } | null>(null);
  
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const { toast } = useToast();

  useEffect(() => {
    loadDashboard();
    
    // Check dark mode preference
    if (localStorage.getItem('darkMode') === 'true') {
      setDarkMode(true);
      document.documentElement.classList.add('dark');
    }

    // Cleanup polling on unmount
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const loadDashboard = async () => {
    try {
      setLoading(true);
      const response = await newsAPI.getDashboard();
      setTopics(response.data.topics || []);
      if (response.data.last_global_update) {
        setLastUpdate(new Date(response.data.last_global_update));
      }
    } catch (error) {
      console.error('Failed to load dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const checkRefreshStatus = async () => {
    try {
      const response = await newsAPI.getRefreshStatus();
      const statuses = response.data.topics || [];
      
      // Update refresh status
      const currentStatus: RefreshResult[] = statuses.map((s: any) => ({
        topic: s.topic,
        status: s.is_refreshing ? 'refreshing' : (s.last_refreshed_at ? 'completed' : 'pending'),
        last_refreshed_at: s.last_refreshed_at,
      }));

      setRefreshStatus(currentStatus);

      // Check if all topics are completed
      const allCompleted = currentStatus.every(s => s.status !== 'refreshing');
      if (allCompleted && currentStatus.length > 0) {
        // Stop polling
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        
        // Reload dashboard data directly (without full page reload)
        try {
          const response = await newsAPI.getDashboard();
          setTopics(response.data.topics || []);
          if (response.data.last_global_update) {
            setLastUpdate(new Date(response.data.last_global_update));
          }
        } catch (error) {
          console.error('Failed to reload dashboard:', error);
        }
        
        // Update toast
        if (refreshToastRef.current) {
          const completedCount = currentStatus.filter(s => s.status === 'completed').length;
          const skippedCount = currentStatus.filter(s => s.status === 'skipped').length;
          
          refreshToastRef.current.update({
            title: '刷新完成',
            description: `成功刷新 ${completedCount} 个主题${skippedCount > 0 ? `，跳过 ${skippedCount} 个主题` : ''}`,
            variant: 'success',
          });
          
          // Dismiss after 1 second
          setTimeout(() => {
            refreshToastRef.current?.dismiss();
            refreshToastRef.current = null;
          }, 1000);
        }
        
        setRefreshing(false);
      }
    } catch (error) {
      console.error('Failed to check refresh status:', error);
    }
  };

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      
      // Show initial toast
      const initialToast = toast({
        title: '开始刷新',
        description: '正在刷新新闻，请稍候...',
        variant: 'info',
        duration: 1000000, // Long duration, will be manually dismissed
      });
      refreshToastRef.current = initialToast;
      
      // Trigger refresh
      const response = await newsAPI.refresh();
      const results = response.data.results || [];
      
      // Update status
      const initialStatus: RefreshResult[] = results.map((r: any) => ({
        topic: r.topic,
        status: r.status === 'refreshing' ? 'refreshing' : 'skipped',
        reason: r.reason,
        message: r.message,
        remaining_seconds: r.remaining_seconds,
      }));
      setRefreshStatus(initialStatus);
      
      // Count refreshing topics
      const refreshingTopics = results.filter((r: any) => r.status === 'refreshing');
      const skippedTopics = results.filter((r: any) => r.status === 'skipped');
      
      if (refreshingTopics.length > 0) {
        // Update toast with topic list
        initialToast.update({
          title: `正在刷新 ${refreshingTopics.length} 个主题`,
          description: refreshingTopics.map((r: any) => r.topic).join('、'),
          variant: 'info',
        });
        
        // Start polling for status updates
        pollingIntervalRef.current = setInterval(checkRefreshStatus, 5000); // Poll every 5 seconds
      } else {
        // All skipped
        initialToast.update({
          title: '刷新跳过',
          description: `所有主题在最近刷新过，已跳过 ${skippedTopics.length} 个主题`,
          variant: 'info',
        });
        
        setTimeout(() => {
          initialToast.dismiss();
          refreshToastRef.current = null;
        }, 1000);
        
        setRefreshing(false);
        // Reload dashboard data directly
        try {
          const response = await newsAPI.getDashboard();
          setTopics(response.data.topics || []);
          if (response.data.last_global_update) {
            setLastUpdate(new Date(response.data.last_global_update));
          }
        } catch (error) {
          console.error('Failed to reload dashboard:', error);
        }
      }
    } catch (error: any) {
      console.error('Failed to refresh:', error);
      
      if (refreshToastRef.current) {
        refreshToastRef.current.update({
          title: '刷新失败',
          description: error.response?.data?.detail || '刷新失败，请稍后重试',
          variant: 'destructive',
        });
        
        setTimeout(() => {
          refreshToastRef.current?.dismiss();
          refreshToastRef.current = null;
        }, 1000);
      }
      
      setRefreshing(false);
    }
  };

  const toggleDarkMode = () => {
    const newMode = !darkMode;
    setDarkMode(newMode);
    localStorage.setItem('darkMode', String(newMode));
    
    if (newMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleNewsClick = async (item: NewsItem) => {
    // Mark as read when user clicks on news item
    if (!item.is_read) {
      try {
        await preferencesAPI.markRead(item.id);
        // Update local state
        setTopics(prevTopics => 
          prevTopics.map(topic => ({
            ...topic,
            news_items: topic.news_items.map(news => 
              news.id === item.id ? { ...news, is_read: true } : news
            )
          }))
        );
      } catch (error) {
        console.error('Failed to mark news as read:', error);
      }
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-slate-600 dark:text-slate-400">加载中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Header - Mobile Optimized */}
      <header className="sticky top-0 z-50 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-b border-slate-200 dark:border-slate-700 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className="p-2 rounded-lg bg-primary/10 dark:bg-primary/20">
                <Newspaper className="h-5 w-5 text-primary" />
              </div>
              <div className="min-w-0 flex-1">
                <h1 className="text-lg sm:text-xl font-semibold text-slate-900 dark:text-slate-50 truncate">
                  Daily Digest
                </h1>
                <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                  {user?.email}
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleDarkMode}
                className="h-9 w-9 sm:h-10 sm:w-10 cursor-pointer transition-colors"
                title={darkMode ? "切换到浅色模式" : "切换到深色模式"}
              >
                {darkMode ? <Sun className="h-4 w-4 sm:h-5 sm:w-5" /> : <Moon className="h-4 w-4 sm:h-5 sm:w-5" />}
              </Button>
              
              <Button
                variant="ghost"
                size="icon"
                onClick={handleRefresh}
                disabled={refreshing}
                className="h-9 w-9 sm:h-10 sm:w-10 cursor-pointer transition-colors"
                title="立即刷新"
              >
                <RefreshCw className={`h-4 w-4 sm:h-5 sm:w-5 ${refreshing ? 'animate-spin' : ''}`} />
              </Button>
              
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigate('/settings')}
                className="h-9 w-9 sm:h-10 sm:w-10 cursor-pointer transition-colors"
                title="设置"
              >
                <Settings className="h-4 w-4 sm:h-5 sm:w-5" />
              </Button>
              
              <Button
                variant="ghost"
                size="icon"
                onClick={handleLogout}
                className="h-9 w-9 sm:h-10 sm:w-10 cursor-pointer transition-colors text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300"
                title="退出登录"
              >
                <LogOut className="h-4 w-4 sm:h-5 sm:w-5" />
              </Button>
            </div>
          </div>
          
          {lastUpdate && (
            <div className="pb-3 border-t border-slate-200 dark:border-slate-700 pt-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">
                最后更新：{format(lastUpdate, 'yyyy年MM月dd日 HH:mm', { locale: zhCN })}
              </p>
            </div>
          )}
        </div>
      </header>

      {/* Main Content - Mobile Optimized */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="space-y-4">
          {topics.length === 0 ? (
            <Card className="border-slate-200 dark:border-slate-700">
              <CardHeader>
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800">
                    <Newspaper className="h-5 w-5 text-slate-600 dark:text-slate-400" />
                  </div>
                  <CardTitle className="text-xl">欢迎使用 Daily Digest</CardTitle>
                </div>
                <CardDescription className="text-base">
                  您还没有订阅任何主题。点击右上角的设置图标开始订阅感兴趣的新闻主题。
                </CardDescription>
              </CardHeader>
            </Card>
          ) : (
            <Accordion type="multiple" className="space-y-4">
              {topics.map((topic, index) => (
                <AccordionItem key={index} value={`item-${index}`} className="border-none">
                  <Card className="border-slate-200 dark:border-slate-700 hover:shadow-md transition-shadow cursor-pointer">
                    <CardHeader className="pb-3">
                      <AccordionTrigger className="hover:no-underline py-2">
                        <div className="flex items-center gap-3 flex-1">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <CardTitle className="text-lg sm:text-xl font-semibold text-slate-900 dark:text-slate-50">
                                {topic.topic}
                              </CardTitle>
                              {topic.roast_mode && (
                                <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-orange-100 dark:bg-orange-900/30">
                                  <Sparkles className="h-3 w-3 text-orange-600 dark:text-orange-400" />
                                  <span className="text-xs font-medium text-orange-600 dark:text-orange-400">吐槽</span>
                                </div>
                              )}
                            </div>
                          </div>
                          <span className="text-sm font-medium text-slate-500 dark:text-slate-400 whitespace-nowrap">
                            {topic.news_items.length} 条
                          </span>
                        </div>
                      </AccordionTrigger>
                    </CardHeader>
                    <AccordionContent>
                      <CardContent className="space-y-4 pt-0">
                        {topic.news_items.map((item) => (
                          <div
                            key={item.id}
                            className={`group p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 hover:border-primary/50 dark:hover:border-primary/50 hover:shadow-sm transition-all cursor-pointer ${
                              item.is_read ? 'opacity-60' : ''
                            }`}
                          >
                            <div className="flex gap-4">
                              {item.image_url && (
                                <img
                                  src={item.image_url}
                                  alt={item.title}
                                  className="w-20 h-20 sm:w-24 sm:h-24 object-cover rounded-lg flex-shrink-0"
                                  onError={(e) => {
                                    e.currentTarget.style.display = 'none';
                                  }}
                                />
                              )}
                              <div className="flex-1 min-w-0">
                                <h4 className="font-semibold text-slate-900 dark:text-slate-50 mb-2 line-clamp-2 group-hover:text-primary transition-colors">
                                  {item.title}
                                </h4>
                                <p className="text-sm text-slate-600 dark:text-slate-400 mb-3 line-clamp-3">
                                  {topic.roast_mode && item.summary_roast 
                                    ? item.summary_roast 
                                    : item.summary}
                                </p>
                                <div className="flex items-center justify-between gap-2">
                                  {item.source && (
                                    <span className="text-xs text-slate-500 dark:text-slate-400 truncate">
                                      {item.source}
                                    </span>
                                  )}
                                  <a
                                    href={item.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleNewsClick(item);
                                    }}
                                    className="flex items-center gap-1 text-xs font-medium text-primary hover:text-primary/80 transition-colors whitespace-nowrap cursor-pointer"
                                  >
                                    阅读原文
                                    <ExternalLink className="h-3 w-3" />
                                  </a>
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </CardContent>
                    </AccordionContent>
                  </Card>
                </AccordionItem>
              ))}
            </Accordion>
          )}
        </div>
      </main>
    </div>
  );
}
