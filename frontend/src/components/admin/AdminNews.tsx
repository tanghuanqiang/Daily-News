import { useState, useEffect } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Search, Calendar, Tag } from 'lucide-react';

interface NewsArticle {
  id: number;
  title: string;
  topic: string;
  summary: string;
  source: string;
  url: string;
  published_at: string;
  created_at: string;
}

export default function AdminNews() {
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchNews();
  }, []);

  const fetchNews = async () => {
    try {
      const response = await fetch('/api/admin/news?limit=100');
      const data = await response.json();
      setNews(data);
    } catch (error) {
      console.error('获取新闻列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredNews = news.filter(article => 
    article.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    article.topic.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return <div className="flex items-center justify-center h-64">加载中...</div>;
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>新闻管理</CardTitle>
          <CardDescription>查看和管理所有新闻文章</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索新闻标题或主题..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
              />
            </div>
            <Button variant="outline">刷新数据</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>文章信息</TableHead>
                <TableHead>主题</TableHead>
                <TableHead>来源</TableHead>
                <TableHead>发布时间</TableHead>
                <TableHead>抓取时间</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredNews.map((article) => (
                <TableRow key={article.id}>
                  <TableCell>
                    <div className="space-y-1">
                      <p className="font-medium line-clamp-1">{article.title}</p>
                      <p className="text-sm text-muted-foreground line-clamp-2">
                        {article.summary}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-xs">
                      {article.topic}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Tag className="h-3 w-3 text-muted-foreground" />
                      <span className="text-sm">{article.source}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="h-3 w-3" />
                      {new Date(article.published_at).toLocaleDateString()}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="h-3 w-3" />
                      {new Date(article.created_at).toLocaleDateString()}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {filteredNews.length === 0 && (
            <div className="py-8 text-center text-muted-foreground">
              暂无新闻数据
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总文章数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{news.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">主题数量</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {new Set(news.map(n => n.topic)).size}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">今日新增</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {news.filter(n => {
                const today = new Date();
                const created = new Date(n.created_at);
                return today.toDateString() === created.toDateString();
              }).length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">本周新增</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {news.filter(n => {
                const weekAgo = new Date();
                weekAgo.setDate(weekAgo.getDate() - 7);
                return new Date(n.created_at) >= weekAgo;
              }).length}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
