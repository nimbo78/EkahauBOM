import { TestBed } from '@angular/core/testing';
import { Router, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { shortLinkGuard } from './short-link.guard';

describe('shortLinkGuard', () => {
  let routerSpy: jasmine.SpyObj<Router>;
  let mockRoute: ActivatedRouteSnapshot;
  let mockState: RouterStateSnapshot;

  beforeEach(() => {
    // Clear sessionStorage before each test
    sessionStorage.clear();

    // Create router spy
    const routerSpyObj = jasmine.createSpyObj('Router', ['navigate']);

    TestBed.configureTestingModule({
      providers: [{ provide: Router, useValue: routerSpyObj }],
    });

    routerSpy = TestBed.inject(Router) as jasmine.SpyObj<Router>;

    // Mock route and state
    mockRoute = {} as ActivatedRouteSnapshot;
    mockState = { url: '/projects' } as RouterStateSnapshot;
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  it('should allow access when not in short link mode', () => {
    // No short_link_mode in sessionStorage

    const result = TestBed.runInInjectionContext(() =>
      shortLinkGuard(mockRoute, mockState)
    );

    expect(result).toBe(true);
    expect(routerSpy.navigate).not.toHaveBeenCalled();
  });

  it('should deny access when in short link mode', () => {
    // Set short link mode
    sessionStorage.setItem('short_link_mode', 'true');

    const result = TestBed.runInInjectionContext(() =>
      shortLinkGuard(mockRoute, mockState)
    );

    expect(result).toBe(false);
  });

  it('should redirect to /forbidden when in short link mode', () => {
    // Set short link mode
    sessionStorage.setItem('short_link_mode', 'true');

    TestBed.runInInjectionContext(() => shortLinkGuard(mockRoute, mockState));

    expect(routerSpy.navigate).toHaveBeenCalledWith(['/forbidden']);
  });

  it('should allow access when short_link_mode is false', () => {
    // Set short link mode to false (not 'true')
    sessionStorage.setItem('short_link_mode', 'false');

    const result = TestBed.runInInjectionContext(() =>
      shortLinkGuard(mockRoute, mockState)
    );

    expect(result).toBe(true);
    expect(routerSpy.navigate).not.toHaveBeenCalled();
  });

  it('should allow access when short_link_mode is empty string', () => {
    // Set short link mode to empty string
    sessionStorage.setItem('short_link_mode', '');

    const result = TestBed.runInInjectionContext(() =>
      shortLinkGuard(mockRoute, mockState)
    );

    expect(result).toBe(true);
    expect(routerSpy.navigate).not.toHaveBeenCalled();
  });

  it('should block access to projects list when in short link mode', () => {
    sessionStorage.setItem('short_link_mode', 'true');
    mockState = { url: '/projects' } as RouterStateSnapshot;

    const result = TestBed.runInInjectionContext(() =>
      shortLinkGuard(mockRoute, mockState)
    );

    expect(result).toBe(false);
    expect(routerSpy.navigate).toHaveBeenCalledWith(['/forbidden']);
  });

  it('should block access to admin routes when in short link mode', () => {
    sessionStorage.setItem('short_link_mode', 'true');
    mockState = { url: '/admin/upload' } as RouterStateSnapshot;

    const result = TestBed.runInInjectionContext(() =>
      shortLinkGuard(mockRoute, mockState)
    );

    expect(result).toBe(false);
    expect(routerSpy.navigate).toHaveBeenCalledWith(['/forbidden']);
  });
});
