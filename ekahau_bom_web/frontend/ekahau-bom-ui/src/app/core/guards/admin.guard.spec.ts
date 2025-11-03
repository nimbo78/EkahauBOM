import { TestBed } from '@angular/core/testing';
import { Router, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { adminGuard } from './admin.guard';
import { AuthService } from '../services/auth.service';
import { signal } from '@angular/core';

describe('adminGuard', () => {
  let authServiceSpy: jasmine.SpyObj<AuthService>;
  let routerSpy: jasmine.SpyObj<Router>;
  let mockRoute: ActivatedRouteSnapshot;
  let mockState: RouterStateSnapshot;

  beforeEach(() => {
    // Create spies
    const authSpy = jasmine.createSpyObj(
      'AuthService',
      ['login', 'logout', 'getToken'],
      {
        isAuthenticated: signal(false),
      }
    );
    const routerSpyObj = jasmine.createSpyObj('Router', ['navigate']);

    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: authSpy },
        { provide: Router, useValue: routerSpyObj },
      ],
    });

    authServiceSpy = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
    routerSpy = TestBed.inject(Router) as jasmine.SpyObj<Router>;

    // Mock route and state
    mockRoute = {} as ActivatedRouteSnapshot;
    mockState = { url: '/admin/upload' } as RouterStateSnapshot;
  });

  it('should allow access when user is authenticated', () => {
    // Set authenticated state
    authServiceSpy.isAuthenticated.set(true);

    const result = TestBed.runInInjectionContext(() =>
      adminGuard(mockRoute, mockState)
    );

    expect(result).toBe(true);
    expect(routerSpy.navigate).not.toHaveBeenCalled();
  });

  it('should deny access when user is not authenticated', () => {
    // Set unauthenticated state
    authServiceSpy.isAuthenticated.set(false);

    const result = TestBed.runInInjectionContext(() =>
      adminGuard(mockRoute, mockState)
    );

    expect(result).toBe(false);
  });

  it('should redirect to /login when user is not authenticated', () => {
    // Set unauthenticated state
    authServiceSpy.isAuthenticated.set(false);

    TestBed.runInInjectionContext(() => adminGuard(mockRoute, mockState));

    expect(routerSpy.navigate).toHaveBeenCalledWith(['/login'], {
      queryParams: { returnUrl: '/admin/upload' },
    });
  });

  it('should include returnUrl query param with current URL', () => {
    // Set unauthenticated state
    authServiceSpy.isAuthenticated.set(false);
    mockState = { url: '/admin/processing/some-id' } as RouterStateSnapshot;

    TestBed.runInInjectionContext(() => adminGuard(mockRoute, mockState));

    expect(routerSpy.navigate).toHaveBeenCalledWith(['/login'], {
      queryParams: { returnUrl: '/admin/processing/some-id' },
    });
  });

  it('should not redirect when user is authenticated', () => {
    // Set authenticated state
    authServiceSpy.isAuthenticated.set(true);

    TestBed.runInInjectionContext(() => adminGuard(mockRoute, mockState));

    expect(routerSpy.navigate).not.toHaveBeenCalled();
  });
});
