'use client';

import { useState } from 'react';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface PDFViewerProps {
  pdfUrl: string | null;
  filename: string;
}

export function PDFViewer({ pdfUrl, filename }: PDFViewerProps) {
  const [zoom, setZoom] = useState(100);

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 25, 200));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 25, 50));
  const handleReset = () => setZoom(100);

  if (!pdfUrl) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>PDF Preview</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-96 bg-gray-100 rounded-lg">
            <p className="text-gray-500">PDF not available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="flex flex-col h-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg truncate">{filename}</CardTitle>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleZoomOut} disabled={zoom <= 50}>
              <ZoomOut className="w-4 h-4" />
            </Button>
            <span className="text-sm font-medium w-12 text-center">{zoom}%</span>
            <Button variant="outline" size="sm" onClick={handleZoomIn} disabled={zoom >= 200}>
              <ZoomIn className="w-4 h-4" />
            </Button>
            <Button variant="outline" size="sm" onClick={handleReset}>
              <Maximize2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 p-0">
        <div className="h-full overflow-auto bg-gray-100 p-4">
          <div
            style={{
              transform: `scale(${zoom / 100})`,
              transformOrigin: 'top center',
              transition: 'transform 0.2s',
            }}
          >
            <iframe
              src={pdfUrl}
              className="w-full border-0 rounded-lg bg-white shadow-lg"
              style={{ height: '800px', minHeight: '600px' }}
              title={filename}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
