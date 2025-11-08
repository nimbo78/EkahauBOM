import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { TuiButton, TuiLoader, TuiTextfield, TuiLabel } from '@taiga-ui/core';
import { TuiCheckbox } from '@taiga-ui/kit';
import { interval, Subscription } from 'rxjs';

import { ApiService } from '../../../core/services/api.service';
import { ErrorMessageService } from '../../../shared/services/error-message.service';
import { ProcessingRequest } from '../../../core/models/project.model';
import {
  StartWatchRequest,
  WatchStatus,
  WatchResponse,
} from '../../../core/models/batch.model';

@Component({
  selector: 'app-watch-mode',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    TuiButton,
    TuiTextfield,
    TuiLabel,
    TuiCheckbox,
  ],
  template: `
    <div class="watch-mode-container">
      <div class="watch-mode-header">
        <h2>Watch Mode</h2>
        <p class="description">
          Monitor a directory for new .esx files and automatically process them.
        </p>
      </div>

      <!-- Watch Status Card -->
      <div class="status-card" [class.running]="watchStatus().is_running">
        <div class="status-header">
          <h3>
            <span class="status-indicator" [class.active]="watchStatus().is_running"></span>
            {{ watchStatus().is_running ? 'Watch Mode Active' : 'Watch Mode Inactive' }}
          </h3>
          <button
            tuiButton
            type="button"
            [appearance]="watchStatus().is_running ? 'secondary-destructive' : 'primary'"
            [size]="'m'"
            [disabled]="loading()"
            (click)="toggleWatch()"
          >
            {{ loading() ? 'Loading...' : (watchStatus().is_running ? 'Stop Watching' : 'Start Watching') }}
          </button>
        </div>

        <!-- Statistics (shown when running) -->
        <div class="statistics" *ngIf="watchStatus().is_running && watchStatus().statistics">
          <div class="stat-grid">
            <div class="stat-item">
              <span class="stat-label">Started At</span>
              <span class="stat-value">{{ formatDateTime(watchStatus().statistics.started_at) }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Last Check</span>
              <span class="stat-value">{{ formatDateTime(watchStatus().statistics.last_check_at) }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Total Checks</span>
              <span class="stat-value">{{ watchStatus().statistics.total_checks }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Files Found</span>
              <span class="stat-value">{{ watchStatus().statistics.total_files_found }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Batches Created</span>
              <span class="stat-value">{{ watchStatus().statistics.total_batches_created }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Processed Files</span>
              <span class="stat-value">{{ watchStatus().statistics.processed_files_count }}</span>
            </div>
          </div>

          <!-- Current Configuration -->
          <div class="current-config" *ngIf="watchStatus().config">
            <h4>Current Configuration</h4>
            <div class="config-grid">
              <div class="config-item">
                <strong>Directory:</strong> {{ watchStatus().config!.watch_directory }}
              </div>
              <div class="config-item">
                <strong>Interval:</strong> {{ watchStatus().config!.interval_seconds }}s
              </div>
              <div class="config-item">
                <strong>Pattern:</strong> {{ watchStatus().config!.file_pattern }}
              </div>
              <div class="config-item">
                <strong>Auto Process:</strong> {{ watchStatus().config!.auto_process ? 'Yes' : 'No' }}
              </div>
              <div class="config-item">
                <strong>Batch Prefix:</strong> {{ watchStatus().config!.batch_name_prefix }}
              </div>
              <div class="config-item">
                <strong>Workers:</strong> {{ watchStatus().config!.parallel_workers }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Configuration Form (shown when not running) -->
      <div class="config-card" *ngIf="!watchStatus().is_running">
        <h3>Configuration</h3>
        <form [formGroup]="watchForm" class="watch-form">
          <!-- Watch Directory -->
          <label tuiLabel>
            <span>Watch Directory</span>
            <input
              tuiTextfield
              type="text"
              formControlName="watchDirectory"
              placeholder="C:\\data\\projects"
            />
          </label>
          <div class="field-hint">
            Absolute path to the directory containing .esx files (e.g., C:\\data\\projects)
          </div>

          <!-- Interval -->
          <label tuiLabel>
            <span>Check Interval (seconds)</span>
            <input
              tuiTextfield
              type="number"
              formControlName="intervalSeconds"
              [min]="10"
              [max]="3600"
            />
          </label>
          <div class="field-hint">
            How often to check for new files (10-3600 seconds)
          </div>

          <!-- File Pattern -->
          <label tuiLabel>
            <span>File Pattern</span>
            <input
              tuiTextfield
              type="text"
              formControlName="filePattern"
            />
          </label>
          <div class="field-hint">
            Glob pattern to match files (e.g., *.esx, project_*.esx)
          </div>

          <!-- Batch Name Prefix -->
          <label tuiLabel>
            <span>Batch Name Prefix</span>
            <input
              tuiTextfield
              type="text"
              formControlName="batchNamePrefix"
            />
          </label>
          <div class="field-hint">
            Prefix for auto-created batch names
          </div>

          <!-- Parallel Workers -->
          <label tuiLabel>
            <span>Parallel Workers</span>
            <input
              tuiTextfield
              type="number"
              formControlName="parallelWorkers"
              [min]="1"
              [max]="8"
            />
          </label>
          <div class="field-hint">
            Number of files to process in parallel (1-8)
          </div>

          <!-- Auto Process Checkbox -->
          <label tuiLabel class="checkbox-label">
            <input
              tuiCheckbox
              type="checkbox"
              formControlName="autoProcess"
            />
            Auto-process new files
          </label>
          <div class="field-hint checkbox-hint">
            Automatically start processing when new files are detected
          </div>

          <!-- Error Message -->
          <div class="error-message" *ngIf="error()">
            <p>{{ error() }}</p>
          </div>
        </form>
      </div>

      <!-- Info Card -->
      <div class="info-card">
        <h3>How Watch Mode Works</h3>
        <ol>
          <li>Specify a directory to monitor for new .esx files</li>
          <li>Watch mode checks the directory at the specified interval</li>
          <li>When new files are detected, a batch is automatically created</li>
          <li>If auto-process is enabled, the batch is immediately processed</li>
          <li>Already processed files are tracked and not processed again</li>
          <li>Stop watch mode at any time to pause monitoring</li>
        </ol>
        <div class="warning-box">
          <strong>⚠️ Important:</strong>
          <ul>
            <li>Watch mode runs in the background on the server</li>
            <li>The directory must be accessible by the backend server</li>
            <li>Files are copied to the storage, originals are not modified</li>
            <li>Use absolute paths (e.g., C:\\data\\projects on Windows, /data/projects on Linux)</li>
          </ul>
        </div>
      </div>
    </div>
  `,
  styleUrl: './watch-mode.component.scss',
})
export class WatchModeComponent implements OnInit, OnDestroy {
  private apiService = inject(ApiService);
  private errorMessageService = inject(ErrorMessageService);

  loading = signal(false);
  error = signal<string | null>(null);
  watchStatus = signal<WatchStatus>({
    is_running: false,
    config: null,
    statistics: {
      started_at: null,
      last_check_at: null,
      total_checks: 0,
      total_files_found: 0,
      total_batches_created: 0,
      processed_files_count: 0,
    },
  });

  private statusPollSubscription?: Subscription;

  watchForm = new FormGroup({
    watchDirectory: new FormControl<string>('', { validators: [Validators.required], nonNullable: true }),
    intervalSeconds: new FormControl<number>(60, { validators: [Validators.required, Validators.min(10), Validators.max(3600)], nonNullable: true }),
    filePattern: new FormControl<string>('*.esx', { validators: [Validators.required], nonNullable: true }),
    batchNamePrefix: new FormControl<string>('Watch', { validators: [Validators.required], nonNullable: true }),
    parallelWorkers: new FormControl<number>(1, { validators: [Validators.required, Validators.min(1), Validators.max(8)], nonNullable: true }),
    autoProcess: new FormControl<boolean>(true, { nonNullable: true }),
  });

  ngOnInit(): void {
    this.loadWatchStatus();
    this.startPolling();
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  loadWatchStatus(): void {
    this.apiService.getWatchStatus().subscribe({
      next: (status) => {
        this.watchStatus.set(status);
      },
      error: (err) => {
        console.error('Error loading watch status:', err);
      },
    });
  }

  toggleWatch(): void {
    if (this.watchStatus().is_running) {
      this.stopWatch();
    } else {
      this.startWatch();
    }
  }

  startWatch(): void {
    if (this.watchForm.invalid) {
      this.error.set('Please fill in all required fields correctly');
      return;
    }

    this.loading.set(true);
    this.error.set(null);

    const formValue = this.watchForm.value;

    const request: StartWatchRequest = {
      watch_directory: formValue.watchDirectory!,
      interval_seconds: formValue.intervalSeconds!,
      file_pattern: formValue.filePattern!,
      auto_process: formValue.autoProcess!,
      batch_name_prefix: formValue.batchNamePrefix!,
      parallel_workers: formValue.parallelWorkers!,
      // TODO: Add processing options configuration
    };

    this.apiService.startWatch(request).subscribe({
      next: (response) => {
        console.log('Watch started:', response);
        this.loading.set(false);
        this.loadWatchStatus(); // Refresh status
      },
      error: (err) => {
        console.error('Error starting watch:', err);
        this.errorMessageService.logError(err, 'Start Watch');
        this.error.set(this.errorMessageService.getErrorMessage(err));
        this.loading.set(false);
      },
    });
  }

  stopWatch(): void {
    this.loading.set(true);
    this.error.set(null);

    this.apiService.stopWatch().subscribe({
      next: (response) => {
        console.log('Watch stopped:', response);
        this.loading.set(false);
        this.loadWatchStatus(); // Refresh status
      },
      error: (err) => {
        console.error('Error stopping watch:', err);
        this.errorMessageService.logError(err, 'Stop Watch');
        this.error.set(this.errorMessageService.getErrorMessage(err));
        this.loading.set(false);
      },
    });
  }

  formatDateTime(dateStr: string | null): string {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    return date.toLocaleString('en-GB', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  }

  private startPolling(): void {
    // Poll status every 5 seconds
    this.statusPollSubscription = interval(5000).subscribe(() => {
      this.loadWatchStatus();
    });
  }

  private stopPolling(): void {
    this.statusPollSubscription?.unsubscribe();
  }
}
