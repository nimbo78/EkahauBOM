import { Component, OnInit, inject } from '@angular/core';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-logout',
  standalone: true,
  template: `
    <div style="display: flex; align-items: center; justify-content: center; height: 100vh; flex-direction: column; gap: 16px;">
      <h2>Logging out...</h2>
      <p>Redirecting to login page...</p>
    </div>
  `,
  styles: []
})
export class LogoutComponent implements OnInit {
  private authService = inject(AuthService);

  ngOnInit(): void {
    // Call logout which will clear token and redirect to /login
    this.authService.logout();
  }
}
