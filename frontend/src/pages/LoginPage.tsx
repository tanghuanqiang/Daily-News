import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { authAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Newspaper, Loader2, Mail, Lock, AlertCircle } from 'lucide-react';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const navigate = useNavigate();
  const { setToken, setUser } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await authAPI.login(email, password);
      const { access_token } = response.data;
      
      setToken(access_token);
      
      // Fetch user info
      const userResponse = await authAPI.getMe();
      setUser(userResponse.data);
      
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || '登录失败，请检查邮箱和密码');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-4">
      <Card className="w-full max-w-md border-slate-200 dark:border-slate-700 shadow-lg">
        <CardHeader className="space-y-4 text-center">
          <div className="mx-auto p-3 rounded-full bg-primary/10 dark:bg-primary/20 w-fit">
            <Newspaper className="h-8 w-8 text-primary" />
          </div>
          <div>
            <CardTitle className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-slate-50">
              Daily Digest
            </CardTitle>
            <CardDescription className="text-base mt-2 text-slate-600 dark:text-slate-400">
              登录您的账户查看每日新闻摘要
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium text-slate-900 dark:text-slate-50 flex items-center gap-2">
                <Mail className="h-4 w-4 text-slate-500 dark:text-slate-400" />
                邮箱
              </label>
              <Input
                id="email"
                type="email"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="h-11 border-slate-300 dark:border-slate-600 focus:border-primary"
                required
                disabled={loading}
              />
            </div>
            
            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium text-slate-900 dark:text-slate-50 flex items-center gap-2">
                <Lock className="h-4 w-4 text-slate-500 dark:text-slate-400" />
                密码
              </label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="h-11 border-slate-300 dark:border-slate-600 focus:border-primary"
                required
                disabled={loading}
              />
            </div>

            {error && (
              <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
              </div>
            )}

            <Button
              type="submit"
              className="w-full h-11 cursor-pointer transition-colors"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  登录中...
                </>
              ) : (
                '登录'
              )}
            </Button>

            <div className="flex flex-col items-center gap-3 text-sm pt-2">
              <Link 
                to="/forgot-password" 
                className="text-primary hover:text-primary/80 hover:underline transition-colors cursor-pointer"
              >
                忘记密码？
              </Link>
              <div className="text-slate-600 dark:text-slate-400">
                还没有账户？{' '}
                <Link 
                  to="/register" 
                  className="text-primary hover:text-primary/80 hover:underline font-medium transition-colors cursor-pointer"
                >
                  立即注册
                </Link>
              </div>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
