import { Component, computed, effect, inject, input, signal, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { TuiLoader } from '@taiga-ui/core';
import { catchError, finalize, throwError } from 'rxjs';

@Component({
  selector: 'app-json-viewer',
  standalone: true,
  imports: [CommonModule, TuiLoader],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="json-viewer">
      @if (loading()) {
        <div class="loading-container">
          <tui-loader size="xl"></tui-loader>
          <p>Loading JSON file...</p>
        </div>
      }

      @if (error()) {
        <div class="error-container">
          <p class="error-message">{{ error() }}</p>
          <button (click)="loadJsonFile()" class="retry-button">Retry</button>
        </div>
      }

      @if (!loading() && !error() && jsonHtml()) {
        <div class="json-content">
          <pre class="json-code" [innerHTML]="jsonHtml()"></pre>
        </div>
      }
    </div>
  `,
  styles: [`
    .json-viewer {
      width: 100%;
      height: 100%;
      min-height: 600px;
      display: flex;
      flex-direction: column;
      background: #1e1e1e;
      color: #d4d4d4;

      .loading-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        gap: 1rem;

        p {
          margin: 0;
          color: #d4d4d4;
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
          color: #f48771;
          margin: 0;
        }

        .retry-button {
          padding: 0.5rem 1rem;
          background: #0e639c;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;

          &:hover {
            background: #1177bb;
          }
        }
      }

      .json-content {
        flex: 1;
        overflow: auto;
        padding: 1rem;
        max-height: calc(100vh - 120px);
      }

      .json-code {
        margin: 0;
        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        font-size: 0.875rem;
        line-height: 1.5;
        white-space: pre-wrap;
        word-wrap: break-word;

        /* JSON Syntax Highlighting - inline styles */
        ::ng-deep .json-key {
          color: #9cdcfe;
        }

        ::ng-deep .json-string {
          color: #ce9178;
        }

        ::ng-deep .json-number {
          color: #b5cea8;
        }

        ::ng-deep .json-boolean {
          color: #569cd6;
        }

        ::ng-deep .json-null {
          color: #569cd6;
        }
      }
    }
  `],
})
export class JsonViewerComponent {
  private readonly http = inject(HttpClient);
  private readonly sanitizer = inject(DomSanitizer);

  projectId = input.required<string>();
  filename = input.required<string>();

  loading = signal(true);
  error = signal<string | null>(null);
  jsonHtml = signal<SafeHtml | null>(null);

  constructor() {
    effect(() => {
      // Trigger load when inputs change
      const projectId = this.projectId();
      const filename = this.filename();
      if (projectId && filename) {
        this.loadJsonFile();
      }
    });
  }

  loadJsonFile(): void {
    this.loading.set(true);
    this.error.set(null);

    const url = `/api/reports/${this.projectId()}/download/${this.filename()}`;

    this.http
      .get(url, { responseType: 'text' })
      .pipe(
        catchError((err) => {
          if (err.status === 404) {
            this.error.set('JSON file not found');
          } else if (err.status === 413) {
            this.error.set('File too large to preview');
          } else {
            this.error.set('Failed to load JSON file');
          }
          return throwError(() => err);
        }),
        finalize(() => this.loading.set(false))
      )
      .subscribe((jsonText) => {
        try {
          const parsed = JSON.parse(jsonText);
          const formatted = JSON.stringify(parsed, null, 2);
          const highlighted = this.syntaxHighlight(formatted);
          const safeHtml = this.sanitizer.bypassSecurityTrustHtml(highlighted);
          this.jsonHtml.set(safeHtml);
        } catch (e) {
          this.error.set('Failed to parse JSON file');
          console.error('JSON parse error:', e);
        }
      });
  }

  private syntaxHighlight(json: string): string {
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return json.replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
      (match) => {
        let cls = 'json-number';
        if (/^"/.test(match)) {
          if (/:$/.test(match)) {
            cls = 'json-key';
          } else {
            cls = 'json-string';
          }
        } else if (/true|false/.test(match)) {
          cls = 'json-boolean';
        } else if (/null/.test(match)) {
          cls = 'json-null';
        }
        return '<span class="' + cls + '">' + match + '</span>';
      }
    );
  }
}
