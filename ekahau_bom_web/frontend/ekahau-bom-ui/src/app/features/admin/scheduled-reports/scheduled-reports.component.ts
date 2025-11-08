import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { TuiButton } from '@taiga-ui/core';

import { ApiService } from '../../../core/services/api.service';
import { ErrorMessageService } from '../../../shared/services/error-message.service';
import {
  TimeRange,
  ReportFormat,
  AggregatedReportResponse,
  AggregatedReportData,
  VendorAnalysisResponse,
} from '../../../core/models/batch.model';

@Component({
  selector: 'app-scheduled-reports',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    TuiButton,
  ],
  template: `
    <div class="reports-container">
      <div class="reports-header">
        <h2>Management Reports</h2>
        <p class="description">
          Generate aggregated BOM reports and vendor analysis across all batches.
        </p>
      </div>

      <!-- Controls -->
      <div class="controls-card">
        <form [formGroup]="reportForm" class="report-form">
          <label class="form-label">
            <span>Time Range</span>
            <select class="form-select" formControlName="timeRange">
              <option value="last_week">Last Week</option>
              <option value="last_month">Last Month</option>
              <option value="last_quarter">Last Quarter</option>
              <option value="last_year">Last Year</option>
            </select>
          </label>

          <div class="button-group">
            <button
              tuiButton
              type="button"
              appearance="primary"
              size="m"
              [disabled]="loading()"
              (click)="generateReport()"
            >
              {{ loading() ? 'Generating...' : 'Generate Report' }}
            </button>

            <button
              tuiButton
              type="button"
              appearance="secondary"
              size="m"
              [disabled]="!reportData()"
              (click)="downloadCSV()"
            >
              Download CSV
            </button>

            <button
              tuiButton
              type="button"
              appearance="secondary"
              size="m"
              [disabled]="!reportData()"
              (click)="downloadText()"
            >
              Download Text
            </button>
          </div>

          <div class="error-message" *ngIf="error()">
            <p>{{ error() }}</p>
          </div>
        </form>
      </div>

      <!-- Summary -->
      <div class="summary-card" *ngIf="reportData()">
        <h3>Summary ({{ getDateRangeText() }})</h3>
        <div class="stat-grid">
          <div class="stat-item">
            <span class="stat-label">Total Batches</span>
            <span class="stat-value">{{ reportData()!.summary.total_batches }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Total Projects</span>
            <span class="stat-value">{{ reportData()!.summary.total_projects }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Successful</span>
            <span class="stat-value success">{{ reportData()!.summary.successful_projects }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Failed</span>
            <span class="stat-value failed">{{ reportData()!.summary.failed_projects }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Access Points</span>
            <span class="stat-value">{{ reportData()!.summary.total_access_points }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Antennas</span>
            <span class="stat-value">{{ reportData()!.summary.total_antennas }}</span>
          </div>
        </div>
      </div>

      <!-- Vendor Analysis -->
      <div class="vendor-card" *ngIf="vendorAnalysis()">
        <h3>Top Vendors</h3>
        <div class="vendor-list">
          <div class="vendor-item" *ngFor="let vendor of vendorAnalysis()!.top_vendors.slice(0, 10)">
            <div class="vendor-info">
              <span class="vendor-name">{{ vendor.vendor }}</span>
              <span class="vendor-stats">{{ vendor.quantity }} APs ({{ vendor.percentage }}%)</span>
            </div>
            <div class="vendor-bar">
              <div class="bar-fill" [style.width.%]="vendor.percentage"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Top Models -->
      <div class="models-card" *ngIf="vendorAnalysis()">
        <h3>Top Models</h3>
        <div class="models-table">
          <table>
            <thead>
              <tr>
                <th>Vendor | Model</th>
                <th>Quantity</th>
                <th>Percentage</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let model of vendorAnalysis()!.top_models.slice(0, 15)">
                <td>{{ model.vendor_model }}</td>
                <td>{{ model.quantity }}</td>
                <td>{{ model.percentage }}%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .reports-container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }

    .reports-header {
      margin-bottom: 24px;

      h2 {
        margin: 0 0 8px 0;
        font-size: 28px;
        font-weight: 600;
      }

      .description {
        margin: 0;
        color: var(--tui-text-02);
      }
    }

    .controls-card, .summary-card, .vendor-card, .models-card {
      background: var(--tui-base-02);
      border: 1px solid var(--tui-base-04);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
    }

    .report-form {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .button-group {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }

    .error-message {
      padding: 12px;
      background: rgba(var(--tui-status-negative-rgb), 0.1);
      border: 1px solid var(--tui-status-negative);
      border-radius: 8px;
      color: var(--tui-status-negative);
    }

    .stat-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 16px;
      margin-top: 16px;
    }

    .stat-item {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 16px;
      background: var(--tui-base-01);
      border-radius: 8px;
    }

    .stat-label {
      font-size: 12px;
      color: var(--tui-text-03);
      text-transform: uppercase;
    }

    .stat-value {
      font-size: 24px;
      font-weight: 600;

      &.success {
        color: var(--tui-status-positive);
      }

      &.failed {
        color: var(--tui-status-negative);
      }
    }

    .vendor-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-top: 16px;
    }

    .vendor-item {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .vendor-info {
      display: flex;
      justify-content: space-between;
      font-size: 14px;
    }

    .vendor-name {
      font-weight: 600;
    }

    .vendor-stats {
      color: var(--tui-text-03);
    }

    .vendor-bar {
      height: 8px;
      background: var(--tui-base-03);
      border-radius: 4px;
      overflow: hidden;
    }

    .bar-fill {
      height: 100%;
      background: var(--tui-primary);
      transition: width 0.3s ease;
    }

    .models-table {
      margin-top: 16px;
      overflow-x: auto;
    }

    table {
      width: 100%;
      border-collapse: collapse;
    }

    th, td {
      padding: 12px;
      text-align: left;
      border-bottom: 1px solid var(--tui-base-04);
    }

    th {
      font-weight: 600;
      color: var(--tui-text-01);
      background: var(--tui-base-01);
    }

    td {
      color: var(--tui-text-02);
    }

    tr:hover td {
      background: var(--tui-base-01);
    }
  `],
})
export class ScheduledReportsComponent implements OnInit {
  private apiService = inject(ApiService);
  private errorMessageService = inject(ErrorMessageService);

  loading = signal(false);
  error = signal<string | null>(null);
  reportData = signal<AggregatedReportData | null>(null);
  vendorAnalysis = signal<VendorAnalysisResponse | null>(null);

  reportForm = new FormGroup({
    timeRange: new FormControl<TimeRange>('last_month', { nonNullable: true }),
  });

  ngOnInit(): void {
    // Generate initial report
    this.generateReport();
  }

  generateReport(): void {
    this.loading.set(true);
    this.error.set(null);

    const timeRange = this.reportForm.value.timeRange!;

    // Generate aggregated report
    this.apiService.getAggregatedReport(timeRange, 'json').subscribe({
      next: (response) => {
        if (response.data) {
          this.reportData.set(response.data);
        }
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Error generating report:', err);
        this.errorMessageService.logError(err, 'Generate Report');
        this.error.set(this.errorMessageService.getErrorMessage(err));
        this.loading.set(false);
      },
    });

    // Generate vendor analysis
    this.apiService.getVendorAnalysis(timeRange).subscribe({
      next: (analysis) => {
        this.vendorAnalysis.set(analysis);
      },
      error: (err) => {
        console.error('Error getting vendor analysis:', err);
      },
    });
  }

  downloadCSV(): void {
    const timeRange = this.reportForm.value.timeRange!;

    this.apiService.getAggregatedReport(timeRange, 'csv').subscribe({
      next: (response) => {
        if (response.content) {
          this.downloadFile(response.content, 'aggregated-report.csv', 'text/csv');
        }
      },
      error: (err) => {
        console.error('Error downloading CSV:', err);
        this.errorMessageService.logError(err, 'Download CSV');
        this.error.set(this.errorMessageService.getErrorMessage(err));
      },
    });
  }

  downloadText(): void {
    const timeRange = this.reportForm.value.timeRange!;

    this.apiService.getAggregatedReport(timeRange, 'text').subscribe({
      next: (response) => {
        if (response.content) {
          this.downloadFile(response.content, 'aggregated-report.txt', 'text/plain');
        }
      },
      error: (err) => {
        console.error('Error downloading text:', err);
        this.errorMessageService.logError(err, 'Download Text');
        this.error.set(this.errorMessageService.getErrorMessage(err));
      },
    });
  }

  private downloadFile(content: string, filename: string, mimeType: string): void {
    const blob = new Blob([content], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    window.URL.revokeObjectURL(url);
  }

  getDateRangeText(): string {
    const data = this.reportData();
    if (!data || !data.date_range.start_date || !data.date_range.end_date) {
      return '';
    }

    const start = new Date(data.date_range.start_date).toLocaleDateString('en-GB');
    const end = new Date(data.date_range.end_date).toLocaleDateString('en-GB');
    return `${start} - ${end}`;
  }
}
