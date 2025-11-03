import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { ReactiveFormsModule } from '@angular/forms';
import { of, throwError } from 'rxjs';
import { LoginComponent } from './login.component';
import { AuthService } from '../../../core/services/auth.service';
import {
  TuiButton,
  TuiTextfield,
  TuiIcon,
  TuiNotification,
  TuiLoader,
  TuiLabel,
  TuiTitle,
  TuiAppearance,
} from '@taiga-ui/core';
import { TuiPassword } from '@taiga-ui/kit';
import { TuiCardLarge, TuiHeader } from '@taiga-ui/layout';

describe('LoginComponent', () => {
  let component: LoginComponent;
  let fixture: ComponentFixture<LoginComponent>;
  let mockAuthService: jasmine.SpyObj<AuthService>;
  let router: Router;
  let activatedRoute: ActivatedRoute;

  beforeEach(async () => {
    mockAuthService = jasmine.createSpyObj('AuthService', ['login']);

    await TestBed.configureTestingModule({
      imports: [
        LoginComponent,
        ReactiveFormsModule,
        RouterTestingModule.withRoutes([]),
        TuiButton,
        TuiTextfield,
        TuiIcon,
        TuiNotification,
        TuiLoader,
        TuiLabel,
        TuiTitle,
        TuiAppearance,
        TuiPassword,
        TuiCardLarge,
        TuiHeader,
      ],
      providers: [
        { provide: AuthService, useValue: mockAuthService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    activatedRoute = TestBed.inject(ActivatedRoute);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('Form Initialization', () => {
    it('should initialize login form with empty fields', () => {
      expect(component.loginForm).toBeDefined();
      expect(component.loginForm.get('username')?.value).toBe('');
      expect(component.loginForm.get('password')?.value).toBe('');
    });

    it('should have required validators on username', () => {
      const usernameControl = component.loginForm.get('username');
      usernameControl?.setValue('');
      expect(usernameControl?.hasError('required')).toBe(true);

      usernameControl?.setValue('admin');
      expect(usernameControl?.hasError('required')).toBe(false);
    });

    it('should have required validators on password', () => {
      const passwordControl = component.loginForm.get('password');
      passwordControl?.setValue('');
      expect(passwordControl?.hasError('required')).toBe(true);

      passwordControl?.setValue('password123');
      expect(passwordControl?.hasError('required')).toBe(false);
    });

    it('should mark form as invalid when fields are empty', () => {
      expect(component.loginForm.valid).toBe(false);
    });

    it('should mark form as valid when both fields are filled', () => {
      component.loginForm.patchValue({
        username: 'admin',
        password: 'password123',
      });
      expect(component.loginForm.valid).toBe(true);
    });
  });

  describe('Form Submission', () => {
    it('should not submit when form is invalid', () => {
      component.loginForm.patchValue({
        username: '',
        password: '',
      });

      component.onSubmit();

      expect(mockAuthService.login).not.toHaveBeenCalled();
    });

    it('should not submit when username is missing', () => {
      component.loginForm.patchValue({
        username: '',
        password: 'password123',
      });

      component.onSubmit();

      expect(mockAuthService.login).not.toHaveBeenCalled();
    });

    it('should not submit when password is missing', () => {
      component.loginForm.patchValue({
        username: 'admin',
        password: '',
      });

      component.onSubmit();

      expect(mockAuthService.login).not.toHaveBeenCalled();
    });

    it('should call AuthService.login when form is valid', () => {
      mockAuthService.login.and.returnValue(of({ access_token: 'test-token', token_type: 'Bearer' }));
      component.loginForm.patchValue({
        username: 'admin',
        password: 'password123',
      });

      component.onSubmit();

      expect(mockAuthService.login).toHaveBeenCalledWith('admin', 'password123');
    });

    it('should set loading to true during login', () => {
      mockAuthService.login.and.returnValue(of({ access_token: 'test-token', token_type: 'Bearer' }));
      component.loginForm.patchValue({
        username: 'admin',
        password: 'password123',
      });

      component.onSubmit();

      expect(component.loading()).toBe(true);
    });

    it('should clear error on submission', () => {
      component.error.set('Previous error');
      mockAuthService.login.and.returnValue(of({ access_token: 'test-token', token_type: 'Bearer' }));
      component.loginForm.patchValue({
        username: 'admin',
        password: 'password123',
      });

      component.onSubmit();

      expect(component.error()).toBeNull();
    });
  });

  describe('Successful Login', () => {
    it('should navigate to /projects after successful login', () => {
      const navigateSpy = spyOn(router, 'navigate');
      mockAuthService.login.and.returnValue(of({ access_token: 'test-token', token_type: 'Bearer' }));
      component.loginForm.patchValue({
        username: 'admin',
        password: 'password123',
      });

      component.onSubmit();

      expect(navigateSpy).toHaveBeenCalledWith(['/projects']);
    });

    it('should navigate to returnUrl if provided', () => {
      const navigateSpy = spyOn(router, 'navigate');
      activatedRoute.snapshot.queryParams['returnUrl'] = '/admin/upload';
      mockAuthService.login.and.returnValue(of({ access_token: 'test-token', token_type: 'Bearer' }));
      component.loginForm.patchValue({
        username: 'admin',
        password: 'password123',
      });

      component.onSubmit();

      expect(navigateSpy).toHaveBeenCalledWith(['/admin/upload']);
    });
  });

  describe('Failed Login', () => {
    it('should show "Invalid username or password" on 401 error', () => {
      const error = { status: 401, message: 'Unauthorized' };
      mockAuthService.login.and.returnValue(throwError(() => error));
      component.loginForm.patchValue({
        username: 'admin',
        password: 'wrong-password',
      });

      component.onSubmit();

      expect(component.error()).toBe('Invalid username or password');
      expect(component.loading()).toBe(false);
    });

    it('should show "Login failed. Please try again." on non-401 error', () => {
      const error = { status: 500, message: 'Internal Server Error' };
      mockAuthService.login.and.returnValue(throwError(() => error));
      component.loginForm.patchValue({
        username: 'admin',
        password: 'password123',
      });

      component.onSubmit();

      expect(component.error()).toBe('Login failed. Please try again.');
      expect(component.loading()).toBe(false);
    });

    it('should show "Login failed. Please try again." on network error', () => {
      const error = { status: 0, message: 'Network Error' };
      mockAuthService.login.and.returnValue(throwError(() => error));
      component.loginForm.patchValue({
        username: 'admin',
        password: 'password123',
      });

      component.onSubmit();

      expect(component.error()).toBe('Login failed. Please try again.');
      expect(component.loading()).toBe(false);
    });
  });

  describe('Signal State Management', () => {
    it('should initialize error signal as null', () => {
      expect(component.error()).toBeNull();
    });

    it('should initialize loading signal as false', () => {
      expect(component.loading()).toBe(false);
    });

    it('should update error signal on failed login', () => {
      const error = { status: 401, message: 'Unauthorized' };
      mockAuthService.login.and.returnValue(throwError(() => error));
      component.loginForm.patchValue({
        username: 'admin',
        password: 'wrong-password',
      });

      component.onSubmit();

      expect(component.error()).toBe('Invalid username or password');
    });
  });
});
