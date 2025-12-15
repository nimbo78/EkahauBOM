import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { TuiLoader, TuiNotification, TuiButton } from '@taiga-ui/core';
import { TuiCardLarge } from '@taiga-ui/layout';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-auth-callback',
  standalone: true,
  imports: [
    CommonModule,
    TuiLoader,
    TuiNotification,
    TuiButton,
    TuiCardLarge,
  ],
  template: `
    <div class="callback-container">
      <div tuiCardLarge class="callback-card">
        @if (loading()) {
          <tui-loader [showLoader]="true" size="l">
            <p class="loading-text">Authenticating...</p>
          </tui-loader>
        }

        @if (error()) {
          <tui-notification appearance="negative" size="m">
            {{ error() }}
          </tui-notification>
          <button
            tuiButton
            appearance="primary"
            size="m"
            (click)="retryLogin()"
            class="retry-button"
          >
            Try Again
          </button>
        }
      </div>
    </div>
  `,
  styles: [`
    .callback-container {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      background: var(--tui-background-base-alt);
    }

    .callback-card {
      padding: 2rem;
      text-align: center;
      min-width: 300px;
    }

    .loading-text {
      margin-top: 1rem;
      color: var(--tui-text-secondary);
    }

    .retry-button {
      margin-top: 1rem;
    }
  `],
})
export class AuthCallbackComponent implements OnInit {
  private authService = inject(AuthService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  loading = signal(true);
  error = signal<string | null>(null);

  ngOnInit(): void {
    const code = this.route.snapshot.queryParams['code'];
    const state = this.route.snapshot.queryParams['state'];
    const errorParam = this.route.snapshot.queryParams['error'];
    const errorDescription = this.route.snapshot.queryParams['error_description'];

    // Handle IdP error response
    if (errorParam) {
      this.loading.set(false);
      this.error.set(errorDescription || `Authentication failed: ${errorParam}`);
      return;
    }

    // Validate required parameters
    if (!code || !state) {
      this.loading.set(false);
      this.error.set('Missing authentication parameters');
      return;
    }

    // Exchange code for token
    this.authService.handleOAuth2Callback(code, state).subscribe({
      next: () => {
        const returnUrl = this.authService.getOAuth2ReturnUrl();
        this.router.navigate([returnUrl]);
      },
      error: (err) => {
        this.loading.set(false);
        if (err.message === 'Invalid state parameter') {
          this.error.set('Security validation failed. Please try logging in again.');
        } else if (err.status === 401) {
          this.error.set('Authentication failed. Please try again.');
        } else {
          this.error.set('Login failed. Please try again.');
        }
      },
    });
  }

  retryLogin(): void {
    this.router.navigate(['/login']);
  }
}
