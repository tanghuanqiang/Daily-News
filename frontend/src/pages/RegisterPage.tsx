import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { authAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Newspaper, Loader2, Mail, Lock, AlertCircle, CheckCircle2, UserPlus, Eye, EyeOff } from 'lucide-react';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [resendTimer, setResendTimer] = useState(0);
  const [showPasswords, setShowPasswords] = useState(false); // 联动控制两个密码框
  
  const navigate = useNavigate();
  const { setToken, setUser } = useAuthStore();

  // Timer for resending verification code
  useEffect(() => {
    if (resendTimer > 0) {
      const timer = setTimeout(() => setResendTimer(resendTimer - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendTimer]);

  // Handle sending verification code
  const handleSendVerificationCode = async () => {
    if (!email) {
      setError('请先输入邮箱');
      return;
    }

    // 先检查错误信息，如果是邮箱已注册，则不显示发送中状态
    if (error.includes('邮箱已注册') || error.includes('Email already registered')) {
      return;
    }

    setSendingCode(true);
    setError('');
    
    try {
      await authAPI.sendVerificationCode(email);
      setSuccessMessage('验证码已发送到您的邮箱，请查收');
      setResendTimer(60); // 60秒后可重新发送
    } catch (err: any) {
      setError(err.response?.data?.detail || '发送验证码失败');
    } finally {
      setSendingCode(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');

    if (password !== confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }

    if (password.length < 6) {
      setError('密码长度至少为6个字符');
      return;
    }

    if (!verificationCode) {
      setError('请输入验证码');
      return;
    }

    setLoading(true);

    try {
      // First verify the code
      await authAPI.verifyCode(email, verificationCode);
      
      // Then register the user
      const response = await authAPI.register(email, password);
      const { access_token } = response.data;
      
      setToken(access_token);
      
      // Fetch user info
      const userResponse = await authAPI.getMe();
      setUser(userResponse.data);
      
      navigate('/dashboard');
    } catch (err: any) {
      // Handle different error cases
      if (err.response?.data?.detail?.includes('验证码') || err.response?.status === 400) {
        setError('验证码无效或已过期');
      } else {
        setError(err.response?.data?.detail || '注册失败，请稍后重试');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-4">
      <Card className="w-full max-w-md border-slate-200 dark:border-slate-700 shadow-lg">
        <CardHeader className="space-y-4 text-center">
          <div className="mx-auto p-3 rounded-full bg-primary/10 dark:bg-primary/20 w-fit">
            <UserPlus className="h-8 w-8 text-primary" />
          </div>
          <div>
            <CardTitle className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-slate-50">
              创建账户
            </CardTitle>
            <CardDescription className="text-base mt-2 text-slate-600 dark:text-slate-400">
              注册并开始个性化新闻订阅
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
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleSendVerificationCode}
                disabled={sendingCode || resendTimer > 0 || (!!error && (error.includes('邮箱已注册') || error.includes('Email already registered')))}
                className="w-full h-9 cursor-pointer transition-colors"
              >
                {sendingCode ? (
                  <>
                    <Loader2 className="h-3 w-3 mr-2 animate-spin" />
                    发送中...
                  </>
                ) : resendTimer > 0 ? (
                  `重新发送 (${resendTimer}s)`
                ) : (
                  '发送验证码'
                )}
              </Button>
            </div>
            
            <div className="space-y-2">
              <label htmlFor="verificationCode" className="text-sm font-medium text-slate-900 dark:text-slate-50">
                验证码
              </label>
              <Input
                id="verificationCode"
                type="text"
                placeholder="输入验证码"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value)}
                className="h-11 border-slate-300 dark:border-slate-600 focus:border-primary text-center text-lg tracking-widest"
                required
                disabled={loading}
              />
            </div>
            
            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium text-slate-900 dark:text-slate-50 flex items-center gap-2">
                <Lock className="h-4 w-4 text-slate-500 dark:text-slate-400" />
                密码
              </label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPasswords ? "text" : "password"}
                  placeholder="至少6个字符"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-11 border-slate-300 dark:border-slate-600 focus:border-primary pr-10"
                  required
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPasswords(!showPasswords)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
                  disabled={loading}
                  title={showPasswords ? "隐藏密码" : "显示密码"}
                >
                  {showPasswords ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <div className="space-y-2">
              <label htmlFor="confirmPassword" className="text-sm font-medium text-slate-900 dark:text-slate-50 flex items-center gap-2">
                <Lock className="h-4 w-4 text-slate-500 dark:text-slate-400" />
                确认密码
              </label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type={showPasswords ? "text" : "password"}
                  placeholder="再次输入密码"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="h-11 border-slate-300 dark:border-slate-600 focus:border-primary pr-10"
                  required
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPasswords(!showPasswords)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
                  disabled={loading}
                  title={showPasswords ? "隐藏密码" : "显示密码"}
                >
                  {showPasswords ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
              </div>
            )}

            {successMessage && (
              <div className="flex items-start gap-2 p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-green-600 dark:text-green-400">{successMessage}</p>
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
                  注册中...
                </>
              ) : (
                '注册'
              )}
            </Button>

            <div className="text-center text-sm pt-2">
              <span className="text-slate-600 dark:text-slate-400">已有账户？</span>{' '}
              <Link 
                to="/login" 
                className="text-primary hover:text-primary/80 hover:underline font-medium transition-colors cursor-pointer"
              >
                立即登录
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
