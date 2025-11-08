import { Component, OnInit, inject, signal, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
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
import { TuiBadge } from '@taiga-ui/kit';
import { ApiService } from '../../../core/services/api.service';
import { ErrorMessageService } from '../../../shared/services/error-message.service';
import {
  BatchListItem,
  BatchStatus,
} from '../../../core/models/batch.model';

@Component({
  selector: 'app-batch-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    ScrollingModule,
    TuiButton,
    TuiIcon,
    TuiNotification,
    TuiLoader,
    TuiBadge,
    TuiHint,
    TuiLink,
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
        <div *ngIf="filteredBatches().length === 0" class="empty-state">
          <tui-icon icon="@tui.layers"></tui-icon>
          <h3>No batches found</h3>
          <p *ngIf="statusFilter()">
            Try adjusting your filter criteria
          </p>
          <p *ngIf="!statusFilter()">
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

        <!-- Virtual scroll table -->
        <cdk-virtual-scroll-viewport
          *ngIf="filteredBatches().length > 0"
          [itemSize]="60"
          class="virtual-scroll-viewport"
        >
          <table class="batches-table">
            <thead>
              <tr>
                <th>Batch Name</th>
                <th>Created Date</th>
                <th>Status</th>
                <th>Total Projects</th>
                <th>Successful</th>
                <th>Failed</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr *cdkVirtualFor="let batch of filteredBatches(); trackBy: trackByBatchId">
                <td>
                  <a tuiLink [routerLink]="['/admin/batches', batch.batch_id]">
                    {{ batch.batch_name || 'Unnamed Batch' }}
                  </a>
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
        margin-bottom: 24px;
      }

      .page-title {
        margin: 0;
        font-size: 28px;
        font-weight: 600;
        color: var(--tui-text-01);
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

      .virtual-scroll-viewport {
        height: calc(100vh - 400px);
        min-height: 400px;
      }

      .batches-table {
        width: 100%;
        border-collapse: collapse;

        thead {
          position: sticky;
          top: 0;
          background: var(--tui-base-03);
          z-index: 1;

          th {
            padding: 16px 20px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
            color: var(--tui-text-02);
            border-bottom: 1px solid var(--tui-base-04);
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
            }
          }
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
export class BatchListComponent implements OnInit {
  private router = inject(Router);
  private apiService = inject(ApiService);
  private errorMessageService = inject(ErrorMessageService);

  // Expose enum to template
  BatchStatus = BatchStatus;

  // Signals for reactive state
  batches = signal<BatchListItem[]>([]);
  filteredBatches = signal<BatchListItem[]>([]);
  statusFilter = signal<BatchStatus | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);

  ngOnInit(): void {
    this.loadBatches();
  }

  loadBatches(): void {
    this.loading.set(true);
    this.error.set(null);

    this.apiService.listBatches().subscribe({
      next: (batches) => {
        console.log('Loaded batches:', batches);
        this.batches.set(batches);
        this.applyFilters();
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

  setStatusFilter(status: BatchStatus | null): void {
    this.statusFilter.set(status);
    this.applyFilters();
  }

  applyFilters(): void {
    let filtered = [...this.batches()];

    // Apply status filter
    const status = this.statusFilter();
    if (status) {
      filtered = filtered.filter((batch) => batch.status === status);
    }

    this.filteredBatches.set(filtered);
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
