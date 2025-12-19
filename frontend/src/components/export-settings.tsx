'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Slider } from '@/components/ui/slider';

interface ExportSettingsProps {
  ocrSource: 'azure' | 'datalab';
  validationSplit: number;
  onOcrSourceChange: (source: 'azure' | 'datalab') => void;
  onValidationSplitChange: (split: number) => void;
}

export function ExportSettings({
  ocrSource,
  validationSplit,
  onOcrSourceChange,
  onValidationSplitChange,
}: ExportSettingsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Export Settings</CardTitle>
        <CardDescription>Configure your dataset export options</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* OCR Source Selection */}
        <div className="space-y-3">
          <Label>OCR Source for Input</Label>
          <RadioGroup value={ocrSource} onValueChange={(v) => onOcrSourceChange(v as 'azure' | 'datalab')}>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="azure" id="azure" />
              <Label htmlFor="azure" className="font-normal cursor-pointer">
                <div>
                  <div className="font-medium">Azure Document Intelligence</div>
                  <div className="text-sm text-gray-500">
                    Use Azure OCR as input text (recommended for better quality)
                  </div>
                </div>
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="datalab" id="datalab" />
              <Label htmlFor="datalab" className="font-normal cursor-pointer">
                <div>
                  <div className="font-medium">Datalab Marker</div>
                  <div className="text-sm text-gray-500">
                    Use Datalab OCR as input text
                  </div>
                </div>
              </Label>
            </div>
          </RadioGroup>
        </div>

        {/* Validation Split */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label>Validation Split</Label>
            <span className="text-sm font-medium">{(validationSplit * 100).toFixed(0)}%</span>
          </div>
          <Slider
            value={[validationSplit * 100]}
            onValueChange={(v) => onValidationSplitChange(v[0] / 100)}
            min={5}
            max={30}
            step={1}
            className="w-full"
          />
          <p className="text-sm text-gray-500">
            Training: {(100 - validationSplit * 100).toFixed(0)}% | Validation: {(validationSplit * 100).toFixed(0)}%
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
