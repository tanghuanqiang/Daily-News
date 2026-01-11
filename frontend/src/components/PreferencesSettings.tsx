import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { preferencesAPI } from '@/lib/api';
import { Loader2, Settings, Eye, EyeOff, Filter } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

interface Preferences {
  hide_read: boolean;
  sort_by: 'time' | 'relevance';
  hidden_sources: string[];
}

export default function PreferencesSettings() {
  const [preferences, setPreferences] = useState<Preferences>({
    hide_read: false,
    sort_by: 'time',
    hidden_sources: [],
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    loadPreferences();
  }, []);

  const loadPreferences = async () => {
    try {
      setLoading(true);
      const response = await preferencesAPI.getMyPreferences();
      setPreferences(response.data);
    } catch (error) {
      console.error('Failed to load preferences:', error);
      toast({
        title: '加载失败',
        description: '无法加载用户偏好设置',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await preferencesAPI.updateMyPreferences(preferences);
      toast({
        title: '保存成功',
        description: '偏好设置已保存',
        variant: 'success',
      });
    } catch (error: any) {
      console.error('Failed to save preferences:', error);
      toast({
        title: '保存失败',
        description: error.response?.data?.detail || '保存偏好设置失败',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleToggleHideRead = (checked: boolean) => {
    setPreferences({ ...preferences, hide_read: checked });
  };

  const handleSortByChange = (sortBy: 'time' | 'relevance') => {
    setPreferences({ ...preferences, sort_by: sortBy });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <Card className="border-slate-200 dark:border-slate-700">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
              <Settings className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <CardTitle className="text-xl">阅读偏好</CardTitle>
              <CardDescription className="text-base mt-1">
                个性化您的新闻阅读体验
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* 隐藏已读新闻 */}
          <div className="flex items-center justify-between py-3 border-b border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-3 flex-1">
              <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800">
                {preferences.hide_read ? (
                  <EyeOff className="h-4 w-4 text-slate-600 dark:text-slate-400" />
                ) : (
                  <Eye className="h-4 w-4 text-slate-600 dark:text-slate-400" />
                )}
              </div>
              <div className="flex-1">
                <Label htmlFor="hide-read" className="text-base font-medium cursor-pointer">
                  隐藏已读新闻
                </Label>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  开启后，已阅读的新闻将不会在列表中显示
                </p>
              </div>
            </div>
            <Switch
              id="hide-read"
              checked={preferences.hide_read}
              onCheckedChange={handleToggleHideRead}
              className="flex-shrink-0"
            />
          </div>

          {/* 排序方式 */}
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800">
                <Filter className="h-4 w-4 text-slate-600 dark:text-slate-400" />
              </div>
              <div>
                <Label className="text-base font-medium">排序方式</Label>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  选择新闻的排序方式
                </p>
              </div>
            </div>
            <div className="flex gap-3 pl-12">
              <Button
                variant={preferences.sort_by === 'time' ? 'default' : 'outline'}
                size="sm"
                onClick={() => handleSortByChange('time')}
                className="flex-1"
              >
                按时间
              </Button>
              <Button
                variant={preferences.sort_by === 'relevance' ? 'default' : 'outline'}
                size="sm"
                onClick={() => handleSortByChange('relevance')}
                className="flex-1"
              >
                按相关性
              </Button>
            </div>
          </div>

          {/* 保存按钮 */}
          <div className="pt-4">
            <Button
              onClick={handleSave}
              disabled={saving}
              className="w-full h-11"
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  保存中...
                </>
              ) : (
                '保存设置'
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
