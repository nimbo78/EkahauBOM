import { Component, signal, OnInit, inject } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, NavigationEnd, NavigationStart, Router } from '@angular/router';
import { TuiRoot, TuiIcon } from '@taiga-ui/core';
import { CommonModule } from '@angular/common';
import { filter } from 'rxjs/operators';
import { LoadingOverlayComponent } from './shared/components/loading-overlay.component';
import { RouterLoadingService } from './core/services/router-loading.service';
import { PerformanceService } from './shared/services/performance.service';
import { KeyboardService } from './core/services/keyboard.service';
import { NotificationService } from './core/services/notification.service';

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
              <a
                routerLink="/admin/batch-upload"
                routerLinkActive="active"
                class="nav-link"
              >
                <tui-icon icon="@tui.upload-cloud"></tui-icon>
                Batch Upload
              </a>
              <a
                routerLink="/admin/batches"
                routerLinkActive="active"
                class="nav-link"
              >
                <tui-icon icon="@tui.layers"></tui-icon>
                Batches
              </a>
              <a
                routerLink="/admin/watch-mode"
                routerLinkActive="active"
                class="nav-link"
              >
                <tui-icon icon="@tui.eye"></tui-icon>
                Watch Mode
              </a>
              <a
                routerLink="/admin/reports"
                routerLinkActive="active"
                class="nav-link"
              >
                <tui-icon icon="@tui.bar-chart"></tui-icon>
                Reports
              </a>
            </nav>
          </div>
        </header>

        <!-- Notification Permission Banner -->
        <div *ngIf="showNotificationBanner()" class="notification-banner">
          <div class="banner-content">
            <div class="banner-icon">
              <tui-icon icon="@tui.bell"></tui-icon>
            </div>
            <div class="banner-text">
              <strong>Enable notifications</strong>
              <span>Get notified when batch processing completes</span>
            </div>
            <div class="banner-actions">
              <button class="btn-enable" (click)="requestNotificationPermission()">
                Enable
              </button>
              <button class="btn-dismiss" (click)="dismissNotificationBanner()">
                Not now
              </button>
            </div>
          </div>
        </div>

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
  showNotificationBanner = signal(false);

  private router = inject(Router);
  private routerLoadingService = inject(RouterLoadingService);
  private performanceService = inject(PerformanceService);
  private keyboardService = inject(KeyboardService); // Initialize global keyboard shortcuts
  private notificationService = inject(NotificationService);

  ngOnInit(): void {
    // Measure initial page load performance
    this.performanceService.measureNavigationTiming();

    // Initialize router loading
    this.routerLoadingService.init();

    // Check short link mode on init
    this.checkShortLinkMode();

    // Check if we should show notification permission banner
    this.checkNotificationPermission();

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

  private checkNotificationPermission(): void {
    // Show banner if:
    // 1. Notifications are supported
    // 2. Permission not yet requested
    // 3. Permission not already granted or denied
    if (
      this.notificationService.isSupported() &&
      !this.notificationService.hasRequestedPermission() &&
      Notification.permission === 'default'
    ) {
      // Show banner after a short delay to not overwhelm user on first load
      setTimeout(() => {
        this.showNotificationBanner.set(true);
      }, 2000);
    }
  }

  async requestNotificationPermission(): Promise<void> {
    const granted = await this.notificationService.requestPermission();
    this.showNotificationBanner.set(false);

    if (granted) {
      console.log('[App] Notification permission granted');
      // Show a test notification
      this.notificationService.showSuccess(
        'Notifications enabled!',
        'You will receive notifications when batch processing completes.'
      );
    }
  }

  dismissNotificationBanner(): void {
    this.showNotificationBanner.set(false);
    // Mark as requested so we don't show the banner again this session
    localStorage.setItem('notification_permission_requested', 'true');
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
