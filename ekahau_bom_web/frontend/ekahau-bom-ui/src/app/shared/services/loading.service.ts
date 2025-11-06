import { Injectable, signal, computed } from '@angular/core';

/**
 * Loading state interface
 */
export interface LoadingState {
  isLoading: boolean;
  message: string | null;
  type?: 'default' | 'upload' | 'processing' | 'router';
  progress?: number; // 0-100 for progress bar
}

/**
 * Centralized loading state management service
 *
 * Use this service to show/hide global loading overlays and track
 * loading states across the application.
 *
 * @example
 * ```typescript
 * // Show loading
 * this.loadingService.show('Loading projects...');
 *
 * // Show with progress
 * this.loadingService.show('Uploading file...', 'upload', 45);
 *
 * // Hide loading
 * this.loadingService.hide();
 * ```
 */
@Injectable({
  providedIn: 'root',
})
export class LoadingService {
  /**
   * Internal loading state signal
   */
  private loadingState = signal<LoadingState>({
    isLoading: false,
    message: null,
    type: 'default',
    progress: undefined,
  });

  /**
   * Computed signal - is loading active?
   */
  readonly isLoading = computed(() => this.loadingState().isLoading);

  /**
   * Computed signal - current loading message
   */
  readonly message = computed(() => this.loadingState().message);

  /**
   * Computed signal - loading type
   */
  readonly type = computed(() => this.loadingState().type);

  /**
   * Computed signal - loading progress (0-100)
   */
  readonly progress = computed(() => this.loadingState().progress);

  /**
   * Computed signal - full loading state
   */
  readonly state = computed(() => this.loadingState());

  /**
   * Show loading overlay
   * @param message Loading message to display
   * @param type Type of loading (default, upload, processing, router)
   * @param progress Progress percentage (0-100) for progress bar
   */
  show(
    message: string = 'Loading...',
    type: LoadingState['type'] = 'default',
    progress?: number
  ): void {
    this.loadingState.set({
      isLoading: true,
      message,
      type,
      progress,
    });
  }

  /**
   * Update loading message and/or progress
   * @param message New message (optional)
   * @param progress New progress (optional)
   */
  update(message?: string, progress?: number): void {
    const currentState = this.loadingState();

    if (!currentState.isLoading) {
      return; // Don't update if not loading
    }

    this.loadingState.set({
      ...currentState,
      message: message ?? currentState.message,
      progress: progress ?? currentState.progress,
    });
  }

  /**
   * Update only progress
   * @param progress Progress percentage (0-100)
   */
  setProgress(progress: number): void {
    const currentState = this.loadingState();

    if (!currentState.isLoading) {
      return;
    }

    this.loadingState.set({
      ...currentState,
      progress: Math.min(100, Math.max(0, progress)), // Clamp to 0-100
    });
  }

  /**
   * Hide loading overlay
   */
  hide(): void {
    this.loadingState.set({
      isLoading: false,
      message: null,
      type: 'default',
      progress: undefined,
    });
  }

  /**
   * Reset loading state (same as hide)
   */
  reset(): void {
    this.hide();
  }
}
