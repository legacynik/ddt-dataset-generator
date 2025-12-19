'use client';

import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, AlertCircle, Clock, FileText } from 'lucide-react';

import { getPreviousResults } from '@/lib/api';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export function PreviousResults() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['previous-results'],
    queryFn: getPreviousResults,
    staleTime: Infinity, // This data doesn't change
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Previous Results</CardTitle>
          <CardDescription>Loading previous processing report...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (error || !data) {
    return null; // Hide if no previous results available
  }

  const formatPercentage = (rate: number) => `${(rate * 100).toFixed(1)}%`;
  const formatTime = (seconds: number) => `${seconds.toFixed(1)}s`;

  return (
    <Card className="border-blue-200 bg-blue-50/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-blue-900">Previous Results</CardTitle>
            <CardDescription className="text-blue-700">
              Report generated: {data.generated_at}
            </CardDescription>
          </div>
          <Badge variant="outline" className="bg-blue-100 text-blue-900 border-blue-300">
            Historical Data
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total PDFs */}
          <div className="flex items-start space-x-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <FileText className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Total PDFs</p>
              <p className="text-2xl font-bold text-gray-900">{data.total_pdfs}</p>
            </div>
          </div>

          {/* Auto-Validated */}
          <div className="flex items-start space-x-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <CheckCircle2 className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Auto-Validated</p>
              <p className="text-2xl font-bold text-gray-900">{data.auto_validated_count}</p>
              <p className="text-xs text-gray-400">
                {formatPercentage(data.auto_validated_count / data.total_pdfs)}
              </p>
            </div>
          </div>

          {/* Needs Review */}
          <div className="flex items-start space-x-3">
            <div className="p-2 bg-yellow-100 rounded-lg">
              <AlertCircle className="w-5 h-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Needs Review</p>
              <p className="text-2xl font-bold text-gray-900">{data.needs_review_count}</p>
              <p className="text-xs text-gray-400">
                {formatPercentage(data.needs_review_count / data.total_pdfs)}
              </p>
            </div>
          </div>

          {/* Avg Processing Time */}
          <div className="flex items-start space-x-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Clock className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Avg Time/PDF</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatTime(data.avg_processing_time)}
              </p>
            </div>
          </div>
        </div>

        {/* Success Rates */}
        <div className="mt-6 pt-6 border-t border-blue-200">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Extractor Success Rates</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Datalab</span>
                <span className="font-medium text-gray-900">
                  {formatPercentage(data.datalab_success_rate)}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full"
                  style={{ width: `${data.datalab_success_rate * 100}%` }}
                />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Azure OCR</span>
                <span className="font-medium text-gray-900">
                  {formatPercentage(data.azure_success_rate)}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-green-600 h-2 rounded-full"
                  style={{ width: `${data.azure_success_rate * 100}%` }}
                />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Gemini</span>
                <span className="font-medium text-gray-900">
                  {formatPercentage(data.gemini_success_rate)}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-purple-600 h-2 rounded-full"
                  style={{ width: `${data.gemini_success_rate * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
