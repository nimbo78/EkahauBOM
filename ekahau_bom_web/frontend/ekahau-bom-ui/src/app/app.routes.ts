import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/projects',
    pathMatch: 'full',
  },
  {
    path: 'projects',
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
    path: 'admin',
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
