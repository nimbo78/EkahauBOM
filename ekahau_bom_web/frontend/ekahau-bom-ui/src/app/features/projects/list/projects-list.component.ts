import { Component, OnInit, OnDestroy, inject, signal, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ScrollingModule } from '@angular/cdk/scrolling';
import {
  TuiButton,
  TuiIcon,
  TuiNotification,
  TuiLoader,
  TuiHint,
  TuiLink,
  TuiTextfield
} from '@taiga-ui/core';
import {
  TuiBadge
} from '@taiga-ui/kit';
import { ApiService } from '../../../core/services/api.service';
import { ProjectService } from '../../../core/services/project.service';
import { AuthService } from '../../../core/services/auth.service';
import { ErrorMessageService } from '../../../shared/services/error-message.service';
import {
  ProjectListItem,
  ProjectStats,
  ProcessingStatus
} from '../../../core/models/project.model';
import { Subscription, debounceTime, distinctUntilChanged } from 'rxjs';

@Component({
  selector: 'app-projects-list',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    ScrollingModule,
    TuiButton,
    TuiIcon,
    TuiNotification,
    TuiLoader,
    TuiBadge,
    TuiTextfield,
    TuiHint,
    TuiLink
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="projects-container">
      <div class="page-header">
        <h1 class="page-title">Projects</h1>
      </div>

      <!-- Statistics cards -->
      <div class="stats-cards" *ngIf="stats()">
        <div
          class="stat-card"
          [class.active]="statusFilter() === null"
          (click)="setStatusFilter(null)"
        >
          <div class="stat-value">{{ stats()?.total || 0 }}</div>
          <div class="stat-label">Total Projects</div>
        </div>
        <div
          class="stat-card pending"
          [class.active]="statusFilter() === ProcessingStatus.PENDING"
          (click)="setStatusFilter(ProcessingStatus.PENDING)"
        >
          <div class="stat-value">{{ stats()?.pending || 0 }}</div>
          <div class="stat-label">Pending</div>
        </div>
        <div
          class="stat-card processing"
          [class.active]="statusFilter() === ProcessingStatus.PROCESSING"
          (click)="setStatusFilter(ProcessingStatus.PROCESSING)"
        >
          <div class="stat-value">{{ stats()?.processing || 0 }}</div>
          <div class="stat-label">Processing</div>
        </div>
        <div
          class="stat-card completed"
          [class.active]="statusFilter() === ProcessingStatus.COMPLETED"
          (click)="setStatusFilter(ProcessingStatus.COMPLETED)"
        >
          <div class="stat-value">{{ stats()?.completed || 0 }}</div>
          <div class="stat-label">Completed</div>
        </div>
        <div
          class="stat-card failed"
          *ngIf="(stats()?.failed || 0) > 0"
          [class.active]="statusFilter() === ProcessingStatus.FAILED"
          (click)="setStatusFilter(ProcessingStatus.FAILED)"
        >
          <div class="stat-value">{{ stats()?.failed || 0 }}</div>
          <div class="stat-label">Failed</div>
        </div>
      </div>

      <!-- Search -->
      <div class="search-row">
        <div class="search-input">
          <tui-textfield>
            <input
              tuiTextfield
              [formControl]="searchControl"
              placeholder="Search projects..."
              type="text"
            />
          </tui-textfield>
        </div>
        <div class="keyboard-shortcuts-hint">
          <tui-icon icon="@tui.command" style="font-size: 14px; margin-right: 0.25rem;"></tui-icon>
          <span class="hint-text">
            Press <kbd>Ctrl</kbd>+<kbd>K</kbd> or <kbd>/</kbd> to focus search
          </span>
        </div>
      </div>

      <!-- Loading state -->
      <div *ngIf="loading()" class="loading-state">
        <tui-loader size="l"></tui-loader>
        <p>Loading projects...</p>
      </div>

      <!-- Error state -->
      <tui-notification *ngIf="error()" status="error" class="notification">
        <div class="error-content">
          <h3>Error loading projects</h3>
          <p>{{ error() }}</p>
          <button tuiButton size="s" (click)="loadProjects()">Retry</button>
        </div>
      </tui-notification>

      <!-- Projects table -->
      <div *ngIf="!loading() && !error()" class="table-wrapper">
        <!-- Empty state -->
        <div *ngIf="filteredProjects().length === 0" class="empty-state">
          <tui-icon icon="@tui.folder"></tui-icon>
          <h3>No projects found</h3>
          <p *ngIf="searchControl.value || statusFilter()">
            Try adjusting your search or filter criteria
          </p>
          <p *ngIf="!searchControl.value && !statusFilter()">
            Use the Upload button in the navigation menu to get started
          </p>
        </div>

        <!-- Virtual scroll table -->
        <div *ngIf="filteredProjects().length > 0" class="table-container">
          <!-- Fixed table header -->
          <table class="projects-table-header">
            <thead>
              <tr>
                <th>Project Name</th>
                <th>File Name</th>
                <th>Upload Date</th>
                <th>APs Count</th>
                <th>Status</th>
                <th>Short Link</th>
                <th>Actions</th>
              </tr>
            </thead>
          </table>

          <!-- Scrollable table body -->
          <cdk-virtual-scroll-viewport
            [itemSize]="60"
            class="virtual-scroll-viewport"
          >
            <table class="projects-table">
              <tbody>
                <tr *cdkVirtualFor="let project of filteredProjects(); trackBy: trackByProjectId">
                <td>
                  <a tuiLink [routerLink]="['/projects', project.project_id]">
                    {{ project.project_name || 'Unnamed Project' }}
                  </a>
                </td>
                <td>{{ project.filename }}</td>
                <td>{{ formatDate(project.upload_date) }}</td>
                <td>{{ project.aps_count || '-' }}</td>
                <td>
                  <tui-badge
                    [appearance]="getStatusAppearance(project.processing_status)"
                    [class]="'status-badge-' + project.processing_status.toLowerCase()"
                  >
                    {{ project.processing_status }}
                  </tui-badge>
                </td>
                <td>
                  <a
                    *ngIf="project.short_link"
                    tuiLink
                    [href]="'/s/' + project.short_link"
                    target="_blank"
                  >
                    {{ project.short_link }}
                  </a>
                  <span *ngIf="!project.short_link">-</span>
                </td>
                <td>
                  <div class="actions">
                    <button
                      tuiButton
                      appearance="flat"
                      size="s"
                      [routerLink]="['/projects', project.project_id]"
                      [tuiHint]="viewHint"
                      style="background-color: #e8eef7; color: #526ed3; min-width: 36px; padding: 8px; border: 1px solid #526ed3; border-radius: 4px; margin-right: 4px;"
                    >
                      <tui-icon icon="@tui.eye"></tui-icon>
                    </button>
                    <button
                      *ngIf="isAuthenticated() &&
                             (project.processing_status === ProcessingStatus.PENDING ||
                              project.processing_status === ProcessingStatus.COMPLETED ||
                              project.processing_status === ProcessingStatus.FAILED)"
                      tuiButton
                      appearance="flat"
                      size="s"
                      [routerLink]="['/admin/processing']"
                      [queryParams]="{projectId: project.project_id}"
                      [tuiHint]="project.processing_status === ProcessingStatus.PENDING ? configureHint : reprocessHint"
                      style="background-color: #e8eef7; color: #526ed3; min-width: 36px; padding: 8px; border: 1px solid #526ed3; border-radius: 4px; margin-right: 4px;"
                    >
                      <tui-icon icon="@tui.settings"></tui-icon>
                    </button>
                    <button
                      *ngIf="isAuthenticated()"
                      tuiButton
                      appearance="flat"
                      size="s"
                      (click)="confirmDelete(project)"
                      [tuiHint]="deleteHint"
                      style="background-color: #fce8e6; color: #e01f19; min-width: 36px; padding: 8px; border: 1px solid #e01f19; border-radius: 4px;"
                    >
                      <tui-icon icon="@tui.trash-2"></tui-icon>
                    </button>
                  </div>
                </td>
              </tr>
              </tbody>
            </table>
          </cdk-virtual-scroll-viewport>
        </div>
      </div>

      <!-- Hint templates with icons -->
      <ng-template #viewHint>
        <div class="custom-hint">
          <tui-icon icon="@tui.eye" class="hint-icon"></tui-icon>
          <span class="hint-text">View Details</span>
        </div>
      </ng-template>

      <ng-template #configureHint>
        <div class="custom-hint">
          <tui-icon icon="@tui.settings" class="hint-icon"></tui-icon>
          <span class="hint-text">Configure Processing</span>
        </div>
      </ng-template>

      <ng-template #reprocessHint>
        <div class="custom-hint">
          <tui-icon icon="@tui.refresh-cw" class="hint-icon"></tui-icon>
          <span class="hint-text">Reprocess Project</span>
        </div>
      </ng-template>

      <ng-template #deleteHint>
        <div class="custom-hint custom-hint-danger">
          <tui-icon icon="@tui.trash-2" class="hint-icon"></tui-icon>
          <span class="hint-text">Delete Project</span>
        </div>
      </ng-template>
    </div>
  `,
  styles: [`
    .projects-container {
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

    .page-title {
      margin: 0;
      font-size: 2rem;
      font-weight: 500;
    }

    .stats-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }

    .stat-card {
      background: var(--tui-base-02);
      border-radius: 0.5rem;
      padding: 1.5rem;
      text-align: center;
      border: 2px solid transparent;
      transition: all 0.3s;
      cursor: pointer;
      user-select: none;

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
      }

      &.active {
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
        transform: translateY(-2px);
      }

      &.pending {
        border-color: var(--tui-warning);

        &.active {
          background: rgba(255, 193, 7, 0.1);
          border-color: var(--tui-warning);
        }
      }

      &.processing {
        border-color: var(--tui-info);

        &.active {
          background: rgba(13, 110, 253, 0.1);
          border-color: var(--tui-info);
        }
      }

      &.completed {
        border-color: var(--tui-success);

        &.active {
          background: rgba(25, 135, 84, 0.1);
          border-color: var(--tui-success);
        }
      }

      &.failed {
        border-color: var(--tui-error);

        &.active {
          background: rgba(220, 53, 69, 0.1);
          border-color: var(--tui-error);
        }
      }

      &:not(.pending):not(.processing):not(.completed):not(.failed).active {
        background: rgba(140, 140, 140, 0.08);
        border-color: rgba(140, 140, 140, 0.4);
      }
    }

    .stat-value {
      font-size: 2rem;
      font-weight: 600;
      color: var(--tui-text-01);
    }

    .stat-label {
      margin-top: 0.5rem;
      font-size: 0.875rem;
      color: var(--tui-text-02);
    }

    .search-row {
      margin-bottom: 2rem;
    }

    .search-input {
      max-width: 400px;
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

    .error-content {
      h3 {
        margin: 0 0 0.5rem;
      }
      p {
        margin: 0.5rem 0;
      }
    }

    .table-wrapper {
      background: var(--tui-base-01);
      border-radius: 0.5rem;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }

    .table-container {
      display: flex;
      flex-direction: column;
      height: calc(100vh - 480px);
      min-height: 400px;
      max-height: 800px;
    }

    .projects-table-header {
      width: 100%;
      flex-shrink: 0;

      thead {
        display: table;
        width: 100%;
        table-layout: fixed;
      }

      th {
        padding: 1rem;
        font-weight: 600;
        background: var(--tui-base-02);
        text-align: left;
      }
    }

    .virtual-scroll-viewport {
      flex: 1;
      width: 100%;

      // Override CDK styles for table support
      ::ng-deep .cdk-virtual-scroll-content-wrapper {
        width: 100%;
      }
    }

    .projects-table {
      width: 100%;
      table-layout: fixed;

      td {
        padding: 1rem;
      }

      tbody tr {
        height: 60px; // Must match itemSize in virtual scroll
        display: table;
        width: 100%;
        table-layout: fixed;

        &:hover {
          background: var(--tui-base-02);
        }
      }
    }

    // Ensure columns match between header and body
    .projects-table-header th:nth-child(1),
    .projects-table td:nth-child(1) { width: 20%; } // Project Name

    .projects-table-header th:nth-child(2),
    .projects-table td:nth-child(2) { width: 20%; } // File Name

    .projects-table-header th:nth-child(3),
    .projects-table td:nth-child(3) { width: 15%; } // Upload Date

    .projects-table-header th:nth-child(4),
    .projects-table td:nth-child(4) { width: 10%; } // APs Count

    .projects-table-header th:nth-child(5),
    .projects-table td:nth-child(5) { width: 12%; } // Status

    .projects-table-header th:nth-child(6),
    .projects-table td:nth-child(6) { width: 10%; } // Short Link

    .projects-table-header th:nth-child(7),
    .projects-table td:nth-child(7) { width: 13%; } // Actions

    .actions {
      display: flex;
      gap: 0.25rem;
    }

    // Color-coded status badges
    tui-badge.status-badge-completed {
      background-color: #D4EDDA !important;
      color: #155724 !important;
      border: 1px solid #C3E6CB !important;
    }

    tui-badge.status-badge-pending {
      background-color: #FFF3CD !important;
      color: #856404 !important;
      border: 1px solid #FFEAA7 !important;
    }

    tui-badge.status-badge-processing {
      background-color: #D1ECF1 !important;
      color: #0C5460 !important;
      border: 1px solid #BEE5EB !important;
    }

    tui-badge.status-badge-failed {
      background-color: #F8D7DA !important;
      color: #721C24 !important;
      border: 1px solid #F5C6CB !important;
    }

    .empty-state {
      padding: 4rem 2rem;
      text-align: center;

      tui-icon {
        font-size: 3rem;
        color: var(--tui-text-03);
      }

      h3 {
        margin: 1rem 0 0.5rem;
        font-size: 1.25rem;
        font-weight: 500;
      }

      p {
        margin: 0.5rem 0 1.5rem;
        color: var(--tui-text-02);
      }
    }

    .columns {
      display: none;
    }

    // Custom hint styles
    .custom-hint {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 0.75rem;
      font-size: 0.875rem;
      font-weight: 500;
      white-space: nowrap;
      background: rgba(45, 45, 45, 0.80);
      border-radius: 6px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
      color: #ffffff;

      .hint-icon {
        font-size: 1rem;
        flex-shrink: 0;
        color: #ffffff;
      }

      .hint-text {
        color: #ffffff;
      }
    }

    .custom-hint-danger {
      background: rgba(224, 31, 25, 0.80);

      .hint-icon,
      .hint-text {
        color: #ffffff;
      }
    }

    // Keyboard shortcuts hint
    .keyboard-shortcuts-hint {
      display: flex;
      align-items: center;
      justify-content: flex-start;
      padding: 0.5rem 1rem;
      margin-left: 1rem;
      background: rgba(var(--tui-text-primary-rgb), 0.04);
      border-radius: 0.5rem;
      font-size: 0.875rem;
      color: var(--tui-text-secondary);

      .hint-text {
        display: flex;
        align-items: center;
        gap: 0.25rem;
      }

      kbd {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        background: var(--tui-background-base);
        border: 1px solid var(--tui-border-normal);
        border-radius: 0.25rem;
        font-family: monospace;
        font-size: 0.8em;
        font-weight: 600;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
      }
    }

    .search-row {
      display: flex;
      align-items: center;
      gap: 1rem;

      .search-input {
        flex: 0 0 300px;
      }
    }
  `]
})
export class ProjectsListComponent implements OnInit, OnDestroy {
  private apiService = inject(ApiService);
  private projectService = inject(ProjectService);
  private authService = inject(AuthService);
  private errorMessageService = inject(ErrorMessageService);
  private router = inject(Router);

  // Signals for component state
  loading = signal(false);
  error = signal<string | null>(null);
  projects = signal<ProjectListItem[]>([]);
  filteredProjects = signal<ProjectListItem[]>([]);
  stats = signal<ProjectStats | null>(null);
  statusFilter = signal<ProcessingStatus | null>(null);
  isAuthenticated = signal<boolean>(false);

  // Form controls
  searchControl = new FormControl('');

  // Subscriptions
  private subscriptions: Subscription[] = [];

  // Make ProcessingStatus available in template
  ProcessingStatus = ProcessingStatus;

  ngOnInit(): void {
    // Check if user is authenticated
    this.isAuthenticated.set(this.authService.isAuthenticated());

    this.loadProjects();
    this.loadStats();
    this.setupSearch();
    this.startPolling();
  }

  ngOnDestroy(): void {
    this.projectService.stopPollingProjects();
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  loadProjects(): void {
    this.loading.set(true);
    this.error.set(null);

    const status = this.statusFilter();
    const search = this.searchControl.value || undefined;

    this.projectService.loadProjects(status || undefined, search).subscribe({
      next: (projects) => {
        this.projects.set(projects);
        this.applyFilters();
        this.loading.set(false);
      },
      error: (err) => {
        this.errorMessageService.logError(err, 'Load Projects');
        this.error.set(this.errorMessageService.getErrorMessage(err));
        this.loading.set(false);
      }
    });
  }

  loadStats(): void {
    this.projectService.loadProjectStats().subscribe({
      next: (stats) => {
        this.stats.set(stats);
      },
      error: (err) => {
        console.error('Error loading stats:', err);
      }
    });
  }

  setupSearch(): void {
    const searchSub = this.searchControl.valueChanges.pipe(
      debounceTime(300),
      distinctUntilChanged()
    ).subscribe(() => {
      this.applyFilters();
    });

    this.subscriptions.push(searchSub);
  }

  startPolling(): void {
    // Poll for updates if there are processing projects
    const pollingSub = this.projectService.projects$.subscribe((projects) => {
      const hasProcessing = projects.some(
        p => p.processing_status === ProcessingStatus.PROCESSING
      );

      if (hasProcessing) {
        this.projectService.startPollingProjects();
      }
    });

    this.subscriptions.push(pollingSub);
  }

  applyFilters(): void {
    let filtered = this.projects();

    // Apply status filter
    const status = this.statusFilter();
    if (status) {
      filtered = filtered.filter(p => p.processing_status === status);
    }

    // Apply search filter
    const searchTerm = this.searchControl.value?.toLowerCase();
    if (searchTerm) {
      filtered = filtered.filter(p =>
        p.project_name?.toLowerCase().includes(searchTerm) ||
        p.filename.toLowerCase().includes(searchTerm) ||
        p.short_link?.toLowerCase().includes(searchTerm)
      );
    }

    this.filteredProjects.set(filtered);
  }

  setStatusFilter(status: ProcessingStatus | null): void {
    this.statusFilter.set(status);
    this.applyFilters();
  }

  confirmDelete(project: ProjectListItem): void {
    if (confirm(`Are you sure you want to delete project "${project.project_name || project.filename}"?`)) {
      this.deleteProject(project.project_id);
    }
  }

  deleteProject(projectId: string): void {
    this.apiService.deleteProject(projectId).subscribe({
      next: () => {
        this.loadProjects();
        this.loadStats();
      },
      error: (err) => {
        this.errorMessageService.logError(err, 'Delete Project');
        const errorMessage = this.errorMessageService.getErrorMessage(err);
        const suggestion = this.errorMessageService.getSuggestion(err);
        this.error.set(suggestion ? `${errorMessage}\n\n${suggestion}` : errorMessage);
      }
    });
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
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

  // TrackBy function for virtual scrolling optimization
  trackByProjectId(index: number, project: ProjectListItem): string {
    return project.project_id;
  }
}
