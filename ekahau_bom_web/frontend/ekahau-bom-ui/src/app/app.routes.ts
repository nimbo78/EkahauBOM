import { Routes } from '@angular/router';
import { adminGuard } from './core/guards/admin.guard';
import { shortLinkGuard } from './core/guards/short-link.guard';
import { enableShortLinkModeGuard } from './core/guards/enable-short-link-mode.guard';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/projects',
    pathMatch: 'full',
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./features/auth/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'forbidden',
    loadComponent: () =>
      import('./features/auth/forbidden/forbidden.component').then(
        (m) => m.ForbiddenComponent
      ),
  },
  {
    path: 'projects',
    canActivate: [shortLinkGuard],
    loadComponent: () =>
      import('./features/projects/list/projects-list.component').then(
        (m) => m.ProjectsListComponent
      ),
  },
  {
    path: 'projects/:id',
    loadComponent: () =>
      import('./features/projects/detail/project-detail.component').then(
        (m) => m.ProjectDetailComponent
      ),
  },
  {
    path: 'reports/view/:projectId',
    loadComponent: () =>
      import('./features/reports/report-viewer-page/report-viewer-page.component').then(
        (m) => m.ReportViewerPageComponent
      ),
  },
  {
    path: 'admin',
    canActivate: [adminGuard, shortLinkGuard],
    children: [
      {
        path: 'upload',
        loadComponent: () =>
          import('./features/admin/upload/upload.component').then(
            (m) => m.UploadComponent
          ),
      },
      {
        path: 'processing',
        loadComponent: () =>
          import('./features/admin/processing/processing.component').then(
            (m) => m.ProcessingComponent
          ),
      },
      {
        path: '',
        redirectTo: 'upload',
        pathMatch: 'full',
      },
    ],
  },
  {
    path: 's/:shortLink',
    canActivate: [enableShortLinkModeGuard],
    loadComponent: () =>
      import('./features/projects/detail/project-detail.component').then(
        (m) => m.ProjectDetailComponent
      ),
  },
  {
    path: '**',
    redirectTo: '/projects',
  },
];
