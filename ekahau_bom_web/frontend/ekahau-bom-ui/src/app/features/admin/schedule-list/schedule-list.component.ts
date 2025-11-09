import { Component, OnInit, inject, signal, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import {
  TuiButton,
  TuiIcon,
  TuiNotification,
  TuiLoader,
  TuiHint,
} from '@taiga-ui/core';
import { TuiBadge, TuiSwitch } from '@taiga-ui/kit';
import { ApiService } from '../../../core/services/api.service';
import { ErrorMessageService } from '../../../shared/services/error-message.service';
import {
  ScheduleListItem,
  ScheduleStatus,
  TriggerType,
  parseCronExpression,
  getStatusColor,
  getStatusIcon,
} from '../../../core/models/schedule.model';

@Component({
  selector: 'app-schedule-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    TuiButton,
    TuiIcon,
    TuiNotification,
    TuiLoader,
    TuiBadge,
    TuiHint,
    TuiSwitch,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="schedules-container">
      <div class="page-header">
        <h1 class="page-title">Scheduled Processing</h1>
        <button
          tuiButton
          appearance="primary"
          size="m"
          (click)="createSchedule()"
        >
          <tui-icon icon="@tui.clock"></tui-icon>
          New Schedule
        </button>
      </div>

      <!-- Filters Section -->
      <div class="filters-section">
        <div class="filters-header">
          <h3 class="filters-title">
            <tui-icon icon="@tui.filter"></tui-icon>
            Filters
          </h3>
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

        <div class="filters-grid">
          <!-- Enabled Filter -->
          <div class="filter-group">
            <label class="filter-label">Status</label>
            <select
              class="tui-select"
              [(ngModel)]="enabledFilter"
              (ngModelChange)="onFilterChange()"
            >
              <option [ngValue]="null">All Schedules</option>
              <option [ngValue]="true">Enabled Only</option>
              <option [ngValue]="false">Disabled Only</option>
            </select>
          </div>

          <!-- Trigger Type Filter -->
          <div class="filter-group">
            <label class="filter-label">Trigger Type</label>
            <select
              class="tui-select"
              [(ngModel)]="triggerTypeFilter"
              (ngModelChange)="onFilterChange()"
            >
              <option [ngValue]="null">All Types</option>
              <option [ngValue]="TriggerType.Cron">Cron (Time-based)</option>
              <option [ngValue]="TriggerType.Directory">Directory Watch</option>
              <option [ngValue]="TriggerType.S3">S3 Watch</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Statistics cards -->
      <div class="stats-cards" *ngIf="schedules().length > 0">
        <div class="stat-card">
          <div class="stat-value">{{ getTotalCount() }}</div>
          <div class="stat-label">Total Schedules</div>
        </div>
        <div class="stat-card enabled">
          <div class="stat-value">{{ getEnabledCount() }}</div>
          <div class="stat-label">Enabled</div>
        </div>
        <div class="stat-card disabled">
          <div class="stat-value">{{ getDisabledCount() }}</div>
          <div class="stat-label">Disabled</div>
        </div>
        <div class="stat-card running" *ngIf="getRunningCount() > 0">
          <div class="stat-value">{{ getRunningCount() }}</div>
          <div class="stat-label">Running Now</div>
        </div>
      </div>

      <!-- Loading state -->
      <div *ngIf="loading()" class="loading-state">
        <tui-loader size="l"></tui-loader>
        <p>Loading schedules...</p>
      </div>

      <!-- Error state -->
      <tui-notification *ngIf="error()" status="error" class="notification">
        <div class="error-content">
          <h3>Error loading schedules</h3>
          <p>{{ error() }}</p>
          <button tuiButton size="s" (click)="loadSchedules()">Retry</button>
        </div>
      </tui-notification>

      <!-- Schedules table -->
      <div *ngIf="!loading() && !error()" class="table-wrapper">
        <!-- Empty state -->
        <div *ngIf="schedules().length === 0" class="empty-state">
          <tui-icon icon="@tui.clock"></tui-icon>
          <h3>No schedules found</h3>
          <p *ngIf="hasActiveFilters()">
            Try adjusting your filter criteria
          </p>
          <p *ngIf="!hasActiveFilters()">
            Create your first automated schedule to process .esx files on a recurring basis.
          </p>
          <button
            tuiButton
            appearance="primary"
            size="m"
            (click)="createSchedule()"
          >
            <tui-icon icon="@tui.clock"></tui-icon>
            Create Schedule
          </button>
        </div>

        <!-- Schedules table -->
        <table *ngIf="schedules().length > 0" class="schedules-table">
          <thead>
            <tr>
              <th>Schedule Name</th>
              <th>Trigger</th>
              <th>Next Run</th>
              <th>Last Run</th>
              <th>Executions</th>
              <th>Enabled</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let schedule of schedules(); trackBy: trackByScheduleId">
              <td>
                <div class="schedule-name">
                  <strong>{{ schedule.name }}</strong>
                  <span class="schedule-desc" *ngIf="schedule.description">
                    {{ schedule.description }}
                  </span>
                </div>
              </td>
              <td>
                <div class="trigger-info">
                  <tui-badge [size]="'m'" [value]="getTriggerTypeLabel(schedule.trigger_type)"></tui-badge>
                  <span class="cron-text" *ngIf="schedule.trigger_type === TriggerType.Cron">
                    {{ parseCronExpression(schedule.cron_expression) }}
                  </span>
                </div>
              </td>
              <td>
                <span *ngIf="schedule.next_run_time" class="next-run-time">
                  {{ formatDate(schedule.next_run_time) }}
                </span>
                <span *ngIf="!schedule.next_run_time || !schedule.enabled" class="no-data">
                  {{ !schedule.enabled ? 'Disabled' : 'N/A' }}
                </span>
              </td>
              <td>
                <div *ngIf="schedule.last_run_status" class="last-run-info">
                  <tui-badge
                    [size]="'m'"
                    [status]="getStatusColor(schedule.last_run_status)"
                    [value]="schedule.last_run_status"
                  ></tui-badge>
                  <span class="last-run-time" *ngIf="schedule.last_run_time">
                    {{ formatDate(schedule.last_run_time) }}
                  </span>
                </div>
                <span *ngIf="!schedule.last_run_status" class="no-data">Never run</span>
              </td>
              <td class="execution-count">
                {{ schedule.execution_count }}
              </td>
              <td>
                <tui-switch
                  [ngModel]="schedule.enabled"
                  (ngModelChange)="toggleSchedule(schedule.schedule_id, $event)"
                ></tui-switch>
              </td>
              <td>
                <div class="actions">
                  <button
                    tuiButton
                    appearance="flat"
                    size="s"
                    [tuiHint]="viewHint"
                    (click)="viewSchedule(schedule.schedule_id)"
                  >
                    <tui-icon icon="@tui.eye"></tui-icon>
                  </button>
                  <button
                    tuiButton
                    appearance="flat"
                    size="s"
                    [tuiHint]="editHint"
                    (click)="editSchedule(schedule.schedule_id)"
                  >
                    <tui-icon icon="@tui.edit"></tui-icon>
                  </button>
                  <button
                    tuiButton
                    appearance="flat"
                    size="s"
                    [tuiHint]="runHint"
                    [disabled]="!schedule.enabled"
                    (click)="runScheduleNow(schedule.schedule_id)"
                  >
                    <tui-icon icon="@tui.play"></tui-icon>
                  </button>
                  <button
                    tuiButton
                    appearance="flat"
                    size="s"
                    [tuiHint]="deleteHint"
                    (click)="confirmDelete(schedule)"
                  >
                    <tui-icon icon="@tui.trash-2"></tui-icon>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Hint templates -->
      <ng-template #viewHint>
        <div class="custom-hint">
          <tui-icon icon="@tui.eye" class="hint-icon"></tui-icon>
          <span class="hint-text">View Details & History</span>
        </div>
      </ng-template>

      <ng-template #editHint>
        <div class="custom-hint">
          <tui-icon icon="@tui.edit" class="hint-icon"></tui-icon>
          <span class="hint-text">Edit Schedule</span>
        </div>
      </ng-template>

      <ng-template #runHint>
        <div class="custom-hint custom-hint-success">
          <tui-icon icon="@tui.play" class="hint-icon"></tui-icon>
          <span class="hint-text">Run Now</span>
        </div>
      </ng-template>

      <ng-template #deleteHint>
        <div class="custom-hint custom-hint-danger">
          <tui-icon icon="@tui.trash-2" class="hint-icon"></tui-icon>
          <span class="hint-text">Delete Schedule</span>
        </div>
      </ng-template>
    </div>
  `,
  styles: [
    `
      .schedules-container {
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
        margin-bottom: 16px;
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

      .tui-select {
        width: 100%;
        padding: 8px 12px;
        border: 1px solid var(--tui-base-04);
        border-radius: 6px;
        font-size: 14px;
        background: var(--tui-base-01);
        color: var(--tui-text-01);
        transition: all 0.2s ease;
        cursor: pointer;

        &:focus {
          outline: none;
          border-color: var(--tui-primary);
          box-shadow: 0 0 0 2px rgba(82, 110, 211, 0.1);
        }
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
        border: 2px solid transparent;
        transition: all 0.2s ease;

        &.enabled {
          border-color: #4caf50;
          background: rgba(76, 175, 80, 0.1);
        }

        &.disabled {
          border-color: #9e9e9e;
          background: rgba(158, 158, 158, 0.1);
        }

        &.running {
          border-color: #2196f3;
          background: rgba(33, 150, 243, 0.1);
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

      .schedules-table {
        width: 100%;
        border-collapse: collapse;

        thead {
          background: var(--tui-base-03);

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
              vertical-align: middle;
            }
          }
        }
      }

      .schedule-name {
        display: flex;
        flex-direction: column;
        gap: 4px;

        strong {
          font-weight: 600;
        }

        .schedule-desc {
          font-size: 12px;
          color: var(--tui-text-03);
        }
      }

      .trigger-info {
        display: flex;
        flex-direction: column;
        gap: 4px;

        .cron-text {
          font-size: 12px;
          color: var(--tui-text-03);
        }
      }

      .next-run-time,
      .last-run-time {
        font-size: 13px;
        color: var(--tui-text-02);
      }

      .last-run-info {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }

      .no-data {
        font-size: 13px;
        color: var(--tui-text-03);
        font-style: italic;
      }

      .execution-count {
        font-weight: 600;
        text-align: center;
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
    `,
  ],
})
export class ScheduleListComponent implements OnInit {
  private router = inject(Router);
  private apiService = inject(ApiService);
  private errorMessageService = inject(ErrorMessageService);

  // Expose enums and functions to template
  TriggerType = TriggerType;
  ScheduleStatus = ScheduleStatus;
  parseCronExpression = parseCronExpression;
  getStatusColor = getStatusColor;
  getStatusIcon = getStatusIcon;

  // Signals for reactive state
  schedules = signal<ScheduleListItem[]>([]);
  loading = signal(true);
  error = signal<string | null>(null);

  // Filter properties
  enabledFilter: boolean | null = null;
  triggerTypeFilter: TriggerType | null = null;

  ngOnInit(): void {
    this.loadSchedules();
  }

  loadSchedules(): void {
    this.loading.set(true);
    this.error.set(null);

    // Build filter options
    const options: any = {};

    if (this.enabledFilter !== null) {
      options.enabled = this.enabledFilter;
    }
    if (this.triggerTypeFilter) {
      options.triggerType = this.triggerTypeFilter;
    }

    this.apiService.listSchedules(options).subscribe({
      next: (schedules) => {
        console.log('Loaded schedules:', schedules);
        this.schedules.set(schedules);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Error loading schedules:', err);
        this.errorMessageService.logError(err, 'Load Schedules');
        const errorMessage = this.errorMessageService.getErrorMessage(err);
        this.error.set(errorMessage);
        this.loading.set(false);
      },
    });
  }

  onFilterChange(): void {
    this.loadSchedules();
  }

  hasActiveFilters(): boolean {
    return this.enabledFilter !== null || this.triggerTypeFilter !== null;
  }

  clearAllFilters(): void {
    this.enabledFilter = null;
    this.triggerTypeFilter = null;
    this.loadSchedules();
  }

  getTotalCount(): number {
    return this.schedules().length;
  }

  getEnabledCount(): number {
    return this.schedules().filter((s) => s.enabled).length;
  }

  getDisabledCount(): number {
    return this.schedules().filter((s) => !s.enabled).length;
  }

  getRunningCount(): number {
    return this.schedules().filter((s) => s.last_run_status === ScheduleStatus.Running).length;
  }

  getTriggerTypeLabel(type: TriggerType): string {
    switch (type) {
      case TriggerType.Cron:
        return 'Cron';
      case TriggerType.Directory:
        return 'Directory';
      case TriggerType.S3:
        return 'S3';
      default:
        return type;
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

  trackByScheduleId(index: number, schedule: ScheduleListItem): string {
    return schedule.schedule_id;
  }

  createSchedule(): void {
    this.router.navigate(['/admin/schedule-create']);
  }

  viewSchedule(scheduleId: string): void {
    this.router.navigate(['/admin/schedule-detail', scheduleId]);
  }

  editSchedule(scheduleId: string): void {
    this.router.navigate(['/admin/schedule-edit', scheduleId]);
  }

  toggleSchedule(scheduleId: string, enabled: boolean): void {
    console.log(`Toggling schedule ${scheduleId} to ${enabled ? 'enabled' : 'disabled'}`);
    this.apiService.toggleSchedule(scheduleId, enabled).subscribe({
      next: () => {
        console.log('Schedule toggled successfully');
        // Reload schedules to get updated next_run_time
        this.loadSchedules();
      },
      error: (err) => {
        console.error('Error toggling schedule:', err);
        this.errorMessageService.logError(err, 'Toggle Schedule');
        this.error.set(this.errorMessageService.getErrorMessage(err));
        // Reload to revert the switch state
        this.loadSchedules();
      },
    });
  }

  runScheduleNow(scheduleId: string): void {
    console.log('Running schedule manually:', scheduleId);
    this.apiService.runSchedule(scheduleId).subscribe({
      next: (response) => {
        console.log('Schedule execution triggered:', response);
        alert(`Schedule execution triggered successfully!\n\nThe schedule will run in the background. Check the execution history for results.`);
        // Reload to show updated status
        this.loadSchedules();
      },
      error: (err) => {
        console.error('Error running schedule:', err);
        this.errorMessageService.logError(err, 'Run Schedule');
        this.error.set(this.errorMessageService.getErrorMessage(err));
      },
    });
  }

  confirmDelete(schedule: ScheduleListItem): void {
    const confirmed = confirm(
      `Are you sure you want to delete schedule "${schedule.name}"?\n\nExecution history will be preserved, but future runs will be cancelled.\n\nThis action cannot be undone.`
    );

    if (confirmed) {
      this.deleteSchedule(schedule.schedule_id);
    }
  }

  deleteSchedule(scheduleId: string): void {
    this.apiService.deleteSchedule(scheduleId).subscribe({
      next: () => {
        console.log('Schedule deleted successfully');
        // Reload the schedule list
        this.loadSchedules();
      },
      error: (err) => {
        console.error('Error deleting schedule:', err);
        this.errorMessageService.logError(err, 'Delete Schedule');
        this.error.set(this.errorMessageService.getErrorMessage(err));
      },
    });
  }
}
