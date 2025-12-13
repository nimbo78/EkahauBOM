import { Injectable, inject } from '@angular/core';
import { Router, NavigationStart, NavigationEnd, NavigationCancel, NavigationError } from '@angular/router';
import { filter } from 'rxjs/operators';
import { LoadingService } from '../../shared/services/loading.service';

/**
 * Router Loading Service
 *
 * Automatically shows loading overlay during route transitions
 * Features:
 * - Shows loading on NavigationStart
 * - Hides loading on NavigationEnd/NavigationCancel/NavigationError
 * - Debounced to avoid flash for fast navigations
 */
@Injectable({
  providedIn: 'root',
})
export class RouterLoadingService {
  private router = inject(Router);
  private loadingService = inject(LoadingService);
  private loadingTimeout: ReturnType<typeof setTimeout> | null = null;

  /**
   * Initialize router loading tracking
   * Call this from app component's ngOnInit
   */
  init(): void {
    // Show loading on navigation start
    this.router.events
      .pipe(filter((event) => event instanceof NavigationStart))
      .subscribe(() => {
        // Debounce - only show if navigation takes > 1000ms
        this.loadingTimeout = setTimeout(() => {
          this.loadingService.show('Loading page...', 'router');
        }, 1000);
      });

    // Hide loading on navigation end/cancel/error
    this.router.events
      .pipe(
        filter(
          (event) =>
            event instanceof NavigationEnd ||
            event instanceof NavigationCancel ||
            event instanceof NavigationError
        )
      )
      .subscribe(() => {
        // Clear timeout if it hasn't fired yet
        if (this.loadingTimeout) {
          clearTimeout(this.loadingTimeout);
          this.loadingTimeout = null;
        }

        // Hide loading
        this.loadingService.hide();
      });
  }
}
