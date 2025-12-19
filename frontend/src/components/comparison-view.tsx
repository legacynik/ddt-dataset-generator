'use client';

import { CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { SampleDetail } from '@/lib/api';

interface ComparisonViewProps {
  sample: SampleDetail;
}

const DDT_FIELDS = [
  { key: 'mittente', label: 'Mittente' },
  { key: 'destinatario', label: 'Destinatario' },
  { key: 'indirizzo_destinazione_completo', label: 'Indirizzo Destinazione' },
  { key: 'data_documento', label: 'Data Documento' },
  { key: 'data_trasporto', label: 'Data Trasporto' },
  { key: 'numero_documento', label: 'Numero Documento' },
  { key: 'numero_ordine', label: 'Numero Ordine' },
  { key: 'codice_cliente', label: 'Codice Cliente' },
];

export function ComparisonView({ sample }: ComparisonViewProps) {
  const hasDiscrepancy = (field: string) => {
    return sample.discrepancies?.includes(field) || false;
  };

  const getFieldValue = (data: Record<string, any> | null, field: string) => {
    if (!data) return null;
    return data[field];
  };

  const valuesMatch = (val1: any, val2: any) => {
    if (val1 === val2) return true;
    if (!val1 || !val2) return false;
    return String(val1).trim() === String(val2).trim();
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Extracted Data Comparison</CardTitle>
          <div className="flex items-center gap-2">
            {sample.match_score !== null && (
              <Badge
                variant={sample.match_score >= 0.95 ? 'default' : 'outline'}
                className="text-sm"
              >
                Match: {(sample.match_score * 100).toFixed(0)}%
              </Badge>
            )}
            {sample.status === 'auto_validated' && (
              <Badge variant="default" className="bg-green-500">
                Auto Validated
              </Badge>
            )}
            {sample.status === 'needs_review' && (
              <Badge variant="outline">Needs Review</Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-auto space-y-4">
        {/* Comparison Table */}
        <Tabs defaultValue="comparison" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="comparison">Comparison</TabsTrigger>
            <TabsTrigger value="datalab">Datalab Only</TabsTrigger>
            <TabsTrigger value="gemini">Gemini Only</TabsTrigger>
          </TabsList>

          <TabsContent value="comparison" className="space-y-3 mt-4">
            {DDT_FIELDS.map((field) => {
              const datalabValue = getFieldValue(sample.datalab_json, field.key);
              const geminiValue = getFieldValue(sample.gemini_json, field.key);
              const hasDisc = hasDiscrepancy(field.key);
              const matches = valuesMatch(datalabValue, geminiValue);

              return (
                <div
                  key={field.key}
                  className={`border rounded-lg p-4 ${
                    hasDisc ? 'border-red-300 bg-red-50' : 'border-gray-200'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-1">
                      {matches ? (
                        <CheckCircle2 className="w-5 h-5 text-green-500" />
                      ) : hasDisc ? (
                        <XCircle className="w-5 h-5 text-red-500" />
                      ) : (
                        <AlertCircle className="w-5 h-5 text-gray-400" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0 space-y-3">
                      <div className="font-medium text-sm text-gray-700">
                        {field.label}
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        {/* Datalab Column */}
                        <div>
                          <div className="text-xs font-medium text-gray-500 mb-1">
                            Datalab
                          </div>
                          <div className="text-sm break-words bg-white rounded p-2 border">
                            {datalabValue !== null && datalabValue !== undefined ? (
                              <span className={hasDisc ? 'text-red-700' : ''}>
                                {String(datalabValue)}
                              </span>
                            ) : (
                              <span className="text-gray-400 italic">-</span>
                            )}
                          </div>
                        </div>

                        {/* Gemini Column */}
                        <div>
                          <div className="text-xs font-medium text-gray-500 mb-1">
                            Gemini
                          </div>
                          <div className="text-sm break-words bg-white rounded p-2 border">
                            {geminiValue !== null && geminiValue !== undefined ? (
                              <span className={hasDisc ? 'text-red-700' : ''}>
                                {String(geminiValue)}
                              </span>
                            ) : (
                              <span className="text-gray-400 italic">-</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </TabsContent>

          <TabsContent value="datalab" className="space-y-3 mt-4">
            {DDT_FIELDS.map((field) => {
              const value = getFieldValue(sample.datalab_json, field.key);
              return (
                <div key={field.key} className="border rounded-lg p-4">
                  <div className="font-medium text-sm text-gray-700 mb-2">
                    {field.label}
                  </div>
                  <div className="text-sm bg-gray-50 rounded p-3 break-words">
                    {value !== null && value !== undefined ? (
                      String(value)
                    ) : (
                      <span className="text-gray-400 italic">-</span>
                    )}
                  </div>
                </div>
              );
            })}
          </TabsContent>

          <TabsContent value="gemini" className="space-y-3 mt-4">
            {DDT_FIELDS.map((field) => {
              const value = getFieldValue(sample.gemini_json, field.key);
              return (
                <div key={field.key} className="border rounded-lg p-4">
                  <div className="font-medium text-sm text-gray-700 mb-2">
                    {field.label}
                  </div>
                  <div className="text-sm bg-gray-50 rounded p-3 break-words">
                    {value !== null && value !== undefined ? (
                      String(value)
                    ) : (
                      <span className="text-gray-400 italic">-</span>
                    )}
                  </div>
                </div>
              );
            })}
          </TabsContent>
        </Tabs>

        {/* Raw OCR Text Section */}
        <div className="border-t pt-4 mt-4">
          <Tabs defaultValue="azure" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="azure">Azure OCR</TabsTrigger>
              <TabsTrigger value="datalab">Datalab OCR</TabsTrigger>
            </TabsList>

            <TabsContent value="azure" className="mt-4">
              <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-auto">
                <pre className="text-xs whitespace-pre-wrap font-mono">
                  {sample.azure_raw_ocr || 'No OCR text available'}
                </pre>
              </div>
            </TabsContent>

            <TabsContent value="datalab" className="mt-4">
              <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-auto">
                <pre className="text-xs whitespace-pre-wrap font-mono">
                  {sample.datalab_raw_ocr || 'No OCR text available'}
                </pre>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </CardContent>
    </Card>
  );
}
