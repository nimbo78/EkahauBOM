import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { finalize } from 'rxjs/operators';
import { LoadingService } from '../../shared/services/loading.service';

/**
 * HTTP Loading Interceptor
 *
 * Automatically shows loading overlay for HTTP requests
 * Features:
 * - Debounced loading (only shows for requests > 500ms)
 * - Multiple request tracking (only hides when ALL complete)
 * - Excludes polling/status endpoints
 * - Handles errors gracefully
 */

// Track active requests
let activeRequests = 0;
let loadingTimeout: ReturnType<typeof setTimeout> | null = null;

/**
 * Endpoints to exclude from auto-loading
 * (polling, status checks, etc.)
 */
const EXCLUDED_ENDPOINTS = [
  '/api/processing/status',  // Polling endpoint
  '/api/health',             // Health checks
];

/**
 * Check if URL should show loading
 */
function shouldShowLoading(url: string): boolean {
  return !EXCLUDED_ENDPOINTS.some(excluded => url.includes(excluded));
}

export const loadingInterceptor: HttpInterceptorFn = (req, next) => {
  const loadingService = inject(LoadingService);

  // Skip loading for excluded endpoints
  if (!shouldShowLoading(req.url)) {
    return next(req);
  }

  // Increment active requests
  activeRequests++;

  // Debounce loading - only show if request takes > 500ms
  if (activeRequests === 1) {
    loadingTimeout = setTimeout(() => {
      if (activeRequests > 0) {
        loadingService.show('Loading...', 'default');
      }
    }, 500);
  }

  return next(req).pipe(
    finalize(() => {
      // Decrement active requests
      activeRequests--;

      // Hide loading only when ALL requests are done
      if (activeRequests === 0) {
        // Clear timeout if it hasn't fired yet
        if (loadingTimeout) {
          clearTimeout(loadingTimeout);
          loadingTimeout = null;
        }

        // Hide loading
        loadingService.hide();
      }
    })
  );
};
