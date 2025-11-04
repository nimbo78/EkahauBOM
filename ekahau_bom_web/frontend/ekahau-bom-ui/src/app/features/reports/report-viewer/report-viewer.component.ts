import { Component, computed, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TuiButton, TuiIcon } from '@taiga-ui/core';

import { HtmlViewerComponent } from '../viewers/html-viewer.component';
import { CsvViewerComponent } from '../viewers/csv-viewer.component';
import { ExcelViewerComponent } from '../viewers/excel-viewer.component';
import { PdfViewerComponent } from '../viewers/pdf-viewer.component';
import { ReportFile } from '../../../core/models/project.model';

@Component({
  selector: 'app-report-viewer',
  standalone: true,
  imports: [
    CommonModule,
    TuiButton,
    TuiIcon,
    HtmlViewerComponent,
    CsvViewerComponent,
    ExcelViewerComponent,
    PdfViewerComponent,
  ],
  templateUrl: './report-viewer.component.html',
  styleUrl: './report-viewer.component.scss',
})
export class ReportViewerComponent {
  // Inputs
  projectId = input.required<string>();
  report = input.required<ReportFile>();

  // Outputs
  closeDialog = output<void>();

  // Determine file type
  isHtml = computed(() => this.report().filename.toLowerCase().endsWith('.html'));
  isCsv = computed(() => this.report().filename.toLowerCase().endsWith('.csv'));
  isExcel = computed(() =>
    this.report().filename.toLowerCase().endsWith('.xlsx') ||
    this.report().filename.toLowerCase().endsWith('.xls')
  );
  isPdf = computed(() => this.report().filename.toLowerCase().endsWith('.pdf'));

  close(): void {
    this.closeDialog.emit();
  }

  downloadReport(): void {
    const url = `/api/reports/${this.projectId()}/download/${this.report().filename}`;
    window.open(url, '_blank');
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  }
}
