import { useState, useEffect } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, User, Calendar } from 'lucide-react';
import { get } from '@/lib/api';

interface User {
  id: number;
  email: string;
  username?: string;
  is_active: boolean;
  is_admin: boolean;
  email_verified: boolean;
  created_at: string;
  last_login?: string;
  preferences?: any;
  invitation_stats?: any;
}

export default function AdminUsers() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await get('/api/admin/users?limit=100');
      const data = await response.json();
      setUsers(data);
    } catch (error) {
      console.error('获取用户列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredUsers = users.filter(user => 
    user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.username?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return <div className="flex items-center justify-center h-64">加载中...</div>;
  }

  return (
    <div className="space-y-4">
      {/* 搜索和筛选 */}
      <Card>
        <CardHeader>
          <CardTitle>用户管理</CardTitle>
          <CardDescription>查看和管理所有用户账户</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索用户邮箱或用户名..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
              />
            </div>
            <Button variant="outline">导出数据</Button>
          </div>
        </CardContent>
      </Card>

      {/* 用户列表 */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>用户信息</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>注册时间</TableHead>
                <TableHead>偏好设置</TableHead>
                <TableHead>邀请统计</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredUsers.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="bg-muted rounded-full p-2">
                        <User className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="font-medium">{user.email}</p>
                        {user.username && (
                          <p className="text-sm text-muted-foreground">@{user.username}</p>
                        )}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-col gap-1">
                      {user.is_admin ? (
                        <Badge variant="destructive">管理员</Badge>
                      ) : (
                        <Badge variant="secondary">普通用户</Badge>
                      )}
                      {user.is_active ? (
                        <Badge variant="outline" className="text-green-600 border-green-600">活跃</Badge>
                      ) : (
                        <Badge variant="outline" className="text-red-600 border-red-600">禁用</Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="h-3 w-3" />
                      {new Date(user.created_at).toLocaleDateString()}
                    </div>
                  </TableCell>
                  <TableCell>
                    {user.preferences?.selected_topics ? (
                      <div className="flex flex-wrap gap-1">
                        {user.preferences.selected_topics.slice(0, 3).map((topic: string) => (
                          <Badge key={topic} variant="outline" className="text-xs">
                            {topic}
                          </Badge>
                        ))}
                        {user.preferences.selected_topics.length > 3 && (
                          <Badge variant="outline" className="text-xs">+{user.preferences.selected_topics.length - 3}</Badge>
                        )}
                      </div>
                    ) : (
                      <span className="text-sm text-muted-foreground">未设置</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {user.invitation_stats ? (
                      <div className="text-sm">
                        <p>邀请: {user.invitation_stats.successful_invites}/{user.invitation_stats.total_invited}</p>
                        <p>点数: {user.invitation_stats.total_points_earned}</p>
                      </div>
                    ) : (
                      <span className="text-sm text-muted-foreground">无</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          
          {filteredUsers.length === 0 && (
            <div className="py-8 text-center text-muted-foreground">
              暂无用户数据
            </div>
          )}
        </CardContent>
      </Card>

      {/* 统计摘要 */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总用户数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{users.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">活跃用户</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {users.filter(u => u.is_active).length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">管理员</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {users.filter(u => u.is_admin).length}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
