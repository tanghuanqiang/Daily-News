import { useEffect } from 'react';
import { 
  XCircle
} from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface RagStatusProps {
  showDetails?: boolean;
  onStatusChange?: (isEnabled: boolean) => void;
}

export function RagStatus({ showDetails = false, onStatusChange }: RagStatusProps) {
  // RAG功能已禁用，直接返回false
  useEffect(() => {
    onStatusChange?.(false);
  }, [onStatusChange]);

  // RAG已禁用，简洁模式下返回空或禁用图标
  if (!showDetails) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-1">
              <XCircle className="h-4 w-4 text-slate-400" />
            </div>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-xs">
            <p className="text-sm text-slate-400">RAG增强未启用</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  // 详细模式（用于设置页面显示）
  return (
    <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
      <div className="flex items-center gap-2 mb-3">
        <XCircle className="h-5 w-5 text-slate-400" />
        <span className="font-medium text-slate-900 dark:text-slate-100">RAG系统状态</span>
      </div>
      <div className="flex items-center gap-2">
        <XCircle className="h-4 w-4 text-slate-400" />
        <span className="text-sm text-slate-500">未启用</span>
      </div>
    </div>
  );
}

export default RagStatus;

