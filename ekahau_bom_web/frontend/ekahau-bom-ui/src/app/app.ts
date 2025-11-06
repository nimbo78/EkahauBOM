import { Component, signal, OnInit, inject } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, NavigationEnd, NavigationStart, Router } from '@angular/router';
import { TuiRoot, TuiIcon } from '@taiga-ui/core';
import { CommonModule } from '@angular/common';
import { filter } from 'rxjs/operators';
import { LoadingOverlayComponent } from './shared/components/loading-overlay.component';
import { RouterLoadingService } from './core/services/router-loading.service';
import { PerformanceService } from './shared/services/performance.service';
import { KeyboardService } from './core/services/keyboard.service';

@Component({
  selector: 'app-root',
  imports: [
    CommonModule,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    TuiRoot,
    TuiIcon,
    LoadingOverlayComponent,
  ],
  template: `
    <tui-root>
      <div class="app-container">
        <header *ngIf="shouldShowHeader()" class="app-header">
          <div class="header-content">
            <div class="logo-section">
              <img src="logo.svg" alt="Ekahau BOM" class="logo-icon" width="40" height="40">
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
            </nav>
          </div>
        </header>
        <main class="app-content">
          <router-outlet />
        </main>
      </div>

      <!-- Global Loading Overlay -->
      <app-loading-overlay />
    </tui-root>
  `,
  styleUrl: './app.scss'
})
export class App implements OnInit {
  title = 'Ekahau BOM Registry';
  isShortLinkMode = signal(false);

  private router = inject(Router);
  private routerLoadingService = inject(RouterLoadingService);
  private performanceService = inject(PerformanceService);
  private keyboardService = inject(KeyboardService); // Initialize global keyboard shortcuts

  ngOnInit(): void {
    // Measure initial page load performance
    this.performanceService.measureNavigationTiming();

    // Initialize router loading
    this.routerLoadingService.init();

    // Check short link mode on init
    this.checkShortLinkMode();

    // Track navigation performance
    this.router.events.subscribe((event) => {
      if (event instanceof NavigationStart) {
        this.performanceService.startTimer(`navigation-${event.url}`);
      } else if (event instanceof NavigationEnd) {
        this.performanceService.endTimer(`navigation-${event.url}`);
        this.checkShortLinkMode();
      }
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
