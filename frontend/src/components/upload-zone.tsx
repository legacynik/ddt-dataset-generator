'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Upload, File, X } from 'lucide-react';
import { toast } from 'sonner';

import { uploadPDF } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

export function UploadZone() {
  const [files, setFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: uploadPDF,
    onSuccess: (data, file) => {
      toast.success(`${file.name} uploaded successfully`);
      setFiles((prev) => prev.filter((f) => f.name !== file.name));
      setUploadProgress((prev) => {
        const newProgress = { ...prev };
        delete newProgress[file.name];
        return newProgress;
      });
      // Invalidate samples query to refresh the list
      queryClient.invalidateQueries({ queryKey: ['samples'] });
      queryClient.invalidateQueries({ queryKey: ['status'] });
    },
    onError: (error, file) => {
      toast.error(`Failed to upload ${file.name}: ${error.message}`);
      setUploadProgress((prev) => {
        const newProgress = { ...prev };
        delete newProgress[file.name];
        return newProgress;
      });
    },
  });

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const pdfFiles = acceptedFiles.filter((file) => file.type === 'application/pdf');

    if (pdfFiles.length < acceptedFiles.length) {
      toast.error('Only PDF files are allowed');
    }

    setFiles((prev) => [...prev, ...pdfFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    multiple: true,
  });

  const handleUploadAll = async () => {
    for (const file of files) {
      setUploadProgress((prev) => ({ ...prev, [file.name]: 0 }));
      uploadMutation.mutate(file);
    }
  };

  const handleRemoveFile = (fileName: string) => {
    setFiles((prev) => prev.filter((f) => f.name !== fileName));
  };

  return (
    <Card className="p-6">
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
          transition-colors duration-200
          ${isDragActive ? 'border-primary bg-primary/5' : 'border-gray-300 hover:border-gray-400'}
        `}
      >
        <input {...getInputProps()} />
        <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
        {isDragActive ? (
          <p className="text-lg font-medium">Drop PDF files here...</p>
        ) : (
          <>
            <p className="text-lg font-medium mb-2">Drop PDF files here</p>
            <p className="text-sm text-gray-500">or click to browse</p>
          </>
        )}
      </div>

      {files.length > 0 && (
        <div className="mt-6 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">
              {files.length} file{files.length > 1 ? 's' : ''} selected
            </h3>
            <Button onClick={handleUploadAll} disabled={uploadMutation.isPending}>
              Upload All
            </Button>
          </div>

          <div className="space-y-2">
            {files.map((file) => (
              <div
                key={file.name}
                className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
              >
                <File className="w-5 h-5 text-gray-500" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{file.name}</p>
                  <p className="text-xs text-gray-500">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                  {uploadProgress[file.name] !== undefined && (
                    <Progress value={100} className="mt-1" />
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleRemoveFile(file.name)}
                  disabled={uploadProgress[file.name] !== undefined}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
