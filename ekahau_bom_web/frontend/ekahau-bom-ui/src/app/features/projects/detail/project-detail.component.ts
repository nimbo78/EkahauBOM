import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import {
  TuiButton,
  TuiIcon,
  TuiNotification,
  TuiLoader,
  TuiLink
} from '@taiga-ui/core';
import {
  TuiBadge,
  TuiAccordion
} from '@taiga-ui/kit';
import { ApiService } from '../../../core/services/api.service';
import { ProjectService } from '../../../core/services/project.service';
import {
  ProjectDetails,
  ProcessingStatus,
  ReportFile
} from '../../../core/models/project.model';

@Component({
  selector: 'app-project-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    TuiButton,
    TuiIcon,
    TuiNotification,
    TuiLoader,
    TuiBadge,
    TuiAccordion,
    TuiLink
  ],
  template: `
    <div class="project-detail-container">
      <!-- Header with back button -->
      <div class="page-header">
        <button tuiButton appearance="ghost" size="s" routerLink="/projects">
          <tui-icon icon="@tui.arrow-left"></tui-icon>
          Back to Projects
        </button>
        <div class="header-actions">
          <button
            *ngIf="project()?.processing_status === ProcessingStatus.PENDING"
            tuiButton
            appearance="primary"
            size="m"
            [routerLink]="['/admin/processing']"
            [queryParams]="{projectId: projectId}"
          >
            <tui-icon icon="@tui.settings"></tui-icon>
            Configure Processing
          </button>
          <button
            *ngIf="project()?.short_link"
            tuiButton
            appearance="outline"
            size="m"
            (click)="copyShortLink()"
          >
            <tui-icon icon="@tui.link"></tui-icon>
            Copy Short Link
          </button>
        </div>
      </div>

      <!-- Loading state -->
      <div *ngIf="loading()" class="loading-state">
        <tui-loader size="l"></tui-loader>
        <p>Loading project details...</p>
      </div>

      <!-- Error state -->
      <tui-notification *ngIf="error()" status="error" class="notification">
        <div class="error-content">
          <h3>Error</h3>
          <p>{{ error() }}</p>
          <button tuiButton size="s" (click)="loadProject()">Retry</button>
        </div>
      </tui-notification>

      <!-- Project content -->
      <div *ngIf="!loading() && !error() && project()" class="project-content">
        <!-- Project header info -->
        <div class="project-header">
          <h1>{{ project()?.project_name || 'Unnamed Project' }}</h1>
          <div class="project-meta">
            <span>File: {{ project()?.filename }}</span>
            <span>•</span>
            <span>Uploaded: {{ formatDate(project()?.upload_date) }}</span>
            <span>•</span>
            <span>APs: {{ project()?.aps_count || 0 }}</span>
            <span>•</span>
            <span>
              <tui-badge
                [appearance]="getStatusAppearance(project()!.processing_status)"
                size="m"
              >
                {{ project()?.processing_status }}
              </tui-badge>
            </span>
          </div>
        </div>

        <!-- Tabs for different sections -->
        <div class="tabs-section">
          <div class="tab-buttons">
            <button
              tuiButton
              [appearance]="activeTab() === 'overview' ? 'primary' : 'outline'"
              size="m"
              (click)="setActiveTab('overview')"
            >
              Overview
            </button>
            <button
              tuiButton
              [appearance]="activeTab() === 'reports' ? 'primary' : 'outline'"
              size="m"
              (click)="setActiveTab('reports')"
              [disabled]="project()?.processing_status !== ProcessingStatus.COMPLETED"
            >
              Reports
            </button>
            <button
              tuiButton
              [appearance]="activeTab() === 'visualizations' ? 'primary' : 'outline'"
              size="m"
              (click)="setActiveTab('visualizations')"
              [disabled]="project()?.processing_status !== ProcessingStatus.COMPLETED"
            >
              Visualizations
            </button>
          </div>

          <div class="tab-content">
            <!-- Overview Tab -->
            <div *ngIf="activeTab() === 'overview'" class="overview-tab">
              <div class="info-cards">
                <div class="info-card">
                  <h3>Processing Information</h3>
                  <div class="info-item">
                    <span class="label">Status:</span>
                    <span class="value">
                      <tui-badge
                        [appearance]="getStatusAppearance(project()!.processing_status)"
                      >
                        {{ project()?.processing_status }}
                      </tui-badge>
                    </span>
                  </div>
                  <div class="info-item" *ngIf="project()?.processed_date">
                    <span class="label">Processed:</span>
                    <span class="value">{{ formatDate(project()?.processed_date) }}</span>
                  </div>
                  <div class="info-item" *ngIf="project()?.short_link">
                    <span class="label">Short Link:</span>
                    <span class="value">
                      <a tuiLink [href]="getShortLinkUrl()" target="_blank">
                        {{ project()?.short_link }}
                      </a>
                    </span>
                  </div>
                  <div class="info-item" *ngIf="project()?.short_link_expires">
                    <span class="label">Expires:</span>
                    <span class="value">{{ formatDate(project()?.short_link_expires) }}</span>
                  </div>
                </div>

                <div class="info-card">
                  <h3>Project Details</h3>
                  <div class="info-item" *ngIf="project()?.customer">
                    <span class="label">Customer:</span>
                    <span class="value">{{ project()?.customer }}</span>
                  </div>
                  <div class="info-item" *ngIf="project()?.location">
                    <span class="label">Location:</span>
                    <span class="value">{{ project()?.location }}</span>
                  </div>
                  <div class="info-item" *ngIf="project()?.responsible_person">
                    <span class="label">Responsible:</span>
                    <span class="value">{{ project()?.responsible_person }}</span>
                  </div>
                  <div class="info-item">
                    <span class="label">Access Points:</span>
                    <span class="value">{{ project()?.aps_count || 0 }}</span>
                  </div>
                  <div class="info-item" *ngIf="project()?.total_antennas">
                    <span class="label">Antennas:</span>
                    <span class="value">{{ project()?.total_antennas }}</span>
                  </div>
                  <div class="info-item" *ngIf="project()?.unique_vendors">
                    <span class="label">Vendors:</span>
                    <span class="value">{{ project()?.unique_vendors }}</span>
                  </div>
                  <div class="info-item" *ngIf="project()?.vendors?.length">
                    <span class="label"></span>
                    <span class="value">
                      <tui-badge *ngFor="let vendor of project()?.vendors" appearance="info" size="s" style="margin-right: 0.5rem;">
                        {{ vendor }}
                      </tui-badge>
                    </span>
                  </div>
                  <div class="info-item" *ngIf="project()?.floors_count">
                    <span class="label">Floors:</span>
                    <span class="value">{{ project()?.floors_count }}</span>
                  </div>
                  <div class="info-item" *ngIf="project()?.floors && (project()?.floors?.length ?? 0) > 0 && (project()?.floors?.length ?? 0) <= 5">
                    <span class="label"></span>
                    <span class="value">
                      <span *ngFor="let floor of project()?.floors; let last = last">
                        {{ floor }}<span *ngIf="!last">, </span>
                      </span>
                    </span>
                  </div>
                  <div class="info-item" *ngIf="project()?.unique_colors !== undefined && project()?.unique_colors !== null">
                    <span class="label">Colors:</span>
                    <span class="value">{{ project()?.unique_colors }}</span>
                  </div>
                </div>

                <div class="info-card" *ngIf="project()?.processing_flags">
                  <h3>Processing Options</h3>
                  <div class="flags-list">
                    <div *ngIf="project()?.processing_flags?.group_by" class="flag-item">
                      <tui-icon icon="@tui.check" style="color: var(--tui-success);"></tui-icon>
                      <span>Group By: {{ project()?.processing_flags?.group_by }}</span>
                    </div>
                    <div *ngIf="project()?.processing_flags?.csv_export" class="flag-item">
                      <tui-icon icon="@tui.check" style="color: var(--tui-success);"></tui-icon>
                      <span>CSV Export</span>
                    </div>
                    <div *ngIf="project()?.processing_flags?.excel_export" class="flag-item">
                      <tui-icon icon="@tui.check" style="color: var(--tui-success);"></tui-icon>
                      <span>Excel Export</span>
                    </div>
                    <div *ngIf="project()?.processing_flags?.json_export" class="flag-item">
                      <tui-icon icon="@tui.check" style="color: var(--tui-success);"></tui-icon>
                      <span>JSON Export</span>
                    </div>
                    <div *ngIf="project()?.processing_flags?.html_export" class="flag-item">
                      <tui-icon icon="@tui.check" style="color: var(--tui-success);"></tui-icon>
                      <span>HTML Report</span>
                    </div>
                    <div *ngIf="project()?.processing_flags?.pdf_export" class="flag-item">
                      <tui-icon icon="@tui.check" style="color: var(--tui-success);"></tui-icon>
                      <span>PDF Report</span>
                    </div>
                    <div *ngIf="project()?.processing_flags?.visualize_floor_plans" class="flag-item">
                      <tui-icon icon="@tui.check" style="color: var(--tui-success);"></tui-icon>
                      <span>Floor Plan Visualizations</span>
                    </div>
                    <div *ngIf="project()?.processing_flags?.show_azimuth_arrows" class="flag-item">
                      <tui-icon icon="@tui.check" style="color: var(--tui-success);"></tui-icon>
                      <span>Show Azimuth Arrows</span>
                    </div>
                    <div *ngIf="project()?.processing_flags?.ap_opacity" class="flag-item">
                      <tui-icon icon="@tui.info" style="color: var(--tui-info);"></tui-icon>
                      <span>AP Opacity: {{ project()?.processing_flags?.ap_opacity }}</span>
                    </div>
                  </div>
                </div>

                <div class="info-card" *ngIf="project()?.metadata">
                  <h3>Project Statistics</h3>
                  <div class="info-item">
                    <span class="label">Access Points:</span>
                    <span class="value">{{ project()?.aps_count || 0 }}</span>
                  </div>
                  <div class="info-item">
                    <span class="label">Unique Models:</span>
                    <span class="value">{{ project()?.metadata?.unique_models || 0 }}</span>
                  </div>
                  <div class="info-item">
                    <span class="label">Floors:</span>
                    <span class="value">{{ project()?.metadata?.floor_count || 0 }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Reports Tab -->
            <div *ngIf="activeTab() === 'reports'" class="reports-tab">
              <div *ngIf="loadingReports()" class="loading-state">
                <tui-loader size="m"></tui-loader>
                <p>Loading reports...</p>
              </div>

              <div *ngIf="!loadingReports() && reports().length > 0" class="reports-list">
                <div *ngFor="let report of reports()" class="report-item">
                  <div class="report-info">
                    <tui-icon [icon]="getFileIcon(report.filename)"></tui-icon>
                    <span class="report-name">{{ report.filename }}</span>
                    <span class="report-size">{{ formatFileSize(report.size) }}</span>
                  </div>
                  <button
                    tuiButton
                    appearance="primary"
                    size="s"
                    (click)="downloadReport(report.filename)"
                  >
                    <tui-icon icon="@tui.download"></tui-icon>
                    Download
                  </button>
                </div>
              </div>

              <div *ngIf="!loadingReports() && reports().length === 0" class="empty-state">
                <tui-icon icon="@tui.file"></tui-icon>
                <p>No reports available</p>
              </div>
            </div>

            <!-- Visualizations Tab -->
            <div *ngIf="activeTab() === 'visualizations'" class="visualizations-tab">
              <div *ngIf="loadingVisualizations()" class="loading-state">
                <tui-loader size="m"></tui-loader>
                <p>Loading visualizations...</p>
              </div>

              <div *ngIf="!loadingVisualizations() && visualizations().length > 0" class="visualizations-grid">
                <div *ngFor="let viz of visualizations()" class="visualization-item">
                  <div class="viz-preview" (click)="openLightbox(viz.filename)">
                    <img [src]="getVisualizationUrl(viz.filename)" [alt]="viz.filename" />
                    <div class="viz-overlay">
                      <tui-icon icon="@tui.eye"></tui-icon>
                      <span>Click to view</span>
                    </div>
                  </div>
                  <div class="viz-info">
                    <span class="viz-name">{{ viz.filename }}</span>
                    <button
                      tuiButton
                      appearance="primary"
                      size="xs"
                      (click)="downloadVisualization(viz.filename)"
                    >
                      <tui-icon icon="@tui.download"></tui-icon>
                      Download
                    </button>
                  </div>
                </div>
              </div>

              <div *ngIf="!loadingVisualizations() && visualizations().length === 0" class="empty-state">
                <tui-icon icon="@tui.image"></tui-icon>
                <p>No visualizations available</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Lightbox for full-size visualization -->
      <div *ngIf="lightboxOpen()" class="lightbox" (click)="closeLightbox()">
        <div class="lightbox-content">
          <button class="lightbox-close" tuiButton appearance="icon" size="l">
            <tui-icon icon="@tui.x"></tui-icon>
          </button>
          <div class="lightbox-image-container">
            <img [src]="lightboxImageUrl()" [alt]="lightboxImageName()" (click)="$event.stopPropagation()" />
          </div>
          <div class="lightbox-footer">
            <span class="lightbox-filename">{{ lightboxImageName() }}</span>
            <button
              tuiButton
              appearance="primary"
              size="m"
              (click)="downloadVisualization(lightboxImageName()); $event.stopPropagation()"
            >
              <tui-icon icon="@tui.download"></tui-icon>
              Download
            </button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .project-detail-container {
      padding: 2rem;
      max-width: 1400px;
      margin: 0 auto;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
    }

    .header-actions {
      display: flex;
      gap: 1rem;
    }

    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 4rem 2rem;
      text-align: center;
    }

    .notification {
      margin-bottom: 2rem;
    }

    .error-content h3 {
      margin: 0 0 0.5rem;
    }

    .error-content p {
      margin: 0.5rem 0;
    }

    .project-content {
      background: var(--tui-base-01);
      border-radius: 0.5rem;
      padding: 2rem;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }

    .project-header {
      margin-bottom: 2rem;
      padding-bottom: 1.5rem;
      border-bottom: 1px solid var(--tui-base-03);
    }

    .project-header h1 {
      margin: 0 0 0.75rem;
      font-size: 2rem;
      font-weight: 500;
    }

    .project-meta {
      display: flex;
      gap: 1rem;
      align-items: center;
      color: var(--tui-text-02);
    }

    .tabs-section {
      margin-top: 2rem;
    }

    .tab-buttons {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 2rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid var(--tui-base-03);
    }

    .tab-content {
      min-height: 400px;
    }

    .info-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 2rem;
    }

    .info-card {
      background: var(--tui-base-02);
      border-radius: 0.5rem;
      padding: 1.5rem;
    }

    .info-card h3 {
      margin: 0 0 1rem;
      font-size: 1.125rem;
      font-weight: 500;
    }

    .info-item {
      display: flex;
      justify-content: space-between;
      padding: 0.5rem 0;
      border-bottom: 1px solid var(--tui-base-03);
    }

    .info-item:last-child {
      border-bottom: none;
    }

    .info-item .label {
      color: var(--tui-text-02);
      font-weight: 400;
    }

    .info-item .value {
      font-weight: 500;
    }

    .flags-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .flag-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .reports-list {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .report-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem;
      background: var(--tui-base-02);
      border-radius: 0.5rem;
    }

    .report-info {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .report-name {
      font-weight: 500;
    }

    .report-size {
      color: var(--tui-text-02);
      font-size: 0.875rem;
    }

    .visualizations-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 2rem;
    }

    .visualization-item {
      background: var(--tui-base-02);
      border-radius: 0.5rem;
      overflow: hidden;
    }

    .viz-preview {
      width: 100%;
      height: 200px;
      background: var(--tui-base-03);
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      cursor: pointer;
      overflow: hidden;
    }

    .viz-preview img {
      width: 100%;
      height: 100%;
      object-fit: contain;
      transition: transform 0.3s ease;
    }

    .viz-preview:hover img {
      transform: scale(1.05);
    }

    .viz-overlay {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.7);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      opacity: 0;
      transition: opacity 0.3s ease;
      color: white;
    }

    .viz-preview:hover .viz-overlay {
      opacity: 1;
    }

    .viz-overlay tui-icon {
      font-size: 2rem;
    }

    .viz-overlay span {
      font-size: 0.875rem;
      font-weight: 500;
    }

    .viz-info {
      padding: 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .viz-name {
      font-size: 0.875rem;
      font-weight: 500;
    }

    .empty-state {
      padding: 4rem 2rem;
      text-align: center;
      color: var(--tui-text-02);
    }

    .empty-state tui-icon {
      font-size: 3rem;
      color: var(--tui-text-03);
    }

    /* Lightbox styles */
    .lightbox {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.95);
      z-index: 9999;
      display: flex;
      align-items: center;
      justify-content: center;
      animation: fadeIn 0.3s ease;
    }

    @keyframes fadeIn {
      from {
        opacity: 0;
      }
      to {
        opacity: 1;
      }
    }

    .lightbox-content {
      position: relative;
      width: 90vw;
      height: 90vh;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .lightbox-close {
      position: absolute;
      top: 1.5rem;
      right: 1.5rem;
      background: rgba(0, 0, 0, 0.5);
      color: white;
      border: none;
      border-radius: 50%;
      cursor: pointer;
      z-index: 10;
      width: 3rem;
      height: 3rem;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease;
    }

    .lightbox-close:hover {
      transform: scale(1.15);
      background: rgba(0, 0, 0, 0.8);
    }

    .lightbox-image-container {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }

    .lightbox-image-container img {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      border-radius: 0.5rem;
      box-shadow: 0 10px 50px rgba(0, 0, 0, 0.5);
    }

    .lightbox-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 0.5rem;
      backdrop-filter: blur(10px);
    }

    .lightbox-filename {
      color: white;
      font-size: 1rem;
      font-weight: 500;
    }
  `]
})
export class ProjectDetailComponent implements OnInit {
  private apiService = inject(ApiService);
  private projectService = inject(ProjectService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  // Signals for component state
  loading = signal(false);
  error = signal<string | null>(null);
  project = signal<ProjectDetails | null>(null);
  activeTab = signal<'overview' | 'reports' | 'visualizations'>('overview');

  loadingReports = signal(false);
  reports = signal<ReportFile[]>([]);

  loadingVisualizations = signal(false);
  visualizations = signal<ReportFile[]>([]);

  // Lightbox state
  lightboxOpen = signal(false);
  lightboxImageUrl = signal('');
  lightboxImageName = signal('');

  projectId: string | null = null;

  // Make ProcessingStatus available in template
  ProcessingStatus = ProcessingStatus;

  ngOnInit(): void {
    // Get project ID from route params or query params (for short links)
    this.route.params.subscribe(params => {
      if (params['id']) {
        this.projectId = params['id'];
        this.loadProject();
      } else if (params['shortLink']) {
        this.loadProjectByShortLink(params['shortLink']);
      }
    });
  }

  loadProject(): void {
    if (!this.projectId) {
      return;
    }

    this.loading.set(true);
    this.error.set(null);

    this.apiService.getProject(this.projectId).subscribe({
      next: (project) => {
        this.project.set(project);
        this.loading.set(false);

        if (project.processing_status === ProcessingStatus.COMPLETED) {
          this.loadReports();
          this.loadVisualizations();
        }
      },
      error: (err) => {
        this.error.set('Failed to load project details');
        this.loading.set(false);
        console.error('Error loading project:', err);
      }
    });
  }

  loadProjectByShortLink(shortLink: string): void {
    this.loading.set(true);
    this.error.set(null);

    this.apiService.getProjectByShortLink(shortLink).subscribe({
      next: (project) => {
        this.project.set(project);
        this.projectId = project.project_id;
        this.loading.set(false);

        if (project.processing_status === ProcessingStatus.COMPLETED) {
          this.loadReports();
          this.loadVisualizations();
        }
      },
      error: (err) => {
        this.error.set('Invalid or expired short link');
        this.loading.set(false);
        console.error('Error loading project by short link:', err);
      }
    });
  }

  loadReports(): void {
    if (!this.projectId) {
      return;
    }

    this.loadingReports.set(true);

    this.apiService.getProjectReports(this.projectId).subscribe({
      next: (reports) => {
        this.reports.set(reports.reports);
        this.loadingReports.set(false);
      },
      error: (err) => {
        console.error('Error loading reports:', err);
        this.loadingReports.set(false);
      }
    });
  }

  loadVisualizations(): void {
    if (!this.projectId) {
      return;
    }

    this.loadingVisualizations.set(true);

    this.apiService.getProjectVisualizations(this.projectId).subscribe({
      next: (visualizations) => {
        this.visualizations.set(visualizations.visualizations);
        this.loadingVisualizations.set(false);
      },
      error: (err) => {
        console.error('Error loading visualizations:', err);
        this.loadingVisualizations.set(false);
      }
    });
  }

  setActiveTab(tab: 'overview' | 'reports' | 'visualizations'): void {
    this.activeTab.set(tab);
  }

  copyShortLink(): void {
    const shortLink = this.project()?.short_link;
    if (shortLink) {
      const url = `${window.location.origin}/s/${shortLink}`;
      navigator.clipboard.writeText(url).then(() => {
        console.log('Short link copied to clipboard');
      });
    }
  }

  getShortLinkUrl(): string {
    return `/s/${this.project()?.short_link}`;
  }

  downloadReport(filename: string): void {
    if (!this.projectId) {
      return;
    }

    const url = `/api/reports/${this.projectId}/download/${filename}`;
    window.open(url, '_blank');
  }

  downloadVisualization(filename: string): void {
    if (!this.projectId) {
      return;
    }

    const url = `/api/reports/${this.projectId}/visualization/${filename}`;
    window.open(url, '_blank');
  }

  getVisualizationUrl(filename: string): string {
    if (!this.projectId) {
      return '';
    }

    return `/api/reports/${this.projectId}/visualization/${filename}`;
  }

  formatDate(dateString: string | null | undefined): string {
    if (!dateString) {
      return 'Unknown';
    }
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  }

  formatFileSize(bytes: number): string {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  }

  getFileIcon(filename: string): string {
    if (filename.endsWith('.csv')) return '@tui.file-text';
    if (filename.endsWith('.xlsx')) return '@tui.file-spreadsheet';
    if (filename.endsWith('.json')) return '@tui.file-code';
    if (filename.endsWith('.html')) return '@tui.file-text';
    if (filename.endsWith('.png') || filename.endsWith('.jpg')) return '@tui.image';
    return '@tui.file';
  }

  getStatusAppearance(status: ProcessingStatus): string {
    switch (status) {
      case ProcessingStatus.PENDING:
        return 'warning';
      case ProcessingStatus.PROCESSING:
        return 'info';
      case ProcessingStatus.COMPLETED:
        return 'success';
      case ProcessingStatus.FAILED:
        return 'error';
      default:
        return 'neutral';
    }
  }

  openLightbox(filename: string): void {
    this.lightboxImageUrl.set(this.getVisualizationUrl(filename));
    this.lightboxImageName.set(filename);
    this.lightboxOpen.set(true);
  }

  closeLightbox(): void {
    this.lightboxOpen.set(false);
    this.lightboxImageUrl.set('');
    this.lightboxImageName.set('');
  }
}
