import { Component, OnInit, signal, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { TuiButton } from '@taiga-ui/core';
import { NgxEchartsModule } from 'ngx-echarts';
import type { EChartsOption } from 'echarts';

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
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    TuiButton,
    NgxEchartsModule,
  ],
  template: `
    <div class="reports-container">
      <div class="reports-header">
        <h2>Batch Processing Dashboard</h2>
        <p class="description">
          Analytics dashboard showing batch processing history, trends, and vendor analysis.
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

      <!-- Charts -->
      <div class="charts-grid" *ngIf="reportData()">
        <!-- Timeline Chart -->
        <div class="chart-card">
          <h3>Batch Processing Timeline</h3>
          <div echarts [options]="timelineChartOptions()" class="chart"></div>
        </div>

        <!-- Success Rate Pie Chart -->
        <div class="chart-card">
          <h3>Success Rate</h3>
          <div echarts [options]="successRateChartOptions()" class="chart"></div>
        </div>

        <!-- Vendor Distribution Bar Chart -->
        <div class="chart-card full-width" *ngIf="vendorAnalysis()">
          <h3>Top Vendors Distribution</h3>
          <div echarts [options]="vendorChartOptions()" class="chart-large"></div>
        </div>
      </div>

      <!-- Top Models -->
      <div class="models-card" *ngIf="vendorAnalysis()">
        <h3>Top Models</h3>
        <div class="models-table">
          <table>
            <thead>
              <tr>
                <th>Vendor</th>
                <th>Model</th>
                <th>Quantity</th>
                <th>Percentage</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let model of vendorAnalysis()!.top_models.slice(0, 15)">
                <td>{{ model.vendor_model.split('|')[0] }}</td>
                <td>{{ model.vendor_model.split('|')[1] || model.vendor_model }}</td>
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
      max-width: 1400px;
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

    .controls-card, .summary-card, .chart-card, .models-card {
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

    .charts-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
      gap: 24px;
      margin-bottom: 24px;

      .full-width {
        grid-column: 1 / -1;
      }
    }

    .chart-card {
      h3 {
        margin: 0 0 16px 0;
        font-size: 18px;
        font-weight: 600;
        color: var(--tui-text-01);
      }
    }

    .chart {
      width: 100%;
      height: 350px;
    }

    .chart-large {
      width: 100%;
      height: 450px;
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

    @media (max-width: 768px) {
      .charts-grid {
        grid-template-columns: 1fr;
      }
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

  // Chart options computed from data
  timelineChartOptions = computed<EChartsOption>(() => {
    const data = this.reportData();
    if (!data || !data.trends) {
      return {};
    }

    const dates = Object.keys(data.trends.batches_by_date).sort();
    const batchCounts = dates.map(date => data.trends.batches_by_date[date]);
    const apCounts = dates.map(date => data.trends.access_points_by_date[date] || 0);

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        }
      },
      legend: {
        data: ['Batches', 'Access Points']
      },
      xAxis: {
        type: 'category',
        data: dates.map(d => new Date(d).toLocaleDateString('en-GB', { month: 'short', day: 'numeric' })),
        axisLabel: {
          rotate: 45
        }
      },
      yAxis: [
        {
          type: 'value',
          name: 'Batches',
          position: 'left',
        },
        {
          type: 'value',
          name: 'Access Points',
          position: 'right',
        }
      ],
      series: [
        {
          name: 'Batches',
          type: 'line',
          data: batchCounts,
          smooth: true,
          itemStyle: { color: '#5b8ff9' },
          areaStyle: { opacity: 0.3 }
        },
        {
          name: 'Access Points',
          type: 'line',
          yAxisIndex: 1,
          data: apCounts,
          smooth: true,
          itemStyle: { color: '#5ad8a6' },
          areaStyle: { opacity: 0.3 }
        }
      ]
    };
  });

  successRateChartOptions = computed<EChartsOption>(() => {
    const data = this.reportData();
    if (!data) {
      return {};
    }

    const successful = data.summary.successful_projects;
    const failed = data.summary.failed_projects;
    const total = successful + failed;
    const successRate = total > 0 ? ((successful / total) * 100).toFixed(1) : '0';

    return {
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        left: 'left'
      },
      series: [
        {
          name: 'Projects',
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          label: {
            show: true,
            formatter: '{b}: {d}%'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 18,
              fontWeight: 'bold'
            }
          },
          data: [
            { value: successful, name: 'Successful', itemStyle: { color: '#52c41a' } },
            { value: failed, name: 'Failed', itemStyle: { color: '#ff4d4f' } }
          ]
        }
      ],
      graphic: {
        type: 'text',
        left: 'center',
        top: 'center',
        style: {
          text: `${successRate}%`,
          fontSize: 32,
          fontWeight: 'bold',
          fill: '#52c41a'
        }
      }
    };
  });

  vendorChartOptions = computed<EChartsOption>(() => {
    const analysis = this.vendorAnalysis();
    if (!analysis) {
      return {};
    }

    const vendors = analysis.top_vendors.slice(0, 10);
    const names = vendors.map(v => v.vendor);
    const quantities = vendors.map(v => v.quantity);

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        },
        formatter: '{b}: {c} APs'
      },
      xAxis: {
        type: 'category',
        data: names,
        axisLabel: {
          rotate: 30,
          interval: 0
        }
      },
      yAxis: {
        type: 'value',
        name: 'Access Points'
      },
      series: [
        {
          name: 'Access Points',
          type: 'bar',
          data: quantities,
          itemStyle: {
            color: '#1890ff'
          },
          label: {
            show: true,
            position: 'top'
          }
        }
      ]
    };
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
