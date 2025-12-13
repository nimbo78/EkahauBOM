import { Component, inject, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LoadingService } from '../services/loading.service';

/**
 * Global loading overlay component
 *
 * Shows a fullscreen loading overlay with:
 * - Backdrop with blur effect
 * - Loading spinner
 * - Optional message
 * - Optional progress bar
 *
 * Controlled by LoadingService.
 * Add to app.component.html: <app-loading-overlay />
 */
@Component({
  selector: 'app-loading-overlay',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (loadingService.isLoading()) {
      <div class="loading-overlay" (click)="$event.stopPropagation()">
        <div class="loading-backdrop"></div>
        <div class="loading-content">
          <div class="spinner-container">
            <div class="css-spinner"></div>
          </div>

          @if (loadingService.message()) {
            <p class="loading-message">{{ loadingService.message() }}</p>
          }

          @if (loadingService.progress() !== undefined) {
            <div class="progress-container">
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  [style.width.%]="loadingService.progress()"
                ></div>
              </div>
              <span class="progress-text">{{ loadingService.progress() }}%</span>
            </div>
          }
        </div>
      </div>
    }
  `,
  styles: [`
    .loading-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      z-index: 10000;
      display: flex;
      align-items: center;
      justify-content: center;
      pointer-events: all;
    }

    .loading-backdrop {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(248, 249, 250, 0.92);
      backdrop-filter: blur(2px);
      -webkit-backdrop-filter: blur(2px);
      animation: fadeIn 0.2s ease-in-out;
    }

    .loading-content {
      position: relative;
      z-index: 10001;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1rem;
      background: white;
      padding: 2rem 2.5rem;
      border-radius: 12px;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
      border: 1px solid #e5e7eb;
      animation: scaleIn 0.3s ease-out;
      min-width: 240px;
    }

    .spinner-container {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 50px;
      width: 100%;
      margin-bottom: 0.5rem;
    }

    /* Simple CSS spinner */
    .css-spinner {
      width: 40px;
      height: 40px;
      border: 3px solid #e5e7eb;
      border-top: 3px solid #3b82f6;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    .loading-message {
      margin: 0;
      font-size: 0.95rem;
      font-weight: 500;
      color: #4b5563;
      text-align: center;
      max-width: 300px;
    }

    .progress-container {
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      align-items: center;
    }

    .progress-bar {
      width: 100%;
      height: 6px;
      background: #f3f4f6;
      border-radius: 6px;
      overflow: hidden;
      position: relative;
    }

    .progress-fill {
      height: 100%;
      background: #3b82f6;
      border-radius: 6px;
      transition: width 0.3s ease-out;
      position: relative;
    }

    .progress-text {
      font-size: 0.875rem;
      font-weight: 600;
      color: #6b7280;
      font-variant-numeric: tabular-nums;
    }

    @keyframes fadeIn {
      from {
        opacity: 0;
      }
      to {
        opacity: 1;
      }
    }

    @keyframes scaleIn {
      from {
        transform: scale(0.95);
        opacity: 0;
      }
      to {
        transform: scale(1);
        opacity: 1;
      }
    }
  `],
})
export class LoadingOverlayComponent {
  loadingService = inject(LoadingService);
}
