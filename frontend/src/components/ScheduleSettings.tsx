import { useEffect, useState } from 'react';
import { scheduleAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Loader2, Send, Clock } from 'lucide-react';

interface ScheduleConfig {
  enabled: boolean;
  schedule_type: 'daily';
  hour?: number;
  minute?: number;
  last_email_sent_at?: string | null;
}

export default function ScheduleSettings() {
  const [config, setConfig] = useState<ScheduleConfig>({
    enabled: false,
    schedule_type: 'daily',
    hour: 9,
    minute: 0,
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    loadSchedule();
  }, []);

  const loadSchedule = async () => {
    try {
      setLoading(true);
      const response = await scheduleAPI.getMySchedule();
      setConfig(response.data);
    } catch (error) {
      console.error('Failed to load schedule:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      // 确保 schedule_type 为 daily
      await scheduleAPI.updateMySchedule({
        ...config,
        schedule_type: 'daily'
      });
      alert('定时设置已保存！');
      await loadSchedule();
    } catch (error: any) {
      alert(error.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    if (!confirm('确定要立即发送测试邮件吗？')) return;
    
    try {
      setTesting(true);
      await scheduleAPI.testEmail();
      alert('测试邮件已发送，请检查您的邮箱！');
    } catch (error: any) {
      alert(error.response?.data?.detail || '发送测试邮件失败');
    } finally {
      setTesting(false);
    }
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
      {/* Enable/Disable Toggle - Mobile Optimized */}
      <div className="flex items-center justify-between p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
        <div className="flex-1">
          <label className="text-sm font-medium text-slate-900 dark:text-slate-50 block">
            启用定时邮件
          </label>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            开启后，系统将根据您的设置自动发送新闻摘要邮件
          </p>
        </div>
        <Switch
          checked={config.enabled}
          onCheckedChange={(checked) => setConfig({ ...config, enabled: checked })}
          className="ml-4"
        />
      </div>

      {config.enabled && (
        <div className="space-y-5 pt-2">
          {/* Daily Schedule */}
          <div className="space-y-3 p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-slate-500 dark:text-slate-400" />
              <label className="text-sm font-medium text-slate-900 dark:text-slate-50">
                每天发送时间
              </label>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <Input
                  type="number"
                  min="0"
                  max="23"
                  value={config.hour || 9}
                  onChange={(e) => setConfig({ ...config, hour: parseInt(e.target.value) || 9 })}
                  className="h-11 text-center text-base"
                />
              </div>
              <span className="text-slate-500 dark:text-slate-400 font-medium">:</span>
              <div className="flex-1">
                <Input
                  type="number"
                  min="0"
                  max="59"
                  value={config.minute || 0}
                  onChange={(e) => setConfig({ ...config, minute: parseInt(e.target.value) || 0 })}
                  className="h-11 text-center text-base"
                />
              </div>
              <span className="text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">时:分</span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 pt-1">
              建议 9 点（系统每日 8 点更新）
            </p>
          </div>

          {/* Last Email Sent Info */}
          {config.last_email_sent_at && (
            <div className="text-xs text-slate-500 dark:text-slate-400 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
              上次发送时间: {new Date(config.last_email_sent_at).toLocaleString('zh-CN')}
            </div>
          )}
        </div>
      )}

      {/* Actions - Mobile Optimized */}
      <div className="flex flex-col gap-3 pt-4 border-t border-slate-200 dark:border-slate-700">
        <Button
          onClick={handleSave}
          disabled={saving}
          className="w-full h-11 cursor-pointer"
          size="default"
        >
          {saving ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              保存中...
            </>
          ) : (
            '保存设置'
          )}
        </Button>
        {config.enabled && (
          <Button
            variant="outline"
            onClick={handleTest}
            disabled={testing}
            className="w-full h-11 cursor-pointer"
            size="default"
          >
            {testing ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                发送中...
              </>
            ) : (
              <>
                <Send className="h-4 w-4 mr-2" />
                发送测试邮件
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  );
}
