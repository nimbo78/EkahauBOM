import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TuiLoader } from '@taiga-ui/core';

@Component({
  selector: 'app-excel-viewer',
  standalone: true,
  imports: [CommonModule, TuiLoader],
  template: `
    <div class="excel-viewer">
      <div class="placeholder">
        <tui-loader size="xl"></tui-loader>
        <p>Excel Viewer - Implementation in progress</p>
        <p class="details">
          This component will parse and display Excel files using SheetJS (xlsx) with multi-sheet support.
        </p>
      </div>
    </div>
  `,
  styles: [`
    .excel-viewer {
      width: 100%;
      height: 100%;
      min-height: 600px;

      .placeholder {
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

          &.details {
            font-size: 0.875rem;
            color: var(--tui-text-03);
            max-width: 400px;
          }
        }
      }
    }
  `],
})
export class ExcelViewerComponent {
  projectId = input.required<string>();
  filename = input.required<string>();
}
