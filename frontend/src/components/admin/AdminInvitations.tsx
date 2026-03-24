import { useState, useEffect } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Search, Link, User, Calendar, Trophy } from 'lucide-react';

interface Invitation {
  id: number;
  code: string;
  generated_by: number;
  is_used: boolean;
  used_by?: number;
  created_at: string;
  used_at?: string;
}

interface InvitationStats {
  user_id: number;
  username?: string;
  email?: string;
  total_invited: number;
  successful_invites: number;
  total_points_earned: number;
  last_invited_at?: string;
  success_rate: number;
}

export default function AdminInvitations() {
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [stats, setStats] = useState<InvitationStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState<'invitations' | 'stats'>('invitations');

  useEffect(() => {
    fetchInvitations();
    fetchStats();
  }, []);

  const fetchInvitations = async () => {
    try {
      const response = await fetch('/api/admin/invitations?limit=100');
      const data = await response.json();
      setInvitations(data);
    } catch (error) {
      console.error('获取邀请码失败:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/admin/invitations/stats');
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('获取邀请统计失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredInvitations = invitations.filter(inv => 
    inv.code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredStats = stats.filter(stat => 
    stat.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    stat.username?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return <div className="flex items-center justify-center h-64">加载中...</div>;
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>邀请码管理</CardTitle>
          <CardDescription>查看邀请码使用情况和邀请统计排行</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索邀请码或用户..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="flex gap-2">
              <Button 
                variant={activeTab === 'invitations' ? 'default' : 'outline'}
                onClick={() => setActiveTab('invitations')}
              >
                邀请码
              </Button>
              <Button 
                variant={activeTab === 'stats' ? 'default' : 'outline'}
                onClick={() => setActiveTab('stats')}
              >
                排行榜
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {activeTab === 'invitations' && (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>邀请码</TableHead>
                  <TableHead>创建者</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>使用者</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead>使用时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredInvitations.map((inv) => (
                  <TableRow key={inv.id}>
                    <TableCell>
                      <div className="flex items-center gap-2 font-mono">
                        <Link className="h-4 w-4 text-muted-foreground" />
                        {inv.code}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <User className="h-3 w-3 text-muted-foreground" />
                        <span className="text-sm">用户 #{inv.generated_by}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      {inv.is_used ? (
                        <Badge className="bg-green-100 text-green-800 border-green-200">
                          已使用
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-gray-600">
                          未使用
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {inv.used_by ? (
                        <span className="text-sm">用户 #{inv.used_by}</span>
                      ) : (
                        <span className="text-sm text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Calendar className="h-3 w-3" />
                        {new Date(inv.created_at).toLocaleString()}
                      </div>
                    </TableCell>
                    <TableCell>
                      {inv.used_at ? (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Calendar className="h-3 w-3" />
                          {new Date(inv.used_at).toLocaleString()}
                        </div>
                      ) : (
                        <span className="text-sm text-muted-foreground">-</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {activeTab === 'stats' && (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>排名</TableHead>
                  <TableHead>用户</TableHead>
                  <TableHead>邀请人数</TableHead>
                  <TableHead>成功邀请</TableHead>
                  <TableHead>成功率</TableHead>
                  <TableHead>获得点数</TableHead>
                  <TableHead>最后邀请</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredStats.map((stat, index) => (
                  <TableRow key={stat.user_id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Trophy className={`h-4 w-4 ${
                          index === 0 ? 'text-yellow-500' :
                          index === 1 ? 'text-gray-400' :
                          index === 2 ? 'text-orange-600' :
                          'text-muted-foreground'
                        }`} />
                        <span className="font-medium">#{index + 1}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div>
                        <p className="font-medium">{stat.email}</p>
                        {stat.username && (
                          <p className="text-sm text-muted-foreground">@{stat.username}</p>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{stat.total_invited}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className="bg-green-100 text-green-800">
                        {stat.successful_invites}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {stat.success_rate}%
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className="bg-purple-100 text-purple-800">
                        {stat.total_points_earned} 点
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {stat.last_invited_at ? (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Calendar className="h-3 w-3" />
                          {new Date(stat.last_invited_at).toLocaleDateString()}
                        </div>
                      ) : (
                        <span className="text-sm text-muted-foreground">从未</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总邀请码</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{invitations.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">已使用</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {invitations.filter(i => i.is_used).length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">使用率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {invitations.length > 0 
                ? Math.round((invitations.filter(i => i.is_used).length / invitations.length) * 100)
                : 0}%
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">TOP用户</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.length > 0 ? stats[0].email : '-'}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
