import { Component, OnInit, OnDestroy, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
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
  TuiBadge,
  TuiPagination
} from '@taiga-ui/kit';
import { ApiService } from '../../../core/services/api.service';
import { ProjectService } from '../../../core/services/project.service';
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
    TuiButton,
    TuiIcon,
    TuiNotification,
    TuiLoader,
    TuiBadge,
    TuiTextfield,
    TuiHint,
    TuiLink,
    TuiPagination
  ],
  template: `
    <div class="projects-container">
      <div class="page-header">
        <h1 class="page-title">Projects</h1>
        <button tuiButton appearance="primary" size="l" routerLink="/admin/upload">
          <tui-icon icon="@tui.plus"></tui-icon>
          Upload New Project
        </button>
      </div>

      <!-- Statistics cards -->
      <div class="stats-cards" *ngIf="stats()">
        <div class="stat-card">
          <div class="stat-value">{{ stats()?.total || 0 }}</div>
          <div class="stat-label">Total Projects</div>
        </div>
        <div class="stat-card pending">
          <div class="stat-value">{{ stats()?.pending || 0 }}</div>
          <div class="stat-label">Pending</div>
        </div>
        <div class="stat-card processing">
          <div class="stat-value">{{ stats()?.processing || 0 }}</div>
          <div class="stat-label">Processing</div>
        </div>
        <div class="stat-card completed">
          <div class="stat-value">{{ stats()?.completed || 0 }}</div>
          <div class="stat-label">Completed</div>
        </div>
        <div class="stat-card failed" *ngIf="(stats()?.failed || 0) > 0">
          <div class="stat-value">{{ stats()?.failed || 0 }}</div>
          <div class="stat-label">Failed</div>
        </div>
      </div>

      <!-- Search and filters -->
      <div class="filters-row">
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

        <div class="status-filters">
          <button
            tuiButton
            [appearance]="statusFilter() === null ? 'primary' : 'secondary'"
            size="m"
            (click)="setStatusFilter(null)"
          >
            All
          </button>
          <button
            tuiButton
            [appearance]="statusFilter() === ProcessingStatus.PENDING ? 'primary' : 'secondary'"
            size="m"
            (click)="setStatusFilter(ProcessingStatus.PENDING)"
          >
            Pending
          </button>
          <button
            tuiButton
            [appearance]="statusFilter() === ProcessingStatus.PROCESSING ? 'primary' : 'secondary'"
            size="m"
            (click)="setStatusFilter(ProcessingStatus.PROCESSING)"
          >
            Processing
          </button>
          <button
            tuiButton
            [appearance]="statusFilter() === ProcessingStatus.COMPLETED ? 'primary' : 'secondary'"
            size="m"
            (click)="setStatusFilter(ProcessingStatus.COMPLETED)"
          >
            Completed
          </button>
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
        <table class="projects-table">
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
          <tbody>
            <tr *ngFor="let project of filteredProjects()">
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
                  size="s"
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
                    tuiHint="View Details"
                    style="background-color: #e8eef7; color: #526ed3; min-width: 36px; padding: 8px; border: 1px solid #526ed3; border-radius: 4px; margin-right: 4px;"
                  >
                    <tui-icon icon="@tui.eye"></tui-icon>
                  </button>
                  <button
                    *ngIf="project.processing_status === ProcessingStatus.PENDING ||
                           project.processing_status === ProcessingStatus.COMPLETED ||
                           project.processing_status === ProcessingStatus.FAILED"
                    tuiButton
                    appearance="flat"
                    size="s"
                    [routerLink]="['/admin/processing']"
                    [queryParams]="{projectId: project.project_id}"
                    [tuiHint]="project.processing_status === ProcessingStatus.PENDING ? 'Configure Processing' : 'Reprocess Project'"
                    style="background-color: #e8eef7; color: #526ed3; min-width: 36px; padding: 8px; border: 1px solid #526ed3; border-radius: 4px; margin-right: 4px;"
                  >
                    <tui-icon icon="@tui.settings"></tui-icon>
                  </button>
                  <button
                    tuiButton
                    appearance="flat"
                    size="s"
                    (click)="confirmDelete(project)"
                    tuiHint="Delete Project"
                    style="background-color: #fce8e6; color: #e01f19; min-width: 36px; padding: 8px; border: 1px solid #e01f19; border-radius: 4px;"
                  >
                    <tui-icon icon="@tui.trash-2"></tui-icon>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Empty state -->
        <div *ngIf="filteredProjects().length === 0" class="empty-state">
          <tui-icon icon="@tui.folder"></tui-icon>
          <h3>No projects found</h3>
          <p *ngIf="searchControl.value || statusFilter()">
            Try adjusting your search or filter criteria
          </p>
          <p *ngIf="!searchControl.value && !statusFilter()">
            Upload your first project to get started
          </p>
          <button tuiButton appearance="primary" size="m" routerLink="/admin/upload">
            <tui-icon icon="@tui.plus"></tui-icon>
            Upload Project
          </button>
        </div>
      </div>
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

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
      }

      &.pending {
        border-color: var(--tui-warning);
      }

      &.processing {
        border-color: var(--tui-info);
      }

      &.completed {
        border-color: var(--tui-success);
      }

      &.failed {
        border-color: var(--tui-error);
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

    .filters-row {
      display: flex;
      gap: 2rem;
      align-items: center;
      margin-bottom: 2rem;
    }

    .search-input {
      flex: 1;
      max-width: 400px;
    }

    .status-filters {
      display: flex;
      gap: 0.5rem;
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

    .projects-table {
      width: 100%;

      th {
        padding: 1rem;
        font-weight: 600;
        background: var(--tui-base-02);
        text-align: left;
      }

      td {
        padding: 1rem;
      }

      tr:hover {
        background: var(--tui-base-02);
      }
    }

    .actions {
      display: flex;
      gap: 0.25rem;
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
  `]
})
export class ProjectsListComponent implements OnInit, OnDestroy {
  private apiService = inject(ApiService);
  private projectService = inject(ProjectService);
  private router = inject(Router);

  // Signals for component state
  loading = signal(false);
  error = signal<string | null>(null);
  projects = signal<ProjectListItem[]>([]);
  filteredProjects = signal<ProjectListItem[]>([]);
  stats = signal<ProjectStats | null>(null);
  statusFilter = signal<ProcessingStatus | null>(null);

  // Form controls
  searchControl = new FormControl('');

  // Subscriptions
  private subscriptions: Subscription[] = [];

  // Make ProcessingStatus available in template
  ProcessingStatus = ProcessingStatus;

  ngOnInit(): void {
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
        this.error.set('Failed to load projects. Please try again.');
        this.loading.set(false);
        console.error('Error loading projects:', err);
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
        this.error.set('Failed to delete project. Please try again.');
        console.error('Error deleting project:', err);
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
}
