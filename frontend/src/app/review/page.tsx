'use client';

import { useSearchParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { ArrowLeft, ChevronLeft, ChevronRight } from 'lucide-react';

import { getSampleDetail, listSamples } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { PDFViewer } from '@/components/pdf-viewer';
import { ComparisonView } from '@/components/comparison-view';
import { ValidationActions } from '@/components/validation-actions';
import { Badge } from '@/components/ui/badge';

export default function ReviewPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const sampleId = searchParams.get('id');

  // Fetch sample detail
  const { data: sample, isLoading, error } = useQuery({
    queryKey: ['sample', sampleId],
    queryFn: () => getSampleDetail(sampleId!),
    enabled: !!sampleId,
  });

  // Fetch all processed samples for navigation (exclude pending/processing)
  const { data: samplesData } = useQuery({
    queryKey: ['samples', 'all-processed'],
    queryFn: () => listSamples({ limit: 100 }),
  });

  // Filter to only processed samples (not pending/processing)
  const processedSamples = samplesData?.samples.filter(
    (s) => s.status !== 'pending' && s.status !== 'processing'
  ) ?? [];

  // Find current sample index for navigation
  const currentIndex = processedSamples.findIndex((s) => s.id === sampleId);
  const hasPrevious = currentIndex > 0;
  const hasNext = currentIndex >= 0 && currentIndex < processedSamples.length - 1;

  const handlePrevious = () => {
    if (hasPrevious) {
      const prevSample = processedSamples[currentIndex - 1];
      router.push(`/review?id=${prevSample.id}`);
    }
  };

  const handleNext = () => {
    if (hasNext) {
      const nextSample = processedSamples[currentIndex + 1];
      router.push(`/review?id=${nextSample.id}`);
    }
  };

  if (!sampleId) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 mb-4">No sample ID provided</p>
          <Link href="/">
            <Button>Go to Home</Button>
          </Link>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-gray-500">Loading sample...</p>
        </div>
      </div>
    );
  }

  if (error || !sample) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 mb-4">
            {error instanceof Error ? error.message : 'Failed to load sample'}
          </p>
          <Link href="/">
            <Button>Go to Home</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/">
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
              </Link>
              <div>
                <h1 className="text-xl font-bold">{sample.filename}</h1>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant={sample.status === 'needs_review' ? 'outline' : 'default'}>
                    {sample.status}
                  </Badge>
                  {sample.match_score !== null && (
                    <span className="text-sm text-gray-500">
                      Match: {(sample.match_score * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Navigation */}
            <div className="flex items-center gap-2">
              {samplesData && (
                <span className="text-sm text-gray-500 mr-2">
                  {currentIndex + 1} / {samplesData.samples.length}
                </span>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={handlePrevious}
                disabled={!hasPrevious}
              >
                <ChevronLeft className="w-4 h-4" />
                Previous
              </Button>
              <Button variant="outline" size="sm" onClick={handleNext} disabled={!hasNext}>
                Next
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content - Split View */}
      <main className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-180px)]">
          {/* Left: PDF Viewer */}
          <div className="h-full">
            <PDFViewer pdfUrl={sample.pdf_url} filename={sample.filename} />
          </div>

          {/* Right: Comparison + Actions */}
          <div className="space-y-6 h-full overflow-auto">
            <ComparisonView sample={sample} />
            <ValidationActions
              sample={sample}
              onValidated={() => {
                // After validation, go to next sample if available
                if (hasNext) {
                  handleNext();
                } else {
                  router.push('/');
                }
              }}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
