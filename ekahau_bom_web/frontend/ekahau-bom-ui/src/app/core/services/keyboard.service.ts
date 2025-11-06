import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from './auth.service';

/**
 * Global keyboard shortcuts service.
 * Handles application-wide keyboard shortcuts for power users.
 */
@Injectable({ providedIn: 'root' })
export class KeyboardService {
  private router = inject(Router);
  private authService = inject(AuthService);

  // Track if search input is focused to avoid conflicts
  private searchFocused = false;

  constructor() {
    this.initializeGlobalShortcuts();
  }

  /**
   * Initialize global keyboard event listeners
   */
  private initializeGlobalShortcuts(): void {
    window.addEventListener('keydown', (event: KeyboardEvent) => {
      this.handleGlobalKeydown(event);
    });
  }

  /**
   * Handle global keydown events
   */
  private handleGlobalKeydown(event: KeyboardEvent): void {
    // Get the target element
    const target = event.target as HTMLElement;
    const isInputField = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;

    // Alt + U: Navigate to /admin/upload (admin only)
    if (event.altKey && event.key === 'u') {
      if (this.authService.isAuthenticated()) {
        event.preventDefault();
        this.router.navigate(['/admin/upload']);
      }
      return;
    }

    // Ctrl/Cmd + K: Focus search input (projects list)
    if (this.isCtrlOrCmd(event) && event.key === 'k') {
      event.preventDefault();
      this.focusSearchInput();
      return;
    }

    // Escape: Clear search or unfocus
    if (event.key === 'Escape') {
      if (isInputField) {
        // Unfocus the input field
        target.blur();
      } else {
        // Clear search if we're on projects list
        this.clearSearch();
      }
      return;
    }

    // / (slash): Focus search (like GitHub) - only if not in input field
    if (event.key === '/' && !isInputField) {
      event.preventDefault();
      this.focusSearchInput();
      return;
    }
  }

  /**
   * Check if Ctrl (Windows/Linux) or Cmd (Mac) key is pressed
   */
  private isCtrlOrCmd(event: KeyboardEvent): boolean {
    return event.ctrlKey || event.metaKey;
  }

  /**
   * Focus the search input on projects list page
   */
  private focusSearchInput(): void {
    const searchInput = document.querySelector('input[type="text"][placeholder*="Search"]') as HTMLInputElement;
    if (searchInput) {
      searchInput.focus();
      searchInput.select();
      this.searchFocused = true;
    }
  }

  /**
   * Clear search input value
   */
  private clearSearch(): void {
    const searchInput = document.querySelector('input[type="text"][placeholder*="Search"]') as HTMLInputElement;
    if (searchInput && searchInput.value) {
      searchInput.value = '';
      // Trigger input event to notify Angular of the change
      searchInput.dispatchEvent(new Event('input', { bubbles: true }));
      this.searchFocused = false;
    }
  }

  /**
   * Register a custom keyboard shortcut handler
   * Can be used by components for component-specific shortcuts
   */
  registerShortcut(
    key: string,
    handler: (event: KeyboardEvent) => void,
    options?: { ctrl?: boolean; shift?: boolean; alt?: boolean }
  ): () => void {
    const listener = (event: KeyboardEvent) => {
      const ctrlMatch = options?.ctrl ? this.isCtrlOrCmd(event) : !event.ctrlKey && !event.metaKey;
      const shiftMatch = options?.shift ? event.shiftKey : !event.shiftKey;
      const altMatch = options?.alt ? event.altKey : !event.altKey;

      if (event.key === key && ctrlMatch && shiftMatch && altMatch) {
        handler(event);
      }
    };

    window.addEventListener('keydown', listener);

    // Return unregister function
    return () => {
      window.removeEventListener('keydown', listener);
    };
  }
}
