import { Injectable, signal, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

interface LoginRequest {
  username: string;
  password: string;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  private readonly TOKEN_KEY = 'access_token'; // Унифицировано с interceptor

  isAuthenticated = signal<boolean>(false);

  constructor() {
    // Check if token exists AND is valid on init
    this.isAuthenticated.set(this.isTokenValid());
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
