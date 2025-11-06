import { Component, computed, inject, OnInit, signal, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { TuiLoader } from '@taiga-ui/core';
import { finalize } from 'rxjs';

import { ReportViewerComponent } from '../report-viewer/report-viewer.component';
import { ReportFile, ReportsList } from '../../../core/models/project.model';

@Component({
  selector: 'app-report-viewer-page',
  standalone: true,
  imports: [CommonModule, TuiLoader, ReportViewerComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="report-viewer-page">
      @if (loading()) {
        <div class="loading-container">
          <tui-loader size="xl"></tui-loader>
          <p>Loading report...</p>
        </div>
      }

      @if (error()) {
        <div class="error-container">
          <h2>Error Loading Report</h2>
          <p>{{ error() }}</p>
          <button (click)="goBack()">Go Back</button>
        </div>
      }

      @if (reportFile() && !loading() && !error()) {
        <app-report-viewer
          [projectId]="projectId()"
          [report]="reportFile()!"
          (closeDialog)="goBack()"
        ></app-report-viewer>
      }
    </div>
  `,
  styles: [`
    .report-viewer-page {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      width: 100vw;
      height: 100vh;
      background: #ffffff;
      overflow: hidden;
      z-index: 9999;

      .loading-container,
      .error-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        gap: 1rem;

        p {
          margin: 0;
          color: var(--tui-text-02);
        }

        button {
          margin-top: 1rem;
          padding: 0.5rem 1rem;
          background: var(--tui-primary);
          color: #ffffff;
          border: none;
          border-radius: 4px;
          cursor: pointer;

          &:hover {
            background: var(--tui-primary-hover);
          }
        }
      }
    }
  `],
})
export class ReportViewerPageComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private http = inject(HttpClient);

  // Route parameters
  projectId = signal<string>('');
  filename = signal<string>('');

  // State
  loading = signal(true);
  error = signal<string | null>(null);
  reportFile = signal<ReportFile | null>(null);

  ngOnInit(): void {
    // Extract route parameters and query parameters
    const projectId = this.route.snapshot.paramMap.get('projectId');
    const filename = this.route.snapshot.queryParamMap.get('filename');

    if (!projectId || !filename) {
      this.error.set('Invalid report URL: missing project ID or filename');
      this.loading.set(false);
      return;
    }

    this.projectId.set(projectId);
    this.filename.set(decodeURIComponent(filename));

    this.loadReportMetadata();
  }

  loadReportMetadata(): void {
    this.loading.set(true);
    this.error.set(null);

    const url = `/api/reports/${this.projectId()}/list`;

    this.http
      .get<ReportsList>(url)
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (reportsList) => {
          // Find the report file in either reports or visualizations
          const allFiles = [...reportsList.reports, ...reportsList.visualizations];
          const report = allFiles.find((f) => f.filename === this.filename());

          if (report) {
            this.reportFile.set(report);
          } else {
            this.error.set(`Report file not found: ${this.filename()}`);
          }
        },
        error: (err) => {
          console.error('Failed to load report metadata:', err);
          this.error.set('Failed to load report metadata');
        },
      });
  }

  goBack(): void {
    // Close the current tab/window
    window.close();
  }
}
