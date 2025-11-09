import { Component, OnInit, inject, signal, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import {
  TuiButton,
  TuiIcon,
  TuiNotification,
  TuiLoader,
  TuiLink,
  TuiHint,
} from '@taiga-ui/core';
import { TuiBadge, TuiAccordion, TuiProgressBar } from '@taiga-ui/kit';
import { ApiService } from '../../../core/services/api.service';
import { ErrorMessageService } from '../../../shared/services/error-message.service';
import { NotificationService } from '../../../core/services/notification.service';
import {
  BatchMetadata,
  BatchStatus,
  BatchProjectStatus,
  ProcessingStatus,
} from '../../../core/models/batch.model';
import { interval, Subscription } from 'rxjs';

@Component({
  selector: 'app-batch-detail',
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
    TuiLink,
    TuiHint,
    TuiProgressBar,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="batch-detail-container">
      <!-- Header with back button -->
      <div class="page-header">
        <button
          tuiButton
          appearance="ghost"
          size="s"
          routerLink="/admin/batches"
        >
          <tui-icon icon="@tui.arrow-left"></tui-icon>
          Back to Batches
        </button>
        <div class="header-actions">
          <button
            *ngIf="batch()?.status === BatchStatus.PENDING"
            tuiButton
            appearance="primary"
            size="m"
            (click)="startProcessing()"
          >
            <tui-icon icon="@tui.play"></tui-icon>
            Start Processing
          </button>
          <button
            tuiButton
            appearance="accent"
            size="m"
            (click)="downloadBatch()"
            tuiHint="Download all batch projects as ZIP archive"
          >
            <tui-icon icon="@tui.download"></tui-icon>
            Download ZIP
          </button>
          <button
            tuiButton
            appearance="outline"
            size="m"
            (click)="deleteBatch()"
          >
            <tui-icon icon="@tui.trash-2"></tui-icon>
            Delete Batch
          </button>
        </div>
      </div>

      <!-- Loading state -->
      <div *ngIf="loading()" class="loading-state">
        <tui-loader size="l"></tui-loader>
        <p>Loading batch details...</p>
      </div>

      <!-- Error state -->
      <tui-notification *ngIf="error()" status="error" class="notification">
        <div class="error-content">
          <h3>Error</h3>
          <p>{{ error() }}</p>
          <button tuiButton size="s" (click)="loadBatch()">Retry</button>
        </div>
      </tui-notification>

      <!-- Batch content -->
      <div *ngIf="!loading() && !error() && batch()" class="batch-content">
        <!-- Batch header info -->
        <div class="batch-header">
          <h1>{{ batch()?.batch_name || 'Unnamed Batch' }}</h1>
          <tui-badge
            [appearance]="getStatusAppearance(batch()!.status)"
            [class]="'status-badge-' + batch()!.status.toLowerCase()"
            size="l"
          >
            {{ batch()!.status }}
          </tui-badge>
        </div>

        <!-- Batch info cards -->
        <div class="info-cards">
          <div class="info-card">
            <div class="info-label">Batch ID</div>
            <div class="info-value monospace">{{ batch()!.batch_id }}</div>
          </div>
          <div class="info-card">
            <div class="info-label">Created</div>
            <div class="info-value">{{ formatDate(batch()!.created_date) }}</div>
          </div>
          <div class="info-card">
            <div class="info-label">Created By</div>
            <div class="info-value">{{ batch()!.created_by }}</div>
          </div>
          <div class="info-card">
            <div class="info-label">Parallel Workers</div>
            <div class="info-value">{{ batch()!.parallel_workers }}</div>
          </div>
        </div>

        <!-- Tags section -->
        <div class="section tags-section">
          <h2 class="section-title">Tags</h2>
          <div class="tags-container">
            <!-- Display existing tags -->
            <div *ngIf="batch()!.tags.length > 0" class="tags-list">
              <tui-badge
                *ngFor="let tag of batch()!.tags"
                [appearance]="'accent'"
                size="m"
                class="tag-badge"
              >
                {{ tag }}
                <button
                  class="tag-remove-btn"
                  (click)="removeTag(tag)"
                  title="Remove tag"
                >
                  ×
                </button>
              </tui-badge>
            </div>

            <!-- No tags message -->
            <p *ngIf="batch()!.tags.length === 0" class="no-tags">
              No tags assigned. Add tags to categorize and organize this batch.
            </p>

            <!-- Add tag input -->
            <div class="add-tag-input">
              <input
                #tagInput
                type="text"
                placeholder="Add a tag (e.g., customer-x, production)..."
                (keyup.enter)="addTag(tagInput.value); tagInput.value = ''"
                class="tag-input"
              />
              <button
                tuiButton
                appearance="secondary"
                size="s"
                (click)="addTag(tagInput.value); tagInput.value = ''"
              >
                <tui-icon icon="@tui.plus"></tui-icon>
                Add Tag
              </button>
            </div>
          </div>
        </div>

        <!-- Statistics section -->
        <div class="section">
          <h2 class="section-title">Statistics</h2>
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-label">Total Projects</div>
              <div class="stat-value">{{ batch()!.statistics.total_projects }}</div>
            </div>
            <div class="stat-item success">
              <div class="stat-label">Successful</div>
              <div class="stat-value">{{ batch()!.statistics.successful_projects }}</div>
            </div>
            <div class="stat-item failed">
              <div class="stat-label">Failed</div>
              <div class="stat-value">{{ batch()!.statistics.failed_projects }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">Processing Time</div>
              <div class="stat-value">{{ formatTime(batch()!.statistics.total_processing_time) }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">Total Access Points</div>
              <div class="stat-value">{{ batch()!.statistics.total_access_points }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">Total Antennas</div>
              <div class="stat-value">{{ batch()!.statistics.total_antennas }}</div>
            </div>
          </div>

          <!-- Progress bar for processing -->
          <div *ngIf="batch()!.status === BatchStatus.PROCESSING" class="progress-section">
            <div class="progress-info">
              <span>Processing Progress</span>
              <span class="progress-percentage">{{ getProcessingProgress() }}%</span>
            </div>
            <progress
              tuiProgressBar
              [value]="getProcessingProgress()"
              [max]="100"
              size="m"
            ></progress>
          </div>
        </div>

        <!-- Projects section -->
        <div class="section">
          <h2 class="section-title">Projects ({{ batch()!.project_statuses.length }})</h2>

          <div class="projects-table">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Filename</th>
                  <th>Status</th>
                  <th>Processing Time</th>
                  <th>Access Points</th>
                  <th>Antennas</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let projectStatus of batch()!.project_statuses; let i = index">
                  <td>{{ i + 1 }}</td>
                  <td>
                    <a
                      *ngIf="projectStatus.status === ProcessingStatus.COMPLETED"
                      tuiLink
                      [routerLink]="['/projects', projectStatus.project_id]"
                    >
                      {{ projectStatus.filename }}
                    </a>
                    <span *ngIf="projectStatus.status !== ProcessingStatus.COMPLETED">
                      {{ projectStatus.filename }}
                    </span>
                  </td>
                  <td>
                    <tui-badge
                      [appearance]="getProjectStatusAppearance(projectStatus.status)"
                      [class]="'status-badge-' + projectStatus.status.toLowerCase()"
                    >
                      {{ projectStatus.status }}
                    </tui-badge>
                  </td>
                  <td>
                    {{ projectStatus.processing_time ? formatTime(projectStatus.processing_time) : '-' }}
                  </td>
                  <td>{{ projectStatus.access_points_count || '-' }}</td>
                  <td>{{ projectStatus.antennas_count || '-' }}</td>
                  <td>
                    <button
                      *ngIf="projectStatus.status === ProcessingStatus.COMPLETED"
                      tuiButton
                      appearance="flat"
                      size="xs"
                      [routerLink]="['/projects', projectStatus.project_id]"
                    >
                      <tui-icon icon="@tui.eye"></tui-icon>
                    </button>
                    <span *ngIf="projectStatus.error_message" [tuiHint]="projectStatus.error_message">
                      <tui-icon icon="@tui.alert-circle" style="color: var(--tui-negative);"></tui-icon>
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Processing options section -->
        <tui-accordion>
          <tui-accordion-item>
            Processing Options
            <ng-template tuiAccordionItemContent>
              <div class="processing-options">
                <div class="option-row">
                  <span class="option-label">Group By:</span>
                  <span class="option-value">{{ batch()!.processing_options.group_by || 'None' }}</span>
                </div>
                <div class="option-row">
                  <span class="option-label">Output Formats:</span>
                  <span class="option-value">{{ batch()!.processing_options.output_formats.join(', ') }}</span>
                </div>
                <div class="option-row">
                  <span class="option-label">Visualize Floor Plans:</span>
                  <span class="option-value">{{ batch()!.processing_options.visualize_floor_plans ? 'Yes' : 'No' }}</span>
                </div>
                <div class="option-row">
                  <span class="option-label">Show Azimuth Arrows:</span>
                  <span class="option-value">{{ batch()!.processing_options.show_azimuth_arrows ? 'Yes' : 'No' }}</span>
                </div>
                <div class="option-row">
                  <span class="option-label">AP Opacity:</span>
                  <span class="option-value">{{ batch()!.processing_options.ap_opacity }}</span>
                </div>
              </div>
            </ng-template>
          </tui-accordion-item>
        </tui-accordion>
      </div>
    </div>
  `,
  styles: [
    `
      .batch-detail-container {
        padding: 24px;
      }

      .page-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
      }

      .header-actions {
        display: flex;
        gap: 12px;
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

      .batch-content {
        max-width: 1400px;
      }

      .batch-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;

        h1 {
          margin: 0;
          font-size: 32px;
          font-weight: 600;
          color: var(--tui-text-01);
        }
      }

      .info-cards {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin-bottom: 32px;
      }

      .info-card {
        background: var(--tui-base-02);
        border-radius: 12px;
        padding: 20px;
      }

      .info-label {
        font-size: 12px;
        color: var(--tui-text-03);
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
      }

      .info-value {
        font-size: 16px;
        color: var(--tui-text-01);
        font-weight: 600;

        &.monospace {
          font-family: monospace;
          font-size: 14px;
        }
      }

      .section {
        background: var(--tui-base-02);
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
      }

      .section-title {
        margin: 0 0 20px 0;
        font-size: 18px;
        font-weight: 600;
        color: var(--tui-text-01);
      }

      // Tags section styles
      .tags-section {
        .tags-container {
          .tags-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 16px;

            .tag-badge {
              display: inline-flex;
              align-items: center;
              gap: 6px;
              position: relative;

              .tag-remove-btn {
                background: none;
                border: none;
                color: currentColor;
                font-size: 18px;
                font-weight: bold;
                line-height: 1;
                padding: 0 2px;
                cursor: pointer;
                opacity: 0.7;
                transition: opacity 0.2s;

                &:hover {
                  opacity: 1;
                }
              }
            }
          }

          .no-tags {
            color: var(--tui-text-03);
            font-style: italic;
            margin-bottom: 16px;
          }

          .add-tag-input {
            display: flex;
            gap: 12px;
            align-items: center;

            .tag-input {
              flex: 1;
              padding: 10px 16px;
              border: 1px solid var(--tui-base-04);
              border-radius: 8px;
              background: var(--tui-base-01);
              color: var(--tui-text-01);
              font-size: 14px;
              transition: border-color 0.2s;

              &:focus {
                outline: none;
                border-color: var(--tui-primary);
              }

              &::placeholder {
                color: var(--tui-text-03);
              }
            }
          }
        }
      }

      .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
      }

      .stat-item {
        text-align: center;
        padding: 16px;
        background: var(--tui-base-01);
        border-radius: 8px;

        &.success {
          background: rgba(76, 175, 80, 0.1);

          .stat-value {
            color: var(--tui-positive);
          }
        }

        &.failed {
          background: rgba(244, 67, 54, 0.1);

          .stat-value {
            color: var(--tui-negative);
          }
        }
      }

      .stat-label {
        font-size: 12px;
        color: var(--tui-text-03);
        margin-bottom: 8px;
      }

      .stat-value {
        font-size: 24px;
        font-weight: 700;
        color: var(--tui-text-01);
      }

      .progress-section {
        margin-top: 24px;
      }

      .progress-info {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
        font-size: 14px;
        color: var(--tui-text-02);
      }

      .progress-percentage {
        font-weight: 600;
        color: var(--tui-text-01);
      }

      .projects-table {
        overflow-x: auto;

        table {
          width: 100%;
          border-collapse: collapse;

          thead {
            th {
              padding: 12px 16px;
              text-align: left;
              font-weight: 600;
              font-size: 12px;
              color: var(--tui-text-03);
              text-transform: uppercase;
              letter-spacing: 0.5px;
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
                padding: 12px 16px;
                font-size: 14px;
                color: var(--tui-text-01);
                border-bottom: 1px solid var(--tui-base-04);
              }
            }
          }
        }
      }

      .processing-options {
        padding: 16px;
      }

      .option-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid var(--tui-base-04);

        &:last-child {
          border-bottom: none;
        }
      }

      .option-label {
        font-weight: 600;
        color: var(--tui-text-02);
      }

      .option-value {
        color: var(--tui-text-01);
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
export class BatchDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private apiService = inject(ApiService);
  private errorMessageService = inject(ErrorMessageService);
  private notificationService = inject(NotificationService);

  // Expose enums to template
  BatchStatus = BatchStatus;
  ProcessingStatus = ProcessingStatus;

  // Signals for reactive state
  batch = signal<BatchMetadata | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);

  // Track previous status for notification on change
  private previousStatus: BatchStatus | null = null;

  // Polling for status updates
  private pollingSubscription?: Subscription;
  batchId: string = '';

  ngOnInit(): void {
    this.route.params.subscribe((params) => {
      this.batchId = params['id'];
      this.loadBatch();
      this.startPolling();
    });
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  loadBatch(): void {
    this.loading.set(true);
    this.error.set(null);

    this.apiService.getBatch(this.batchId).subscribe({
      next: (batch) => {
        console.log('Loaded batch:', batch);

        // Store previous status for comparison
        const previousBatch = this.batch();
        const statusChanged = previousBatch && previousBatch.status !== batch.status;

        this.batch.set(batch);
        this.loading.set(false);

        // Show notification if status changed to final state
        if (statusChanged && this.previousStatus === BatchStatus.PROCESSING) {
          this.showBatchNotification(batch);
        }

        // Update previous status
        this.previousStatus = batch.status;

        // Stop polling if batch is in final state
        if (
          batch.status === BatchStatus.COMPLETED ||
          batch.status === BatchStatus.FAILED ||
          batch.status === BatchStatus.PARTIAL
        ) {
          this.stopPolling();
        }
      },
      error: (err) => {
        console.error('Error loading batch:', err);
        this.errorMessageService.logError(err, 'Load Batch');
        const errorMessage = this.errorMessageService.getErrorMessage(err);
        this.error.set(errorMessage);
        this.loading.set(false);
      },
    });
  }

  private showBatchNotification(batch: BatchMetadata): void {
    const successCount = batch.project_statuses.filter(
      (p) => p.status === ProcessingStatus.COMPLETED
    ).length;
    const totalCount = batch.project_statuses.length;
    const processingTime = this.formatTime(batch.statistics.total_processing_time || 0);

    if (batch.status === BatchStatus.COMPLETED) {
      // All projects completed successfully
      this.notificationService.notifyBatchComplete(
        batch.batch_id,
        batch.batch_name || 'Untitled Batch',
        successCount,
        totalCount,
        processingTime
      );
    } else if (batch.status === BatchStatus.PARTIAL) {
      // Some projects failed
      this.notificationService.notifyBatchComplete(
        batch.batch_id,
        batch.batch_name || 'Untitled Batch',
        successCount,
        totalCount,
        processingTime
      );
    } else if (batch.status === BatchStatus.FAILED) {
      // Batch failed completely
      this.notificationService.notifyBatchFailed(
        batch.batch_id,
        batch.batch_name || 'Untitled Batch',
        'Batch processing failed'
      );
    }
  }

  startPolling(): void {
    // Poll every 5 seconds if batch is processing
    this.pollingSubscription = interval(5000).subscribe(() => {
      const currentBatch = this.batch();
      if (currentBatch?.status === BatchStatus.PROCESSING) {
        this.loadBatch();
      }
    });
  }

  stopPolling(): void {
    if (this.pollingSubscription) {
      this.pollingSubscription.unsubscribe();
      this.pollingSubscription = undefined;
    }
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

  getProjectStatusAppearance(status: ProcessingStatus): string {
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

  getProcessingProgress(): number {
    const batch = this.batch();
    if (!batch || batch.statistics.total_projects === 0) {
      return 0;
    }

    const completed = batch.statistics.successful_projects + batch.statistics.failed_projects;
    return Math.round((completed / batch.statistics.total_projects) * 100);
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

  formatTime(seconds: number): string {
    if (seconds < 60) {
      return `${seconds.toFixed(1)}s`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = Math.floor(seconds % 60);
      return `${minutes}m ${remainingSeconds}s`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return `${hours}h ${minutes}m`;
    }
  }

  startProcessing(): void {
    console.log('Starting processing for batch:', this.batchId);
    this.apiService.processBatch(this.batchId).subscribe({
      next: () => {
        console.log('Batch processing started');
        // Reload the batch to update status
        this.loadBatch();
        this.startPolling();
      },
      error: (err) => {
        console.error('Error starting batch processing:', err);
        this.errorMessageService.logError(err, 'Start Batch Processing');
        this.error.set(this.errorMessageService.getErrorMessage(err));
      },
    });
  }

  downloadBatch(): void {
    console.log('Downloading batch:', this.batchId);

    this.apiService.downloadBatch(this.batchId).subscribe({
      next: (blob: Blob) => {
        // Create blob URL and trigger download
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        // Generate filename from batch data
        const batch = this.batch();
        const safeBatchName = batch?.batch_name?.replace(/[/\\]/g, '_').replace(/\s/g, '_') || 'batch';
        a.download = `batch_${safeBatchName}_${this.batchId}.zip`;

        document.body.appendChild(a);
        a.click();

        // Cleanup
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        console.log('Batch download started');
      },
      error: (err) => {
        console.error('Download failed:', err);
        this.errorMessageService.logError(err, 'Download Batch');
        this.error.set(this.errorMessageService.getErrorMessage(err));
      }
    });
  }

  deleteBatch(): void {
    const batch = this.batch();
    const confirmed = confirm(
      `Are you sure you want to delete batch "${batch?.batch_name || 'Unnamed Batch'}"?\n\nThis will delete all ${batch?.statistics.total_projects} projects in this batch and cannot be undone.`
    );

    if (!confirmed) {
      return;
    }

    this.apiService.deleteBatch(this.batchId).subscribe({
      next: () => {
        console.log('Batch deleted successfully');
        // Navigate back to batch list
        this.router.navigate(['/admin/batches']);
      },
      error: (err) => {
        console.error('Error deleting batch:', err);
        this.errorMessageService.logError(err, 'Delete Batch');
        this.error.set(this.errorMessageService.getErrorMessage(err));
      },
    });
  }

  /**
   * Add a tag to the batch
   */
  addTag(tag: string): void {
    const trimmedTag = tag.trim();

    // Validate tag
    if (!trimmedTag) {
      return; // Empty tag
    }

    const currentBatch = this.batch();
    if (!currentBatch) {
      return;
    }

    // Check if tag already exists
    if (currentBatch.tags.includes(trimmedTag)) {
      this.notificationService.showError('Tag already exists', 'This tag is already assigned to this batch.');
      return;
    }

    // Call API to add tag
    this.apiService.updateBatchTags(this.batchId, [trimmedTag], []).subscribe({
      next: (response) => {
        console.log('Tag added successfully:', response);
        // Reload batch to get updated tags
        this.loadBatch();
        this.notificationService.showSuccess('Tag Added', `Tag "${trimmedTag}" has been added.`);
      },
      error: (err) => {
        console.error('Error adding tag:', err);
        this.errorMessageService.logError(err, 'Add Tag');
        this.notificationService.showError('Failed to add tag', this.errorMessageService.getErrorMessage(err));
      },
    });
  }

  /**
   * Remove a tag from the batch
   */
  removeTag(tag: string): void {
    if (!confirm(`Remove tag "${tag}"?`)) {
      return;
    }

    // Call API to remove tag
    this.apiService.updateBatchTags(this.batchId, [], [tag]).subscribe({
      next: (response) => {
        console.log('Tag removed successfully:', response);
        // Reload batch to get updated tags
        this.loadBatch();
        this.notificationService.showSuccess('Tag Removed', `Tag "${tag}" has been removed.`);
      },
      error: (err) => {
        console.error('Error removing tag:', err);
        this.errorMessageService.logError(err, 'Remove Tag');
        this.notificationService.showError('Failed to remove tag', this.errorMessageService.getErrorMessage(err));
      },
    });
  }
}
