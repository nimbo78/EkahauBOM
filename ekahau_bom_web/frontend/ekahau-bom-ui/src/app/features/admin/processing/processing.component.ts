import { Component, OnInit, OnDestroy, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import {
  TuiButton,
  TuiIcon,
  TuiNotification,
  TuiLoader,
  TuiTextfield,
  TuiLabel
} from '@taiga-ui/core';
import { TuiCheckbox, TuiBadge } from '@taiga-ui/kit';
import { ApiService } from '../../../core/services/api.service';
import { ProjectService } from '../../../core/services/project.service';
import {
  ProcessingFlags,
  ProcessingRequest,
  ProjectDetails,
  ProcessingStatus
} from '../../../core/models/project.model';
import { Subscription, interval } from 'rxjs';

@Component({
  selector: 'app-processing',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    TuiButton,
    TuiIcon,
    TuiNotification,
    TuiLoader,
    TuiCheckbox,
    TuiTextfield,
    TuiLabel,
    TuiBadge
  ],
  template: `
    <div class="processing-container">
      <div class="page-header">
        <h1 class="page-title">Configure Processing</h1>
        <button tuiButton appearance="outline" size="l" routerLink="/projects">
          <tui-icon icon="@tui.arrow-left"></tui-icon>
          Back to Projects
        </button>
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

      <!-- Processing form -->
      <div *ngIf="!loading() && !error() && project()" class="form-container">
        <div class="project-info">
          <h2>{{ project()?.project_name || 'Unnamed Project' }}</h2>
          <p class="project-details">
            <span>File: {{ project()?.filename }}</span>
            <span>•</span>
            <span>Uploaded: {{ formatDate(project()?.upload_date) }}</span>
            <span>•</span>
            <span>Status:
              <tui-badge
                [appearance]="getStatusAppearance(project()!.processing_status)"
                [class]="'status-badge-' + project()!.processing_status.toLowerCase()"
              >
                {{ project()?.processing_status }}
              </tui-badge>
            </span>
          </p>
        </div>

        <form [formGroup]="processingForm" class="processing-form">
          <h3>Processing Options</h3>

          <div class="form-section">
            <h4>General Options</h4>
            <label class="field-label">
              <span>Group Access Points By</span>
              <select
                formControlName="group_by"
                class="group-select"
              >
                <option value="">No Grouping</option>
                <option value="model">Model</option>
                <option value="floor">Floor</option>
                <option value="color">Color</option>
                <option value="vendor">Vendor</option>
                <option value="tag">Tag</option>
              </select>
            </label>
          </div>

          <div class="form-section">
            <h4>Export Formats</h4>
            <div class="checkbox-group">
              <label tuiLabel class="checkbox-label">
                <input
                  tuiCheckbox
                  type="checkbox"
                  formControlName="csv_export"
                />
                CSV Export
              </label>

              <label tuiLabel class="checkbox-label">
                <input
                  tuiCheckbox
                  type="checkbox"
                  formControlName="excel_export"
                />
                Excel Export
              </label>

              <label tuiLabel class="checkbox-label">
                <input
                  tuiCheckbox
                  type="checkbox"
                  formControlName="json_export"
                />
                JSON Export
              </label>

              <label tuiLabel class="checkbox-label">
                <input
                  tuiCheckbox
                  type="checkbox"
                  formControlName="html_export"
                />
                HTML Report
              </label>

              <label tuiLabel class="checkbox-label">
                <input
                  tuiCheckbox
                  type="checkbox"
                  formControlName="pdf_export"
                />
                PDF Report
              </label>
            </div>
          </div>

          <div class="form-section">
            <h4>Visualization Options</h4>
            <div class="checkbox-group">
              <label tuiLabel class="checkbox-label">
                <input
                  tuiCheckbox
                  type="checkbox"
                  formControlName="visualize_floor_plans"
                />
                Generate Floor Plan Visualizations
              </label>

              <label tuiLabel class="checkbox-label">
                <input
                  tuiCheckbox
                  type="checkbox"
                  formControlName="show_azimuth_arrows"
                />
                Show Azimuth Direction Arrows
              </label>

              <label tuiLabel class="checkbox-label">
                <input
                  tuiCheckbox
                  type="checkbox"
                  formControlName="include_text_notes"
                />
                Include Text Notes on Floor Plans
              </label>

              <label tuiLabel class="checkbox-label">
                <input
                  tuiCheckbox
                  type="checkbox"
                  formControlName="include_picture_notes"
                />
                Include Picture Note Markers on Floor Plans
              </label>

              <label tuiLabel class="checkbox-label">
                <input
                  tuiCheckbox
                  type="checkbox"
                  formControlName="include_cable_notes"
                />
                Include Cable Routing Paths on Floor Plans
              </label>
            </div>

            <label class="field-label" style="margin-top: 1rem;">
              <span>AP Marker Opacity (0.0 - 1.0)</span>
              <tui-textfield>
                <input
                  tuiTextfield
                  type="number"
                  formControlName="ap_opacity"
                  placeholder="0.6"
                  min="0"
                  max="1"
                  step="0.1"
                />
              </tui-textfield>
              <small style="color: var(--tui-text-03); font-size: 0.8rem;">
                Default: 0.6 (60% opacity for better floor plan visibility)
              </small>
            </label>
          </div>

          <div class="form-section">
            <h4>Short Link Options</h4>
            <label class="field-label">
              <span>Link Expiry (days)</span>
              <tui-textfield>
                <input
                  tuiTextfield
                  type="number"
                  formControlName="short_link_days"
                  placeholder="30"
                  min="1"
                  max="365"
                />
              </tui-textfield>
            </label>
          </div>

          <div class="form-actions">
            <button
              tuiButton
              appearance="primary"
              size="l"
              type="button"
              [disabled]="processing()"
              (click)="startProcessing()"
            >
              <tui-icon *ngIf="!processing()" icon="@tui.play"></tui-icon>
              <tui-loader *ngIf="processing()" size="s"></tui-loader>
              {{ processing() ? 'Processing...' : 'Start Processing' }}
            </button>

            <button
              tuiButton
              appearance="outline"
              size="l"
              type="button"
              routerLink="/projects"
            >
              Cancel
            </button>
          </div>
        </form>

        <!-- Processing progress -->
        <div *ngIf="processing()" class="progress-section">
          <h3>Processing Progress</h3>
          <div class="progress-bar">
            <div
              class="progress-fill"
              [style.width.%]="progressValue()"
            ></div>
          </div>
          <p class="progress-text">{{ progressText() }}</p>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .processing-container {
      padding: 2rem;
      max-width: 1000px;
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

    .form-container {
      background: var(--tui-base-01);
      border-radius: 0.5rem;
      padding: 2rem;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }

    .project-info {
      margin-bottom: 2rem;
      padding-bottom: 1.5rem;
      border-bottom: 1px solid var(--tui-base-03);
    }

    .project-info h2 {
      margin: 0 0 0.5rem;
      font-size: 1.5rem;
      font-weight: 500;
    }

    .project-details {
      color: var(--tui-text-02);
      display: flex;
      gap: 1rem;
      align-items: center;
    }

    .processing-form h3 {
      margin: 0 0 1.5rem;
      font-size: 1.25rem;
      font-weight: 500;
    }

    .form-section {
      margin-bottom: 2rem;
    }

    .form-section h4 {
      margin: 0 0 1rem;
      font-size: 1rem;
      font-weight: 500;
      color: var(--tui-text-02);
    }

    .checkbox-group {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      cursor: pointer;
      font-size: 0.9rem;
      padding: 0.5rem;
      border-radius: 4px;
      transition: background-color 0.2s;
    }

    .checkbox-label:hover {
      background-color: #f5f5f5;
    }

    .checkbox-label input[type="checkbox"] {
      margin-right: 0.5rem;
      width: 18px;
      height: 18px;
      cursor: pointer;
      accent-color: #526ed3;
    }

    .field-label {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      max-width: 300px;
    }

    .field-label span {
      font-size: 0.9rem;
      color: var(--tui-text-02);
    }

    .group-select {
      width: 100%;
      padding: 0.5rem;
      border: 1px solid var(--tui-base-04);
      border-radius: 4px;
      background: var(--tui-base-01);
      color: var(--tui-text-01);
      font-size: 0.9rem;
      cursor: pointer;
    }

    .group-select:focus {
      outline: 2px solid var(--tui-primary);
      outline-offset: 2px;
    }

    .form-actions {
      display: flex;
      gap: 1rem;
      margin-top: 2rem;
      padding-top: 2rem;
      border-top: 1px solid var(--tui-base-03);
    }

    .progress-section {
      margin-top: 2rem;
      padding-top: 2rem;
      border-top: 1px solid var(--tui-base-03);
    }

    .progress-section h3 {
      margin: 0 0 1rem;
      font-size: 1.125rem;
      font-weight: 500;
    }

    .progress-bar {
      width: 100%;
      height: 8px;
      background: var(--tui-base-03);
      border-radius: 4px;
      overflow: hidden;
      margin-bottom: 1rem;
    }

    .progress-fill {
      height: 100%;
      background: var(--tui-primary);
      transition: width 0.3s ease;
    }

    .progress-text {
      color: var(--tui-text-02);
      font-size: 0.9rem;
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
  `]
})
export class ProcessingComponent implements OnInit, OnDestroy {
  private fb = inject(FormBuilder);
  private apiService = inject(ApiService);
  private projectService = inject(ProjectService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  // Signals for component state
  loading = signal(false);
  error = signal<string | null>(null);
  project = signal<ProjectDetails | null>(null);
  processing = signal(false);
  progressValue = signal(0);
  progressText = signal('Initializing...');

  // Form
  processingForm!: FormGroup;

  // Subscriptions
  private subscriptions: Subscription[] = [];
  private projectId: string | null = null;

  ngOnInit(): void {
    this.initForm();

    // Get project ID from route
    this.route.queryParams.subscribe(params => {
      this.projectId = params['projectId'] || null;
      if (this.projectId) {
        this.loadProject();
      } else {
        this.error.set('No project ID provided');
      }
    });
  }

  ngOnDestroy(): void {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  initForm(): void {
    this.processingForm = this.fb.group({
      group_by: ['model'], // default to group by model
      csv_export: [true],
      excel_export: [true],
      json_export: [false],
      html_export: [false],
      pdf_export: [false],
      visualize_floor_plans: [true],
      show_azimuth_arrows: [false],
      ap_opacity: [0.6],
      include_text_notes: [false],
      include_picture_notes: [false],
      include_cable_notes: [false],
      short_link_days: [30]
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

        // If project has existing processing flags, update form ONLY if user hasn't made changes
        // This prevents overwriting user's checkbox changes when they click "Retry"
        if (project.processing_flags && this.processingForm.pristine) {
          this.processingForm.patchValue({
            group_by: project.processing_flags['group_by'] || 'model',
            csv_export: project.processing_flags['csv_export'] || false,
            excel_export: project.processing_flags['excel_export'] || false,
            json_export: project.processing_flags['json_export'] || false,
            html_export: project.processing_flags['html_export'] || false,
            pdf_export: project.processing_flags['pdf_export'] || false,
            visualize_floor_plans: project.processing_flags['visualize_floor_plans'] || false,
            show_azimuth_arrows: project.processing_flags['show_azimuth_arrows'] || false,
            ap_opacity: project.processing_flags['ap_opacity'] || 0.6,
            include_text_notes: project.processing_flags['include_text_notes'] || false,
            include_picture_notes: project.processing_flags['include_picture_notes'] || false,
            include_cable_notes: project.processing_flags['include_cable_notes'] || false
          });
        }

        this.loading.set(false);
      },
      error: (err) => {
        this.error.set('Failed to load project details');
        this.loading.set(false);
        console.error('Error loading project:', err);
      }
    });
  }

  startProcessing(): void {
    if (!this.projectId) {
      return;
    }

    const formValue = this.processingForm.value;

    // Collect output formats from checkboxes
    const outputFormats: string[] = [];
    if (formValue.csv_export) outputFormats.push('csv');
    if (formValue.excel_export) outputFormats.push('excel');
    if (formValue.json_export) outputFormats.push('json');
    if (formValue.html_export) outputFormats.push('html');
    if (formValue.pdf_export) outputFormats.push('pdf');

    // Validate at least one format selected
    if (outputFormats.length === 0) {
      this.error.set('Please select at least one export format');
      return;
    }

    const request: ProcessingRequest = {
      group_by: formValue.group_by || undefined,
      output_formats: outputFormats,
      visualize_floor_plans: formValue.visualize_floor_plans || false,
      show_azimuth_arrows: formValue.show_azimuth_arrows || false,
      ap_opacity: formValue.ap_opacity || 0.6,
      include_text_notes: formValue.include_text_notes || false,
      include_picture_notes: formValue.include_picture_notes || false,
      include_cable_notes: formValue.include_cable_notes || false,
    };

    const shortLinkDays = this.processingForm.get('short_link_days')?.value || 30;

    this.processing.set(true);
    this.progressValue.set(10);
    this.progressText.set('Starting processing...');

    this.apiService.processProject(this.projectId, request as any, shortLinkDays).subscribe({
      next: () => {
        // Start polling for progress
        this.pollProgress();
      },
      error: (err) => {
        this.processing.set(false);
        this.progressValue.set(0);
        this.error.set('Failed to start processing');
        console.error('Error starting processing:', err);
      }
    });
  }

  pollProgress(): void {
    const pollSub = interval(2000).subscribe(() => {
      if (!this.projectId) {
        return;
      }

      this.apiService.getProject(this.projectId).subscribe({
        next: (project) => {
          this.project.set(project);

          if (project.processing_status === ProcessingStatus.PROCESSING) {
            // Simulate progress (in real app, backend would provide actual progress)
            const currentProgress = this.progressValue();
            if (currentProgress < 90) {
              this.progressValue.set(currentProgress + 10);
              this.progressText.set('Processing... Please wait');
            }
          } else if (project.processing_status === ProcessingStatus.COMPLETED) {
            this.progressValue.set(100);
            this.progressText.set('Processing completed!');
            this.processing.set(false);

            // Stop polling
            pollSub.unsubscribe();

            // Redirect to project details after a delay
            setTimeout(() => {
              this.router.navigate(['/projects', this.projectId]);
            }, 2000);
          } else if (project.processing_status === ProcessingStatus.FAILED) {
            this.progressValue.set(0);
            this.progressText.set('Processing failed');
            this.processing.set(false);
            this.error.set('Processing failed. Please try again.');

            // Stop polling
            pollSub.unsubscribe();
          }
        },
        error: (err) => {
          console.error('Error polling progress:', err);
        }
      });
    });

    this.subscriptions.push(pollSub);
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

  formatDate(dateString: string | null | undefined): string {
    if (!dateString) {
      return 'Unknown';
    }
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  }
}
