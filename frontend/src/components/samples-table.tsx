'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { FileText, ChevronRight } from 'lucide-react';

import { listSamples, type SampleStatus } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

const STATUS_LABELS: Record<SampleStatus, string> = {
  pending: 'Pending',
  processing: 'Processing',
  auto_validated: 'Auto Validated',
  needs_review: 'Needs Review',
  manually_validated: 'Manually Validated',
  rejected: 'Rejected',
  error: 'Error',
};

const STATUS_VARIANTS: Record<
  SampleStatus,
  'default' | 'secondary' | 'outline' | 'destructive'
> = {
  pending: 'secondary',
  processing: 'default',
  auto_validated: 'default',
  needs_review: 'outline',
  manually_validated: 'default',
  rejected: 'destructive',
  error: 'destructive',
};

export function SamplesTable() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState<SampleStatus | 'all'>('all');
  const [page, setPage] = useState(0);
  const limit = 20;

  const { data, isLoading } = useQuery({
    queryKey: ['samples', statusFilter, page],
    queryFn: () =>
      listSamples({
        status: statusFilter === 'all' ? undefined : statusFilter,
        limit,
        offset: page * limit,
      }),
  });

  const handleRowClick = (sampleId: string, status: SampleStatus) => {
    // Allow review for all processed samples (not pending/processing)
    if (status !== 'pending' && status !== 'processing') {
      router.push(`/review?id=${sampleId}`);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Samples</CardTitle>
            <CardDescription>
              {data?.total || 0} total samples
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Status Filter Tabs */}
        <Tabs value={statusFilter} onValueChange={(v) => {
          setStatusFilter(v as SampleStatus | 'all');
          setPage(0);
        }}>
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="pending">Pending</TabsTrigger>
            <TabsTrigger value="auto_validated">Auto</TabsTrigger>
            <TabsTrigger value="needs_review">Review</TabsTrigger>
            <TabsTrigger value="error">Errors</TabsTrigger>
          </TabsList>
        </Tabs>

        {/* Table */}
        {isLoading ? (
          <div className="text-center py-12 text-gray-500">Loading...</div>
        ) : !data || data.samples.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p className="text-gray-500">No samples found</p>
            <p className="text-sm text-gray-400 mt-1">Upload some PDFs to get started</p>
          </div>
        ) : (
          <>
            <div className="border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Filename</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Match Score</TableHead>
                    <TableHead>Discrepancies</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.samples.map((sample) => {
                    const isClickable = sample.status !== 'pending' && sample.status !== 'processing';
                    return (
                    <TableRow
                      key={sample.id}
                      className={
                        isClickable
                          ? 'cursor-pointer hover:bg-gray-50'
                          : 'cursor-default'
                      }
                      onClick={() => handleRowClick(sample.id, sample.status)}
                    >
                      <TableCell className="font-medium">
                        {sample.filename}
                      </TableCell>
                      <TableCell>
                        <Badge variant={STATUS_VARIANTS[sample.status]}>
                          {STATUS_LABELS[sample.status]}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {sample.match_score !== null
                          ? `${(sample.match_score * 100).toFixed(0)}%`
                          : '-'}
                      </TableCell>
                      <TableCell>
                        {sample.discrepancies && sample.discrepancies.length > 0
                          ? sample.discrepancies.length
                          : '-'}
                      </TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {new Date(sample.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right">
                        {isClickable && (
                          <Button variant="ghost" size="sm">
                            Review
                            <ChevronRight className="w-4 h-4 ml-1" />
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>

            {/* Pagination */}
            {data.total > limit && (
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-500">
                  Showing {page * limit + 1}-
                  {Math.min((page + 1) * limit, data.total)} of {data.total}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(page - 1)}
                    disabled={page === 0}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(page + 1)}
                    disabled={(page + 1) * limit >= data.total}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
