import { Component, computed, inject, input, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer } from '@angular/platform-browser';

@Component({
  selector: 'app-html-viewer',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="html-viewer">
      <iframe
        [src]="safeUrl()"
        class="html-iframe"
      ></iframe>
    </div>
  `,
  styles: [`
    .html-viewer {
      width: 100%;
      height: 100%;
      min-height: 600px;
      position: relative;

      .html-iframe {
        width: 100%;
        height: 100%;
        border: none;
        background: white;
      }
    }
  `],
})
export class HtmlViewerComponent {
  private readonly sanitizer = inject(DomSanitizer);

  projectId = input.required<string>();
  filename = input.required<string>();

  // Generate safe URL for iframe
  safeUrl = computed(() => {
    const url = `/api/reports/${this.projectId()}/download/${this.filename()}`;
    return this.sanitizer.bypassSecurityTrustResourceUrl(url);
  });
}
