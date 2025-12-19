'use client';

import Link from 'next/link';
import { FileDown } from 'lucide-react';

import { UploadZone } from '@/components/upload-zone';
import { ProcessingStatus } from '@/components/processing-status';
import { SamplesTable } from '@/components/samples-table';
import { PreviousResults } from '@/components/previous-results';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">DDT Dataset Generator</h1>
              <p className="text-sm text-gray-500">
                Generate training datasets from Italian DDT documents
              </p>
            </div>
            <Link href="/export">
              <Button variant="outline">
                <FileDown className="w-4 h-4 mr-2" />
                Export Dataset
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 space-y-8">
        {/* Previous Results Section */}
        <section>
          <PreviousResults />
        </section>

        <Separator />

        {/* Upload Section */}
        <section>
          <h2 className="text-lg font-semibold mb-4">Upload PDFs</h2>
          <UploadZone />
        </section>

        <Separator />

        {/* Processing Status Section */}
        <section>
          <h2 className="text-lg font-semibold mb-4">Processing Status</h2>
          <ProcessingStatus />
        </section>

        <Separator />

        {/* Samples Table Section */}
        <section>
          <h2 className="text-lg font-semibold mb-4">All Samples</h2>
          <SamplesTable />
        </section>
      </main>
    </div>
  );
}
