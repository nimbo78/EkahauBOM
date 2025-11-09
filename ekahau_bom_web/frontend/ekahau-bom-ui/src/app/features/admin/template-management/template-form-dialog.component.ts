import { Component, OnInit, signal, inject, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { TuiButton, TuiIcon, TuiLabel } from '@taiga-ui/core';

import { ApiService } from '../../../core/services/api.service';
import { ErrorMessageService } from '../../../shared/services/error-message.service';
import { BatchTemplate, TemplateCreateRequest, TemplateUpdateRequest } from '../../../core/models/batch.model';

type DialogMode = 'create' | 'edit';

@Component({
  selector: 'app-template-form-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    TuiButton,
    TuiIcon,
    TuiLabel,
  ],
  template: `
    <div class="dialog-backdrop" (click)="onBackdropClick($event)">
      <div class="dialog-container" (click)="$event.stopPropagation()">
        <!-- Header -->
        <div class="dialog-header">
          <h2 class="dialog-title">
            <tui-icon [icon]="mode() === 'create' ? '@tui.plus-circle' : '@tui.edit-2'"></tui-icon>
            {{ mode() === 'create' ? 'Create New Template' : 'Edit Template' }}
          </h2>
          <button tuiButton appearance="flat" size="s" (click)="onCancel()" type="button">
            <tui-icon icon="@tui.x"></tui-icon>
          </button>
        </div>

        <!-- Form -->
        <form [formGroup]="form" (ngSubmit)="onSubmit()" class="dialog-content">
          <!-- Basic Info -->
          <div class="form-section">
            <h3>Basic Information</h3>

            <div class="form-field">
              <label tuiLabel class="field-label">
                Template Name <span class="required">*</span>
              </label>
              <input
                type="text"
                formControlName="name"
                placeholder="e.g., My Custom Template"
                class="tui-input"
                [class.error]="form.get('name')?.invalid && form.get('name')?.touched"
              />
              <div *ngIf="form.get('name')?.invalid && form.get('name')?.touched" class="error-message">
                Template name is required (min 3 characters)
              </div>
            </div>

            <div class="form-field">
              <label tuiLabel class="field-label">Description</label>
              <textarea
                formControlName="description"
                placeholder="Brief description of this template"
                rows="3"
                class="tui-textarea"
              ></textarea>
            </div>
          </div>

          <!-- Processing Options -->
          <div class="form-section">
            <h3>Processing Options</h3>

            <div class="form-field">
              <label tuiLabel class="field-label">Group By</label>
              <select formControlName="groupBy" class="tui-select">
                <option value="model">Model</option>
                <option value="vendor">Vendor</option>
                <option value="floor">Floor</option>
              </select>
            </div>

            <div class="form-field">
              <label tuiLabel class="field-label">Output Formats</label>
              <div class="checkbox-group">
                <label class="checkbox-label">
                  <input type="checkbox" formControlName="formatCsv" class="tui-checkbox" />
                  <span>CSV</span>
                </label>
                <label class="checkbox-label">
                  <input type="checkbox" formControlName="formatExcel" class="tui-checkbox" />
                  <span>Excel</span>
                </label>
                <label class="checkbox-label">
                  <input type="checkbox" formControlName="formatHtml" class="tui-checkbox" />
                  <span>HTML</span>
                </label>
                <label class="checkbox-label">
                  <input type="checkbox" formControlName="formatPdf" class="tui-checkbox" />
                  <span>PDF</span>
                </label>
                <label class="checkbox-label">
                  <input type="checkbox" formControlName="formatJson" class="tui-checkbox" />
                  <span>JSON</span>
                </label>
              </div>
            </div>
          </div>

          <!-- Visualization Options -->
          <div class="form-section">
            <h3>Visualization Options</h3>

            <label class="checkbox-label">
              <input type="checkbox" formControlName="visualizeFloorPlans" class="tui-checkbox" />
              <span>Generate Floor Plan Visualizations</span>
            </label>

            <label class="checkbox-label">
              <input type="checkbox" formControlName="showAzimuthArrows" class="tui-checkbox" />
              <span>Show Azimuth Arrows</span>
            </label>

            <div class="form-field">
              <label tuiLabel class="field-label">AP Opacity (%)</label>
              <input
                type="number"
                formControlName="apOpacity"
                min="0"
                max="100"
                placeholder="60"
                class="tui-input"
              />
            </div>
          </div>

          <!-- Notes Options -->
          <div class="form-section">
            <h3>Notes Options</h3>

            <label class="checkbox-label">
              <input type="checkbox" formControlName="includeTextNotes" class="tui-checkbox" />
              <span>Include Text Notes</span>
            </label>

            <label class="checkbox-label">
              <input type="checkbox" formControlName="includePictureNotes" class="tui-checkbox" />
              <span>Include Picture Notes</span>
            </label>

            <label class="checkbox-label">
              <input type="checkbox" formControlName="includeCableNotes" class="tui-checkbox" />
              <span>Include Cable Notes</span>
            </label>
          </div>

          <!-- Performance -->
          <div class="form-section">
            <h3>Performance</h3>

            <div class="form-field">
              <label tuiLabel class="field-label">Parallel Workers</label>
              <input
                type="number"
                formControlName="parallelWorkers"
                min="1"
                max="8"
                placeholder="1"
                class="tui-input"
              />
              <p class="field-hint">Number of projects to process simultaneously (1-8)</p>
            </div>
          </div>

          <!-- Actions -->
          <div class="dialog-actions">
            <button tuiButton type="button" appearance="secondary" (click)="onCancel()">
              Cancel
            </button>
            <button
              tuiButton
              type="submit"
              appearance="primary"
              [disabled]="!form.valid || submitting()"
            >
              <tui-icon *ngIf="submitting()" icon="@tui.loader"></tui-icon>
              {{ submitting() ? 'Saving...' : (mode() === 'create' ? 'Create Template' : 'Update Template') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  `,
  styles: [`
    .dialog-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      backdrop-filter: blur(2px);
      animation: fadeIn 0.2s ease;
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    .dialog-container {
      background: var(--tui-base-01);
      border-radius: 12px;
      max-width: 700px;
      width: 90%;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
      animation: slideIn 0.3s ease;
    }

    @keyframes slideIn {
      from {
        transform: translateY(-20px);
        opacity: 0;
      }
      to {
        transform: translateY(0);
        opacity: 1;
      }
    }

    .dialog-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 24px 24px 16px 24px;
      border-bottom: 1px solid var(--tui-base-03);

      .dialog-title {
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 0;
        font-size: 20px;
        font-weight: 600;
        color: var(--tui-text-01);

        tui-icon {
          font-size: 24px;
          color: var(--tui-primary);
        }
      }
    }

    .dialog-content {
      flex: 1;
      overflow-y: auto;
      padding: 24px;
    }

    .form-section {
      margin-bottom: 32px;

      &:last-child {
        margin-bottom: 0;
      }

      h3 {
        margin: 0 0 16px 0;
        font-size: 16px;
        font-weight: 600;
        color: var(--tui-text-01);
        border-bottom: 2px solid var(--tui-primary-hover);
        padding-bottom: 8px;
      }
    }

    .form-field {
      margin-bottom: 20px;

      .field-label {
        display: block;
        margin-bottom: 8px;
        font-size: 14px;
        font-weight: 500;
        color: var(--tui-text-02);

        .required {
          color: var(--tui-error);
        }
      }

      .field-hint {
        margin: 6px 0 0 0;
        font-size: 12px;
        color: var(--tui-text-03);
      }

      .tui-input,
      .tui-textarea,
      .tui-select {
        width: 100%;
        padding: 10px 12px;
        border: 1px solid var(--tui-base-04);
        border-radius: 6px;
        background: var(--tui-base-01);
        color: var(--tui-text-01);
        font-size: 14px;
        transition: all 0.2s ease;

        &:focus {
          outline: none;
          border-color: var(--tui-primary);
          box-shadow: 0 0 0 3px var(--tui-primary-hover);
        }

        &.error {
          border-color: var(--tui-error);
        }
      }

      .tui-textarea {
        resize: vertical;
        min-height: 80px;
      }

      .error-message {
        margin-top: 6px;
        font-size: 12px;
        color: var(--tui-error);
      }
    }

    .checkbox-group {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
    }

    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      font-size: 14px;
      color: var(--tui-text-01);
      transition: color 0.2s ease;

      &:hover {
        color: var(--tui-primary);
      }

      .tui-checkbox {
        cursor: pointer;
        width: 18px;
        height: 18px;
      }
    }

    .dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      padding: 16px 24px;
      border-top: 1px solid var(--tui-base-03);
      background: var(--tui-base-02);
      border-radius: 0 0 12px 12px;

      button {
        min-width: 120px;
      }
    }

    @media (max-width: 768px) {
      .dialog-container {
        width: 95%;
        max-height: 95vh;
      }

      .checkbox-group {
        flex-direction: column;
        gap: 12px;
      }
    }
  `]
})
export class TemplateFormDialogComponent implements OnInit {
  private readonly apiService = inject(ApiService);
  private readonly errorMessageService = inject(ErrorMessageService);
  private readonly fb = inject(FormBuilder);

  // Inputs
  mode = input.required<DialogMode>();
  template = input<BatchTemplate | null>(null);

  // Outputs
  saved = output<BatchTemplate>();
  cancelled = output<void>();

  // State
  submitting = signal(false);

  form: FormGroup = this.fb.group({
    name: ['', [Validators.required, Validators.minLength(3)]],
    description: [''],
    groupBy: ['model'],
    formatCsv: [true],
    formatExcel: [true],
    formatHtml: [true],
    formatPdf: [true],
    formatJson: [false],
    visualizeFloorPlans: [true],
    showAzimuthArrows: [true],
    apOpacity: [60, [Validators.min(0), Validators.max(100)]],
    includeTextNotes: [true],
    includePictureNotes: [true],
    includeCableNotes: [true],
    parallelWorkers: [1, [Validators.required, Validators.min(1), Validators.max(8)]],
  });

  ngOnInit(): void {
    // If editing, populate form with template data
    if (this.mode() === 'edit' && this.template()) {
      const t = this.template()!;
      const options = t.processing_options;

      this.form.patchValue({
        name: t.name,
        description: t.description || '',
        groupBy: options.group_by || 'model',
        formatCsv: options.output_formats?.includes('csv') ?? true,
        formatExcel: options.output_formats?.includes('excel') ?? true,
        formatHtml: options.output_formats?.includes('html') ?? true,
        formatPdf: options.output_formats?.includes('pdf') ?? true,
        formatJson: options.output_formats?.includes('json') ?? false,
        visualizeFloorPlans: options.visualize_floor_plans ?? true,
        showAzimuthArrows: options.show_azimuth_arrows ?? true,
        apOpacity: options.ap_opacity ? Math.round(options.ap_opacity * 100) : 60,
        includeTextNotes: options.include_text_notes ?? true,
        includePictureNotes: options.include_picture_notes ?? true,
        includeCableNotes: options.include_cable_notes ?? true,
        parallelWorkers: t.parallel_workers || 1,
      });
    }
  }

  onSubmit(): void {
    if (!this.form.valid) {
      // Mark all fields as touched to show validation errors
      Object.keys(this.form.controls).forEach(key => {
        this.form.get(key)?.markAsTouched();
      });
      return;
    }

    const formValue = this.form.value;

    // Build output_formats array
    const outputFormats: string[] = [];
    if (formValue.formatCsv) outputFormats.push('csv');
    if (formValue.formatExcel) outputFormats.push('excel');
    if (formValue.formatHtml) outputFormats.push('html');
    if (formValue.formatPdf) outputFormats.push('pdf');
    if (formValue.formatJson) outputFormats.push('json');

    const processingOptions = {
      group_by: formValue.groupBy,
      output_formats: outputFormats,
      visualize_floor_plans: formValue.visualizeFloorPlans,
      show_azimuth_arrows: formValue.showAzimuthArrows,
      ap_opacity: formValue.apOpacity / 100, // Convert to 0-1 scale
      include_text_notes: formValue.includeTextNotes,
      include_picture_notes: formValue.includePictureNotes,
      include_cable_notes: formValue.includeCableNotes,
    };

    this.submitting.set(true);

    if (this.mode() === 'create') {
      const request: TemplateCreateRequest = {
        name: formValue.name,
        description: formValue.description || undefined,
        processing_options: processingOptions,
        parallel_workers: formValue.parallelWorkers,
      };

      this.apiService.createTemplate(request).subscribe({
        next: (template) => {
          console.log('Template created:', template);
          this.submitting.set(false);
          this.saved.emit(template);
        },
        error: (err) => {
          console.error('Error creating template:', err);
          this.errorMessageService.logError(err, 'Create Template');
          this.submitting.set(false);
          alert(`Failed to create template: ${this.errorMessageService.getErrorMessage(err)}`);
        },
      });
    } else {
      const request: TemplateUpdateRequest = {
        name: formValue.name,
        description: formValue.description || undefined,
        processing_options: processingOptions,
        parallel_workers: formValue.parallelWorkers,
      };

      this.apiService.updateTemplate(this.template()!.template_id, request).subscribe({
        next: (template) => {
          console.log('Template updated:', template);
          this.submitting.set(false);
          this.saved.emit(template);
        },
        error: (err) => {
          console.error('Error updating template:', err);
          this.errorMessageService.logError(err, 'Update Template');
          this.submitting.set(false);
          alert(`Failed to update template: ${this.errorMessageService.getErrorMessage(err)}`);
        },
      });
    }
  }

  onCancel(): void {
    this.cancelled.emit();
  }

  onBackdropClick(event: MouseEvent): void {
    // Close dialog when clicking on backdrop
    if (event.target === event.currentTarget) {
      this.onCancel();
    }
  }
}
