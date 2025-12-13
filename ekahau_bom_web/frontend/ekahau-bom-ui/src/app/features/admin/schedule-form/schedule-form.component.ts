import { Component, OnInit, inject, signal, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import {
  TuiButton,
  TuiIcon,
  TuiNotification,
  TuiLoader,
  TuiTextfield,
  TuiLabel,
} from '@taiga-ui/core';
import { TuiCheckbox, TuiTextarea } from '@taiga-ui/kit';
import { ApiService } from '../../../core/services/api.service';
import { ErrorMessageService } from '../../../shared/services/error-message.service';
import {
  Schedule,
  ScheduleCreateRequest,
  ScheduleUpdateRequest,
  TriggerType,
  CRON_PRESETS,
  validateCronExpression,
} from '../../../core/models/schedule.model';

@Component({
  selector: 'app-schedule-form',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    TuiButton,
    TuiIcon,
    TuiNotification,
    TuiLoader,
    TuiCheckbox,
    TuiTextfield,
    TuiLabel,
    TuiTextarea,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="schedule-form-container">
      <div class="page-header">
        <h1 class="page-title">{{ isEditMode() ? 'Edit Schedule' : 'Create Schedule' }}</h1>
        <button tuiButton appearance="flat" size="m" (click)="cancel()">
          <tui-icon icon="@tui.x"></tui-icon>
          Cancel
        </button>
      </div>

      <!-- Loading state -->
      <div *ngIf="loading()" class="loading-state">
        <tui-loader size="l"></tui-loader>
        <p>{{ isEditMode() ? 'Loading schedule...' : 'Initializing form...' }}</p>
      </div>

      <!-- Error state -->
      <tui-notification *ngIf="error()" status="error" class="notification">
        <div class="error-content">
          <h3>Error</h3>
          <p>{{ error() }}</p>
          <button tuiButton size="s" (click)="error.set(null)">Dismiss</button>
        </div>
      </tui-notification>

      <!-- Form -->
      <form *ngIf="!loading() && scheduleForm" [formGroup]="scheduleForm" (ngSubmit)="onSubmit()" class="schedule-form">
        <!-- Basic Information -->
        <div class="form-section">
          <h2 class="section-title">
            <tui-icon icon="@tui.info"></tui-icon>
            Basic Information
          </h2>

          <div class="form-group">
            <label tuiLabel class="form-label" [for]="'name'">
              Schedule Name *
            </label>
            <input
              tuiTextfield
              class="tui-input-full"
              id="name"
              formControlName="name"
              placeholder="e.g., Nightly Processing"
            />
            <div *ngIf="scheduleForm.get('name')?.invalid && scheduleForm.get('name')?.touched" class="error-message">
              Schedule name is required
            </div>
          </div>

          <div class="form-group">
            <label tuiLabel class="form-label" [for]="'description'">
              Description
            </label>
            <textarea
              tuiTextarea
              class="tui-textarea-full"
              id="description"
              formControlName="description"
              placeholder="Describe what this schedule does..."
              rows="3"
            ></textarea>
          </div>

          <div class="form-group">
            <label class="checkbox-label">
              <input
                tuiCheckbox
                type="checkbox"
                formControlName="enabled"
              />
              <span>Enable schedule immediately</span>
            </label>
          </div>
        </div>

        <!-- Schedule Configuration -->
        <div class="form-section">
          <h2 class="section-title">
            <tui-icon icon="@tui.clock"></tui-icon>
            Schedule Configuration
          </h2>

          <div class="form-group">
            <label tuiLabel class="form-label">Trigger Type *</label>
            <select
              class="tui-select-full"
              formControlName="trigger_type"
              (change)="onTriggerTypeChange()"
            >
              <option [value]="TriggerType.Cron">Cron (Time-based)</option>
              <option [value]="TriggerType.Directory">Directory Watch</option>
              <option [value]="TriggerType.S3">S3 Bucket Watch</option>
            </select>
          </div>

          <!-- Cron Expression (for Cron trigger) -->
          <div *ngIf="scheduleForm.get('trigger_type')?.value === TriggerType.Cron" class="cron-section">
            <div class="form-group">
              <label tuiLabel class="form-label">Cron Presets</label>
              <div class="cron-presets">
                <button
                  *ngFor="let preset of cronPresetArray"
                  type="button"
                  tuiButton
                  appearance="outline"
                  size="s"
                  class="preset-button"
                  (click)="selectCronPreset(preset.expression)"
                >
                  {{ preset.label }}
                </button>
              </div>
            </div>

            <div class="form-group">
              <label tuiLabel class="form-label" [for]="'cron_expression'">
                Cron Expression *
              </label>
              <input
                tuiTextfield
                class="tui-input-full"
                id="cron_expression"
                formControlName="cron_expression"
                placeholder="e.g., 0 2 * * * (Daily at 2:00 AM)"
                (blur)="validateCron()"
              />
              <div class="help-text">
                Format: minute hour day month weekday (e.g., "0 2 * * *" = Daily at 2:00 AM UTC)
              </div>
              <div *ngIf="cronValidationMessage()" [class.error-message]="!cronValidationMessage()?.valid" [class.success-message]="cronValidationMessage()?.valid">
                {{ cronValidationMessage()?.message }}
              </div>
            </div>
          </div>

          <!-- Directory Configuration (for Directory trigger) -->
          <div *ngIf="scheduleForm.get('trigger_type')?.value === TriggerType.Directory" formGroupName="trigger_config">
            <div class="form-group">
              <label tuiLabel class="form-label" [for]="'directory'">
                Directory Path *
              </label>
              <input
                tuiTextfield
                class="tui-input-full"
                id="directory"
                formControlName="directory"
                placeholder="e.g., /data/ekahau/input"
              />
            </div>

            <div class="form-group">
              <label tuiLabel class="form-label" [for]="'pattern'">
                File Pattern
              </label>
              <input
                tuiTextfield
                class="tui-input-full"
                id="pattern"
                formControlName="pattern"
                placeholder="e.g., *.esx"
              />
            </div>

            <div class="form-group">
              <label class="checkbox-label">
                <input
                  tuiCheckbox
                  type="checkbox"
                  formControlName="recursive"
                />
                <span>Scan subdirectories recursively</span>
              </label>
            </div>
          </div>

          <!-- S3 Configuration (for S3 trigger) -->
          <div *ngIf="scheduleForm.get('trigger_type')?.value === TriggerType.S3" formGroupName="trigger_config">
            <div class="form-group">
              <label tuiLabel class="form-label" [for]="'s3_bucket'">
                S3 Bucket Name *
              </label>
              <input
                tuiTextfield
                class="tui-input-full"
                id="s3_bucket"
                formControlName="s3_bucket"
                placeholder="e.g., my-ekahau-files"
              />
            </div>

            <div class="form-group">
              <label tuiLabel class="form-label" [for]="'s3_prefix'">
                S3 Prefix (optional)
              </label>
              <input
                tuiTextfield
                class="tui-input-full"
                id="s3_prefix"
                formControlName="s3_prefix"
                placeholder="e.g., input/ekahau/"
              />
            </div>

            <div class="form-group">
              <label tuiLabel class="form-label" [for]="'s3_pattern'">
                File Pattern
              </label>
              <input
                tuiTextfield
                class="tui-input-full"
                id="s3_pattern"
                formControlName="pattern"
                placeholder="e.g., *.esx"
              />
            </div>
          </div>
        </div>

        <!-- Notification Configuration -->
        <div class="form-section">
          <h2 class="section-title">
            <tui-icon icon="@tui.bell"></tui-icon>
            Notifications
          </h2>

          <div formGroupName="notification_config">
            <div class="form-group">
              <label tuiLabel class="form-label" [for]="'email'">
                Email Recipients
              </label>
              <input
                tuiTextfield
                class="tui-input-full"
                id="email"
                formControlName="email"
                placeholder="email1@example.com, email2@example.com"
              />
              <div class="help-text">
                Comma-separated email addresses
              </div>
            </div>

            <div class="form-group">
              <label tuiLabel class="form-label" [for]="'webhook_url'">
                Webhook URL
              </label>
              <input
                tuiTextfield
                class="tui-input-full"
                id="webhook_url"
                formControlName="webhook_url"
                placeholder="https://your-server.com/webhook"
              />
            </div>

            <div class="form-group">
              <label tuiLabel class="form-label" [for]="'slack_webhook'">
                Slack Webhook URL
              </label>
              <input
                tuiTextfield
                class="tui-input-full"
                id="slack_webhook"
                formControlName="slack_webhook"
                placeholder="https://hooks.slack.com/services/..."
              />
            </div>

            <div class="notification-checkboxes">
              <label class="checkbox-label">
                <input
                  tuiCheckbox
                  type="checkbox"
                  formControlName="notify_on_success"
                />
                <span>Notify on success</span>
              </label>

              <label class="checkbox-label">
                <input
                  tuiCheckbox
                  type="checkbox"
                  formControlName="notify_on_failure"
                />
                <span>Notify on failure</span>
              </label>

              <label class="checkbox-label">
                <input
                  tuiCheckbox
                  type="checkbox"
                  formControlName="notify_on_partial"
                />
                <span>Notify on partial success</span>
              </label>
            </div>
          </div>
        </div>

        <!-- Form Actions -->
        <div class="form-actions">
          <button
            type="button"
            tuiButton
            appearance="flat"
            size="m"
            (click)="cancel()"
          >
            Cancel
          </button>
          <button
            type="submit"
            tuiButton
            appearance="primary"
            size="m"
            [disabled]="!scheduleForm.valid || submitting()"
          >
            <tui-loader *ngIf="submitting()" size="s"></tui-loader>
            <span *ngIf="!submitting()">
              {{ isEditMode() ? 'Update Schedule' : 'Create Schedule' }}
            </span>
          </button>
        </div>
      </form>
    </div>
  `,
  styles: [`
    .schedule-form-container {
      padding: 24px;
      max-width: 900px;
      margin: 0 auto;
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

    .schedule-form {
      display: flex;
      flex-direction: column;
      gap: 32px;
    }

    .form-section {
      background: var(--tui-base-02);
      border-radius: 12px;
      padding: 24px;
    }

    .section-title {
      margin: 0 0 20px 0;
      font-size: 20px;
      font-weight: 600;
      color: var(--tui-text-01);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .form-group {
      margin-bottom: 20px;

      &:last-child {
        margin-bottom: 0;
      }
    }

    .form-label {
      display: block;
      margin-bottom: 8px;
      font-weight: 500;
      font-size: 14px;
      color: var(--tui-text-01);
    }

    .tui-input-full,
    .tui-textarea-full,
    .tui-select-full {
      width: 100%;
      padding: 10px 14px;
      border: 1px solid var(--tui-base-04);
      border-radius: 8px;
      font-size: 14px;
      background: var(--tui-base-01);
      color: var(--tui-text-01);
      transition: all 0.2s ease;

      &:focus {
        outline: none;
        border-color: var(--tui-primary);
        box-shadow: 0 0 0 3px rgba(82, 110, 211, 0.1);
      }

      &::placeholder {
        color: var(--tui-text-03);
      }
    }

    .tui-select-full {
      cursor: pointer;
    }

    .help-text {
      margin-top: 6px;
      font-size: 12px;
      color: var(--tui-text-03);
    }

    .error-message {
      margin-top: 6px;
      font-size: 12px;
      color: var(--tui-negative);
    }

    .success-message {
      margin-top: 6px;
      font-size: 12px;
      color: var(--tui-positive);
    }

    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 14px;
      color: var(--tui-text-01);
      cursor: pointer;

      input[type="checkbox"] {
        cursor: pointer;
      }
    }

    .cron-section {
      margin-top: 16px;
    }

    .cron-presets {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .preset-button {
      font-size: 12px;
    }

    .notification-checkboxes {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .form-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      padding-top: 24px;
      border-top: 1px solid var(--tui-base-04);
    }
  `],
})
export class ScheduleFormComponent implements OnInit {
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private fb = inject(FormBuilder);
  private apiService = inject(ApiService);
  private errorMessageService = inject(ErrorMessageService);

  // Expose enums to template
  TriggerType = TriggerType;

  // Signals
  loading = signal(true);
  error = signal<string | null>(null);
  submitting = signal(false);
  isEditMode = signal(false);
  cronValidationMessage = signal<{ valid: boolean; message: string } | null>(null);

  scheduleId: string | null = null;
  scheduleForm!: FormGroup;

  // Cron presets
  cronPresetArray = Object.values(CRON_PRESETS);

  ngOnInit(): void {
    // Check if edit mode
    this.scheduleId = this.route.snapshot.paramMap.get('id');
    this.isEditMode.set(!!this.scheduleId);

    this.initializeForm();

    if (this.isEditMode() && this.scheduleId) {
      this.loadSchedule(this.scheduleId);
    } else {
      this.loading.set(false);
    }
  }

  private initializeForm(): void {
    this.scheduleForm = this.fb.group({
      name: ['', [Validators.required, Validators.maxLength(100)]],
      description: [''],
      enabled: [true],
      trigger_type: [TriggerType.Cron, Validators.required],
      cron_expression: ['0 2 * * *', Validators.required],
      trigger_config: this.fb.group({
        directory: [''],
        s3_bucket: [''],
        s3_prefix: [''],
        pattern: ['*.esx'],
        recursive: [true],
      }),
      notification_config: this.fb.group({
        email: [''],
        webhook_url: [''],
        slack_webhook: [''],
        notify_on_success: [true],
        notify_on_failure: [true],
        notify_on_partial: [true],
      }),
    });
  }

  private loadSchedule(scheduleId: string): void {
    this.apiService.getSchedule(scheduleId).subscribe({
      next: (schedule) => {
        console.log('Loaded schedule:', schedule);
        this.patchFormWithSchedule(schedule);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Error loading schedule:', err);
        this.errorMessageService.logError(err, 'Load Schedule');
        this.error.set(this.errorMessageService.getErrorMessage(err));
        this.loading.set(false);
      },
    });
  }

  private patchFormWithSchedule(schedule: Schedule): void {
    // Parse email string back to form
    const emailString = schedule.notification_config.email?.join(', ') || '';

    this.scheduleForm.patchValue({
      name: schedule.name,
      description: schedule.description,
      enabled: schedule.enabled,
      trigger_type: schedule.trigger_type,
      cron_expression: schedule.cron_expression,
      trigger_config: schedule.trigger_config,
      notification_config: {
        ...schedule.notification_config,
        email: emailString,
      },
    });
  }

  onTriggerTypeChange(): void {
    const triggerType = this.scheduleForm.get('trigger_type')?.value;
    console.log('Trigger type changed:', triggerType);
    // Could add validation logic here based on trigger type
  }

  selectCronPreset(expression: string): void {
    this.scheduleForm.patchValue({ cron_expression: expression });
    this.validateCron();
  }

  validateCron(): void {
    const cronExpression = this.scheduleForm.get('cron_expression')?.value;
    if (!cronExpression) {
      this.cronValidationMessage.set(null);
      return;
    }

    const validation = validateCronExpression(cronExpression);
    if (validation.valid) {
      // Try to parse to human-readable
      try {
        const parsed = this.parseCronToHumanReadable(cronExpression);
        this.cronValidationMessage.set({
          valid: true,
          message: `✓ Valid: ${parsed}`,
        });
      } catch (e) {
        this.cronValidationMessage.set({
          valid: true,
          message: '✓ Valid cron expression',
        });
      }
    } else {
      this.cronValidationMessage.set({
        valid: false,
        message: `✗ ${validation.error}`,
      });
    }
  }

  private parseCronToHumanReadable(expression: string): string {
    // Import parseCronExpression from model
    const { parseCronExpression } = require('../../../core/models/schedule.model');
    return parseCronExpression(expression);
  }

  onSubmit(): void {
    if (this.scheduleForm.invalid) {
      this.scheduleForm.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    this.error.set(null);

    const formValue = this.scheduleForm.value;

    // Parse email string to array
    const emailString = formValue.notification_config.email || '';
    const emailArray = emailString
      .split(',')
      .map((e: string) => e.trim())
      .filter((e: string) => e.length > 0);

    const request: ScheduleCreateRequest | ScheduleUpdateRequest = {
      name: formValue.name,
      description: formValue.description,
      enabled: formValue.enabled,
      trigger_type: formValue.trigger_type,
      cron_expression: formValue.cron_expression,
      trigger_config: formValue.trigger_config,
      notification_config: {
        ...formValue.notification_config,
        email: emailArray,
      },
    };

    const apiCall = this.isEditMode() && this.scheduleId
      ? this.apiService.updateSchedule(this.scheduleId, request)
      : this.apiService.createSchedule(request as ScheduleCreateRequest);

    apiCall.subscribe({
      next: (schedule) => {
        console.log('Schedule saved:', schedule);
        this.submitting.set(false);
        // Navigate back to list
        this.router.navigate(['/admin/schedules']);
      },
      error: (err) => {
        console.error('Error saving schedule:', err);
        this.errorMessageService.logError(err, 'Save Schedule');
        this.error.set(this.errorMessageService.getErrorMessage(err));
        this.submitting.set(false);
      },
    });
  }

  cancel(): void {
    this.router.navigate(['/admin/schedules']);
  }
}
