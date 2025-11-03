import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

export const shortLinkGuard: CanActivateFn = (route, state) => {
  const router = inject(Router);
  const isShortLinkMode = sessionStorage.getItem('short_link_mode') === 'true';

  if (isShortLinkMode) {
    // User is in short link mode - block access to projects list and admin
    router.navigate(['/forbidden']);
    return false;
  }

  return true;
};
