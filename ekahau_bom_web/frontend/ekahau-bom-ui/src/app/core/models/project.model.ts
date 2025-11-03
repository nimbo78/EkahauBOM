export enum ProcessingStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export interface ProjectMetadata {
  project_id: string;
  filename: string;
  upload_date: string;
  file_size: number;
  processing_status: ProcessingStatus;
  project_name?: string;
  buildings_count?: number;
  floors_count?: number;
  aps_count?: number;

  // Project details from .esx
  customer?: string;
  location?: string;
  responsible_person?: string;

  // Summary from JSON report
  total_antennas?: number;
  unique_vendors?: number;
  unique_colors?: number;
  vendors?: string[];
  floors?: string[];

  processing_flags?: Record<string, any>;
  processing_started?: string;
  processing_completed?: string;
  processing_error?: string;
  original_file: string;
  reports_dir?: string;
  visualizations_dir?: string;
  short_link?: string;
  short_link_expires?: string;
}

export interface ProjectListItem {
  project_id: string;
  project_name: string;
  filename: string;
  upload_date: string;
  aps_count?: number;
  processing_status: ProcessingStatus;
  short_link?: string;
}

export interface UploadResponse {
  project_id: string;
  message: string;
  short_link?: string;
  exists?: boolean; // True if project with same name already exists
  existing_project?: ProjectListItem; // Details of existing project
}

export interface ProcessingRequest {
  group_by?: string; // 'model', 'floor', 'color', 'vendor', 'tag', or null/undefined for no grouping
  output_formats: string[]; // ['csv', 'excel', 'html', 'json', 'pdf']
  visualize_floor_plans: boolean;
  show_azimuth_arrows: boolean;
  ap_opacity: number; // 0.0-1.0, default 0.6
}

export interface ProjectStats {
  total: number;
  pending: number;
  processing: number;
  completed: number;
  failed: number;
}

export interface ReportsList {
  project_id: string;
  reports: ReportFile[];
  visualizations: ReportFile[];
}

export interface ReportFile {
  filename: string;
  size: number;
  created: string;
}

export interface ProcessingFlags {
  group_by?: string; // 'model', 'floor', 'color', 'vendor', 'tag', or null for no grouping
  csv_export: boolean;
  excel_export: boolean;
  json_export: boolean;
  html_export: boolean;
  pdf_export: boolean;
  visualize_floor_plans: boolean;
  show_azimuth_arrows: boolean;
  ap_opacity: number; // 0.0-1.0
}

export interface ProjectDetails extends ProjectMetadata {
  metadata?: {
    unique_models?: number;
    floor_count?: number;
  };
  processing_flags?: ProcessingFlags;
  processed_date?: string;
}
