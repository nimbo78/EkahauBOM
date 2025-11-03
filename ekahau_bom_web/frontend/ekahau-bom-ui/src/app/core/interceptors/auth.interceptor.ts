import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const token = localStorage.getItem('access_token');

  // Add Authorization header if token exists
  if (token) {
    req = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  return next(req).pipe(
    catchError((error) => {
      // Handle 401 Unauthorized - token expired or invalid
      if (error.status === 401) {
        // Clear token
        localStorage.removeItem('access_token');

        // Redirect to login with returnUrl
        const currentUrl = router.url;
        router.navigate(['/login'], {
          queryParams: { returnUrl: currentUrl },
        });
      }

      return throwError(() => error);
    })
  );
};
