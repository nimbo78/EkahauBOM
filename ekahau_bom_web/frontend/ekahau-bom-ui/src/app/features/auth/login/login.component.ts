import { Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
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
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
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
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  private authService = inject(AuthService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  loginForm = new FormGroup({
    username: new FormControl('', [Validators.required]),
    password: new FormControl('', [Validators.required]),
  });

  error = signal<string | null>(null);
  loading = signal<boolean>(false);

  onSubmit(): void {
    if (this.loginForm.invalid) {
      return;
    }

    const { username, password } = this.loginForm.value;
    if (!username || !password) {
      return;
    }

    this.loading.set(true);
    this.error.set(null);

    this.authService.login(username, password).subscribe({
      next: () => {
        // Get returnUrl from query params or default to /projects
        const returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/projects';
        this.router.navigate([returnUrl]);
      },
      error: (err) => {
        this.loading.set(false);
        if (err.status === 401) {
          this.error.set('Invalid username or password');
        } else {
          this.error.set('Login failed. Please try again.');
        }
      },
    });
  }
}
