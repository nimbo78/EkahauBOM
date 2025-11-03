import { TestBed } from '@angular/core/testing';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { AuthService } from './auth.service';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;
  let routerSpy: jasmine.SpyObj<Router>;

  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();

    // Create router spy
    const routerSpyObj = jasmine.createSpyObj('Router', ['navigate']);

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: routerSpyObj },
      ],
    });

    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
    routerSpy = TestBed.inject(Router) as jasmine.SpyObj<Router>;
  });

  afterEach(() => {
    // Verify no outstanding HTTP requests
    httpMock.verify();
    localStorage.clear();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('Constructor', () => {
    it('should set isAuthenticated to false when no token in localStorage', () => {
      expect(service.isAuthenticated()).toBe(false);
    });

    it('should set isAuthenticated to true when token exists in localStorage', () => {
      // Reset TestBed to allow reconfiguration
      TestBed.resetTestingModule();

      // Set token before creating service
      localStorage.setItem('admin_token', 'test-token');

      // Create new TestBed instance with fresh AuthService
      TestBed.configureTestingModule({
        providers: [
          AuthService,
          provideHttpClient(),
          provideHttpClientTesting(),
          { provide: Router, useValue: routerSpy },
        ],
      });
      const newService = TestBed.inject(AuthService);

      expect(newService.isAuthenticated()).toBe(true);
    });
  });

  describe('login()', () => {
    it('should send POST request to /api/auth/login with credentials', () => {
      const username = 'admin';
      const password = 'password123';

      service.login(username, password).subscribe();

      const req = httpMock.expectOne('/api/auth/login');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ username, password });

      req.flush({ access_token: 'test-token', token_type: 'bearer' });
    });

    it('should store access token in localStorage on successful login', () => {
      const username = 'admin';
      const password = 'password123';
      const mockResponse = {
        access_token: 'test-jwt-token',
        token_type: 'bearer',
      };

      service.login(username, password).subscribe();

      const req = httpMock.expectOne('/api/auth/login');
      req.flush(mockResponse);

      expect(localStorage.getItem('admin_token')).toBe('test-jwt-token');
    });

    it('should set isAuthenticated to true on successful login', () => {
      const username = 'admin';
      const password = 'password123';
      const mockResponse = {
        access_token: 'test-jwt-token',
        token_type: 'bearer',
      };

      expect(service.isAuthenticated()).toBe(false);

      service.login(username, password).subscribe();

      const req = httpMock.expectOne('/api/auth/login');
      req.flush(mockResponse);

      expect(service.isAuthenticated()).toBe(true);
    });

    it('should return TokenResponse observable', (done) => {
      const username = 'admin';
      const password = 'password123';
      const mockResponse = {
        access_token: 'test-jwt-token',
        token_type: 'bearer',
      };

      service.login(username, password).subscribe((response) => {
        expect(response).toEqual(mockResponse);
        done();
      });

      const req = httpMock.expectOne('/api/auth/login');
      req.flush(mockResponse);
    });

    it('should handle login error', (done) => {
      const username = 'admin';
      const password = 'wrong-password';

      service.login(username, password).subscribe({
        next: () => fail('should have failed'),
        error: (error) => {
          expect(error.status).toBe(401);
          expect(service.isAuthenticated()).toBe(false);
          expect(localStorage.getItem('admin_token')).toBeNull();
          done();
        },
      });

      const req = httpMock.expectOne('/api/auth/login');
      req.flush({ detail: 'Invalid credentials' }, { status: 401, statusText: 'Unauthorized' });
    });
  });

  describe('logout()', () => {
    beforeEach(() => {
      // Set up authenticated state
      localStorage.setItem('admin_token', 'test-token');
      service.isAuthenticated.set(true);
    });

    it('should remove token from localStorage', () => {
      service.logout();

      expect(localStorage.getItem('admin_token')).toBeNull();
    });

    it('should set isAuthenticated to false', () => {
      expect(service.isAuthenticated()).toBe(true);

      service.logout();

      expect(service.isAuthenticated()).toBe(false);
    });

    it('should navigate to /login', () => {
      service.logout();

      expect(routerSpy.navigate).toHaveBeenCalledWith(['/login']);
    });
  });

  describe('getToken()', () => {
    it('should return null when no token exists', () => {
      expect(service.getToken()).toBeNull();
    });

    it('should return token when it exists in localStorage', () => {
      localStorage.setItem('admin_token', 'my-jwt-token');

      expect(service.getToken()).toBe('my-jwt-token');
    });
  });
});
