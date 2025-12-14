import { Injectable, signal, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap, map, of, catchError } from 'rxjs';

interface LoginRequest {
  username: string;
  password: string;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
}

interface AuthInfo {
  auth_backend: 'simple' | 'oauth2';
  oauth2_enabled: boolean;
  simple_enabled: boolean;
}

interface OAuth2LoginUrl {
  login_url: string;
  state: string;
}

interface OAuth2CallbackRequest {
  code: string;
  state: string;
  redirect_uri: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  private readonly TOKEN_KEY = 'access_token';
  private readonly OAUTH2_STATE_KEY = 'oauth2_state';
  private readonly OAUTH2_RETURN_URL_KEY = 'oauth2_return_url';

  isAuthenticated = signal<boolean>(false);
  authBackend = signal<'simple' | 'oauth2'>('simple');
  authInfoLoaded = signal<boolean>(false);

  constructor() {
    // Check if token exists AND is valid on init
    this.isAuthenticated.set(this.isTokenValid());
  }

  /**
   * Get authentication backend info from server
   */
  getAuthInfo(): Observable<AuthInfo> {
    return this.http.get<AuthInfo>('/api/auth/info').pipe(
      tap((info) => {
        this.authBackend.set(info.auth_backend);
        this.authInfoLoaded.set(true);
      }),
      catchError(() => {
        // Default to simple auth on error
        this.authBackend.set('simple');
        this.authInfoLoaded.set(true);
        return of({ auth_backend: 'simple', oauth2_enabled: false, simple_enabled: true } as AuthInfo);
      })
    );
  }

  /**
   * Get OAuth2 login URL and redirect to IdP
   */
  getOAuth2LoginUrl(returnUrl: string = '/projects'): Observable<OAuth2LoginUrl> {
    const redirectUri = `${window.location.origin}/auth/callback`;
    return this.http.get<OAuth2LoginUrl>('/api/auth/oauth2/login', {
      params: { redirect_uri: redirectUri }
    }).pipe(
      tap((response) => {
        // Store state and return URL for callback verification
        localStorage.setItem(this.OAUTH2_STATE_KEY, response.state);
        localStorage.setItem(this.OAUTH2_RETURN_URL_KEY, returnUrl);
      })
    );
  }

  /**
   * Redirect to OAuth2 login
   */
  redirectToOAuth2Login(returnUrl: string = '/projects'): void {
    this.getOAuth2LoginUrl(returnUrl).subscribe({
      next: (response) => {
        window.location.href = response.login_url;
      },
      error: (err) => {
        console.error('Failed to get OAuth2 login URL:', err);
      }
    });
  }

  /**
   * Handle OAuth2 callback - exchange code for token
   */
  handleOAuth2Callback(code: string, state: string): Observable<TokenResponse> {
    const storedState = localStorage.getItem(this.OAUTH2_STATE_KEY);
    const redirectUri = `${window.location.origin}/auth/callback`;

    // Verify state to prevent CSRF
    if (state !== storedState) {
      throw new Error('Invalid state parameter');
    }

    return this.http.post<TokenResponse>('/api/auth/oauth2/callback', {
      code,
      state,
      redirect_uri: redirectUri
    }).pipe(
      tap((response) => {
        localStorage.setItem(this.TOKEN_KEY, response.access_token);
        localStorage.removeItem(this.OAUTH2_STATE_KEY);
        this.isAuthenticated.set(true);
      })
    );
  }

  /**
   * Get stored return URL for post-login redirect
   */
  getOAuth2ReturnUrl(): string {
    const url = localStorage.getItem(this.OAUTH2_RETURN_URL_KEY) || '/projects';
    localStorage.removeItem(this.OAUTH2_RETURN_URL_KEY);
    return url;
  }

  login(username: string, password: string): Observable<TokenResponse> {
    return this.http
      .post<TokenResponse>('/api/auth/login', { username, password })
      .pipe(
        tap((response) => {
          localStorage.setItem(this.TOKEN_KEY, response.access_token);
          this.isAuthenticated.set(true);
        })
      );
  }

  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    this.isAuthenticated.set(false);
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  /**
   * Check if token exists and is not expired
   */
  isTokenValid(): boolean {
    const token = this.getToken();
    if (!token) {
      return false;
    }

    try {
      // Decode JWT to check expiration
      const payload = this.decodeToken(token);
      if (!payload || !payload.exp) {
        return false;
      }

      // Check if token is expired (exp is in seconds, Date.now() is in milliseconds)
      const expirationTime = payload.exp * 1000;
      const currentTime = Date.now();

      if (currentTime >= expirationTime) {
        // Token expired, clear it
        localStorage.removeItem(this.TOKEN_KEY);
        this.isAuthenticated.set(false);
        return false;
      }

      return true;
    } catch (error) {
      // Invalid token format
      console.error('Error decoding token:', error);
      localStorage.removeItem(this.TOKEN_KEY);
      this.isAuthenticated.set(false);
      return false;
    }
  }

  /**
   * Decode JWT token payload (without verification - backend handles that)
   */
  private decodeToken(token: string): any {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) {
        return null;
      }

      const payload = parts[1];
      // Decode base64url to base64
      const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
      const decoded = atob(base64);
      return JSON.parse(decoded);
    } catch (error) {
      return null;
    }
  }
}
