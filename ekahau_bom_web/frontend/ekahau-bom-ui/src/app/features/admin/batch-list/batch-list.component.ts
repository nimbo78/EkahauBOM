import { Component, OnInit, OnDestroy, inject, signal, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ScrollingModule } from '@angular/cdk/scrolling';
import {
  TuiButton,
  TuiIcon,
  TuiNotification,
  TuiLoader,
  TuiHint,
  TuiLink,
} from '@taiga-ui/core';
import { TuiBadge, TuiChip } from '@taiga-ui/kit';
import { ApiService } from '../../../core/services/api.service';
import { ErrorMessageService } from '../../../shared/services/error-message.service';
import { WebSocketService } from '../../../core/services/websocket.service';
import {
  BatchListItem,
  BatchStatus,
} from '../../../core/models/batch.model';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-batch-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    ScrollingModule,
    TuiButton,
    TuiIcon,
    TuiNotification,
    TuiLoader,
    TuiBadge,
    TuiHint,
    TuiLink,
    TuiChip,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="batches-container">
      <div class="page-header">
        <h1 class="page-title">Batch Processing</h1>
        <button
          tuiButton
          appearance="primary"
          size="m"
          [routerLink]="['/admin/batch-upload']"
        >
          <tui-icon icon="@tui.upload-cloud"></tui-icon>
          New Batch Upload
        </button>
      </div>

      <!-- Advanced Filters Section -->
      <div class="filters-section">
        <div class="filters-header">
          <button
            tuiButton
            appearance="flat"
            size="m"
            (click)="toggleFilters()"
            class="toggle-filters-btn"
          >
            <tui-icon [icon]="filtersExpanded() ? '@tui.chevron-up' : '@tui.chevron-down'"></tui-icon>
            {{ filtersExpanded() ? 'Hide' : 'Show' }} Filters
            <span *ngIf="hasActiveFilters()" class="active-filters-count">({{ getActiveFiltersCount() }})</span>
          </button>
          <button
            *ngIf="hasActiveFilters()"
            tuiButton
            appearance="flat"
            size="s"
            (click)="clearAllFilters()"
          >
            <tui-icon icon="@tui.x"></tui-icon>
            Clear All
          </button>
        </div>

        <div *ngIf="filtersExpanded()" class="filters-grid">
          <!-- Search -->
          <div class="filter-group">
            <label class="filter-label">Search</label>
            <input
              class="tui-input"
              type="text"
              [(ngModel)]="searchQuery"
              (ngModelChange)="onFilterChange()"
              placeholder="Batch name or project name..."
            />
          </div>

          <!-- Tags Filter -->
          <div class="filter-group">
            <label class="filter-label">Tags</label>
            <input
              class="tui-input"
              type="text"
              [(ngModel)]="tagsFilter"
              (ngModelChange)="onFilterChange()"
              placeholder="tag1, tag2..."
            />
          </div>

          <!-- Date Range -->
          <div class="filter-group">
            <label class="filter-label">Created After</label>
            <input
              class="tui-input"
              type="date"
              [(ngModel)]="createdAfter"
              (ngModelChange)="onFilterChange()"
            />
          </div>

          <div class="filter-group">
            <label class="filter-label">Created Before</label>
            <input
              class="tui-input"
              type="date"
              [(ngModel)]="createdBefore"
              (ngModelChange)="onFilterChange()"
            />
          </div>

          <!-- Project Count Range -->
          <div class="filter-group">
            <label class="filter-label">Min Projects</label>
            <input
              class="tui-input"
              type="number"
              [(ngModel)]="minProjects"
              (ngModelChange)="onFilterChange()"
              min="0"
              placeholder="Min"
            />
          </div>

          <div class="filter-group">
            <label class="filter-label">Max Projects</label>
            <input
              class="tui-input"
              type="number"
              [(ngModel)]="maxProjects"
              (ngModelChange)="onFilterChange()"
              min="0"
              placeholder="Max"
            />
          </div>

          <!-- Sort Options -->
          <div class="filter-group">
            <label class="filter-label">Sort By</label>
            <select
              class="tui-select"
              [(ngModel)]="sortBy"
              (ngModelChange)="onFilterChange()"
            >
              <option value="date">Date</option>
              <option value="name">Name</option>
              <option value="project_count">Project Count</option>
              <option value="success_rate">Success Rate</option>
            </select>
          </div>

          <div class="filter-group">
            <label class="filter-label">Order</label>
            <select
              class="tui-select"
              [(ngModel)]="sortOrder"
              (ngModelChange)="onFilterChange()"
            >
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </div>
        </div>

        <!-- Active Filters Display -->
        <div *ngIf="filtersExpanded() && hasActiveFilters()" class="active-filters">
          <span class="active-filters-label">Active Filters:</span>
          <tui-chip
            *ngIf="searchQuery"
            removable
            (remove)="searchQuery = ''; onFilterChange()"
          >
            Search: {{ searchQuery }}
          </tui-chip>
          <tui-chip
            *ngIf="tagsFilter"
            removable
            (remove)="tagsFilter = ''; onFilterChange()"
          >
            Tags: {{ tagsFilter }}
          </tui-chip>
          <tui-chip
            *ngIf="createdAfter"
            removable
            (remove)="createdAfter = ''; onFilterChange()"
          >
            After: {{ createdAfter }}
          </tui-chip>
          <tui-chip
            *ngIf="createdBefore"
            removable
            (remove)="createdBefore = ''; onFilterChange()"
          >
            Before: {{ createdBefore }}
          </tui-chip>
          <tui-chip
            *ngIf="minProjects !== null"
            removable
            (remove)="minProjects = null; onFilterChange()"
          >
            Min: {{ minProjects }}
          </tui-chip>
          <tui-chip
            *ngIf="maxProjects !== null"
            removable
            (remove)="maxProjects = null; onFilterChange()"
          >
            Max: {{ maxProjects }}
          </tui-chip>
        </div>
      </div>

      <!-- Statistics cards -->
      <div class="stats-cards" *ngIf="batches().length > 0">
        <div
          class="stat-card"
          [class.active]="statusFilter() === null"
          (click)="setStatusFilter(null)"
        >
          <div class="stat-value">{{ getTotalCount() }}</div>
          <div class="stat-label">Total Batches</div>
        </div>
        <div
          class="stat-card pending"
          [class.active]="statusFilter() === BatchStatus.PENDING"
          (click)="setStatusFilter(BatchStatus.PENDING)"
        >
          <div class="stat-value">{{ getStatusCount(BatchStatus.PENDING) }}</div>
          <div class="stat-label">Pending</div>
        </div>
        <div
          class="stat-card processing"
          [class.active]="statusFilter() === BatchStatus.PROCESSING"
          (click)="setStatusFilter(BatchStatus.PROCESSING)"
        >
          <div class="stat-value">{{ getStatusCount(BatchStatus.PROCESSING) }}</div>
          <div class="stat-label">Processing</div>
        </div>
        <div
          class="stat-card completed"
          [class.active]="statusFilter() === BatchStatus.COMPLETED"
          (click)="setStatusFilter(BatchStatus.COMPLETED)"
        >
          <div class="stat-value">{{ getStatusCount(BatchStatus.COMPLETED) }}</div>
          <div class="stat-label">Completed</div>
        </div>
        <div
          class="stat-card partial"
          *ngIf="getStatusCount(BatchStatus.PARTIAL) > 0"
          [class.active]="statusFilter() === BatchStatus.PARTIAL"
          (click)="setStatusFilter(BatchStatus.PARTIAL)"
        >
          <div class="stat-value">{{ getStatusCount(BatchStatus.PARTIAL) }}</div>
          <div class="stat-label">Partial</div>
        </div>
        <div
          class="stat-card failed"
          *ngIf="getStatusCount(BatchStatus.FAILED) > 0"
          [class.active]="statusFilter() === BatchStatus.FAILED"
          (click)="setStatusFilter(BatchStatus.FAILED)"
        >
          <div class="stat-value">{{ getStatusCount(BatchStatus.FAILED) }}</div>
          <div class="stat-label">Failed</div>
        </div>
      </div>

      <!-- Loading state -->
      <div *ngIf="loading()" class="loading-state">
        <tui-loader size="l"></tui-loader>
        <p>Loading batches...</p>
      </div>

      <!-- Error state -->
      <tui-notification *ngIf="error()" status="error" class="notification">
        <div class="error-content">
          <h3>Error loading batches</h3>
          <p>{{ error() }}</p>
          <button tuiButton size="s" (click)="loadBatches()">Retry</button>
        </div>
      </tui-notification>

      <!-- Batches table -->
      <div *ngIf="!loading() && !error()" class="table-wrapper">
        <!-- Empty state -->
        <div *ngIf="batches().length === 0" class="empty-state">
          <tui-icon icon="@tui.layers"></tui-icon>
          <h3>No batches found</h3>
          <p *ngIf="hasActiveFilters() || statusFilter()">
            Try adjusting your filter criteria
          </p>
          <p *ngIf="!hasActiveFilters() && !statusFilter()">
            Use the "New Batch Upload" button to create your first batch
          </p>
          <button
            tuiButton
            appearance="primary"
            size="m"
            [routerLink]="['/admin/batch-upload']"
          >
            <tui-icon icon="@tui.upload-cloud"></tui-icon>
            Create First Batch
          </button>
        </div>

        <!-- Table with fixed header and virtual scrolling body -->
        <div *ngIf="batches().length > 0" class="table-container">
          <!-- Fixed header -->
          <table class="batches-table batches-table-header">
            <thead>
              <tr>
                <th>Batch Name</th>
                <th>Tags</th>
                <th>Created Date</th>
                <th>Status</th>
                <th>Total Projects</th>
                <th>Successful</th>
                <th>Failed</th>
                <th>Actions</th>
              </tr>
            </thead>
          </table>

          <!-- Virtual scroll body -->
          <cdk-virtual-scroll-viewport
            [itemSize]="60"
            class="virtual-scroll-viewport"
          >
            <table class="batches-table batches-table-body">
              <tbody>
                <tr *cdkVirtualFor="let batch of batches(); trackBy: trackByBatchId">
                  <td>
                    <a tuiLink [routerLink]="['/admin/batches', batch.batch_id]">
                      {{ batch.batch_name || 'Unnamed Batch' }}
                    </a>
                  </td>
                  <td>
                    <div class="tags-cell" *ngIf="batch.tags && batch.tags.length > 0">
                      <tui-badge
                        *ngFor="let tag of batch.tags"
                        [appearance]="'accent'"
                        size="s"
                        class="tag-badge-small"
                      >
                        {{ tag }}
                      </tui-badge>
                    </div>
                    <span *ngIf="!batch.tags || batch.tags.length === 0" class="no-tags-text">—</span>
                  </td>
                  <td>{{ formatDate(batch.created_date) }}</td>
                  <td>
                    <tui-badge
                      [appearance]="getStatusAppearance(batch.status)"
                      [class]="'status-badge-' + batch.status.toLowerCase()"
                    >
                      {{ batch.status }}
                    </tui-badge>
                  </td>
                  <td>{{ batch.total_projects }}</td>
                  <td class="success-count">{{ batch.successful_projects }}</td>
                  <td class="failed-count" [class.has-failures]="batch.failed_projects > 0">
                    {{ batch.failed_projects }}
                  </td>
                  <td>
                    <div class="actions">
                      <button
                        tuiButton
                        appearance="flat"
                        size="s"
                        [routerLink]="['/admin/batches', batch.batch_id]"
                        [tuiHint]="viewHint"
                        style="background-color: #e8eef7; color: #526ed3; min-width: 36px; padding: 8px; border: 1px solid #526ed3; border-radius: 4px; margin-right: 4px;"
                      >
                        <tui-icon icon="@tui.eye"></tui-icon>
                      </button>
                      <button
                        *ngIf="batch.status === BatchStatus.PENDING"
                        tuiButton
                        appearance="flat"
                        size="s"
                        (click)="startProcessing(batch.batch_id)"
                        [tuiHint]="processHint"
                        style="background-color: #e8f5e9; color: #4caf50; min-width: 36px; padding: 8px; border: 1px solid #4caf50; border-radius: 4px; margin-right: 4px;"
                      >
                        <tui-icon icon="@tui.play"></tui-icon>
                      </button>
                      <button
                        tuiButton
                        appearance="flat"
                        size="s"
                        (click)="confirmDelete(batch)"
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

      <!-- Hint templates -->
      <ng-template #viewHint>
        <div class="custom-hint">
          <tui-icon icon="@tui.eye" class="hint-icon"></tui-icon>
          <span class="hint-text">View Details</span>
        </div>
      </ng-template>

      <ng-template #processHint>
        <div class="custom-hint custom-hint-success">
          <tui-icon icon="@tui.play" class="hint-icon"></tui-icon>
          <span class="hint-text">Start Processing</span>
        </div>
      </ng-template>

      <ng-template #deleteHint>
        <div class="custom-hint custom-hint-danger">
          <tui-icon icon="@tui.trash-2" class="hint-icon"></tui-icon>
          <span class="hint-text">Delete Batch</span>
        </div>
      </ng-template>
    </div>
  `,
  styles: [
    `
      .batches-container {
        padding: 24px;
      }

      .page-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
      }

      .page-title {
        margin: 0;
        font-size: 28px;
        font-weight: 600;
        color: var(--tui-text-01);
      }

      /* Filters Section */
      .filters-section {
        background: var(--tui-base-02);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 24px;
      }

      .filters-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0;
      }

      .toggle-filters-btn {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 500;
      }

      .active-filters-count {
        color: var(--tui-primary);
        font-weight: 600;
        margin-left: 4px;
      }

      .filters-title {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
        color: var(--tui-text-01);
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .filters-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin-top: 16px;
        margin-bottom: 16px;
      }

      .filter-group {
        display: flex;
        flex-direction: column;
        gap: 6px;
      }

      .filter-label {
        font-size: 13px;
        font-weight: 500;
        color: var(--tui-text-02);
      }

      .tui-input,
      .tui-select {
        width: 100%;
        padding: 8px 12px;
        border: 1px solid var(--tui-base-04);
        border-radius: 6px;
        font-size: 14px;
        background: var(--tui-base-01);
        color: var(--tui-text-01);
        transition: all 0.2s ease;

        &:focus {
          outline: none;
          border-color: var(--tui-primary);
          box-shadow: 0 0 0 2px rgba(82, 110, 211, 0.1);
        }

        &::placeholder {
          color: var(--tui-text-03);
        }
      }

      .tui-select {
        cursor: pointer;
      }

      .active-filters {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        align-items: center;
        padding-top: 16px;
        border-top: 1px solid var(--tui-base-04);
      }

      .active-filters-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--tui-text-02);
      }

      .stats-cards {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
      }

      .stat-card {
        background: var(--tui-base-02);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s ease;
        border: 2px solid transparent;

        &:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        &.active {
          border-color: var(--tui-primary);
          background: var(--tui-primary-bg);
        }

        &.pending {
          &.active {
            border-color: #ff9800;
            background: rgba(255, 152, 0, 0.1);
          }
        }

        &.processing {
          &.active {
            border-color: #2196f3;
            background: rgba(33, 150, 243, 0.1);
          }
        }

        &.completed {
          &.active {
            border-color: #4caf50;
            background: rgba(76, 175, 80, 0.1);
          }
        }

        &.partial {
          &.active {
            border-color: #ffc107;
            background: rgba(255, 193, 7, 0.1);
          }
        }

        &.failed {
          &.active {
            border-color: #f44336;
            background: rgba(244, 67, 54, 0.1);
          }
        }
      }

      .stat-value {
        font-size: 32px;
        font-weight: 700;
        color: var(--tui-text-01);
        margin-bottom: 8px;
      }

      .stat-label {
        font-size: 14px;
        color: var(--tui-text-03);
        font-weight: 500;
      }

      .loading-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 48px;
        gap: 16px;
        color: var(--tui-text-02);
      }

      .notification {
        margin-bottom: 16px;
      }

      .error-content {
        h3 {
          margin: 0 0 8px 0;
        }

        p {
          margin: 8px 0;
        }
      }

      .table-wrapper {
        background: var(--tui-base-02);
        border-radius: 12px;
        overflow: hidden;
      }

      .empty-state {
        padding: 48px;
        text-align: center;

        tui-icon {
          font-size: 64px;
          color: var(--tui-text-03);
          margin-bottom: 16px;
          display: block;
        }

        h3 {
          margin: 0 0 8px 0;
          color: var(--tui-text-01);
        }

        p {
          margin: 8px 0 24px 0;
          color: var(--tui-text-03);
        }
      }

      .table-container {
        display: flex;
        flex-direction: column;
      }

      .virtual-scroll-viewport {
        height: calc(100vh - 650px);
        min-height: 400px;
      }

      .batches-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;

        // Define fixed column widths for alignment
        th:nth-child(1), td:nth-child(1) { width: 20%; } // Batch Name
        th:nth-child(2), td:nth-child(2) { width: 15%; } // Tags
        th:nth-child(3), td:nth-child(3) { width: 12%; } // Created Date
        th:nth-child(4), td:nth-child(4) { width: 10%; } // Status
        th:nth-child(5), td:nth-child(5) { width: 10%; } // Total Projects
        th:nth-child(6), td:nth-child(6) { width: 9%; }  // Successful
        th:nth-child(7), td:nth-child(7) { width: 8%; }  // Failed
        th:nth-child(8), td:nth-child(8) { width: 16%; } // Actions

        thead {
          background: var(--tui-base-03);

          th {
            padding: 16px 20px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
            color: var(--tui-text-02);
            border-bottom: 2px solid var(--tui-base-04);
          }
        }

        tbody {
          tr {
            transition: background-color 0.2s ease;

            &:hover {
              background: var(--tui-base-01);
            }

            td {
              padding: 16px 20px;
              font-size: 14px;
              color: var(--tui-text-01);
              border-bottom: 1px solid var(--tui-base-04);
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
            }
          }
        }
      }

      .batches-table-header {
        // Fixed header table - no scroll
        display: block;

        thead {
          display: block;
          width: 100%;
        }

        tr {
          display: table;
          width: 100%;
          table-layout: fixed;
        }
      }

      .batches-table-body {
        // Body table inside virtual scroll
        display: block;

        tbody {
          display: block;
          width: 100%;
        }

        tr {
          display: table;
          width: 100%;
          table-layout: fixed;
        }
      }

      .success-count {
        color: var(--tui-positive);
        font-weight: 600;
      }

      .failed-count {
        color: var(--tui-text-03);

        &.has-failures {
          color: var(--tui-negative);
          font-weight: 600;
        }
      }

      .actions {
        display: flex;
        gap: 8px;
        align-items: center;
      }

      .tags-cell {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        max-width: 100%;
        white-space: normal !important;

        .tag-badge-small {
          font-size: 11px;
        }
      }

      // Allow tags column to wrap
      td:nth-child(2) {
        white-space: normal !important;
      }

      .no-tags-text {
        color: var(--tui-text-03);
        font-style: italic;
      }

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

      .custom-hint-success {
        background: rgba(76, 175, 80, 0.85);

        .hint-icon,
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

      .status-badge-pending {
        background-color: rgba(255, 152, 0, 0.1);
        color: #ff9800;
      }

      .status-badge-processing {
        background-color: rgba(33, 150, 243, 0.1);
        color: #2196f3;
      }

      .status-badge-completed {
        background-color: rgba(76, 175, 80, 0.1);
        color: #4caf50;
      }

      .status-badge-partial {
        background-color: rgba(255, 193, 7, 0.1);
        color: #ffc107;
      }

      .status-badge-failed {
        background-color: rgba(244, 67, 54, 0.1);
        color: #f44336;
      }
    `,
  ],
})
export class BatchListComponent implements OnInit, OnDestroy {
  private router = inject(Router);
  private apiService = inject(ApiService);
  private errorMessageService = inject(ErrorMessageService);
  private wsService = inject(WebSocketService);

  // Expose enum to template
  BatchStatus = BatchStatus;

  // Signals for reactive state
  batches = signal<BatchListItem[]>([]);
  statusFilter = signal<BatchStatus | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);
  filtersExpanded = signal(false); // Filters collapsed by default

  // Filter properties
  searchQuery: string = '';
  tagsFilter: string = '';
  createdAfter: string = '';
  createdBefore: string = '';
  minProjects: number | null = null;
  maxProjects: number | null = null;
  sortBy: 'date' | 'name' | 'project_count' | 'success_rate' = 'date';
  sortOrder: 'asc' | 'desc' = 'desc';

  // WebSocket subscriptions
  private batchUpdateSubscription?: Subscription;
  private batchCreatedSubscription?: Subscription;
  private batchDeletedSubscription?: Subscription;

  ngOnInit(): void {
    this.loadBatches();
    this.setupWebSocketSubscriptions();

    // Connect to WebSocket if not already connected
    if (!this.wsService.isConnected()) {
      this.wsService.connect();
    }
  }

  ngOnDestroy(): void {
    // Clean up WebSocket subscriptions
    this.batchUpdateSubscription?.unsubscribe();
    this.batchCreatedSubscription?.unsubscribe();
    this.batchDeletedSubscription?.unsubscribe();
  }

  private setupWebSocketSubscriptions(): void {
    // Subscribe to batch updates (status changes)
    this.batchUpdateSubscription = this.wsService.batchUpdates$.subscribe((update) => {
      console.log('[BatchList] Received batch update:', update);
      // Reload list to reflect status changes
      this.loadBatches();
    });

    // Subscribe to new batch creations
    this.batchCreatedSubscription = this.wsService.batchCreated$.subscribe((data) => {
      console.log('[BatchList] Received batch created:', data);
      // Reload list to show new batch
      this.loadBatches();
    });

    // Subscribe to batch deletions
    this.batchDeletedSubscription = this.wsService.batchDeleted$.subscribe((data) => {
      console.log('[BatchList] Received batch deleted:', data);
      // Reload list to remove deleted batch
      this.loadBatches();
    });
  }

  loadBatches(): void {
    this.loading.set(true);
    this.error.set(null);

    // Build filter options
    const options: any = {
      sortBy: this.sortBy,
      sortOrder: this.sortOrder,
    };

    if (this.statusFilter()) {
      options.status = this.statusFilter();
    }
    if (this.searchQuery) {
      options.search = this.searchQuery;
    }
    if (this.tagsFilter) {
      options.tags = this.tagsFilter.split(',').map(t => t.trim()).filter(t => t);
    }
    if (this.createdAfter) {
      options.createdAfter = new Date(this.createdAfter).toISOString();
    }
    if (this.createdBefore) {
      options.createdBefore = new Date(this.createdBefore).toISOString();
    }
    if (this.minProjects !== null) {
      options.minProjects = this.minProjects;
    }
    if (this.maxProjects !== null) {
      options.maxProjects = this.maxProjects;
    }

    this.apiService.listBatches(options).subscribe({
      next: (batches) => {
        console.log('Loaded batches:', batches);
        this.batches.set(batches);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Error loading batches:', err);
        this.errorMessageService.logError(err, 'Load Batches');
        const errorMessage = this.errorMessageService.getErrorMessage(err);
        this.error.set(errorMessage);
        this.loading.set(false);
      },
    });
  }

  onFilterChange(): void {
    this.loadBatches();
  }

  setStatusFilter(status: BatchStatus | null): void {
    this.statusFilter.set(status);
    this.loadBatches();
  }

  hasActiveFilters(): boolean {
    return !!(
      this.searchQuery ||
      this.tagsFilter ||
      this.createdAfter ||
      this.createdBefore ||
      this.minProjects !== null ||
      this.maxProjects !== null
    );
  }

  toggleFilters(): void {
    this.filtersExpanded.set(!this.filtersExpanded());
  }

  getActiveFiltersCount(): number {
    let count = 0;
    if (this.searchQuery) count++;
    if (this.tagsFilter) count++;
    if (this.createdAfter) count++;
    if (this.createdBefore) count++;
    if (this.minProjects !== null) count++;
    if (this.maxProjects !== null) count++;
    return count;
  }

  clearAllFilters(): void {
    this.searchQuery = '';
    this.tagsFilter = '';
    this.createdAfter = '';
    this.createdBefore = '';
    this.minProjects = null;
    this.maxProjects = null;
    this.sortBy = 'date';
    this.sortOrder = 'desc';
    this.statusFilter.set(null);
    this.loadBatches();
  }

  getTotalCount(): number {
    return this.batches().length;
  }

  getStatusCount(status: BatchStatus): number {
    return this.batches().filter((batch) => batch.status === status).length;
  }

  getStatusAppearance(status: BatchStatus): string {
    switch (status) {
      case BatchStatus.PENDING:
        return 'warning';
      case BatchStatus.PROCESSING:
        return 'info';
      case BatchStatus.COMPLETED:
        return 'success';
      case BatchStatus.PARTIAL:
        return 'warning';
      case BatchStatus.FAILED:
        return 'error';
      default:
        return 'neutral';
    }
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  }

  trackByBatchId(index: number, batch: BatchListItem): string {
    return batch.batch_id;
  }

  startProcessing(batchId: string): void {
    console.log('Starting processing for batch:', batchId);
    this.apiService.processBatch(batchId).subscribe({
      next: () => {
        console.log('Batch processing started');
        // Reload the batch list to update status
        this.loadBatches();
      },
      error: (err) => {
        console.error('Error starting batch processing:', err);
        this.errorMessageService.logError(err, 'Start Batch Processing');
        this.error.set(this.errorMessageService.getErrorMessage(err));
      },
    });
  }

  confirmDelete(batch: BatchListItem): void {
    const confirmed = confirm(
      `Are you sure you want to delete batch "${batch.batch_name || 'Unnamed Batch'}"?\n\nThis will delete all ${batch.total_projects} projects in this batch and cannot be undone.`
    );

    if (confirmed) {
      this.deleteBatch(batch.batch_id);
    }
  }

  deleteBatch(batchId: string): void {
    this.apiService.deleteBatch(batchId).subscribe({
      next: () => {
        console.log('Batch deleted successfully');
        // Reload the batch list
        this.loadBatches();
      },
      error: (err) => {
        console.error('Error deleting batch:', err);
        this.errorMessageService.logError(err, 'Delete Batch');
        this.error.set(this.errorMessageService.getErrorMessage(err));
      },
    });
  }
}
