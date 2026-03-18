import { useState, useEffect } from 'react';
import { newsAPI } from '@/lib/api';
import { 
  Database, 
  Zap, 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  Loader2,
  RefreshCw
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface RagStatusData {
  is_enabled: boolean;
  vector_store_status: {
    total_vectors: number;
    collection_name: string;
    last_indexed: string | null;
  };
  embedding_model: string;
  index_coverage: number;
}

interface RagStatusProps {
  showDetails?: boolean;
  onStatusChange?: (isEnabled: boolean) => void;
}

export function RagStatus({ showDetails = false, onStatusChange }: RagStatusProps) {
  const [status, setStatus] = useState<RagStatusData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await newsAPI.getRagStatus();
      setStatus(response.data);
      onStatusChange?.(response.data.is_enabled);
    } catch (err: any) {
      console.error('Failed to load RAG status:', err);
      setError(err.response?.data?.detail || '获取RAG状态失败');
      onStatusChange?.(false);
    } finally {
      setLoading(false);
    }
  };

  // 简洁模式（用于header显示）
  if (!showDetails) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-1">
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
              ) : error || !status?.is_enabled ? (
                <XCircle className="h-4 w-4 text-slate-400" />
              ) : (
                <div className="flex items-center gap-1">
                  <Zap className="h-4 w-4 text-purple-500" />
                  <span className="text-xs text-purple-500 font-medium">
                    RAG
                  </span>
                </div>
              )}
            </div>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-xs">
            {loading ? (
              <p className="text-sm">检查RAG状态中...</p>
            ) : error ? (
              <p className="text-sm text-red-400">{error}</p>
            ) : status?.is_enabled ? (
              <div className="space-y-1">
                <p className="text-sm font-medium text-green-400">RAG增强已启用</p>
                <p className="text-xs text-slate-400">
                  向量库: {status.vector_store_status?.total_vectors || 0} 条新闻已索引
                </p>
                <p className="text-xs text-slate-400">
                  覆盖率: {Math.round((status.index_coverage || 0) * 100)}%
                </p>
              </div>
            ) : (
              <p className="text-sm text-slate-400">RAG增强未启用</p>
            )}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  // 详细模式（用于设置页面显示）
  return (
    <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Database className="h-5 w-5 text-purple-500" />
          <span className="font-medium text-slate-900 dark:text-slate-100">RAG系统状态</span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={loadStatus}
          disabled={loading}
          className="h-8 w-8"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-5 w-5 animate-spin text-purple-500" />
          <span className="ml-2 text-sm text-slate-500">加载状态...</span>
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 text-red-500">
          <AlertCircle className="h-4 w-4" />
          <span className="text-sm">{error}</span>
        </div>
      ) : status ? (
        <div className="space-y-3">
          {/* 主状态 */}
          <div className="flex items-center gap-2">
            {status.is_enabled ? (
              <>
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                <span className="text-sm text-green-600 dark:text-green-400">已启用</span>
              </>
            ) : (
              <>
                <XCircle className="h-4 w-4 text-slate-400" />
                <span className="text-sm text-slate-500">未启用</span>
              </>
            )}
          </div>

          {/* 详细信息 */}
          {status.is_enabled && (
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-slate-500">向量数量:</span>
                <span className="font-medium text-slate-900 dark:text-slate-100">
                  {status.vector_store_status?.total_vectors || 0}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-slate-500">索引覆盖率:</span>
                <span className="font-medium text-slate-900 dark:text-slate-100">
                  {Math.round((status.index_coverage || 0) * 100)}%
                </span>
              </div>
              <div className="flex items-center gap-2 col-span-2">
                <span className="text-slate-500">Embedding模型:</span>
                <span className="font-medium text-slate-900 dark:text-slate-100 text-xs truncate">
                  {status.embedding_model || 'N/A'}
                </span>
              </div>
              {status.vector_store_status?.last_indexed && (
                <div className="flex items-center gap-2 col-span-2">
                  <span className="text-slate-500">最后索引:</span>
                  <span className="font-medium text-slate-900 dark:text-slate-100 text-xs">
                    {new Date(status.vector_store_status.last_indexed).toLocaleString('zh-CN')}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <p className="text-sm text-slate-500">无法获取状态</p>
      )}
    </div>
  );
}

export default RagStatus;
