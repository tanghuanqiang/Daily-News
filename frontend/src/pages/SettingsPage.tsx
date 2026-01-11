import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { ArrowLeft, Moon, Sun, Settings as SettingsIcon, Mail, Bell } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import SubscriptionManager from '@/components/SubscriptionManager';
import ScheduleSettings from '@/components/ScheduleSettings';
import PreferencesSettings from '@/components/PreferencesSettings';

export default function SettingsPage() {
  const [darkMode, setDarkMode] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    // Check dark mode preference
    if (localStorage.getItem('darkMode') === 'true') {
      setDarkMode(true);
      document.documentElement.classList.add('dark');
    }
  }, []);

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

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      {/* Fixed Header */}
      <header className="sticky top-0 z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-700 shadow-sm">
        <div className="px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigate('/dashboard')}
                className="h-10 w-10 cursor-pointer"
                title="返回仪表盘"
              >
                <ArrowLeft className="h-5 w-5" />
              </Button>
              <div className="flex items-center gap-2">
                <SettingsIcon className="h-5 w-5 text-slate-700 dark:text-slate-300" />
                <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
                  设置
                </h1>
              </div>
            </div>
            
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleDarkMode}
              className="h-10 w-10 cursor-pointer"
              title={darkMode ? "切换到浅色模式" : "切换到深色模式"}
            >
              {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content - Mobile Optimized */}
      <main className="px-4 py-6 pb-20 max-w-2xl mx-auto">
        <div className="space-y-4">
          {/* Schedule Settings Card */}
          <Card className="border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-shadow cursor-pointer">
            <CardHeader className="pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                  <Bell className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <CardTitle className="text-base font-semibold text-slate-900 dark:text-slate-50">
                    定时邮件设置
                  </CardTitle>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    配置邮件发送频率和时间
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <ScheduleSettings />
            </CardContent>
          </Card>

          {/* Subscription Manager Card */}
          <Card className="border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-shadow cursor-pointer">
            <CardHeader className="pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/30">
                  <Mail className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <CardTitle className="text-base font-semibold text-slate-900 dark:text-slate-50">
                    订阅管理
                  </CardTitle>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    管理您订阅的新闻主题
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <SubscriptionManager onUpdate={() => {}} />
            </CardContent>
          </Card>

          {/* Preferences Settings Card */}
          <Card className="border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-shadow cursor-pointer">
            <CardHeader className="pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
                  <SettingsIcon className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <CardTitle className="text-base font-semibold text-slate-900 dark:text-slate-50">
                    阅读偏好
                  </CardTitle>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    个性化您的新闻阅读体验
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <PreferencesSettings />
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
