import { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Users, Mail, BarChart3, TestTube, Link, Activity } from 'lucide-react';
import AdminOverview from '@/components/admin/AdminOverview';
import AdminUsers from '@/components/admin/AdminUsers';
import AdminNews from '@/components/admin/AdminNews';
import AdminInvitations from '@/components/admin/AdminInvitations';
import AdminExperiments from '@/components/admin/AdminExperiments';
import AdminLogs from '@/components/admin/AdminLogs';
import { useAuthStore } from '@/store/authStore';
import { Navigate } from 'react-router-dom';

export default function AdminPage() {
  const { user } = useAuthStore();
  const [activeTab, setActiveTab] = useState('overview');

  // 检查是否为管理员
  if (!user?.is_admin) {
    return <Navigate to="/dashboard" />;
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">管理员面板</h1>
          <p className="text-muted-foreground mt-1">
            管理系统数据、查看统计信息和监控系统状态
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Activity className="h-4 w-4" />
          <span>系统运行正常</span>
        </div>
      </div>

      {/* 快速统计卡片 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <QuickStats />
      </div>

      {/* 主要内容区域 */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-6 lg:grid-cols-6">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            <span className="hidden sm:inline">概览</span>
          </TabsTrigger>
          <TabsTrigger value="users" className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            <span className="hidden sm:inline">用户</span>
          </TabsTrigger>
          <TabsTrigger value="news" className="flex items-center gap-2">
            <Mail className="h-4 w-4" />
            <span className="hidden sm:inline">新闻</span>
          </TabsTrigger>
          <TabsTrigger value="invitations" className="flex items-center gap-2">
            <Link className="h-4 w-4" />
            <span className="hidden sm:inline">邀请</span>
          </TabsTrigger>
          <TabsTrigger value="experiments" className="flex items-center gap-2">
            <TestTube className="h-4 w-4" />
            <span className="hidden sm:inline">实验</span>
          </TabsTrigger>
          <TabsTrigger value="logs" className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            <span className="hidden sm:inline">日志</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <AdminOverview />
        </TabsContent>

        <TabsContent value="users" className="space-y-4">
          <AdminUsers />
        </TabsContent>

        <TabsContent value="news" className="space-y-4">
          <AdminNews />
        </TabsContent>

        <TabsContent value="invitations" className="space-y-4">
          <AdminInvitations />
        </TabsContent>

        <TabsContent value="experiments" className="space-y-4">
          <AdminExperiments />
        </TabsContent>

        <TabsContent value="logs" className="space-y-4">
          <AdminLogs />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// 快速统计卡片组件
function QuickStats() {
  const [stats, setStats] = useState({
    users: { total: 0, active: 0 },
    news: { total: 0 },
    invitations: { total: 0, used: 0 },
    experiments: { total: 0, running: 0 }
  });

  useEffect(() => {
    fetch('/api/admin/overview')
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(err => console.error('获取统计失败:', err));
  }, []);

  const cards = [
    {
      title: '用户总数',
      value: stats.users.total,
      change: `${stats.users.active} 活跃用户`,
      icon: Users,
      color: 'text-blue-500'
    },
    {
      title: '新闻总数',
      value: stats.news.total,
      change: '已抓取文章',
      icon: Mail,
      color: 'text-green-500'
    },
    {
      title: '邀请码',
      value: stats.invitations.total,
      change: `${stats.invitations.used} 已使用`,
      icon: Link,
      color: 'text-purple-500'
    },
    {
      title: 'A/B测试',
      value: stats.experiments.total,
      change: `${stats.experiments.running} 运行中`,
      icon: TestTube,
      color: 'text-orange-500'
    }
  ];

  return (
    <>
      {cards.map((card, index) => (
        <Card key={index}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {card.title}
            </CardTitle>
            <card.icon className={`h-4 w-4 ${card.color}`} />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{card.value}</div>
            <p className="text-xs text-muted-foreground">
              {card.change}
            </p>
          </CardContent>
        </Card>
      ))}
    </>
  );
}
