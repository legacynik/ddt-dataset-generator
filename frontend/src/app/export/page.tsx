'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useMutation } from '@tanstack/react-query';
import { ArrowLeft, Download, FileText, BarChart3 } from 'lucide-react';
import { toast } from 'sonner';

import { exportDataset, type ExportResponse } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ExportSummary } from '@/components/export-summary';
import { ExportSettings } from '@/components/export-settings';

export default function ExportPage() {
  const [ocrSource, setOcrSource] = useState<'azure' | 'datalab'>('azure');
  const [validationSplit, setValidationSplit] = useState(0.07); // 7%
  const [exportResult, setExportResult] = useState<ExportResponse | null>(null);

  const exportMutation = useMutation({
    mutationFn: () => exportDataset({ ocr_source: ocrSource, validation_split: validationSplit }),
    onSuccess: (data) => {
      setExportResult(data);
      toast.success('Dataset exported successfully!');
    },
    onError: (error: Error) => {
      toast.error(`Export failed: ${error.message}`);
    },
  });

  const handleExport = () => {
    exportMutation.mutate();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link href="/">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Home
              </Button>
            </Link>
            <h1 className="text-2xl font-bold">Export Dataset</h1>
            <div className="w-24" /> {/* Spacer for alignment */}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 space-y-6 max-w-5xl">
        {/* Summary */}
        <ExportSummary />

        {/* Settings */}
        <ExportSettings
          ocrSource={ocrSource}
          validationSplit={validationSplit}
          onOcrSourceChange={setOcrSource}
          onValidationSplitChange={setValidationSplit}
        />

        {/* Export Button */}
        <Card>
          <CardHeader>
            <CardTitle>Generate Dataset</CardTitle>
            <CardDescription>
              Export validated samples to Alpaca JSONL format for LLM fine-tuning
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              onClick={handleExport}
              disabled={exportMutation.isPending}
              size="lg"
              className="w-full"
            >
              {exportMutation.isPending ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  Generating...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4 mr-2" />
                  Export Dataset
                </>
              )}
            </Button>

            <p className="text-sm text-gray-500 text-center">
              Files will be generated in JSONL format compatible with LLaMA Factory
            </p>
          </CardContent>
        </Card>

        {/* Export Result */}
        {exportResult && (
          <Card className="border-green-200 bg-green-50">
            <CardHeader>
              <CardTitle className="text-green-900">Export Complete!</CardTitle>
              <CardDescription className="text-green-700">
                Your dataset has been generated successfully
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-white rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-green-900">
                    {exportResult.total_samples}
                  </div>
                  <div className="text-sm text-gray-600">Total Samples</div>
                </div>
                <div className="bg-white rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-green-900">
                    {exportResult.training_samples}
                  </div>
                  <div className="text-sm text-gray-600">Training</div>
                </div>
                <div className="bg-white rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-green-900">
                    {exportResult.validation_samples}
                  </div>
                  <div className="text-sm text-gray-600">Validation</div>
                </div>
              </div>

              {/* Download Links */}
              <div className="space-y-2">
                <h4 className="font-medium text-green-900 mb-2">Download Files:</h4>
                <a
                  href={exportResult.download_urls.training}
                  className="flex items-center gap-2 p-3 bg-white rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <FileText className="w-5 h-5 text-green-600" />
                  <span className="flex-1 font-medium">train.jsonl</span>
                  <Download className="w-4 h-4 text-gray-400" />
                </a>
                <a
                  href={exportResult.download_urls.validation}
                  className="flex items-center gap-2 p-3 bg-white rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <FileText className="w-5 h-5 text-green-600" />
                  <span className="flex-1 font-medium">validation.jsonl</span>
                  <Download className="w-4 h-4 text-gray-400" />
                </a>
                <a
                  href={exportResult.download_urls.report}
                  className="flex items-center gap-2 p-3 bg-white rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <BarChart3 className="w-5 h-5 text-green-600" />
                  <span className="flex-1 font-medium">quality_report.json</span>
                  <Download className="w-4 h-4 text-gray-400" />
                </a>
              </div>

              {/* Quality Report */}
              {exportResult.quality_report && (
                <div className="bg-white rounded-lg p-4">
                  <h4 className="font-medium mb-3">Quality Metrics</h4>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Overall Quality Score</span>
                      <span className="font-bold text-green-900">
                        {(exportResult.quality_report.quality_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 mt-2">
                      Field coverage: {Object.keys(exportResult.quality_report.field_coverage).length} fields tracked
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
