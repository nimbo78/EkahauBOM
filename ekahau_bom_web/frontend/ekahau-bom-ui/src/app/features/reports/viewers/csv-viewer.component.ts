import { Component, inject, input, OnInit, signal, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { TuiLoader, TuiIcon } from '@taiga-ui/core';
import { TuiTable } from '@taiga-ui/addon-table';
import { finalize } from 'rxjs';

@Component({
  selector: 'app-csv-viewer',
  standalone: true,
  imports: [CommonModule, TuiLoader, TuiTable, TuiIcon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="csv-viewer">
      @if (loading()) {
        <div class="loading-state">
          <tui-loader size="xl"></tui-loader>
          <p>Loading CSV data...</p>
        </div>
      }

      @if (error()) {
        <div class="error-state">
          <tui-icon icon="@tui.alert-circle" class="error-icon"></tui-icon>
          <p>{{ error() }}</p>
          <button (click)="retry()">Retry</button>
        </div>
      }

      @if (!loading() && !error() && csvData().length > 0) {
        <div class="csv-content">
          <div class="csv-info">
            <span>{{ csvData().length }} rows, {{ csvHeaders().length }} columns</span>
          </div>

          <div class="table-container">
            <table class="csv-table">
              <thead>
                <tr>
                  <th *ngFor="let header of csvHeaders()" class="csv-header">
                    {{ header }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let row of csvData(); let i = index" class="csv-row">
                  <td *ngFor="let header of csvHeaders()" class="csv-cell">
                    {{ row[header] }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      }

      @if (!loading() && !error() && csvData().length === 0) {
        <div class="empty-state">
          <tui-icon icon="@tui.file"></tui-icon>
          <p>No data found in CSV file</p>
        </div>
      }
    </div>
  `,
  styles: [`
    .csv-viewer {
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: column;
      overflow: hidden;

      .loading-state,
      .error-state,
      .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        gap: 1rem;
        text-align: center;

        p {
          margin: 0;
          color: var(--tui-text-02);
        }

        .error-icon {
          font-size: 3rem;
          color: var(--tui-status-negative);
        }
      }

      .csv-content {
        display: flex;
        flex-direction: column;
        height: 100%;
        overflow: hidden;
        background: #ffffff;

        .csv-info {
          padding: 0.75rem 1rem;
          background: var(--tui-base-02);
          border-bottom: 1px solid var(--tui-base-03);
          font-size: 0.875rem;
          color: var(--tui-text-02);
        }

        .table-container {
          flex: 1;
          overflow: auto;
          background: #ffffff;
        }

        .csv-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.875rem;

          .csv-header {
            position: sticky;
            top: 0;
            background: #ffffff;
            color: var(--tui-text-01);
            font-weight: 600;
            padding: 0.75rem 1rem;
            text-align: left;
            border: 1px solid #e0e0e0;
            border-bottom: 2px solid var(--tui-base-04);
            z-index: 10;
          }

          .csv-row {
            background: #ffffff;

            &:nth-child(even) {
              background: #f5f5f5;
            }

            &:hover {
              background: #999999;
            }
          }

          .csv-cell {
            padding: 0.5rem 1rem;
            border: 1px solid #e0e0e0;
            color: var(--tui-text-02);
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
        }
      }
    }
  `],
})
export class CsvViewerComponent implements OnInit {
  private http = inject(HttpClient);

  projectId = input.required<string>();
  filename = input.required<string>();

  loading = signal(true);
  error = signal<string | null>(null);
  csvHeaders = signal<string[]>([]);
  csvData = signal<any[]>([]);

  ngOnInit(): void {
    this.loadCsvData();
  }

  loadCsvData(): void {
    this.loading.set(true);
    this.error.set(null);

    const url = `/api/reports/${this.projectId()}/download/${this.filename()}`;

    this.http
      .get(url, { responseType: 'text' })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: async (csvText) => {
          try {
            // Check if this is a multi-section analytics report
            if (csvText.includes('===') && this.filename().includes('analytics')) {
              await this.parseMultiSectionCsv(csvText);
            } else {
              await this.parseStandardCsv(csvText);
            }
          } catch (err) {
            this.error.set('Failed to parse CSV file');
            console.error('CSV parse error:', err);
          }
        },
        error: (err) => {
          this.error.set('Failed to load CSV file');
          console.error('CSV load error:', err);
        },
      });
  }

  private async parseStandardCsv(csvText: string): Promise<void> {
    // Lazy load papaparse only when needed
    const Papa = (await import('papaparse')).default;

    const result = Papa.parse(csvText, {
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
      comments: '#',
    });

    if (result.errors.length > 0) {
      console.error('CSV parsing errors:', result.errors);
    }

    this.csvHeaders.set(result.meta.fields || []);
    this.csvData.set(result.data);
  }

  private async parseMultiSectionCsv(csvText: string): Promise<void> {
    // Lazy load papaparse only when needed
    const Papa = (await import('papaparse')).default;

    // For multi-section reports, flatten all data into a single table
    // with Section, Key, Value, Unit columns
    const lines = csvText.split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('#'));
    const flatData: any[] = [];
    let currentSection = '';

    for (const line of lines) {
      // Section header
      if (line.startsWith('===') && line.endsWith('===')) {
        currentSection = line.replace(/=/g, '').trim();
        continue;
      }

      // Parse CSV line
      const parsed = Papa.parse(line, { header: false }).data[0] as string[];
      if (!parsed || parsed.length === 0) continue;

      // Add row with section context
      if (parsed.length >= 2) {
        flatData.push({
          Section: currentSection,
          Key: parsed[0],
          Value: parsed[1] || '',
          Unit: parsed[2] || ''
        });
      }
    }

    this.csvHeaders.set(['Section', 'Key', 'Value', 'Unit']);
    this.csvData.set(flatData);
  }

  retry(): void {
    this.loadCsvData();
  }
}
