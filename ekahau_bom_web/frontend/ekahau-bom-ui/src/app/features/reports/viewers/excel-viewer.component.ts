import { Component, computed, effect, inject, input, signal, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { TuiLoader, TuiButton } from '@taiga-ui/core';
import { catchError, finalize, throwError } from 'rxjs';

interface ExcelSheet {
  name: string;
  headers: string[];
  rows: any[][];
}

@Component({
  selector: 'app-excel-viewer',
  standalone: true,
  imports: [CommonModule, TuiLoader, TuiButton],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="excel-viewer">
      @if (loading()) {
        <div class="loading-container">
          <tui-loader size="xl"></tui-loader>
          <p>Loading Excel file...</p>
        </div>
      }

      @if (error()) {
        <div class="error-container">
          <p class="error-message">{{ error() }}</p>
          <button tuiButton appearance="primary" (click)="loadExcelFile()">Retry</button>
        </div>
      }

      @if (!loading() && !error() && sheets().length > 0) {
        <!-- Sheet tabs -->
        <div class="sheet-tabs">
          @for (sheet of sheets(); track sheet.name; let i = $index) {
            <button
              tuiButton
              [appearance]="activeSheetIndex() === i ? 'primary' : 'secondary'"
              size="s"
              (click)="activeSheetIndex.set(i)"
            >
              {{ sheet.name }}
            </button>
          }
        </div>

        <!-- Sheet content -->
        @if (activeSheet(); as sheet) {
          <div class="sheet-content">
            <div class="table-container">
              <table class="excel-table">
                <thead>
                  <tr>
                    @for (header of sheet.headers; track header) {
                      <th>{{ header }}</th>
                    }
                  </tr>
                </thead>
                <tbody>
                  @for (row of sheet.rows; track $index) {
                    <tr>
                      @for (cell of row; track $index) {
                        <td>{{ cell ?? '' }}</td>
                      }
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .excel-viewer {
      width: 100%;
      height: 100%;
      min-height: 600px;
      display: flex;
      flex-direction: column;
      background: white;

      .loading-container {
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
      }

      .error-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        gap: 1rem;
        padding: 2rem;

        .error-message {
          color: var(--tui-error-fill);
          margin: 0;
        }
      }

      .sheet-tabs {
        display: flex;
        gap: 0.5rem;
        padding: 1rem;
        border-bottom: 1px solid #e0e0e0;
        background: #f5f5f5;
        flex-wrap: wrap;
      }

      .sheet-content {
        flex: 1;
        overflow: auto;
        padding: 1rem;
      }

      .table-container {
        width: 100%;
        overflow-x: auto;
      }

      .excel-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.875rem;

        th {
          background: white;
          color: #333;
          font-weight: 600;
          text-align: left;
          padding: 0.75rem;
          border: 1px solid #ddd;
          position: sticky;
          top: 0;
          z-index: 10;
        }

        td {
          padding: 0.5rem 0.75rem;
          border: 1px solid #ddd;
          color: #333;
        }

        tbody tr:hover {
          background: #f9f9f9;
        }
      }
    }
  `],
})
export class ExcelViewerComponent {
  private readonly http = inject(HttpClient);

  projectId = input.required<string>();
  filename = input.required<string>();

  loading = signal(true);
  error = signal<string | null>(null);
  sheets = signal<ExcelSheet[]>([]);
  activeSheetIndex = signal(0);

  activeSheet = computed(() => {
    const idx = this.activeSheetIndex();
    return this.sheets()[idx] || null;
  });

  constructor() {
    effect(() => {
      // Trigger load when inputs change
      const projectId = this.projectId();
      const filename = this.filename();
      if (projectId && filename) {
        this.loadExcelFile();
      }
    });
  }

  loadExcelFile(): void {
    this.loading.set(true);
    this.error.set(null);

    const url = `/api/reports/${this.projectId()}/download/${this.filename()}`;

    this.http
      .get(url, { responseType: 'arraybuffer' })
      .pipe(
        catchError((err) => {
          if (err.status === 404) {
            this.error.set('Excel file not found');
          } else if (err.status === 413) {
            this.error.set('File too large to preview');
          } else {
            this.error.set('Failed to load Excel file');
          }
          return throwError(() => err);
        }),
        finalize(() => this.loading.set(false))
      )
      .subscribe(async (buffer) => {
        try {
          await this.parseExcelFile(buffer);
        } catch (e) {
          this.error.set('Failed to parse Excel file');
          console.error('Excel parse error:', e);
        }
      });
  }

  private async parseExcelFile(buffer: ArrayBuffer): Promise<void> {
    // Lazy load xlsx library only when needed
    const XLSX = await import('xlsx');

    const workbook = XLSX.read(buffer, { type: 'array' });
    const parsedSheets: ExcelSheet[] = [];

    for (const sheetName of workbook.SheetNames) {
      const worksheet = workbook.Sheets[sheetName];
      const jsonData = XLSX.utils.sheet_to_json(worksheet, {
        header: 1,
        defval: '',
      }) as any[][];

      if (jsonData.length > 0) {
        const headers = jsonData[0].map((h: any) => String(h));
        const rows = jsonData.slice(1);

        parsedSheets.push({
          name: sheetName,
          headers,
          rows,
        });
      }
    }

    this.sheets.set(parsedSheets);
    this.activeSheetIndex.set(0);
  }
}
