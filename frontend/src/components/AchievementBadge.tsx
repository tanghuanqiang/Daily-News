import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { toast } from '@/components/ui/use-toast';
import api from '@/lib/api';
import { TrophyIcon } from '@/components/ui/icons/TrophyIcon';

interface Achievement {
  id: number;
  code: string;
  name: string;
  description: string;
  icon: string | null;
  category: string | null;
  points: number;
  is_unlocked: boolean;
  unlocked_at: string | null;
  progress: number;
  current_value: number;
  requirement_value: number;
}

interface AchievementBadgeProps {
  userId: number;
}

export function AchievementBadge({ userId }: AchievementBadgeProps) {
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total_achievements: 0,
    unlocked_count: 0,
    total_points: 0,
    unlock_rate: 0
  });

  useEffect(() => {
    loadAchievements();
  }, [userId]);

  const loadAchievements = async () => {
    try {
      setLoading(true);
      const [achievementsRes, statsRes] = await Promise.all([
        api.achievements.getMyAchievementsWithProgress(),
        api.achievements.getStats()
      ]);

      setAchievements(achievementsRes.data);
      setStats(statsRes.data);
    } catch (error) {
      console.error('加载成就失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const getCategoryColor = (category: string | null) => {
    switch (category) {
      case 'reading':
        return 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400';
      case 'exploration':
        return 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400';
      case 'early_bird':
        return 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400';
      case 'sharing':
        return 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400';
      default:
        return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400';
    }
  };

  const getCategoryName = (category: string | null) => {
    switch (category) {
      case 'reading':
        return '阅读成就';
      case 'exploration':
        return '探索成就';
      case 'early_bird':
        return '早起成就';
      case 'sharing':
        return '分享成就';
      default:
        return '其他成就';
    }
  };

  const handleAchievementClick = (achievement: Achievement) => {
    if (achievement.is_unlocked) {
      toast({
        title: `🏆 ${achievement.name}`,
        description: (
          <div className="space-y-2">
            <p>{achievement.description}</p>
            <p className="text-sm text-slate-500">
              解锁时间: {new Date(achievement.unlocked_at!).toLocaleDateString('zh-CN')}
            </p>
            <p className="text-sm font-medium text-primary">
              +{achievement.points} 点数
            </p>
          </div>
        ),
        duration: 4000
      });
    } else {
      const progressPercent = Math.round(achievement.progress * 100);
      toast({
        title: `🔒 ${achievement.name}`,
        description: (
          <div className="space-y-2">
            <p>{achievement.description}</p>
            <div className="w-full bg-slate-200 rounded-full h-2 dark:bg-slate-700">
              <div
                className="bg-primary h-2 rounded-full transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <p className="text-sm text-slate-500">
              进度: {achievement.current_value} / {achievement.requirement_value} ({progressPercent}%)
            </p>
          </div>
        ),
        duration: 4000
      });
    }
  };

  if (loading) {
    return (
      <Card className="border-slate-200 dark:border-slate-700">
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-slate-200 dark:border-slate-700">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <TrophyIcon className="h-5 w-5 text-yellow-500" />
            我的成就
          </CardTitle>
          <div className="text-sm text-slate-500 dark:text-slate-400">
            {stats.unlocked_count} / {stats.total_achievements} ({stats.unlock_rate}%)
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 统计信息 */}
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-primary">{stats.total_points}</div>
            <div className="text-xs text-slate-500 dark:text-slate-400">总点数</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-green-600">{stats.unlocked_count}</div>
            <div className="text-xs text-slate-500 dark:text-slate-400">已解锁</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-blue-600">{stats.total_achievements - stats.unlocked_count}</div>
            <div className="text-xs text-slate-500 dark:text-slate-400">未解锁</div>
          </div>
        </div>

        {/* 成就列表 */}
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {achievements.map((achievement) => (
            <Button
              key={achievement.id}
              variant="ghost"
              className="w-full h-auto p-3 justify-start hover:bg-slate-100 dark:hover:bg-slate-800"
              onClick={() => handleAchievementClick(achievement)}
            >
              <div className="flex items-center gap-3 w-full">
                {/* 图标 */}
                <div className="flex-shrink-0">
                  {achievement.is_unlocked ? (
                    <div className="text-2xl">
                      {achievement.icon || '🏆'}
                    </div>
                  ) : (
                    <div className="text-2xl opacity-30">
                      🔒
                    </div>
                  )}
                </div>

                {/* 信息 */}
                <div className="flex-1 text-left min-w-0">
                  <div className="flex items-center gap-2">
                    <div className="font-medium text-sm truncate">
                      {achievement.name}
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${getCategoryColor(achievement.category)}`}>
                      {getCategoryName(achievement.category)}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 truncate">
                    {achievement.description}
                  </div>

                  {/* 进度条（未解锁时显示） */}
                  {!achievement.is_unlocked && (
                    <div className="mt-2">
                      <div className="w-full bg-slate-200 rounded-full h-1.5 dark:bg-slate-700">
                        <div
                          className="bg-primary h-1.5 rounded-full transition-all duration-300"
                          style={{ width: `${Math.round(achievement.progress * 100)}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* 点数 */}
                <div className="flex-shrink-0 text-xs font-medium text-primary">
                  +{achievement.points}
                </div>
              </div>
            </Button>
          ))}
        </div>

        {/* 空状态 */}
        {achievements.length === 0 && (
          <div className="text-center py-8">
            <div className="text-4xl mb-2">🏆</div>
            <p className="text-slate-500 dark:text-slate-400">还没有成就</p>
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">开始阅读新闻来解锁成就吧！</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
