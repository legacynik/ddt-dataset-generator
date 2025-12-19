'use client';

import { useQuery } from '@tanstack/react-query';
import { FileText, CheckCircle, AlertCircle, XCircle } from 'lucide-react';
import { getStatus } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function ExportSummary() {
  const { data: status } = useQuery({
    queryKey: ['status'],
    queryFn: getStatus,
  });

  if (!status) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Dataset Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-500">Loading...</p>
        </CardContent>
      </Card>
    );
  }

  const exportableCount = status.auto_validated + status.manually_validated;
  const needsReviewCount = status.needs_review;
  const errorCount = status.errors;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Dataset Summary</CardTitle>
        <CardDescription>Overview of samples ready for export</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Main Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            icon={<FileText className="w-5 h-5" />}
            label="Total Samples"
            value={status.total}
            variant="default"
          />
          <StatCard
            icon={<CheckCircle className="w-5 h-5" />}
            label="Exportable"
            value={exportableCount}
            variant="success"
          />
          <StatCard
            icon={<AlertCircle className="w-5 h-5" />}
            label="Needs Review"
            value={needsReviewCount}
            variant="warning"
          />
          <StatCard
            icon={<XCircle className="w-5 h-5" />}
            label="Errors"
            value={errorCount}
            variant="destructive"
          />
        </div>

        {/* Breakdown */}
        <div className="border-t pt-4">
          <h4 className="text-sm font-medium mb-3">Validation Breakdown</h4>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Auto-validated</span>
              <span className="font-medium">{status.auto_validated}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Manually validated</span>
              <span className="font-medium">{status.manually_validated}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Pending</span>
              <span className="font-medium text-gray-400">{status.pending}</span>
            </div>
          </div>
        </div>

        {/* Export Ready Message */}
        {exportableCount > 0 ? (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-sm text-green-800 font-medium">
              ✓ {exportableCount} sample{exportableCount > 1 ? 's' : ''} ready for export
            </p>
          </div>
        ) : (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-sm text-yellow-800 font-medium">
              ⚠ No samples available for export. Process and validate some samples first.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function StatCard({
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
