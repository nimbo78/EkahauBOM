import { ProcessingRequest } from './project.model';

export enum BatchStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  PARTIAL = 'partial',
}

export enum ProcessingStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export interface BatchProjectStatus {
  project_id: string;
  filename: string;
  status: ProcessingStatus;
  processing_time?: number; // seconds
  error_message?: string;
  access_points_count?: number;
  antennas_count?: number;
}

export interface BatchStatistics {
  total_projects: number;
  successful_projects: number;
  failed_projects: number;
  total_processing_time: number; // seconds

  // Equipment totals
  total_access_points: number;
  total_antennas: number;

  // Aggregated BOM (vendor+model -> quantity)
  ap_by_vendor_model: Record<string, number>; // "Vendor|Model" -> quantity
  antenna_by_model: Record<string, number>; // "Model" -> quantity
}

export interface BatchMetadata {
  batch_id: string;
  batch_name?: string;
  created_date: string;
  created_by: string;

  // Tags for categorization and organization
  tags: string[];

  // Batch status
  status: BatchStatus;
  processing_started?: string;
  processing_completed?: string;

  // Projects in batch
  project_ids: string[];
  project_statuses: BatchProjectStatus[];

  // Processing options (inherited by all projects)
  processing_options: ProcessingRequest;

  // Parallel processing
  parallel_workers: number;

  // Statistics
  statistics: BatchStatistics;

  // File paths (relative)
  batch_dir: string; // batches/{batch_id}/
  aggregated_reports_dir?: string; // batches/{batch_id}/aggregated/

  // Archive
  archived: boolean;
  last_accessed?: string;
}

export interface BatchListItem {
  batch_id: string;
  batch_name?: string;
  created_date: string;
  status: BatchStatus;
  total_projects: number;
  successful_projects: number;
  failed_projects: number;
  tags: string[];
}

export interface BatchUploadRequest {
  batch_name?: string;
  processing_options?: ProcessingRequest;
  parallel_workers: number;
}

export interface BatchUploadResponse {
  batch_id: string;
  message: string;
  files_count: number;
  files_uploaded: string[];
  files_failed: string[];
}

export interface BatchStatusResponse {
  batch_id: string;
  status: BatchStatus;
  total_projects: number;
  completed_projects: number;
  failed_projects: number;
  statistics: BatchStatistics;
}

export interface ScannedFile {
  filename: string;
  filepath: string;
  filesize: number;
  modified_date: string;
}

export interface DirectoryScanResponse {
  directory: string;
  total_files: number;
  files: ScannedFile[];
  subdirectories_scanned: number;
}

export interface ImportFromPathsRequest {
  file_paths: string[];
  batch_name?: string;
  parallel_workers: number;
  processing_options?: ProcessingRequest;
  auto_process: boolean;
}

// ============================================================================
// Watch Mode Models
// ============================================================================

export interface WatchConfig {
  watch_directory: string;
  interval_seconds: number;
  file_pattern: string;
  auto_process: boolean;
  batch_name_prefix: string;
  processing_options?: ProcessingRequest | null;
  parallel_workers: number;
}

export interface WatchStatistics {
  started_at: string | null;
  last_check_at: string | null;
  total_checks: number;
  total_files_found: number;
  total_batches_created: number;
  processed_files_count: number;
}

export interface WatchStatus {
  is_running: boolean;
  config: WatchConfig | null;
  statistics: WatchStatistics;
}

export interface StartWatchRequest {
  watch_directory: string;
  interval_seconds: number;
  file_pattern: string;
  auto_process: boolean;
  batch_name_prefix: string;
  parallel_workers: number;
  processing_options?: ProcessingRequest;
}

export interface WatchResponse {
  status: 'started' | 'stopped';
  message: string;
  config?: WatchConfig;
}

// ============================================================================
// Scheduled Reports Models
// ============================================================================

export type TimeRange = 'last_week' | 'last_month' | 'last_quarter' | 'last_year' | 'custom';
export type ReportFormat = 'json' | 'csv' | 'text';

export interface AggregatedReportSummary {
  total_batches: number;
  total_projects: number;
  successful_projects: number;
  failed_projects: number;
  total_access_points: number;
  total_antennas: number;
}

export interface AggregatedReportEquipment {
  access_points_by_vendor_model: Record<string, number>;
  antennas_by_model: Record<string, number>;
}

export interface AggregatedReportTrends {
  batches_by_date: Record<string, number>;
  access_points_by_date: Record<string, number>;
}

export interface AggregatedReportDateRange {
  start_date: string | null;
  end_date: string | null;
}

export interface AggregatedReportData {
  summary: AggregatedReportSummary;
  equipment: AggregatedReportEquipment;
  trends: AggregatedReportTrends;
  date_range: AggregatedReportDateRange;
}

export interface AggregatedReportResponse {
  format: ReportFormat;
  data?: AggregatedReportData;
  content?: string; // For CSV/Text formats
}

export interface VendorDistribution {
  vendor: string;
  quantity: number;
  percentage: number;
}

export interface ModelDistribution {
  vendor_model: string;
  quantity: number;
  percentage: number;
}

export interface VendorAnalysisResponse {
  time_range: string;
  total_access_points: number;
  top_vendors: VendorDistribution[];
  top_models: ModelDistribution[];
}

// ============================================================================
// Template Models
// ============================================================================

export interface BatchTemplate {
  template_id: string;
  name: string;
  description?: string;
  created_date: string;
  created_by: string;
  last_used?: string;
  usage_count: number;
  is_system: boolean;
  processing_options: ProcessingRequest;
  parallel_workers: number;
}

export interface TemplateListItem {
  template_id: string;
  name: string;
  description?: string;
  created_date: string;
  last_used?: string;
  usage_count: number;
  is_system: boolean;
}

export interface TemplateCreateRequest {
  name: string;
  description?: string;
  processing_options: ProcessingRequest;
  parallel_workers: number;
}

export interface TemplateUpdateRequest {
  name?: string;
  description?: string;
  processing_options?: ProcessingRequest;
  parallel_workers?: number;
}
