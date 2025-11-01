import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { TuiRoot, TuiIcon } from '@taiga-ui/core';
import { CommonModule } from '@angular/common';

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
        <header class="app-header">
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
export class App {
  title = 'Ekahau BOM Registry';
}
