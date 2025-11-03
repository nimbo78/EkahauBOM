import { Component, signal, OnInit } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, NavigationEnd, Router } from '@angular/router';
import { TuiRoot, TuiIcon } from '@taiga-ui/core';
import { CommonModule } from '@angular/common';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  imports: [
    CommonModule,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    TuiRoot,
    TuiIcon,
  ],
  template: `
    <tui-root>
      <div class="app-container">
        <header *ngIf="shouldShowHeader()" class="app-header">
          <div class="header-content">
            <div class="logo-section">
              <tui-icon icon="@tui.database" class="logo-icon"></tui-icon>
              <h1 class="app-title">Ekahau BOM Registry</h1>
            </div>
            <nav class="nav-menu">
              <a
                routerLink="/projects"
                routerLinkActive="active"
                class="nav-link"
              >
                <tui-icon icon="@tui.folder"></tui-icon>
                Projects
              </a>
              <a
                routerLink="/admin/upload"
                routerLinkActive="active"
                class="nav-link"
              >
                <tui-icon icon="@tui.upload"></tui-icon>
                Upload
              </a>
              <a
                routerLink="/admin/processing"
                routerLinkActive="active"
                class="nav-link"
              >
                <tui-icon icon="@tui.settings"></tui-icon>
                Processing
              </a>
            </nav>
          </div>
        </header>
        <main class="app-content">
          <router-outlet />
        </main>
      </div>
    </tui-root>
  `,
  styleUrl: './app.scss'
})
export class App implements OnInit {
  title = 'Ekahau BOM Registry';
  isShortLinkMode = signal(false);

  constructor(private router: Router) {}

  ngOnInit(): void {
    // Check short link mode on init
    this.checkShortLinkMode();

    // Check on every navigation
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe(() => {
        this.checkShortLinkMode();
      });
  }

  private checkShortLinkMode(): void {
    const isShortLink = sessionStorage.getItem('short_link_mode') === 'true';
    this.isShortLinkMode.set(isShortLink);
  }

  shouldShowHeader(): boolean {
    // Don't show header in short link mode
    if (this.isShortLinkMode()) {
      return false;
    }

    // Don't show header on login page
    if (this.router.url === '/login') {
      return false;
    }

    return true;
  }
}
