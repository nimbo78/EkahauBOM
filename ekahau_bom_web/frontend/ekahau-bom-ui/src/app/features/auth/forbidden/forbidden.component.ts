import { Component } from '@angular/core';
import { TuiButton } from '@taiga-ui/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-forbidden',
  standalone: true,
  imports: [TuiButton],
  templateUrl: './forbidden.component.html',
  styleUrl: './forbidden.component.scss',
})
export class ForbiddenComponent {
  constructor(private router: Router) {}

  goHome(): void {
    // Clear short link mode if set
    sessionStorage.removeItem('short_link_mode');
    this.router.navigate(['/projects']);
  }
}
