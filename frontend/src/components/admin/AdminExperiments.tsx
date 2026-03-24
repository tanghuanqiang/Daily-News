import { useState, useEffect } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { TestTube, BarChart3, Play, Pause, RotateCcw } from 'lucide-react';

interface Experiment {
  id: number;
  name: string;
  description: string;
  status: string;
  traffic_allocation: number;
  created_by: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  variant_count: number;
  total_users: number;
}

export default function AdminExperiments() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    fetchExperiments();
  }, []);

  const fetchExperiments = async () => {
    try {
      const url = statusFilter === 'all' 
        ? '/api/admin/experiments'
        : `/api/admin/experiments?status=${statusFilter}`;
      const response = await fetch(url);
      const data = await response.json();
      setExperiments(data);
    } catch (error) {
      console.error('获取实验列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateExperimentStatus = async (experimentId: number, status: string) => {
    try {
      const response = await fetch(`/api/admin/experiments/${experimentId}/status?status=${status}`, {
        method: 'PUT'
      });
      
      if (response.ok) {
        fetchExperiments(); // 刷新列表
      }
    } catch (error) {
      console.error('更新实验状态失败:', error);
    }
  };

  const getStatusBadge = (status: string) => {
    const styles = {
      draft: 'bg-gray-100 text-gray-800 border-gray-200',
      running: 'bg-green-100 text-green-800 border-green-200',
      paused: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      completed: 'bg-blue-100 text-blue-800 border-blue-200'
    };
    
    return (
      <Badge className={styles[status as keyof typeof styles]}>
        {status === 'draft' ? '草稿' :
         status === 'running' ? '运行中' :
         status === 'paused' ? '已暂停' : '已完成'}
      </Badge>
    );
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64">加载中...</div>;
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>A/B测试管理</CardTitle>
          <CardDescription>管理实验、查看结果和控制实验状态</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">状态筛选:</span>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="draft">草稿</SelectItem>
                  <SelectItem value="running">运行中</SelectItem>
                  <SelectItem value="paused">已暂停</SelectItem>
                  <SelectItem value="completed">已完成</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button onClick={fetchExperiments}>刷新</Button>
            <Button variant="outline" onClick={() => window.open('/static/experiment-dashboard.html', '_blank')}>
              <BarChart3 className="h-4 w-4 mr-2" />
              可视化仪表板
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>实验信息</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>流量分配</TableHead>
                <TableHead>版本数</TableHead>
                <TableHead>参与用户</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {experiments.map((exp) => (
                <TableRow key={exp.id}>
                  <TableCell>
                    <div className="space-y-1">
                      <p className="font-medium">{exp.name}</p>
                      <p className="text-sm text-muted-foreground line-clamp-2">
                        {exp.description}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    {getStatusBadge(exp.status)}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">
                      {(exp.traffic_allocation * 100).toFixed(0)}%
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">
                      {exp.variant_count}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className="bg-blue-100 text-blue-800">
                      {exp.total_users}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm text-muted-foreground">
                      {new Date(exp.created_at).toLocaleDateString()}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      {exp.status === 'draft' && (
                        <Button 
                          size="sm" 
                          onClick={() => updateExperimentStatus(exp.id, 'running')}
                        >
                          <Play className="h-3 w-3 mr-1" />
                          启动
                        </Button>
                      )}
                      {exp.status === 'running' && (
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => updateExperimentStatus(exp.id, 'paused')}
                        >
                          <Pause className="h-3 w-3 mr-1" />
                          暂停
                        </Button>
                      )}
                      {exp.status === 'paused' && (
                        <Button 
                          size="sm" 
                          onClick={() => updateExperimentStatus(exp.id, 'running')}
                        >
                          <RotateCcw className="h-3 w-3 mr-1" />
                          恢复
                        </Button>
                      )}
                      {exp.status === 'running' && (
                        <Button 
                          size="sm" 
                          variant="default"
                          onClick={() => updateExperimentStatus(exp.id, 'completed')}
                        >
                          完成
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {experiments.length === 0 && (
            <div className="py-8 text-center text-muted-foreground">
              暂无实验数据
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总实验数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{experiments.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">运行中</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {experiments.filter(e => e.status === 'running').length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总参与用户</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {experiments.reduce((sum, e) => sum + e.total_users, 0)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">平均版本数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {experiments.length > 0 
                ? (experiments.reduce((sum, e) => sum + e.variant_count, 0) / experiments.length).toFixed(1)
                : 0}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
