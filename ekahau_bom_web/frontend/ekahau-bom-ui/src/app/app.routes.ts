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
    path: 'logout',
    loadComponent: () =>
      import('./features/auth/logout/logout.component').then((m) => m.LogoutComponent),
  },
  {
    path: 'auth/callback',
    loadComponent: () =>
      import('./features/auth/auth-callback/auth-callback.component').then(
        (m) => m.AuthCallbackComponent
      ),
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
        path: 'batch-upload',
        loadComponent: () =>
          import('./features/admin/batch-upload/batch-upload.component').then(
            (m) => m.BatchUploadComponent
          ),
      },
      {
        path: 'batches',
        loadComponent: () =>
          import('./features/admin/batch-list/batch-list.component').then(
            (m) => m.BatchListComponent
          ),
      },
      {
        path: 'batches/:id',
        loadComponent: () =>
          import('./features/admin/batch-detail/batch-detail.component').then(
            (m) => m.BatchDetailComponent
          ),
      },
      {
        path: 'templates',
        loadComponent: () =>
          import('./features/admin/template-management/template-management.component').then(
            (m) => m.TemplateManagementComponent
          ),
      },
      {
        path: 'watch-mode',
        loadComponent: () =>
          import('./features/admin/watch-mode/watch-mode.component').then(
            (m) => m.WatchModeComponent
          ),
      },
      {
        path: 'reports',
        loadComponent: () =>
          import('./features/admin/scheduled-reports/scheduled-reports.component').then(
            (m) => m.ScheduledReportsComponent
          ),
      },
      {
        path: 'schedules',
        loadComponent: () =>
          import('./features/admin/schedule-list/schedule-list.component').then(
            (m) => m.ScheduleListComponent
          ),
      },
      {
        path: 'schedule-create',
        loadComponent: () =>
          import('./features/admin/schedule-form/schedule-form.component').then(
            (m) => m.ScheduleFormComponent
          ),
      },
      {
        path: 'schedule-edit/:id',
        loadComponent: () =>
          import('./features/admin/schedule-form/schedule-form.component').then(
            (m) => m.ScheduleFormComponent
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
