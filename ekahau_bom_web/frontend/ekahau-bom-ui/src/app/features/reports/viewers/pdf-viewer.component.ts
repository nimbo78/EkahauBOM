import { Component, computed, effect, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { TuiLoader } from '@taiga-ui/core';

@Component({
  selector: 'app-pdf-viewer',
  standalone: true,
  imports: [CommonModule, TuiLoader],
  template: `
    <div class="pdf-viewer">
      @if (loading()) {
        <div class="loading-state">
          <tui-loader size="xl"></tui-loader>
          <p>Loading PDF document...</p>
        </div>
      }
      @if (!loading() && !error()) {
        <iframe
          [src]="safeUrl()"
          class="pdf-iframe"
          title="PDF Viewer"
        ></iframe>
      }
      @if (error()) {
        <div class="error-state">
          <p>{{ error() }}</p>
          <p class="hint">Your browser may not support PDF preview. Please download the file instead.</p>
        </div>
      }
    </div>
  `,
  styles: [`
    .pdf-viewer {
      width: 100%;
      height: 100%;
      min-height: 800px;
      position: relative;

      .loading-state {
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

      .pdf-iframe {
        width: 100%;
        height: 100%;
        min-height: 800px;
        border: none;
        border-radius: 0.5rem;
      }

      .error-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        gap: 0.5rem;
        text-align: center;

        p {
          color: var(--tui-status-negative);
          margin: 0;

          &.hint {
            color: var(--tui-text-03);
            font-size: 0.875rem;
            max-width: 400px;
          }
        }
      }
    }
  `],
})
export class PdfViewerComponent {
  private readonly sanitizer = inject(DomSanitizer);

  projectId = input.required<string>();
  filename = input.required<string>();

  loading = signal(true);
  error = signal<string | null>(null);

  // Generate safe URL for PDF embed
  safeUrl = computed(() => {
    const url = `/api/reports/${this.projectId()}/download/${this.filename()}`;
    return this.sanitizer.bypassSecurityTrustResourceUrl(url);
  });

  constructor() {
    effect(() => {
      // When inputs change, reset state and start loading
      const projectId = this.projectId();
      const filename = this.filename();

      if (projectId && filename) {
        this.loading.set(true);
        this.error.set(null);

        // Set a timeout to hide loading spinner after 1 second
        // PDF embed doesn't always trigger load events reliably
        setTimeout(() => {
          this.loading.set(false);
        }, 1000);
      }
    });
  }
}
