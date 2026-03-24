import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { toast } from '@/components/ui/use-toast';
import { api } from '@/lib/api';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface ShareButtonProps {
  newsId: number;
  title: string;
  summary: string;
  className?: string;
  useRoastMode?: boolean;
}

export function ShareButton({ 
  newsId, 
  title, 
  summary, 
  className = "", 
  useRoastMode = false 
}: ShareButtonProps) {
  const [isSharing, setIsSharing] = useState(false);

  const handleShare = async (platform: string) => {
    if (isSharing) return;

    setIsSharing(true);
    try {
      // 生成分享文案
      const shareContent = await api.sharing.generateShareContent({
        news_id: newsId,
        platform,
        use_roast_mode: useRoastMode
      });

      // 记录分享行为
      await api.sharing.trackShare({
        news_id: newsId,
        platform
      });

      // 根据不同平台处理
      if (platform === 'copy') {
        // 复制到剪贴板
        await navigator.clipboard.writeText(shareContent.text);
        toast({
          title: '已复制到剪贴板',
          description: '分享文案已复制',
          duration: 2000
        });
      } else {
        // 其他平台，打开新窗口或提示
        toast({
          title: '准备分享',
          description: `分享到${platform}`,
          duration: 2000
        });
        
        // 如果是Web Share API支持的，使用它
        if (navigator.share && platform === 'wechat') {
          try {
            await navigator.share({
              title: title,
              text: summary,
              url: shareContent.url
            });
          } catch (error) {
            // 用户取消分享
          }
        }
      }
    } catch (error) {
      console.error('分享失败:', error);
      toast({
        title: '分享失败',
        description: '请稍后重试',
        variant: 'destructive',
        duration: 2000
      });
    } finally {
      setIsSharing(false);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          disabled={isSharing}
          className={`h-8 px-2 text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 ${className}`}
          title="分享这条新闻"
        >
          <span className="text-lg">📤</span>
          <span className="sr-only">分享</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuItem onClick={() => handleShare('wechat')}>
          <span className="mr-2">💬</span>
          微信
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleShare('weibo')}>
          <span className="mr-2">📝</span>
          微博
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleShare('twitter')}>
          <span className="mr-2">🐦</span>
          Twitter
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleShare('copy')}>
          <span className="mr-2">📋</span>
          复制链接
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
