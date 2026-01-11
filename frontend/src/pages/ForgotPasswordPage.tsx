import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuthStore } from '@/store/authStore';
import { Key, Loader2, Mail, Lock, AlertCircle, CheckCircle2, ArrowLeft } from 'lucide-react';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [resendTimer, setResendTimer] = useState(0);
  const [codeSent, setCodeSent] = useState(false);
  
  const navigate = useNavigate();
  const { setToken, setUser } = useAuthStore();

  // Timer for resending verification code
  useEffect(() => {
    if (resendTimer > 0) {
      const timer = setTimeout(() => setResendTimer(resendTimer - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendTimer]);

  // Handle sending reset password verification code
  const handleSendResetCode = async () => {
    if (!email) {
      setError('请先输入邮箱');
      return;
    }

    setSendingCode(true);
    setError('');
    
    try {
      await authAPI.sendResetPasswordCode(email);
      setSuccessMessage('重置密码验证码已发送到您的邮箱，请查收');
      setResendTimer(60); // 60秒后可重新发送
      setCodeSent(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || '发送验证码失败');
    } finally {
      setSendingCode(false);
    }
  };

  // Handle reset password
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');

    if (newPassword !== confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }

    if (newPassword.length < 6) {
      setError('密码长度至少为6个字符');
      return;
    }

    if (!verificationCode) {
      setError('请输入验证码');
      return;
    }

    setLoading(true);

    try {
      // Reset the password directly, the backend will verify the code
      const response = await authAPI.resetPassword(email, verificationCode, newPassword);
      
      // Save the token for automatic login
      if (response.data.access_token) {
        setToken(response.data.access_token);
        
        // Fetch user info
        const userResponse = await authAPI.getMe();
        setUser(userResponse.data);
      }
      
      setSuccessMessage('密码重置成功，正在跳转至仪表盘...');
      
      // Redirect to dashboard page after 3 seconds
      setTimeout(() => {
        navigate('/dashboard');
      }, 3000);
    } catch (err: any) {
      // Handle different error cases
      let errorMessage = '密码重置失败，请稍后重试';
      
      if (err.response) {
        const { status, data } = err.response;
        
        if (status === 400 || (data?.detail && typeof data.detail === 'string' && data.detail.includes('验证码'))) {
          errorMessage = '验证码无效或已过期';
        } else if (status === 422) {
          errorMessage = '请求参数错误，请检查输入';
        } else if (data?.detail) {
          // Ensure we only display strings
          errorMessage = typeof data.detail === 'string' ? data.detail : '请求处理失败';
        }
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-4">
      <Card className="w-full max-w-md border-slate-200 dark:border-slate-700 shadow-lg">
        <CardHeader className="space-y-4 text-center">
          <div className="mx-auto p-3 rounded-full bg-primary/10 dark:bg-primary/20 w-fit">
            <Key className="h-8 w-8 text-primary" />
          </div>
          <div>
            <CardTitle className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-slate-50">
              重置密码
            </CardTitle>
            <CardDescription className="text-base mt-2 text-slate-600 dark:text-slate-400">
              输入您的邮箱以重置密码
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleResetPassword} className="space-y-5">
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
                disabled={codeSent || loading}
                required
              />
              {!codeSent && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleSendResetCode}
                  disabled={sendingCode || resendTimer > 0}
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
                    '发送重置验证码'
                  )}
                </Button>
              )}
            </div>
            
            {codeSent && (
              <>
                <div className="space-y-2">
                  <label htmlFor="verificationCode" className="text-sm font-medium text-slate-900 dark:text-slate-50">
                    验证码
                  </label>
                  <Input
                    id="verificationCode"
                    type="text"
                    placeholder="输入6位验证码"
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, ''))}
                    maxLength={6}
                    className="h-11 border-slate-300 dark:border-slate-600 focus:border-primary text-center text-lg tracking-widest"
                    required
                    disabled={loading}
                  />
                </div>
                
                <div className="space-y-2">
                  <label htmlFor="newPassword" className="text-sm font-medium text-slate-900 dark:text-slate-50 flex items-center gap-2">
                    <Lock className="h-4 w-4 text-slate-500 dark:text-slate-400" />
                    新密码
                  </label>
                  <Input
                    id="newPassword"
                    type="password"
                    placeholder="至少6个字符"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="h-11 border-slate-300 dark:border-slate-600 focus:border-primary"
                    required
                    disabled={loading}
                  />
                </div>

                <div className="space-y-2">
                  <label htmlFor="confirmPassword" className="text-sm font-medium text-slate-900 dark:text-slate-50 flex items-center gap-2">
                    <Lock className="h-4 w-4 text-slate-500 dark:text-slate-400" />
                    确认新密码
                  </label>
                  <Input
                    id="confirmPassword"
                    type="password"
                    placeholder="再次输入新密码"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="h-11 border-slate-300 dark:border-slate-600 focus:border-primary"
                    required
                    disabled={loading}
                  />
                </div>
              </>
            )}

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

            {codeSent && (
              <Button
                type="submit"
                className="w-full h-11 cursor-pointer transition-colors"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    重置中...
                  </>
                ) : (
                  '重置密码'
                )}
              </Button>
            )}

            <div className="text-center text-sm pt-2">
              <Link 
                to="/login" 
                className="inline-flex items-center gap-1 text-primary hover:text-primary/80 hover:underline font-medium transition-colors cursor-pointer"
              >
                <ArrowLeft className="h-3 w-3" />
                返回登录
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
