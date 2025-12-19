'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircle, Edit, XCircle, Save } from 'lucide-react';
import { toast } from 'sonner';

import { validateSample, type SampleDetail, type ValidationRequest } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

interface ValidationActionsProps {
  sample: SampleDetail;
  onValidated?: () => void;
}

const DDT_FIELDS = [
  { key: 'mittente', label: 'Mittente', type: 'text' },
  { key: 'destinatario', label: 'Destinatario', type: 'text' },
  { key: 'indirizzo_destinazione_completo', label: 'Indirizzo Destinazione', type: 'textarea' },
  { key: 'data_documento', label: 'Data Documento', type: 'date' },
  { key: 'data_trasporto', label: 'Data Trasporto', type: 'date' },
  { key: 'numero_documento', label: 'Numero Documento', type: 'text' },
  { key: 'numero_ordine', label: 'Numero Ordine', type: 'text' },
  { key: 'codice_cliente', label: 'Codice Cliente', type: 'text' },
];

export function ValidationActions({ sample, onValidated }: ValidationActionsProps) {
  const [notes, setNotes] = useState(sample.validator_notes || '');
  const [manualData, setManualData] = useState<Record<string, any>>(
    sample.validated_output || sample.gemini_json || sample.datalab_json || {}
  );
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const queryClient = useQueryClient();

  const validateMutation = useMutation({
    mutationFn: (data: ValidationRequest) => validateSample(sample.id, data),
    onSuccess: () => {
      toast.success('Sample validated successfully');
      queryClient.invalidateQueries({ queryKey: ['sample', sample.id] });
      queryClient.invalidateQueries({ queryKey: ['samples'] });
      queryClient.invalidateQueries({ queryKey: ['status'] });
      onValidated?.();
    },
    onError: (error: Error) => {
      toast.error(`Validation failed: ${error.message}`);
    },
  });

  const handleAcceptDatalab = () => {
    if (!sample.datalab_json) {
      toast.error('No Datalab data available');
      return;
    }

    validateMutation.mutate({
      status: 'manually_validated',
      validated_output: sample.datalab_json,
      validation_source: 'datalab',
      validator_notes: notes || undefined,
    });
  };

  const handleAcceptGemini = () => {
    if (!sample.gemini_json) {
      toast.error('No Gemini data available');
      return;
    }

    validateMutation.mutate({
      status: 'manually_validated',
      validated_output: sample.gemini_json,
      validation_source: 'gemini',
      validator_notes: notes || undefined,
    });
  };

  const handleManualEdit = () => {
    validateMutation.mutate({
      status: 'manually_validated',
      validated_output: manualData,
      validation_source: 'manual',
      validator_notes: notes || undefined,
    });
    setIsEditDialogOpen(false);
  };

  const handleReject = () => {
    if (!confirm('Are you sure you want to reject this sample?')) return;

    validateMutation.mutate({
      status: 'rejected',
      validator_notes: notes || 'Rejected',
    });
  };

  const handleFieldChange = (key: string, value: string) => {
    setManualData((prev) => ({
      ...prev,
      [key]: value || null,
    }));
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Validation Actions</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Quick Actions */}
        <div className="grid grid-cols-2 gap-3">
          <Button
            onClick={handleAcceptDatalab}
            disabled={!sample.datalab_json || validateMutation.isPending}
            variant="outline"
            className="w-full"
          >
            <CheckCircle className="w-4 h-4 mr-2" />
            Accept Datalab
          </Button>
          <Button
            onClick={handleAcceptGemini}
            disabled={!sample.gemini_json || validateMutation.isPending}
            variant="outline"
            className="w-full"
          >
            <CheckCircle className="w-4 h-4 mr-2" />
            Accept Gemini
          </Button>
        </div>

        {/* Manual Edit Dialog */}
        <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
          <DialogTrigger asChild>
            <Button variant="default" className="w-full">
              <Edit className="w-4 h-4 mr-2" />
              Edit Manually
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Manual Edit</DialogTitle>
              <DialogDescription>
                Edit the extracted data manually. All fields are optional.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              {DDT_FIELDS.map((field) => (
                <div key={field.key} className="space-y-2">
                  <Label htmlFor={field.key}>{field.label}</Label>
                  {field.type === 'textarea' ? (
                    <Textarea
                      id={field.key}
                      value={manualData[field.key] || ''}
                      onChange={(e) => handleFieldChange(field.key, e.target.value)}
                      rows={3}
                    />
                  ) : (
                    <Input
                      id={field.key}
                      type={field.type}
                      value={manualData[field.key] || ''}
                      onChange={(e) => handleFieldChange(field.key, e.target.value)}
                    />
                  )}
                </div>
              ))}
              <div className="flex gap-3 pt-4">
                <Button onClick={handleManualEdit} disabled={validateMutation.isPending}>
                  <Save className="w-4 h-4 mr-2" />
                  Save Changes
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setIsEditDialogOpen(false)}
                  disabled={validateMutation.isPending}
                >
                  Cancel
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* Notes */}
        <div className="space-y-2">
          <Label htmlFor="notes">Validation Notes</Label>
          <Textarea
            id="notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add notes about this validation..."
            rows={3}
          />
        </div>

        {/* Reject Button */}
        <Button
          variant="destructive"
          className="w-full"
          onClick={handleReject}
          disabled={validateMutation.isPending}
        >
          <XCircle className="w-4 h-4 mr-2" />
          Reject Sample
        </Button>

        {/* Current Status */}
        {sample.validated_output && (
          <div className="text-sm text-gray-500 border-t pt-4">
            <p className="font-medium mb-1">Current Status:</p>
            <p>
              Status: <span className="font-medium">{sample.status}</span>
            </p>
            {sample.validation_source && (
              <p>
                Source: <span className="font-medium">{sample.validation_source}</span>
              </p>
            )}
            {sample.validator_notes && (
              <p className="mt-2">
                Notes: <span className="italic">{sample.validator_notes}</span>
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
