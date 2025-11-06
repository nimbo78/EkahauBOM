import { Injectable } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';

/**
 * Service for converting HTTP errors to user-friendly messages
 */
@Injectable({
  providedIn: 'root',
})
export class ErrorMessageService {
  /**
   * HTTP status code to user-friendly message mapping
   */
  private readonly statusMessages: Record<number, string> = {
    // Client errors (4xx)
    400: 'Invalid request. Please check your input and try again.',
    401: 'Your session has expired. Please log in again.',
    403: 'You do not have permission to perform this action.',
    404: 'The requested resource was not found. It may have been deleted.',
    408: 'Request timeout. Please check your internet connection and try again.',
    413: 'File is too large. Maximum size is 100 MB.',
    415: 'Unsupported file type. Please upload an .esx file.',
    422: 'Unable to process the file. The file may be corrupted or invalid.',
    429: 'Too many requests. Please wait a moment and try again.',

    // Server errors (5xx)
    500: 'Server error occurred. Please try again later.',
    502: 'Service temporarily unavailable. Please try again in a few moments.',
    503: 'Service is currently under maintenance. Please try again later.',
    504: 'Gateway timeout. The server took too long to respond.',
  };

  /**
   * Special error messages for specific scenarios
   */
  private readonly specialMessages: Record<string, string> = {
    network_error: 'Network error. Please check your internet connection.',
    timeout: 'Request timed out. Please try again.',
    unknown: 'An unexpected error occurred. Please try again.',
    parse_error: 'Unable to parse server response.',
    cors_error: 'Cross-origin request blocked. Please contact support.',
  };

  /**
   * Get user-friendly error message from HttpErrorResponse
   */
  getErrorMessage(error: HttpErrorResponse | Error | string): string {
    // Handle string errors
    if (typeof error === 'string') {
      return error;
    }

    // Handle generic Error objects
    if (!(error instanceof HttpErrorResponse)) {
      return error.message || this.specialMessages['unknown'];
    }

    // Handle network errors (no internet connection)
    if (error.status === 0) {
      return this.specialMessages['network_error'];
    }

    // Check if server provided a custom error message
    if (error.error?.detail) {
      return this.formatServerMessage(error.error.detail);
    }

    if (error.error?.message) {
      return this.formatServerMessage(error.error.message);
    }

    // Use predefined message for status code
    const statusMessage = this.statusMessages[error.status];
    if (statusMessage) {
      return statusMessage;
    }

    // Fallback for unknown errors
    return `Error ${error.status}: ${error.statusText || 'Unknown error'}`;
  }

  /**
   * Format server-provided error messages to be more user-friendly
   */
  private formatServerMessage(message: string): string {
    // Remove technical jargon and format nicely
    return message
      .replace(/^Error:\s*/i, '')
      .replace(/^Exception:\s*/i, '')
      .trim();
  }

  /**
   * Get error message with retry suggestion
   */
  getErrorWithRetry(error: HttpErrorResponse | Error | string): string {
    const message = this.getErrorMessage(error);

    // Add retry suggestion for temporary errors
    if (
      error instanceof HttpErrorResponse &&
      (error.status === 0 ||
        error.status === 408 ||
        error.status === 429 ||
        error.status >= 500)
    ) {
      return `${message}\n\nWould you like to retry?`;
    }

    return message;
  }

  /**
   * Check if error is retryable
   */
  isRetryable(error: HttpErrorResponse | Error): boolean {
    if (!(error instanceof HttpErrorResponse)) {
      return false;
    }

    // Network errors, timeouts, rate limiting, and server errors are retryable
    return (
      error.status === 0 ||
      error.status === 408 ||
      error.status === 429 ||
      error.status >= 500
    );
  }

  /**
   * Get suggestion for fixing the error
   */
  getSuggestion(error: HttpErrorResponse): string | null {
    if (!(error instanceof HttpErrorResponse)) {
      return null;
    }

    const suggestions: Record<number, string> = {
      400: 'Please verify that you uploaded a valid .esx file.',
      401: 'Click here to log in again.',
      403: 'Please contact your administrator for access.',
      404: 'Try refreshing the project list.',
      413: 'Try uploading a smaller project file.',
      415: 'Only .esx files are supported.',
      422: 'Try re-exporting the project from Ekahau ESS.',
      500: 'Our team has been notified and is working on it.',
    };

    const suggestion = suggestions[error.status];
    return suggestion || null;
  }

  /**
   * Log error for debugging (in development mode)
   */
  logError(error: HttpErrorResponse | Error, context?: string): void {
    if (typeof window !== 'undefined' && !window.location.hostname.includes('localhost')) {
      return; // Don't log in production
    }

    console.group(`[ErrorMessageService] ${context || 'Error'}`);
    console.error('Error:', error);

    if (error instanceof HttpErrorResponse) {
      console.log('Status:', error.status);
      console.log('Status Text:', error.statusText);
      console.log('URL:', error.url);
      console.log('Error Body:', error.error);
    }

    console.groupEnd();
  }
}
