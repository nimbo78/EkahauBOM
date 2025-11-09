import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map, filter } from 'rxjs/operators';
import {
  ProjectListItem,
  ProjectMetadata,
  ProjectDetails,
  UploadResponse,
  ProcessingRequest,
  ProcessingFlags,
  ProjectStats,
  ReportsList,
  ProcessingStatus,
} from '../models/project.model';
import { NotesData } from '../models/notes.model';
import {
  BatchListItem,
  BatchMetadata,
  BatchUploadResponse,
  BatchStatusResponse,
  BatchStatus,
  DirectoryScanResponse,
  StartWatchRequest,
  WatchResponse,
  WatchStatus,
  TimeRange,
  ReportFormat,
  AggregatedReportResponse,
  VendorAnalysisResponse,
} from '../models/batch.model';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private readonly apiUrl = '/api';

  constructor(private http: HttpClient) {}

  // Upload endpoints
  uploadFile(file: File): Observable<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<UploadResponse>(`${this.apiUrl}/upload`, formData);
  }

  /**
   * Upload file with progress tracking
   * Returns HttpEvent stream with upload progress
   */
  uploadFileWithProgress(file: File): Observable<HttpEvent<UploadResponse>> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<UploadResponse>(`${this.apiUrl}/upload`, formData, {
      reportProgress: true,
      observe: 'events'
    });
  }

  updateProject(projectId: string, file: File): Observable<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.put<UploadResponse>(`${this.apiUrl}/upload/${projectId}/update`, formData);
  }

  /**
   * Update project with progress tracking
   * Returns HttpEvent stream with upload progress
   */
  updateProjectWithProgress(projectId: string, file: File): Observable<HttpEvent<UploadResponse>> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.put<UploadResponse>(`${this.apiUrl}/upload/${projectId}/update`, formData, {
      reportProgress: true,
      observe: 'events'
    });
  }

  startProcessing(
    projectId: string,
    request: ProcessingRequest
  ): Observable<any> {
    return this.http.post(
      `${this.apiUrl}/upload/${projectId}/process`,
      request
    );
  }

  // Projects endpoints
  listProjects(
    status?: ProcessingStatus,
    limit?: number,
    search?: string
  ): Observable<ProjectListItem[]> {
    let params = new HttpParams();
    if (status) {
      params = params.set('status', status);
    }
    if (limit) {
      params = params.set('limit', limit.toString());
    }
    if (search) {
      params = params.set('search', search);
    }
    return this.http.get<ProjectListItem[]>(`${this.apiUrl}/projects`, {
      params,
    });
  }

  getProject(projectId: string): Observable<ProjectDetails> {
    return this.http.get<ProjectDetails>(
      `${this.apiUrl}/projects/${projectId}`
    );
  }

  getProjectByShortLink(shortLink: string): Observable<ProjectDetails> {
    return this.http.get<ProjectDetails>(
      `${this.apiUrl}/projects/short/${shortLink}`
    );
  }

  processProject(projectId: string, flags: ProcessingFlags, shortLinkDays: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/upload/${projectId}/process`, {
      ...flags,
      short_link_days: shortLinkDays
    });
  }

  deleteProject(projectId: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/projects/${projectId}`);
  }

  getProjectStats(): Observable<ProjectStats> {
    return this.http.get<ProjectStats>(
      `${this.apiUrl}/projects/stats/summary`
    );
  }

  // Reports endpoints
  listReports(projectId: string): Observable<ReportsList> {
    return this.http.get<ReportsList>(
      `${this.apiUrl}/reports/${projectId}/list`
    );
  }

  getProjectReports(projectId: string): Observable<ReportsList> {
    return this.http.get<ReportsList>(
      `${this.apiUrl}/reports/${projectId}/list`
    );
  }

  getProjectVisualizations(projectId: string): Observable<ReportsList> {
    return this.http.get<ReportsList>(
      `${this.apiUrl}/reports/${projectId}/list`
    );
  }

  getReportDownloadUrl(projectId: string, filename: string): string {
    return `${this.apiUrl}/reports/${projectId}/download/${filename}`;
  }

  getVisualizationUrl(projectId: string, filename: string): string {
    return `${this.apiUrl}/reports/${projectId}/visualization/${filename}`;
  }

  getOriginalFileUrl(projectId: string): string {
    return `${this.apiUrl}/reports/${projectId}/original`;
  }

  // Notes endpoints
  getNotes(projectId: string): Observable<NotesData> {
    return this.http.get<NotesData>(`${this.apiUrl}/notes/${projectId}`);
  }

  // Health check
  checkHealth(): Observable<any> {
    return this.http.get('/health');
  }

  // Short link management (admin only)
  renewShortLink(projectId: string, days: number = 30): Observable<any> {
    return this.http.post(`${this.apiUrl}/projects/${projectId}/short-link/renew?days=${days}`, {});
  }

  createShortLink(projectId: string, days: number = 30): Observable<any> {
    return this.http.post(`${this.apiUrl}/projects/${projectId}/short-link/create?days=${days}`, {});
  }

  deleteShortLink(projectId: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/projects/${projectId}/short-link`);
  }

  // Batch processing endpoints
  /**
   * Upload multiple .esx files for batch processing
   * Returns HttpEvent stream with upload progress
   */
  uploadBatch(
    files: File[],
    batchName?: string,
    parallelWorkers: number = 1,
    processingOptions?: ProcessingRequest,
    autoProcess: boolean = false
  ): Observable<HttpEvent<BatchUploadResponse>> {
    const formData = new FormData();

    // Append all files
    files.forEach(file => {
      formData.append('files', file);
    });

    // Append optional parameters
    if (batchName) {
      formData.append('batch_name', batchName);
    }
    formData.append('parallel_workers', parallelWorkers.toString());

    if (processingOptions) {
      formData.append('processing_options', JSON.stringify(processingOptions));
    }

    formData.append('auto_process', autoProcess.toString());

    return this.http.post<BatchUploadResponse>(
      `${this.apiUrl}/batches/upload`,
      formData,
      {
        reportProgress: true,
        observe: 'events'
      }
    );
  }

  /**
   * Upload multiple .esx files for batch processing with per-file actions
   * Returns HttpEvent stream with upload progress
   */
  uploadBatchWithActions(
    files: File[],
    fileActions: Array<{filename: string; action: 'new' | 'update' | 'skip'; existingProjectId?: string}>,
    batchName?: string,
    parallelWorkers: number = 1,
    processingOptions?: ProcessingRequest,
    autoProcess: boolean = false
  ): Observable<HttpEvent<BatchUploadResponse>> {
    const formData = new FormData();

    // Append all files
    files.forEach(file => {
      formData.append('files', file);
    });

    // Append file actions configuration
    formData.append('file_actions', JSON.stringify(fileActions));

    // Append optional parameters
    if (batchName) {
      formData.append('batch_name', batchName);
    }
    formData.append('parallel_workers', parallelWorkers.toString());

    if (processingOptions) {
      formData.append('processing_options', JSON.stringify(processingOptions));
    }

    formData.append('auto_process', autoProcess.toString());

    return this.http.post<BatchUploadResponse>(
      `${this.apiUrl}/batches/upload`,
      formData,
      {
        reportProgress: true,
        observe: 'events'
      }
    );
  }

  /**
   * List all batches with advanced filtering and sorting
   */
  listBatches(options?: {
    status?: BatchStatus;
    tags?: string[];
    search?: string;
    createdAfter?: string;
    createdBefore?: string;
    minProjects?: number;
    maxProjects?: number;
    sortBy?: 'date' | 'name' | 'project_count' | 'success_rate';
    sortOrder?: 'asc' | 'desc';
    limit?: number;
  }): Observable<BatchListItem[]> {
    let params = new HttpParams();

    if (options) {
      if (options.status) {
        params = params.set('status', options.status);
      }
      if (options.tags && options.tags.length > 0) {
        params = params.set('tags', options.tags.join(','));
      }
      if (options.search) {
        params = params.set('search', options.search);
      }
      if (options.createdAfter) {
        params = params.set('created_after', options.createdAfter);
      }
      if (options.createdBefore) {
        params = params.set('created_before', options.createdBefore);
      }
      if (options.minProjects !== undefined) {
        params = params.set('min_projects', options.minProjects.toString());
      }
      if (options.maxProjects !== undefined) {
        params = params.set('max_projects', options.maxProjects.toString());
      }
      if (options.sortBy) {
        params = params.set('sort_by', options.sortBy);
      }
      if (options.sortOrder) {
        params = params.set('sort_order', options.sortOrder);
      }
      if (options.limit) {
        params = params.set('limit', options.limit.toString());
      }
    }

    return this.http.get<BatchListItem[]>(`${this.apiUrl}/batches`, { params });
  }

  /**
   * Get batch details by ID
   */
  getBatch(batchId: string): Observable<BatchMetadata> {
    return this.http.get<BatchMetadata>(`${this.apiUrl}/batches/${batchId}`);
  }

  /**
   * Start processing a batch
   */
  processBatch(batchId: string): Observable<BatchMetadata> {
    return this.http.post<BatchMetadata>(
      `${this.apiUrl}/batches/${batchId}/process`,
      {}
    );
  }

  /**
   * Get batch processing status
   */
  getBatchStatus(batchId: string): Observable<BatchStatusResponse> {
    return this.http.get<BatchStatusResponse>(
      `${this.apiUrl}/batches/${batchId}/status`
    );
  }

  /**
   * Scan a directory for .esx files
   */
  scanDirectory(
    directoryPath: string,
    recursive: boolean = false
  ): Observable<DirectoryScanResponse> {
    const formData = new FormData();
    formData.append('directory_path', directoryPath);
    formData.append('recursive', recursive.toString());

    return this.http.post<DirectoryScanResponse>(
      `${this.apiUrl}/batches/scan-directory`,
      formData
    );
  }

  /**
   * Import files from server paths into a batch
   */
  importFromPaths(
    filePaths: string[],
    batchName?: string,
    parallelWorkers: number = 1,
    processingOptions?: ProcessingRequest,
    autoProcess: boolean = false
  ): Observable<BatchUploadResponse> {
    const request = {
      file_paths: filePaths,
      batch_name: batchName,
      parallel_workers: parallelWorkers,
      processing_options: processingOptions,
      auto_process: autoProcess
    };

    return this.http.post<BatchUploadResponse>(
      `${this.apiUrl}/batches/import-from-paths`,
      request
    );
  }

  /**
   * Delete a batch and all its data
   */
  deleteBatch(batchId: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/batches/${batchId}`);
  }

  /**
   * Update batch tags (add and/or remove tags)
   */
  updateBatchTags(
    batchId: string,
    tagsToAdd: string[] = [],
    tagsToRemove: string[] = []
  ): Observable<{ batch_id: string; tags: string[]; message: string }> {
    let params = new HttpParams();

    // Add tags to add
    tagsToAdd.forEach(tag => {
      params = params.append('tags_to_add', tag);
    });

    // Add tags to remove
    tagsToRemove.forEach(tag => {
      params = params.append('tags_to_remove', tag);
    });

    return this.http.patch<{ batch_id: string; tags: string[]; message: string }>(
      `${this.apiUrl}/batches/${batchId}/tags`,
      null,
      { params }
    );
  }

  /**
   * Get aggregated report download URL for a batch
   */
  getBatchAggregatedReportUrl(batchId: string, filename: string): string {
    return `${this.apiUrl}/batches/${batchId}/aggregated/${filename}`;
  }

  /**
   * Get batch download URL (ZIP archive with all projects)
   */
  getBatchDownloadUrl(batchId: string): string {
    return `${this.apiUrl}/batches/${batchId}/download`;
  }

  /**
   * Download batch as ZIP archive
   * Returns Observable with Blob for authenticated download
   */
  downloadBatch(batchId: string): Observable<Blob> {
    const url = this.getBatchDownloadUrl(batchId);
    return this.http.get(url, {
      responseType: 'blob',
      observe: 'body'
    });
  }

  // ============================================================================
  // Watch Mode API Methods
  // ============================================================================

  /**
   * Start watch mode to monitor directory for new .esx files
   */
  startWatch(request: StartWatchRequest): Observable<WatchResponse> {
    const formData = new FormData();
    formData.append('watch_directory', request.watch_directory);
    formData.append('interval_seconds', request.interval_seconds.toString());
    formData.append('file_pattern', request.file_pattern);
    formData.append('auto_process', request.auto_process.toString());
    formData.append('batch_name_prefix', request.batch_name_prefix);
    formData.append('parallel_workers', request.parallel_workers.toString());

    if (request.processing_options) {
      formData.append('processing_options', JSON.stringify(request.processing_options));
    }

    return this.http.post<WatchResponse>(`${this.apiUrl}/batches/watch/start`, formData);
  }

  /**
   * Stop watch mode
   */
  stopWatch(): Observable<WatchResponse> {
    return this.http.post<WatchResponse>(`${this.apiUrl}/batches/watch/stop`, {});
  }

  /**
   * Get watch mode status and statistics
   */
  getWatchStatus(): Observable<WatchStatus> {
    return this.http.get<WatchStatus>(`${this.apiUrl}/batches/watch/status`);
  }

  // ============================================================================
  // Scheduled Reports API Methods
  // ============================================================================

  /**
   * Get aggregated report across all batches for specified time range
   */
  getAggregatedReport(timeRange: TimeRange, format: ReportFormat = 'json'): Observable<AggregatedReportResponse> {
    const params = new HttpParams()
      .set('time_range', timeRange)
      .set('format', format);

    return this.http.get<AggregatedReportResponse>(`${this.apiUrl}/batches/reports/aggregated`, { params });
  }

  /**
   * Get vendor/model distribution analysis
   */
  getVendorAnalysis(timeRange: TimeRange): Observable<VendorAnalysisResponse> {
    const params = new HttpParams().set('time_range', timeRange);

    return this.http.get<VendorAnalysisResponse>(`${this.apiUrl}/batches/reports/vendor-analysis`, { params });
  }
}
