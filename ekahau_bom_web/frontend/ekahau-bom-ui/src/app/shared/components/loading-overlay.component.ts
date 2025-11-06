import { Component, inject, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TuiLoader } from '@taiga-ui/core';
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
  imports: [CommonModule, TuiLoader],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (loadingService.isLoading()) {
      <div class="loading-overlay" (click)="$event.stopPropagation()">
        <div class="loading-backdrop"></div>
        <div class="loading-content">
          <tui-loader size="xxl" [showLoader]="true"></tui-loader>

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
      background: rgba(0, 0, 0, 0.5);
      backdrop-filter: blur(4px);
      animation: fadeIn 0.2s ease-in-out;
    }

    .loading-content {
      position: relative;
      z-index: 10001;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1.5rem;
      background: var(--tui-base-01);
      padding: 3rem 4rem;
      border-radius: 1rem;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
      animation: scaleIn 0.3s ease-out;
      min-width: 300px;
    }

    .loading-message {
      margin: 0;
      font-size: 1.125rem;
      font-weight: 500;
      color: var(--tui-text-01);
      text-align: center;
      max-width: 400px;
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
      height: 8px;
      background: var(--tui-base-03);
      border-radius: 4px;
      overflow: hidden;
      position: relative;
    }

    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, var(--tui-primary), var(--tui-primary-hover));
      border-radius: 4px;
      transition: width 0.3s ease-out;
      position: relative;

      &::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(
          90deg,
          transparent,
          rgba(255, 255, 255, 0.3),
          transparent
        );
        animation: shimmer 1.5s infinite;
      }
    }

    .progress-text {
      font-size: 0.875rem;
      font-weight: 600;
      color: var(--tui-text-02);
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
        transform: scale(0.9);
        opacity: 0;
      }
      to {
        transform: scale(1);
        opacity: 1;
      }
    }

    @keyframes shimmer {
      0% {
        transform: translateX(-100%);
      }
      100% {
        transform: translateX(100%);
      }
    }

    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
      .loading-backdrop {
        background: rgba(0, 0, 0, 0.7);
      }

      .loading-content {
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
      }
    }
  `],
})
export class LoadingOverlayComponent {
  loadingService = inject(LoadingService);
}
