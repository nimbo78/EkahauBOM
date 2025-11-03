import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const adminGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  // Check token validity (not just existence) - проверяет expiration
  if (authService.isTokenValid()) {
    // Update signal to reflect valid authentication
    authService.isAuthenticated.set(true);
    return true;
  }

  // Token is invalid or expired - redirect to login page
  authService.isAuthenticated.set(false);
  router.navigate(['/login'], { queryParams: { returnUrl: state.url } });
  return false;
};
