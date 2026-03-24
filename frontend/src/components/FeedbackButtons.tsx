import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { toast } from '@/components/ui/use-toast';
import { api } from '@/lib/api';

interface FeedbackButtonsProps {
  newsId: number;
  className?: string;
}

export function FeedbackButtons({ newsId, className = "" }: FeedbackButtonsProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasLiked, setHasLiked] = useState(false);
  const [hasDisliked, setHasDisliked] = useState(false);

  const handleFeedback = async (feedbackType: 'like' | 'dislike') => {
    if (isSubmitting) return;

    setIsSubmitting(true);
    try {
      await api.feedback.createFeedback({
        news_id: newsId,
        feedback_type: feedbackType
      });

      // 更新本地状态
      if (feedbackType === 'like') {
        setHasLiked(true);
        setHasDisliked(false);
      } else {
        setHasDisliked(true);
        setHasLiked(false);
      }

      toast({
        title: '反馈已提交',
        description: '感谢你的反馈！',
        duration: 2000
      });
    } catch (error) {
      console.error('提交反馈失败:', error);
      toast({
        title: '提交失败',
        description: '请稍后重试',
        variant: 'destructive',
        duration: 2000
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => handleFeedback('like')}
        disabled={isSubmitting}
        className={`h-8 px-2 ${hasLiked ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400' : 'text-slate-500 dark:text-slate-400 hover:text-green-600 dark:hover:text-green-400'}`}
        title="这篇摘要有用"
      >
        <span className="text-lg">👍</span>
        <span className="sr-only">有用</span>
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={() => handleFeedback('dislike')}
        disabled={isSubmitting}
        className={`h-8 px-2 ${hasDisliked ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400' : 'text-slate-500 dark:text-slate-400 hover:text-red-600 dark:hover:text-red-400'}`}
        title="这篇摘要无用"
      >
        <span className="text-lg">👎</span>
        <span className="sr-only">无用</span>
      </Button>
    </div>
  );
}
