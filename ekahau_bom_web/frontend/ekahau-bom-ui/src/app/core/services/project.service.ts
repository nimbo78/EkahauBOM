import { Injectable, signal } from '@angular/core';
import { BehaviorSubject, Observable, timer, of } from 'rxjs';
import { switchMap, tap, catchError } from 'rxjs/operators';
import { ApiService } from './api.service';
import {
  ProjectListItem,
  ProjectMetadata,
  ProcessingStatus,
  ProjectStats,
} from '../models/project.model';

@Injectable({
  providedIn: 'root',
})
export class ProjectService {
  // Reactive signals for state management
  private projectsSubject = new BehaviorSubject<ProjectListItem[]>([]);
  public projects$ = this.projectsSubject.asObservable();

  private loadingSubject = new BehaviorSubject<boolean>(false);
  public loading$ = this.loadingSubject.asObservable();

  private errorSubject = new BehaviorSubject<string | null>(null);
  public error$ = this.errorSubject.asObservable();

  private statsSubject = new BehaviorSubject<ProjectStats | null>(null);
  public stats$ = this.statsSubject.asObservable();

  // Polling for processing status updates
  private pollingInterval = 5000; // 5 seconds
  private pollingSubscription: any;

  constructor(private apiService: ApiService) {}

  loadProjects(
    status?: ProcessingStatus,
    search?: string
  ): Observable<ProjectListItem[]> {
    this.loadingSubject.next(true);
    this.errorSubject.next(null);

    return this.apiService.listProjects(status, undefined, search).pipe(
      tap((projects) => {
        this.projectsSubject.next(projects);
        this.loadingSubject.next(false);
      }),
      catchError((error) => {
        this.errorSubject.next('Failed to load projects');
        this.loadingSubject.next(false);
        return of([]);
      })
    );
  }

  loadProjectStats(): Observable<ProjectStats> {
    return this.apiService.getProjectStats().pipe(
      tap((stats) => this.statsSubject.next(stats)),
      catchError((error) => {
        console.error('Failed to load stats:', error);
        return of({
          total: 0,
          pending: 0,
          processing: 0,
          completed: 0,
          failed: 0,
        });
      })
    );
  }

  startPollingProjects(): void {
    this.stopPollingProjects();
    this.pollingSubscription = timer(0, this.pollingInterval)
      .pipe(
        switchMap(() => this.loadProjects()),
        switchMap(() => this.loadProjectStats())
      )
      .subscribe();
  }

  stopPollingProjects(): void {
    if (this.pollingSubscription) {
      this.pollingSubscription.unsubscribe();
    }
  }

  getProcessingProjects(): ProjectListItem[] {
    const projects = this.projectsSubject.value;
    return projects.filter(
      (p) => p.processing_status === ProcessingStatus.PROCESSING
    );
  }

  hasProcessingProjects(): boolean {
    return this.getProcessingProjects().length > 0;
  }

  clearError(): void {
    this.errorSubject.next(null);
  }
}
