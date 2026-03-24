import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';
import { TrendingUp, Users, Link, TestTube } from 'lucide-react';

export default function AdminOverview() {
  const [overviewData, setOverviewData] = useState<any>(null);

  useEffect(() => {
    fetch('/api/admin/overview')
      .then(res => res.json())
      .then(data => setOverviewData(data))
      .catch(err => console.error('获取概览数据失败:', err));
  }, []);

  if (!overviewData) {
    return <div className="flex items-center justify-center h-64">加载中...</div>;
  }

  // 模拟图表数据
  const weeklyActivity = [
    { day: '周一', users: 120, active: 85 },
    { day: '周二', users: 132, active: 92 },
    { day: '周三', users: 101, active: 78 },
    { day: '周四', users: 134, active: 95 },
    { day: '周五', users: 90, active: 68 },
    { day: '周六', users: 230, active: 180 },
    { day: '周日', users: 210, active: 165 }
  ];

  const topicDistribution = [
    { name: '科技', value: 35, color: '#3b82f6' },
    { name: '财经', value: 25, color: '#10b981' },
    { name: '体育', value: 20, color: '#f59e0b' },
    { name: '娱乐', value: 20, color: '#ef4444' }
  ];

  return (
    <div className="space-y-6">
      {/* 详细统计卡片 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <StatCard
          title="用户活跃度"
          value={`${overviewData.users.active_rate}%`}
          change="较上周 +5.2%"
          icon={Users}
          color="text-blue-500"
        />
        <StatCard
          title="邀请成功率"
          value={`${overviewData.invitations.success_rate}%`}
          change="较上月 +2.1%"
          icon={Link}
          color="text-purple-500"
        />
        <StatCard
          title="实验运行中"
          value={overviewData.experiments.running}
          change="系统优化持续进行"
          icon={TestTube}
          color="text-orange-500"
        />
      </div>

      {/* 图表区域 */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* 用户活跃度趋势 */}
        <Card>
          <CardHeader>
            <CardTitle>本周用户活跃度</CardTitle>
            <CardDescription>每日新增用户和活跃用户趋势</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={weeklyActivity}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="users" stroke="#3b82f6" name="新增用户" />
                <Line type="monotone" dataKey="active" stroke="#10b981" name="活跃用户" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* 主题分布 */}
        <Card>
          <CardHeader>
            <CardTitle>新闻主题分布</CardTitle>
            <CardDescription>各主题新闻占比</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={topicDistribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }: { name: string; percent: number }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {topicDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* 最近活动 */}
      <Card>
        <CardHeader>
          <CardTitle>最近系统活动</CardTitle>
          <CardDescription>最近30分钟的系统事件</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <ActivityItem
              time="2分钟前"
              message="用户 john@example.com 订阅了新的主题"
              type="success"
            />
            <ActivityItem
              time="5分钟前"
              message="A/B测试 'ui_optimization_test' 收到新的用户分配"
              type="info"
            />
            <ActivityItem
              time="8分钟前"
              message="邀请码 ABC123 被成功使用"
              type="success"
            />
            <ActivityItem
              time="12分钟前"
              message="系统发送了每日推送邮件给 156 个用户"
              type="info"
            />
            <ActivityItem
              time="15分钟前"
              message="抓取了 23 篇新文章"
              type="info"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// 统计卡片组件
function StatCard({ title, value, change, icon: Icon, color }: any) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">
          {title}
        </CardTitle>
        <Icon className={`h-4 w-4 ${color}`} />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <div className="flex items-center gap-2 mt-1">
          <TrendingUp className="h-4 w-4 text-green-500" />
          <p className="text-xs text-muted-foreground">
            {change}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

// 活动项组件
function ActivityItem({ time, message, type }: any) {
  const colors = {
    success: 'bg-green-100 text-green-800 border-green-200',
    info: 'bg-blue-100 text-blue-800 border-blue-200',
    warning: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    error: 'bg-red-100 text-red-800 border-red-200'
  };

  return (
    <div className="flex items-start gap-4">
      <div className={`px-2 py-1 rounded-full text-xs font-medium border ${colors[type as keyof typeof colors]}`}>
        {type}
      </div>
      <div className="flex-1">
        <p className="text-sm">{message}</p>
        <p className="text-xs text-muted-foreground mt-1">{time}</p>
      </div>
    </div>
  );
}
