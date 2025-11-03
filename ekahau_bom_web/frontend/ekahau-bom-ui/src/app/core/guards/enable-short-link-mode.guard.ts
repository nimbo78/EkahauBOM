import { CanActivateFn } from '@angular/router';

/**
 * Guard to enable short link mode before component loads.
 * This ensures the app component hides navigation before rendering.
 */
export const enableShortLinkModeGuard: CanActivateFn = () => {
  // Set short link mode in session storage
  sessionStorage.setItem('short_link_mode', 'true');
  return true;
};
