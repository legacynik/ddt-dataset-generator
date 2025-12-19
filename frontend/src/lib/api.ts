/**
 * API client for DDT Dataset Generator backend.
 *
 * All API calls to the FastAPI backend.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ===== Types =====

export type SampleStatus =
  | 'pending'
  | 'processing'
  | 'auto_validated'
  | 'needs_review'
  | 'manually_validated'
  | 'rejected'
  | 'error';

export type ValidationSource = 'datalab' | 'gemini' | 'manual';

export interface Sample {
  id: string;
  filename: string;
  status: SampleStatus;
  match_score: number | null;
  discrepancies: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface SampleDetail extends Sample {
  pdf_url: string | null;
  storage_path: string | null;
  datalab_json: Record<string, any> | null;
  gemini_json: Record<string, any> | null;
  validated_output: Record<string, any> | null;
  datalab_raw_ocr: string | null;
  azure_raw_ocr: string | null;
  validation_source: ValidationSource | null;
  validator_notes: string | null;
}

export interface StatusResponse {
  is_processing: boolean;
  total: number;
  processed: number;
  auto_validated: number;
  needs_review: number;
  manually_validated: number;
  errors: number;
  pending: number;
  progress_percent: number;
}

export interface SamplesListResponse {
  samples: Sample[];
  total: number;
  limit: number;
  offset: number;
}

export interface UploadResponse {
  id: string;
  filename: string;
  status: SampleStatus;
  pdf_url: string | null;
}

export interface ProcessResponse {
  message: string;
  pending_count: number;
}

export interface ValidationRequest {
  status?: SampleStatus;
  validated_output?: Record<string, any>;
  validation_source?: ValidationSource;
  validator_notes?: string;
}

export interface ExportRequest {
  ocr_source: 'azure' | 'datalab';
  validation_split: number;
}

export interface ExportResponse {
  total_samples: number;
  training_samples: number;
  validation_samples: number;
  ocr_source: string;
  download_urls: {
    training: string;
    validation: string;
    report: string;
  };
  quality_report: {
    field_coverage: Record<string, number>;
    quality_score: number;
  } | null;
}

// ===== API Functions =====

/**
 * Upload a PDF file.
 */
export async function uploadPDF(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail || 'Upload failed');
  }

  return response.json();
}

/**
 * Start processing pending samples.
 */
export async function startProcessing(sampleIds?: string[]): Promise<ProcessResponse> {
  const response = await fetch(`${API_BASE_URL}/api/process`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ sample_ids: sampleIds || null }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Processing failed' }));
    throw new Error(error.detail || 'Processing failed');
  }

  return response.json();
}

/**
 * Get current processing status.
 */
export async function getStatus(): Promise<StatusResponse> {
  const response = await fetch(`${API_BASE_URL}/api/status`);

  if (!response.ok) {
    throw new Error('Failed to fetch status');
  }

  return response.json();
}

/**
 * List samples with optional filtering and pagination.
 */
export async function listSamples(params?: {
  status?: SampleStatus;
  limit?: number;
  offset?: number;
}): Promise<SamplesListResponse> {
  const queryParams = new URLSearchParams();

  if (params?.status) queryParams.append('status', params.status);
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  if (params?.offset) queryParams.append('offset', params.offset.toString());

  const url = `${API_BASE_URL}/api/samples${queryParams.toString() ? `?${queryParams}` : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error('Failed to fetch samples');
  }

  return response.json();
}

/**
 * Get detailed information about a sample.
 */
export async function getSampleDetail(sampleId: string): Promise<SampleDetail> {
  const response = await fetch(`${API_BASE_URL}/api/samples/${sampleId}`);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Sample not found');
    }
    throw new Error('Failed to fetch sample detail');
  }

  return response.json();
}

/**
 * Update sample validation.
 */
export async function validateSample(
  sampleId: string,
  data: ValidationRequest
): Promise<SampleDetail> {
  const response = await fetch(`${API_BASE_URL}/api/samples/${sampleId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Validation failed' }));
    throw new Error(error.detail || 'Validation failed');
  }

  return response.json();
}

/**
 * Export dataset to Alpaca JSONL format.
 */
export async function exportDataset(request: ExportRequest): Promise<ExportResponse> {
  const response = await fetch(`${API_BASE_URL}/api/export`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Export failed' }));
    throw new Error(error.detail || 'Export failed');
  }

  return response.json();
}

/**
 * Check API health.
 */
export async function checkHealth(): Promise<{ status: string; version: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error('API health check failed');
  }

  return response.json();
}

// ===== Previous Results =====

export interface PreviousResults {
  total_pdfs: number;
  generated_at: string;
  datalab_success_rate: number;
  azure_success_rate: number;
  gemini_success_rate: number;
  auto_validated_count: number;
  needs_review_count: number;
  error_count: number;
  avg_processing_time: number;
}

/**
 * Get statistics from previous processing report.
 */
export async function getPreviousResults(): Promise<PreviousResults> {
  const response = await fetch(`${API_BASE_URL}/api/previous-results`);

  if (!response.ok) {
    throw new Error('Failed to fetch previous results');
  }

  return response.json();
}
