import { useEffect, useState } from 'react';
import { subscriptionsAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Trash2, Plus, Loader2, ChevronDown, ChevronUp, CheckCircle2, Circle } from 'lucide-react';

interface Subscription {
  id: number;
  topic: string;
  roast_mode: boolean;
  is_active: boolean;
  created_at: string;
}

interface CustomRSSFeed {
  id: number;
  topic: string;
  feed_url: string;
  is_active: boolean;
  roast_mode: boolean;
  created_at: string;
}

interface Props {
  onUpdate: () => void;
}

export default function SubscriptionManager({ onUpdate }: Props) {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [presetTopics, setPresetTopics] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  
  // Custom RSS feed state
  const [customRSSFeeds, setCustomRSSFeeds] = useState<CustomRSSFeed[]>([]);
  const [newCustomTopic, setNewCustomTopic] = useState('');
  const [newCustomFeedUrl, setNewCustomFeedUrl] = useState('');
  const [showCustomRSS, setShowCustomRSS] = useState(false);

  useEffect(() => {
    loadSubscriptions();
    loadPresetTopics();
    loadCustomRSSFeeds();
  }, []);

  const loadSubscriptions = async () => {
    try {
      const response = await subscriptionsAPI.getAll();
      setSubscriptions(response.data);
    } catch (error) {
      console.error('Failed to load subscriptions:', error);
    }
  };

  const loadPresetTopics = async () => {
    try {
      const response = await subscriptionsAPI.getPresetTopics();
      setPresetTopics(response.data.topics);
    } catch (error) {
      console.error('Failed to load preset topics:', error);
    }
  };

  const loadCustomRSSFeeds = async () => {
    try {
      const response = await subscriptionsAPI.getCustomRSSFeeds();
      setCustomRSSFeeds(response.data);
    } catch (error) {
      console.error('Failed to load custom RSS feeds:', error);
    }
  };

  const handleAddTopic = async (topic: string) => {
    if (!topic.trim()) return;
    
    setLoading(true);
    try {
      await subscriptionsAPI.create(topic.trim(), false);
      await loadSubscriptions();
      onUpdate();
    } catch (error: any) {
      alert(error.response?.data?.detail || '添加订阅失败');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleRoast = async (id: number, currentMode: boolean) => {
    try {
      await subscriptionsAPI.update(id, { roast_mode: !currentMode });
      await loadSubscriptions();
      onUpdate();
    } catch (error) {
      console.error('Failed to toggle roast mode:', error);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定要取消订阅吗？')) return;
    
    try {
      await subscriptionsAPI.delete(id);
      await loadSubscriptions();
      onUpdate();
    } catch (error) {
      console.error('Failed to delete subscription:', error);
    }
  };

  const handleAddCustomRSSFeed = async () => {
    if (!newCustomTopic.trim() || !newCustomFeedUrl.trim()) return;
    
    setLoading(true);
    try {
      await subscriptionsAPI.createCustomRSSFeed(newCustomTopic.trim(), newCustomFeedUrl.trim());
      await loadCustomRSSFeeds();
      setNewCustomTopic('');
      setNewCustomFeedUrl('');
    } catch (error: any) {
      alert(error.response?.data?.detail || '添加自定义RSS源失败');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleCustomRSSFeed = async (id: number, currentActive: boolean) => {
    try {
      await subscriptionsAPI.updateCustomRSSFeed(id, { is_active: !currentActive });
      await loadCustomRSSFeeds();
    } catch (error) {
      console.error('Failed to toggle custom RSS feed:', error);
    }
  };

  const handleToggleCustomRSSRoastMode = async (id: number, currentRoastMode: boolean) => {
    try {
      await subscriptionsAPI.updateCustomRSSFeed(id, { roast_mode: !currentRoastMode });
      await loadCustomRSSFeeds();
    } catch (error) {
      console.error('Failed to toggle custom RSS roast mode:', error);
    }
  };

  const handleDeleteCustomRSSFeed = async (id: number) => {
    if (!confirm('确定要删除这个自定义RSS源吗？')) return;
    
    try {
      await subscriptionsAPI.deleteCustomRSSFeed(id);
      await loadCustomRSSFeeds();
    } catch (error) {
      console.error('Failed to delete custom RSS feed:', error);
    }
  };

  return (
    <div className="space-y-5">
      {/* Preset Topics - Mobile Optimized */}
      <div className="space-y-3">
        <label className="text-sm font-medium text-slate-900 dark:text-slate-50 block">
          热门主题
        </label>
        <div className="flex flex-wrap gap-2">
          {presetTopics.map((topic) => {
            const isSubscribed = subscriptions.some(s => s.topic === topic);
            return (
              <Button
                key={topic}
                variant={isSubscribed ? "secondary" : "outline"}
                size="sm"
                onClick={() => !isSubscribed && handleAddTopic(topic)}
                disabled={isSubscribed || loading}
                className="h-9 cursor-pointer transition-colors text-xs"
              >
                {isSubscribed ? (
                  <CheckCircle2 className="h-3 w-3 mr-1.5" />
                ) : (
                  <Circle className="h-3 w-3 mr-1.5" />
                )}
                {topic}
              </Button>
            );
          })}
        </div>
      </div>

      {/* Current Subscriptions - Mobile Optimized */}
      <div className="space-y-3">
        <label className="text-sm font-medium text-slate-900 dark:text-slate-50 block">
          当前订阅 ({subscriptions.length})
        </label>
        <div className="space-y-2">
          {subscriptions.map((sub) => (
            <div
              key={sub.id}
              className="flex items-center justify-between p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700"
            >
              <div className="flex-1 min-w-0 pr-3">
                <div className="font-medium text-sm text-slate-900 dark:text-slate-50 truncate">
                  {sub.topic}
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <Switch
                    checked={sub.roast_mode}
                    onCheckedChange={() => handleToggleRoast(sub.id, sub.roast_mode)}
                  />
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    {sub.roast_mode ? '吐槽模式' : '正常模式'}
                  </span>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => handleDelete(sub.id)}
                className="h-9 w-9 text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 cursor-pointer flex-shrink-0"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
          
          {subscriptions.length === 0 && (
            <div className="text-center py-8 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                还没有订阅任何主题
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Custom RSS Feeds - Mobile Optimized */}
      <div className="space-y-3 border-t border-slate-200 dark:border-slate-700 pt-5">
        <button
          onClick={() => setShowCustomRSS(!showCustomRSS)}
          className="flex items-center justify-between w-full cursor-pointer"
        >
          <label className="text-sm font-medium text-slate-900 dark:text-slate-50">
            自定义RSS源 ({customRSSFeeds.length})
          </label>
          {showCustomRSS ? (
            <ChevronUp className="h-4 w-4 text-slate-500 dark:text-slate-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-slate-500 dark:text-slate-400" />
          )}
        </button>
        
        {showCustomRSS && (
          <div className="space-y-4 pt-2">
            {/* Add Custom RSS Feed */}
            <div className="space-y-3 p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
              <div className="space-y-2">
                <Input
                  placeholder="主题名称"
                  value={newCustomTopic}
                  onChange={(e) => setNewCustomTopic(e.target.value)}
                  className="h-11"
                />
                <Input
                  placeholder="RSS源URL"
                  value={newCustomFeedUrl}
                  onChange={(e) => setNewCustomFeedUrl(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAddCustomRSSFeed()}
                  className="h-11"
                />
              </div>
              <Button
                onClick={handleAddCustomRSSFeed}
                disabled={loading || !newCustomTopic.trim() || !newCustomFeedUrl.trim()}
                className="w-full h-11 cursor-pointer"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    添加中...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4 mr-2" />
                    添加RSS源
                  </>
                )}
              </Button>
            </div>

            {/* Custom RSS Feeds List */}
            <div className="space-y-2">
              {customRSSFeeds.map((feed) => (
                <div
                  key={feed.id}
                  className="flex items-center justify-between p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700"
                >
                  <div className="flex-1 min-w-0 pr-3">
                    <div className="font-medium text-sm text-slate-900 dark:text-slate-50 truncate">
                      {feed.topic}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400 truncate mt-1">
                      {feed.feed_url}
                    </div>
                    <div className="flex flex-col gap-2 mt-2">
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={feed.is_active}
                          onCheckedChange={() => handleToggleCustomRSSFeed(feed.id, feed.is_active)}
                        />
                        <span className="text-xs text-slate-500 dark:text-slate-400">
                          {feed.is_active ? '已订阅' : '未订阅'}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={feed.roast_mode}
                          onCheckedChange={() => handleToggleCustomRSSRoastMode(feed.id, feed.roast_mode)}
                          disabled={!feed.is_active}
                        />
                        <span className={`text-xs ${feed.is_active ? 'text-slate-500 dark:text-slate-400' : 'text-slate-400 dark:text-slate-600'}`}>
                          {feed.roast_mode ? '吐槽模式' : '正常模式'}
                        </span>
                      </div>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDeleteCustomRSSFeed(feed.id)}
                    className="h-9 w-9 text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 cursor-pointer flex-shrink-0"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              
              {customRSSFeeds.length === 0 && (
                <div className="text-center py-8 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    还没有添加任何自定义RSS源
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
