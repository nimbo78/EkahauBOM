import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
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

  updateProject(projectId: string, file: File): Observable<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.put<UploadResponse>(`${this.apiUrl}/upload/${projectId}/update`, formData);
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
}
