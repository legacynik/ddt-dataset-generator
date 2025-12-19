'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Play, CheckCircle, AlertCircle, Clock } from 'lucide-react';
import { toast } from 'sonner';

import { getStatus, startProcessing } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';

export function ProcessingStatus() {
  const queryClient = useQueryClient();

  // Poll status every 2 seconds when processing
  const { data: status, isLoading } = useQuery({
    queryKey: ['status'],
    queryFn: getStatus,
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.is_processing ? 2000 : 30000; // 2s when processing, 30s otherwise
    },
  });

  const startProcessingMutation = useMutation({
    mutationFn: () => startProcessing(),
    onSuccess: (data) => {
      toast.success(data.message);
      queryClient.invalidateQueries({ queryKey: ['status'] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to start processing: ${error.message}`);
    },
  });

  if (isLoading || !status) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Processing Status</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">Loading...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Processing Status</CardTitle>
          {status.is_processing && (
            <Badge variant="secondary" className="animate-pulse">
              Processing...
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Progress</span>
            <span className="font-medium">
              {status.processed}/{status.total} ({status.progress_percent.toFixed(1)}%)
            </span>
          </div>
          <Progress value={status.progress_percent} className="h-2" />
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatusCard
            icon={<Clock className="w-5 h-5" />}
            label="Pending"
            value={status.pending}
            variant="default"
          />
          <StatusCard
            icon={<CheckCircle className="w-5 h-5" />}
            label="Auto Validated"
            value={status.auto_validated}
            variant="success"
          />
          <StatusCard
            icon={<AlertCircle className="w-5 h-5" />}
            label="Needs Review"
            value={status.needs_review}
            variant="warning"
          />
          <StatusCard
            icon={<AlertCircle className="w-5 h-5" />}
            label="Errors"
            value={status.errors}
            variant="destructive"
          />
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <Button
            onClick={() => startProcessingMutation.mutate()}
            disabled={status.is_processing || status.pending === 0 || startProcessingMutation.isPending}
            className="flex-1"
          >
            <Play className="w-4 h-4 mr-2" />
            {status.is_processing ? 'Processing...' : 'Start Processing'}
          </Button>
          <Button
            variant="outline"
            onClick={() => queryClient.invalidateQueries({ queryKey: ['samples'] })}
          >
            Refresh
          </Button>
        </div>

        {status.pending === 0 && status.total > 0 && (
          <p className="text-sm text-center text-gray-500">
            All samples have been processed. Upload more PDFs to continue.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function StatusCard({
  icon,
  label,
  value,
  variant,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  variant: 'default' | 'success' | 'warning' | 'destructive';
}) {
  const variantStyles = {
    default: 'bg-gray-50 text-gray-700',
    success: 'bg-green-50 text-green-700',
    warning: 'bg-yellow-50 text-yellow-700',
    destructive: 'bg-red-50 text-red-700',
  };

  return (
    <div className={`p-4 rounded-lg ${variantStyles[variant]}`}>
      <div className="flex items-center gap-2 mb-1">{icon}</div>
      <div className="text-2xl font-bold mb-1">{value}</div>
      <div className="text-xs font-medium">{label}</div>
    </div>
  );
}
