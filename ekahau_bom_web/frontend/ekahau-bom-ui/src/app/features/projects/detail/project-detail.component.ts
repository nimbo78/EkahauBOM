import { Component, OnInit, HostListener, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import {
  TuiButton,
  TuiIcon,
  TuiNotification,
  TuiLoader,
  TuiLink
} from '@taiga-ui/core';
import {
  TuiBadge,
  TuiAccordion
} from '@taiga-ui/kit';
import { ApiService } from '../../../core/services/api.service';
import { ProjectService } from '../../../core/services/project.service';
import {
  ProjectDetails,
  ProcessingStatus,
  ReportFile
} from '../../../core/models/project.model';
import { NotesData } from '../../../core/models/notes.model';

@Component({
  selector: 'app-project-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    TuiButton,
    TuiIcon,
    TuiNotification,
    TuiLoader,
    TuiBadge,
    TuiAccordion,
    TuiLink
  ],
  template: `
    <div class="project-detail-container">
      <!-- Header with back button -->
      <div class="page-header">
        <button
          *ngIf="!isShortLinkMode()"
          tuiButton
          appearance="ghost"
          size="s"
          routerLink="/projects"
        >
          <tui-icon icon="@tui.arrow-left"></tui-icon>
          Back to Projects
        </button>
        <div class="header-actions">
          <button
            *ngIf="!isShortLinkMode() && project()?.processing_status === ProcessingStatus.PENDING"
            tuiButton
            appearance="primary"
            size="m"
            [routerLink]="['/admin/processing']"
            [queryParams]="{projectId: projectId}"
          >
            <tui-icon icon="@tui.settings"></tui-icon>
            Configure Processing
          </button>
          <button
            *ngIf="!isShortLinkMode() && project()?.short_link"
            tuiButton
            appearance="outline"
            size="m"
            (click)="copyShortLink()"
          >
            <tui-icon icon="@tui.link"></tui-icon>
            Copy Short Link
          </button>
        </div>
      </div>

      <!-- Loading state -->
      <div *ngIf="loading()" class="loading-state">
        <tui-loader size="l"></tui-loader>
        <p>Loading project details...</p>
      </div>

      <!-- Error state -->
      <tui-notification *ngIf="error()" status="error" class="notification">
        <div class="error-content">
          <h3>Error</h3>
          <p>{{ error() }}</p>
          <button tuiButton size="s" (click)="loadProject()">Retry</button>
        </div>
      </tui-notification>

      <!-- Project content -->
      <div *ngIf="!loading() && !error() && project()" class="project-content">
        <!-- Project header info -->
        <div class="project-header">
          <h1>{{ project()?.project_name || 'Unnamed Project' }}</h1>
          <div class="project-meta">
            <span>File: {{ project()?.filename }}</span>
            <span>•</span>
            <span>Uploaded: {{ formatDate(project()?.upload_date) }}</span>
            <span>•</span>
            <span>APs: {{ project()?.aps_count || 0 }}</span>
            <span>•</span>
            <span>
              <tui-badge
                [appearance]="getStatusAppearance(project()!.processing_status)"
                [class]="'status-badge-' + project()!.processing_status.toLowerCase()"
              >
                {{ project()?.processing_status }}
              </tui-badge>
            </span>
          </div>
        </div>

        <!-- Tabs for different sections -->
        <div class="tabs-section">
          <div class="tab-buttons">
            <div
              class="tab-card"
              [class.active]="activeTab() === 'overview'"
              (click)="setActiveTab('overview')"
            >
              <tui-icon icon="@tui.info" class="tab-icon"></tui-icon>
              <span class="tab-label">Overview</span>
            </div>
            <div
              class="tab-card"
              [class.active]="activeTab() === 'reports'"
              [class.disabled]="project()?.processing_status !== ProcessingStatus.COMPLETED"
              (click)="project()?.processing_status === ProcessingStatus.COMPLETED && setActiveTab('reports')"
            >
              <tui-icon icon="@tui.file-text" class="tab-icon"></tui-icon>
              <span class="tab-label">Reports</span>
            </div>
            <div
              class="tab-card"
              [class.active]="activeTab() === 'visualizations'"
              [class.disabled]="project()?.processing_status !== ProcessingStatus.COMPLETED"
              (click)="project()?.processing_status === ProcessingStatus.COMPLETED && setActiveTab('visualizations')"
            >
              <tui-icon icon="@tui.image" class="tab-icon"></tui-icon>
              <span class="tab-label">Visualizations</span>
            </div>
            <div
              class="tab-card"
              [class.active]="activeTab() === 'notes'"
              [class.disabled]="project()?.processing_status !== ProcessingStatus.COMPLETED"
              (click)="project()?.processing_status === ProcessingStatus.COMPLETED && setActiveTab('notes')"
            >
              <tui-icon icon="@tui.message-circle" class="tab-icon"></tui-icon>
              <span class="tab-label">Notes</span>
            </div>
          </div>

          <div class="tab-content">
            <!-- Overview Tab -->
            <div *ngIf="activeTab() === 'overview'" class="overview-tab">
              <div class="info-cards">
                <div class="info-card">
                  <h3>Processing Information</h3>
                  <div class="info-item">
                    <span class="label">Status:</span>
                    <span class="value">
                      <tui-badge
                        [appearance]="getStatusAppearance(project()!.processing_status)"
                        [class]="'status-badge-' + project()!.processing_status.toLowerCase()"
                      >
                        {{ project()?.processing_status }}
                      </tui-badge>
                    </span>
                  </div>
                  <div class="info-item" *ngIf="project()?.processed_date">
                    <span class="label">Processed:</span>
                    <span class="value">{{ formatDate(project()?.processed_date) }}</span>
                  </div>
                  <div class="info-item" *ngIf="project()?.short_link">
                    <span class="label">Short Link:</span>
                    <span class="value">
                      <a tuiLink [href]="getShortLinkUrl()" target="_blank">
                        {{ project()?.short_link }}
                      </a>
                    </span>
                  </div>
                  <div class="info-item" *ngIf="project()?.short_link_expires">
                    <span class="label">Expires:</span>
                    <span class="value">{{ formatDate(project()?.short_link_expires) }}</span>
                  </div>
                </div>

                <div class="info-card">
                  <h3>Project Details</h3>
                  <div class="info-item" *ngIf="project()?.customer">
                    <span class="label">Customer:</span>
                    <span class="value">{{ project()?.customer }}</span>
                  </div>
                  <div class="info-item" *ngIf="project()?.location">
                    <span class="label">Location:</span>
                    <span class="value">{{ project()?.location }}</span>
                  </div>
                  <div class="info-item" *ngIf="project()?.responsible_person">
                    <span class="label">Responsible:</span>
                    <span class="value">{{ project()?.responsible_person }}</span>
                  </div>
                  <div class="info-item">
                    <span class="label">Access Points:</span>
                    <span class="value">{{ project()?.aps_count || 0 }}</span>
                  </div>
                  <div class="info-item" *ngIf="project()?.total_antennas">
                    <span class="label">Antennas:</span>
                    <span class="value">{{ project()?.total_antennas }}</span>
                  </div>
                  <div class="info-item" *ngIf="project()?.vendors?.length">
                    <span class="label">Vendors:</span>
                    <span class="value">
                      <span class="badges-container">
                        <tui-badge *ngFor="let vendor of project()?.vendors" appearance="info">
                          {{ vendor }}
                        </tui-badge>
                      </span>
                    </span>
                  </div>
                  <div class="info-item" *ngIf="project()?.floors_count">
                    <span class="label">Floors:</span>
                    <span class="value">{{ project()?.floors_count }}</span>
                  </div>
                  <div class="info-item" *ngIf="project()?.floors && (project()?.floors?.length ?? 0) > 0 && (project()?.floors?.length ?? 0) <= 5">
                    <span class="label"></span>
                    <span class="value">
                      <span *ngFor="let floor of project()?.floors; let last = last">
                        {{ floor }}<span *ngIf="!last">, </span>
                      </span>
                    </span>
                  </div>
                  <div class="info-item" *ngIf="project()?.unique_colors !== undefined && project()?.unique_colors !== null">
                    <span class="label">Colors:</span>
                    <span class="value">{{ project()?.unique_colors }}</span>
                  </div>
                </div>

                <div class="info-card" *ngIf="project()?.processing_flags">
                  <h3>Processing Options</h3>
                  <div class="flags-list">
                    <div *ngIf="project()?.processing_flags?.group_by" class="flag-item">
                      <tui-icon icon="@tui.check" style="color: var(--tui-success);"></tui-icon>
                      <span>Group By: {{ project()?.processing_flags?.group_by }}</span>
                    </div>
                    <div *ngIf="project()?.processing_flags?.csv_export" class="flag-item">
                      <tui-icon icon="@tui.check" style="color: var(--tui-success);"></tui-icon>
                      <span>CSV Export</span>
                    </div>
                    <div *ngIf="project()?.processing_flags?.excel_export" class="flag-item">
                      <tui-icon icon="@tui.check" style="color: var(--tui-success);"></tui-icon>
                      <span>Excel Export</span>
                    </div>
                    <div *ngIf="project()?.processing_flags?.json_export" class="flag-item">
                      <tui-icon icon="@tui.check" style="color: var(--tui-success);"></tui-icon>
                      <span>JSON Export</span>
                    </div>
                    <div *ngIf="project()?.processing_flags?.html_export" class="flag-item">
                      <tui-icon icon="@tui.check" style="color: var(--tui-success);"></tui-icon>
                      <span>HTML Report</span>
                    </div>
                    <div *ngIf="project()?.processing_flags?.pdf_export" class="flag-item">
                      <tui-icon icon="@tui.check" style="color: var(--tui-success);"></tui-icon>
                      <span>PDF Report</span>
                    </div>
                    <div *ngIf="project()?.processing_flags?.visualize_floor_plans" class="flag-item">
                      <tui-icon icon="@tui.check" style="color: var(--tui-success);"></tui-icon>
                      <span>Floor Plan Visualizations</span>
                    </div>
                    <div *ngIf="project()?.processing_flags?.show_azimuth_arrows" class="flag-item">
                      <tui-icon icon="@tui.check" style="color: var(--tui-success);"></tui-icon>
                      <span>Show Azimuth Arrows</span>
                    </div>
                    <div *ngIf="project()?.processing_flags?.ap_opacity" class="flag-item">
                      <tui-icon icon="@tui.info" style="color: var(--tui-info);"></tui-icon>
                      <span>AP Opacity: {{ project()?.processing_flags?.ap_opacity }}</span>
                    </div>
                  </div>
                </div>

                <div class="info-card" *ngIf="project()?.metadata">
                  <h3>Project Statistics</h3>
                  <div class="info-item">
                    <span class="label">Access Points:</span>
                    <span class="value">{{ project()?.aps_count || 0 }}</span>
                  </div>
                  <div class="info-item">
                    <span class="label">Unique Models:</span>
                    <span class="value">{{ project()?.metadata?.unique_models || 0 }}</span>
                  </div>
                  <div class="info-item">
                    <span class="label">Floors:</span>
                    <span class="value">{{ project()?.metadata?.floor_count || 0 }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Reports Tab -->
            <div *ngIf="activeTab() === 'reports'" class="reports-tab">
              <div *ngIf="loadingReports()" class="loading-state">
                <tui-loader size="m"></tui-loader>
                <p>Loading reports...</p>
              </div>

              <div *ngIf="!loadingReports() && reports().length > 0" class="reports-list">
                <div *ngFor="let report of reports()" class="report-item">
                  <div class="report-info">
                    <tui-icon [icon]="getFileIcon(report.filename)"></tui-icon>
                    <span class="report-name">{{ report.filename }}</span>
                    <span class="report-size">{{ formatFileSize(report.size) }}</span>
                  </div>
                  <button
                    tuiButton
                    appearance="primary"
                    size="s"
                    (click)="downloadReport(report.filename)"
                  >
                    <tui-icon icon="@tui.download"></tui-icon>
                    Download
                  </button>
                </div>
              </div>

              <div *ngIf="!loadingReports() && reports().length === 0" class="empty-state">
                <tui-icon icon="@tui.file"></tui-icon>
                <p>No reports available</p>
              </div>
            </div>

            <!-- Visualizations Tab -->
            <div *ngIf="activeTab() === 'visualizations'" class="visualizations-tab">
              <div *ngIf="loadingVisualizations()" class="loading-state">
                <tui-loader size="m"></tui-loader>
                <p>Loading visualizations...</p>
              </div>

              <div *ngIf="!loadingVisualizations() && visualizations().length > 0" class="visualizations-grid">
                <div *ngFor="let viz of visualizations(); let i = index" class="visualization-item">
                  <div class="viz-preview" (click)="openLightbox(i)">
                    <img [src]="getVisualizationUrl(viz.filename)" [alt]="viz.filename" />
                    <div class="viz-overlay">
                      <tui-icon icon="@tui.eye"></tui-icon>
                      <span>Click to view</span>
                    </div>
                  </div>
                  <div class="viz-info">
                    <span class="viz-name">{{ viz.filename }}</span>
                    <button
                      tuiButton
                      appearance="primary"
                      size="xs"
                      (click)="downloadVisualization(viz.filename)"
                    >
                      <tui-icon icon="@tui.download"></tui-icon>
                      Download
                    </button>
                  </div>
                </div>
              </div>

              <div *ngIf="!loadingVisualizations() && visualizations().length === 0" class="empty-state">
                <tui-icon icon="@tui.image"></tui-icon>
                <p>No visualizations available</p>
              </div>
            </div>

            <!-- Notes Tab -->
            <div *ngIf="activeTab() === 'notes'" class="notes-tab">
              <div *ngIf="loadingNotes()" class="loading-state">
                <tui-loader size="m"></tui-loader>
                <p>Loading notes...</p>
              </div>

              <div *ngIf="!loadingNotes() && notes()">
                <!-- Summary Cards -->
                <div class="notes-summary">
                  <div class="summary-card">
                    <tui-icon icon="@tui.file-text" class="summary-icon"></tui-icon>
                    <div class="summary-info">
                      <span class="summary-count">{{ notes()?.summary?.total_text_notes || 0 }}</span>
                      <span class="summary-label">Text Notes</span>
                    </div>
                  </div>
                  <div class="summary-card">
                    <tui-icon icon="@tui.image" class="summary-icon"></tui-icon>
                    <div class="summary-info">
                      <span class="summary-count">{{ notes()?.summary?.total_picture_notes || 0 }}</span>
                      <span class="summary-label">Picture Notes</span>
                    </div>
                  </div>
                  <div class="summary-card">
                    <tui-icon icon="@tui.trending-up" class="summary-icon"></tui-icon>
                    <div class="summary-info">
                      <span class="summary-count">{{ notes()?.summary?.total_cable_notes || 0 }}</span>
                      <span class="summary-label">Cable Notes</span>
                    </div>
                  </div>
                </div>

                <!-- Text Notes Section -->
                <div *ngIf="notes()?.text_notes && notes()!.text_notes.length > 0" class="notes-section">
                  <h3><tui-icon icon="@tui.file-text"></tui-icon> Text Notes</h3>
                  <div class="notes-list">
                    <div *ngFor="let note of notes()!.text_notes" class="note-item">
                      <div class="note-header">
                        <tui-badge appearance="info">{{ note.id.substring(0, 8) }}</tui-badge>
                        <span class="note-date">{{ formatDate(note.created_at) }}</span>
                      </div>
                      <div class="note-content">
                        <p>{{ note.text }}</p>
                      </div>
                      <div class="note-footer">
                        <span class="note-author">
                          <tui-icon icon="@tui.user"></tui-icon>
                          {{ note.created_by || 'Unknown' }}
                        </span>
                        <tui-badge [appearance]="note.status === 'ACTIVE' ? 'success' : 'neutral'">
                          {{ note.status }}
                        </tui-badge>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Picture Notes Section -->
                <div *ngIf="notes()?.picture_notes && notes()!.picture_notes.length > 0" class="notes-section">
                  <h3><tui-icon icon="@tui.image"></tui-icon> Picture Notes</h3>
                  <div class="notes-list">
                    <div *ngFor="let note of notes()!.picture_notes" class="note-item">
                      <div class="note-header">
                        <tui-badge appearance="warning">{{ note.id.substring(0, 8) }}</tui-badge>
                        <span *ngIf="note.location" class="note-location">
                          <tui-icon icon="@tui.map-pin"></tui-icon>
                          {{ note.location.floor_name }}
                        </span>
                      </div>
                      <div class="note-content" *ngIf="note.location">
                        <div class="location-details">
                          <span>X: {{ note.location.x | number:'1.2-2' }}</span>
                          <span>Y: {{ note.location.y | number:'1.2-2' }}</span>
                        </div>
                      </div>
                      <div class="note-footer">
                        <span *ngIf="note.note_ids && note.note_ids.length > 0" class="linked-notes">
                          <tui-icon icon="@tui.link"></tui-icon>
                          {{ note.note_ids.length }} linked text note(s)
                        </span>
                        <tui-badge [appearance]="note.status === 'ACTIVE' ? 'success' : 'neutral'">
                          {{ note.status }}
                        </tui-badge>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Cable Notes Section -->
                <div *ngIf="notes()?.cable_notes && notes()!.cable_notes.length > 0" class="notes-section">
                  <h3><tui-icon icon="@tui.trending-up"></tui-icon> Cable Notes</h3>
                  <div class="notes-list">
                    <div *ngFor="let note of notes()!.cable_notes" class="note-item">
                      <div class="note-header">
                        <tui-badge appearance="primary">{{ note.id.substring(0, 8) }}</tui-badge>
                        <span class="note-location">
                          <tui-icon icon="@tui.map-pin"></tui-icon>
                          {{ note.floor_name }}
                        </span>
                      </div>
                      <div class="note-content">
                        <div class="cable-details">
                          <span>
                            <tui-icon icon="@tui.more-vertical"></tui-icon>
                            {{ note.points.length }} points
                          </span>
                          <span class="color-indicator" [style.background-color]="note.color || '#404040'"></span>
                        </div>
                      </div>
                      <div class="note-footer">
                        <span *ngIf="note.note_ids && note.note_ids.length > 0" class="linked-notes">
                          <tui-icon icon="@tui.link"></tui-icon>
                          {{ note.note_ids.length }} linked text note(s)
                        </span>
                        <tui-badge [appearance]="note.status === 'ACTIVE' ? 'success' : 'neutral'">
                          {{ note.status }}
                        </tui-badge>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Empty state for no notes -->
                <div *ngIf="!notes()?.text_notes?.length && !notes()?.picture_notes?.length && !notes()?.cable_notes?.length" class="empty-state">
                  <tui-icon icon="@tui.message-circle"></tui-icon>
                  <p>No notes found in this project</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Lightbox for full-size visualization -->
      <div *ngIf="lightboxOpen()" class="lightbox" (click)="closeLightbox()">
        <div class="lightbox-content">
          <!-- Close button -->
          <button class="lightbox-close" tuiButton appearance="icon" size="l">
            <tui-icon icon="@tui.x"></tui-icon>
          </button>

          <!-- Navigation buttons (only if multiple images) -->
          <button
            *ngIf="visualizations().length > 1"
            class="lightbox-nav lightbox-nav-prev"
            tuiButton
            appearance="icon"
            size="l"
            [disabled]="currentVisualizationIndex() === 0"
            (click)="previousImage(); $event.stopPropagation()"
            tuiHint="Previous (←)"
          >
            <tui-icon icon="@tui.chevron-left"></tui-icon>
          </button>

          <button
            *ngIf="visualizations().length > 1"
            class="lightbox-nav lightbox-nav-next"
            tuiButton
            appearance="icon"
            size="l"
            [disabled]="currentVisualizationIndex() === visualizations().length - 1"
            (click)="nextImage(); $event.stopPropagation()"
            tuiHint="Next (→)"
          >
            <tui-icon icon="@tui.chevron-right"></tui-icon>
          </button>

          <!-- Image container with zoom -->
          <div
            #imageContainer
            class="lightbox-image-container"
            [style.cursor]="zoomLevel() > 1 ? (isDragging() ? 'grabbing' : 'grab') : 'default'"
            (mousedown)="onImageMouseDown($event, imageContainer)"
            (mousemove)="onImageMouseMove($event, imageContainer)"
            (mouseup)="onImageMouseUp()"
            (mouseleave)="onImageMouseLeave()"
            (wheel)="onImageMouseWheel($event, imageContainer)"
            (click)="$event.stopPropagation()"
          >
            <img
              [src]="lightboxImageUrl()"
              [alt]="lightboxImageName()"
              [style.transform]="'scale(' + zoomLevel() + ')'"
              [style.user-select]="'none'"
              [style.pointer-events]="'none'"
            />
          </div>

          <!-- Footer with controls -->
          <div class="lightbox-footer">
            <!-- Zoom controls -->
            <div class="zoom-controls">
              <button
                tuiButton
                appearance="secondary"
                size="s"
                (click)="zoomOut(); $event.stopPropagation()"
                [disabled]="zoomLevel() <= 1.0"
                tuiHint="Zoom Out (-)"
              >
                <tui-icon icon="@tui.minus"></tui-icon>
              </button>
              <span class="zoom-level">{{ (zoomLevel() * 100) | number:'1.0-0' }}%</span>
              <button
                tuiButton
                appearance="secondary"
                size="s"
                (click)="zoomIn(); $event.stopPropagation()"
                [disabled]="zoomLevel() >= 3.0"
                tuiHint="Zoom In (+)"
              >
                <tui-icon icon="@tui.plus"></tui-icon>
              </button>
              <button
                tuiButton
                appearance="secondary"
                size="s"
                (click)="resetZoom(); $event.stopPropagation()"
                [disabled]="zoomLevel() === 1.0"
                tuiHint="Reset Zoom (0)"
              >
                Reset
              </button>
            </div>

            <!-- Image counter (only if multiple images) -->
            <div class="image-counter" *ngIf="visualizations().length > 1">
              {{ currentVisualizationIndex() + 1 }} / {{ visualizations().length }}
            </div>

            <!-- Filename -->
            <span class="lightbox-filename">{{ lightboxImageName() }}</span>

            <!-- Download button -->
            <button
              tuiButton
              appearance="primary"
              size="m"
              (click)="downloadVisualization(lightboxImageName()); $event.stopPropagation()"
              tuiHint="Download"
            >
              <tui-icon icon="@tui.download"></tui-icon>
              Download
            </button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .project-detail-container {
      padding: 2rem;
      max-width: 1400px;
      margin: 0 auto;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
    }

    .header-actions {
      display: flex;
      gap: 1rem;
      align-items: center;

      button {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem 1.25rem;

        tui-icon {
          display: flex;
          align-items: center;
          justify-content: center;
        }
      }
    }

    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 4rem 2rem;
      text-align: center;
    }

    .notification {
      margin-bottom: 2rem;
    }

    .error-content h3 {
      margin: 0 0 0.5rem;
    }

    .error-content p {
      margin: 0.5rem 0;
    }

    .project-content {
      background: var(--tui-base-01);
      border-radius: 0.5rem;
      padding: 2rem;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }

    .project-header {
      margin-bottom: 2rem;
      padding-bottom: 1.5rem;
      border-bottom: 1px solid var(--tui-base-03);
    }

    .project-header h1 {
      margin: 0 0 0.75rem;
      font-size: 2rem;
      font-weight: 500;
    }

    .project-meta {
      display: flex;
      gap: 1rem;
      align-items: center;
      color: var(--tui-text-02);
    }

    .tabs-section {
      margin-top: 1rem;
    }

    .tab-buttons {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }

    .tab-card {
      background: var(--tui-base-02);
      border-radius: 0.5rem;
      padding: 1.25rem;
      text-align: center;
      border: 2px solid transparent;
      transition: all 0.3s ease;
      cursor: pointer;
      user-select: none;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.75rem;

      &:hover:not(.disabled) {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        border-color: var(--tui-primary);
      }

      &.active {
        background: rgba(140, 140, 140, 0.08);
        border-color: rgba(140, 140, 140, 0.4);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
        transform: translateY(-2px);
      }

      &.disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
    }

    .tab-icon {
      font-size: 1.75rem;
      color: var(--tui-text-01);
      transition: color 0.3s ease;

      .tab-card.active & {
        color: var(--tui-primary);
      }

      .tab-card.disabled & {
        color: var(--tui-text-03);
      }
    }

    .tab-label {
      font-size: 1rem;
      font-weight: 500;
      color: var(--tui-text-01);

      .tab-card.active & {
        color: var(--tui-primary);
        font-weight: 600;
      }

      .tab-card.disabled & {
        color: var(--tui-text-03);
      }
    }

    .tab-content {
      // Removed min-height to avoid unnecessary scrolling
    }

    .info-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 1rem;
    }

    .info-card {
      background: var(--tui-base-02);
      border-radius: 0.5rem;
      padding: 1.5rem;
    }

    .info-card h3 {
      margin: 0 0 1rem;
      font-size: 1.125rem;
      font-weight: 500;
    }

    .info-item {
      display: flex;
      justify-content: space-between;
      padding: 0.5rem 0;
      border-bottom: 1px solid var(--tui-base-03);
    }

    .info-item:last-child {
      border-bottom: none;
    }

    .info-item .label {
      color: var(--tui-text-02);
      font-weight: 400;
    }

    .info-item .value {
      font-weight: 500;
    }

    .badges-container {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      justify-content: flex-end;
    }

    .flags-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .flag-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .reports-list {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .report-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem;
      background: var(--tui-base-02);
      border-radius: 0.5rem;
    }

    .report-info {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .report-name {
      font-weight: 500;
    }

    .report-size {
      color: var(--tui-text-02);
      font-size: 0.875rem;
    }

    .visualizations-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 2rem;
    }

    .visualization-item {
      background: var(--tui-base-02);
      border-radius: 0.5rem;
      overflow: hidden;
    }

    .viz-preview {
      width: 100%;
      height: 200px;
      background: var(--tui-base-03);
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      cursor: pointer;
      overflow: hidden;
    }

    .viz-preview img {
      width: 100%;
      height: 100%;
      object-fit: contain;
      transition: transform 0.3s ease;
    }

    .viz-preview:hover img {
      transform: scale(1.05);
    }

    .viz-overlay {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.7);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      opacity: 0;
      transition: opacity 0.3s ease;
      color: white;
    }

    .viz-preview:hover .viz-overlay {
      opacity: 1;
    }

    .viz-overlay tui-icon {
      font-size: 2rem;
    }

    .viz-overlay span {
      font-size: 0.875rem;
      font-weight: 500;
    }

    .viz-info {
      padding: 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .viz-name {
      font-size: 0.875rem;
      font-weight: 500;
    }

    .empty-state {
      padding: 4rem 2rem;
      text-align: center;
      color: var(--tui-text-02);
    }

    .empty-state tui-icon {
      font-size: 3rem;
      color: var(--tui-text-03);
    }

    /* Notes tab styles */
    .notes-summary {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }

    .summary-card {
      background: var(--tui-base-02);
      border-radius: 0.5rem;
      padding: 1.5rem;
      display: flex;
      align-items: center;
      gap: 1rem;
      border: 2px solid transparent;
      transition: all 0.3s ease;
    }

    .summary-card:hover {
      border-color: var(--tui-primary);
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    .summary-icon {
      font-size: 2.5rem;
      color: var(--tui-primary);
    }

    .summary-info {
      display: flex;
      flex-direction: column;
    }

    .summary-count {
      font-size: 2rem;
      font-weight: 600;
      color: var(--tui-text-01);
    }

    .summary-label {
      font-size: 0.875rem;
      color: var(--tui-text-02);
    }

    .notes-section {
      margin-bottom: 2rem;
    }

    .notes-section h3 {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 1.25rem;
      font-weight: 500;
      margin-bottom: 1rem;
      color: var(--tui-text-01);
    }

    .notes-section h3 tui-icon {
      color: var(--tui-primary);
    }

    .notes-list {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .note-item {
      background: var(--tui-base-02);
      border-radius: 0.5rem;
      padding: 1.25rem;
      border-left: 4px solid var(--tui-primary);
      transition: all 0.2s ease;
    }

    .note-item:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      transform: translateX(4px);
    }

    .note-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.75rem;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .note-date,
    .note-location {
      display: flex;
      align-items: center;
      gap: 0.25rem;
      font-size: 0.875rem;
      color: var(--tui-text-02);
    }

    .note-content {
      margin-bottom: 0.75rem;
    }

    .note-content p {
      margin: 0;
      color: var(--tui-text-01);
      line-height: 1.6;
    }

    .note-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
      flex-wrap: wrap;
    }

    .note-author,
    .linked-notes {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
      color: var(--tui-text-02);
    }

    .location-details,
    .cable-details {
      display: flex;
      gap: 1rem;
      font-size: 0.875rem;
      color: var(--tui-text-02);
    }

    .cable-details {
      align-items: center;
    }

    .cable-details span {
      display: flex;
      align-items: center;
      gap: 0.25rem;
    }

    .color-indicator {
      width: 32px;
      height: 16px;
      border-radius: 4px;
      border: 1px solid var(--tui-base-03);
    }

    /* Lightbox styles */
    .lightbox {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.95);
      z-index: 9999;
      display: flex;
      align-items: center;
      justify-content: center;
      animation: fadeIn 0.3s ease;
    }

    @keyframes fadeIn {
      from {
        opacity: 0;
      }
      to {
        opacity: 1;
      }
    }

    .lightbox-content {
      position: relative;
      width: 90vw;
      height: 90vh;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .lightbox-close {
      position: absolute;
      top: 1.5rem;
      right: 1.5rem;
      background: rgba(0, 0, 0, 0.5);
      color: white;
      border: none;
      border-radius: 50%;
      cursor: pointer;
      z-index: 10;
      width: 3rem;
      height: 3rem;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease;
    }

    .lightbox-close:hover {
      transform: scale(1.15);
      background: rgba(0, 0, 0, 0.8);
    }

    .lightbox-image-container {
      flex: 1;
      display: flex;
      align-items: flex-start;
      justify-content: flex-start;
      overflow: auto;
      position: relative;
    }

    .lightbox-image-container img {
      max-width: 100%;
      max-height: 100%;
      min-width: 100%;
      min-height: 100%;
      object-fit: contain;
      border-radius: 0.5rem;
      box-shadow: 0 10px 50px rgba(0, 0, 0, 0.5);
      transform-origin: top left;
      margin: auto;
    }

    .lightbox-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 0.5rem;
      backdrop-filter: blur(10px);
      gap: 1rem;
      flex-wrap: wrap;
    }

    .lightbox-filename {
      color: white;
      font-size: 1rem;
      font-weight: 500;
      flex: 1;
      min-width: 200px;
    }

    .zoom-controls {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .zoom-level {
      min-width: 50px;
      text-align: center;
      color: white;
      font-weight: 500;
      font-size: 0.9rem;
    }

    .image-counter {
      padding: 0.5rem 1rem;
      background: rgba(255, 255, 255, 0.15);
      border-radius: 0.25rem;
      font-size: 0.9rem;
      color: white;
      font-weight: 500;
      min-width: 60px;
      text-align: center;
    }

    .lightbox-nav {
      position: absolute;
      top: 50%;
      transform: translateY(-50%);
      z-index: 10001;
      background: rgba(255, 255, 255, 0.1);
      backdrop-filter: blur(10px);
      border: none;
      color: white;
      width: 3.5rem;
      height: 3.5rem;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .lightbox-nav-prev {
      left: 2rem;
    }

    .lightbox-nav-next {
      right: 2rem;
    }

    .lightbox-nav:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.25);
      transform: translateY(-50%) scale(1.1);
    }

    .lightbox-nav:disabled {
      opacity: 0.3;
      cursor: not-allowed;
    }

    // Color-coded status badges
    tui-badge.status-badge-completed {
      background-color: #D4EDDA !important;
      color: #155724 !important;
      border: 1px solid #C3E6CB !important;
    }

    tui-badge.status-badge-pending {
      background-color: #FFF3CD !important;
      color: #856404 !important;
      border: 1px solid #FFEAA7 !important;
    }

    tui-badge.status-badge-processing {
      background-color: #D1ECF1 !important;
      color: #0C5460 !important;
      border: 1px solid #BEE5EB !important;
    }

    tui-badge.status-badge-failed {
      background-color: #F8D7DA !important;
      color: #721C24 !important;
      border: 1px solid #F5C6CB !important;
    }
  `]
})
export class ProjectDetailComponent implements OnInit {
  private apiService = inject(ApiService);
  private projectService = inject(ProjectService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  // Signals for component state
  loading = signal(false);
  error = signal<string | null>(null);
  project = signal<ProjectDetails | null>(null);
  activeTab = signal<'overview' | 'reports' | 'visualizations' | 'notes'>('overview');

  loadingReports = signal(false);
  reports = signal<ReportFile[]>([]);

  loadingVisualizations = signal(false);
  visualizations = signal<ReportFile[]>([]);

  loadingNotes = signal(false);
  notes = signal<NotesData | null>(null);

  // Lightbox state
  lightboxOpen = signal(false);
  lightboxImageUrl = signal('');
  lightboxImageName = signal('');

  // Lightbox zoom state
  zoomLevel = signal(1.0);

  // Drag-to-pan state
  isDragging = signal(false);
  dragStartX = signal(0);
  dragStartY = signal(0);
  scrollStartX = signal(0);
  scrollStartY = signal(0);

  // Gallery navigation state
  currentVisualizationIndex = signal(0);

  // Short link mode tracking
  isShortLinkMode = signal(false);

  projectId: string | null = null;

  // Make ProcessingStatus available in template
  ProcessingStatus = ProcessingStatus;

  ngOnInit(): void {
    // Get project ID from route params or query params (for short links)
    this.route.params.subscribe(params => {
      if (params['id']) {
        this.projectId = params['id'];
        this.loadProject();
      } else if (params['shortLink']) {
        this.loadProjectByShortLink(params['shortLink']);
      }
    });
  }

  loadProject(): void {
    if (!this.projectId) {
      return;
    }

    this.loading.set(true);
    this.error.set(null);

    this.apiService.getProject(this.projectId).subscribe({
      next: (project) => {
        this.project.set(project);
        this.loading.set(false);

        if (project.processing_status === ProcessingStatus.COMPLETED) {
          this.loadReports();
          this.loadVisualizations();
        }
      },
      error: (err) => {
        this.error.set('Failed to load project details');
        this.loading.set(false);
        console.error('Error loading project:', err);
      }
    });
  }

  loadProjectByShortLink(shortLink: string): void {
    this.loading.set(true);
    this.error.set(null);

    // Enable short link mode
    this.isShortLinkMode.set(true);
    sessionStorage.setItem('short_link_mode', 'true');

    this.apiService.getProjectByShortLink(shortLink).subscribe({
      next: (project) => {
        this.project.set(project);
        this.projectId = project.project_id;
        this.loading.set(false);

        if (project.processing_status === ProcessingStatus.COMPLETED) {
          this.loadReports();
          this.loadVisualizations();
        }
      },
      error: (err) => {
        this.error.set('Invalid or expired short link');
        this.loading.set(false);
        console.error('Error loading project by short link:', err);
      }
    });
  }

  loadReports(): void {
    if (!this.projectId) {
      return;
    }

    this.loadingReports.set(true);

    this.apiService.getProjectReports(this.projectId).subscribe({
      next: (reports) => {
        this.reports.set(reports.reports);
        this.loadingReports.set(false);
      },
      error: (err) => {
        console.error('Error loading reports:', err);
        this.loadingReports.set(false);
      }
    });
  }

  loadVisualizations(): void {
    if (!this.projectId) {
      return;
    }

    this.loadingVisualizations.set(true);

    this.apiService.getProjectVisualizations(this.projectId).subscribe({
      next: (visualizations) => {
        this.visualizations.set(visualizations.visualizations);
        this.loadingVisualizations.set(false);
      },
      error: (err) => {
        console.error('Error loading visualizations:', err);
        this.loadingVisualizations.set(false);
      }
    });
  }

  loadNotes(): void {
    if (!this.projectId) {
      return;
    }

    this.loadingNotes.set(true);

    this.apiService.getNotes(this.projectId).subscribe({
      next: (notes) => {
        this.notes.set(notes);
        this.loadingNotes.set(false);
      },
      error: (err) => {
        console.error('Error loading notes:', err);
        this.loadingNotes.set(false);
      }
    });
  }

  setActiveTab(tab: 'overview' | 'reports' | 'visualizations' | 'notes'): void {
    this.activeTab.set(tab);

    // Load data when switching to specific tabs
    if (tab === 'notes' && !this.notes() && this.project()?.processing_status === ProcessingStatus.COMPLETED) {
      this.loadNotes();
    }
  }

  copyShortLink(): void {
    const shortLink = this.project()?.short_link;
    if (shortLink) {
      const url = `${window.location.origin}/s/${shortLink}`;
      navigator.clipboard.writeText(url).then(() => {
        console.log('Short link copied to clipboard');
      });
    }
  }

  getShortLinkUrl(): string {
    return `/s/${this.project()?.short_link}`;
  }

  downloadReport(filename: string): void {
    if (!this.projectId) {
      return;
    }

    const url = `/api/reports/${this.projectId}/download/${filename}`;
    window.open(url, '_blank');
  }

  downloadVisualization(filename: string): void {
    if (!this.projectId) {
      return;
    }

    const url = `/api/reports/${this.projectId}/visualization/${filename}`;
    window.open(url, '_blank');
  }

  getVisualizationUrl(filename: string): string {
    if (!this.projectId) {
      return '';
    }

    return `/api/reports/${this.projectId}/visualization/${filename}`;
  }

  formatDate(dateString: string | null | undefined): string {
    if (!dateString) {
      return 'Unknown';
    }
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  }

  formatFileSize(bytes: number): string {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  }

  getFileIcon(filename: string): string {
    if (filename.endsWith('.csv')) return '@tui.file-text';
    if (filename.endsWith('.xlsx')) return '@tui.file-spreadsheet';
    if (filename.endsWith('.json')) return '@tui.file-code';
    if (filename.endsWith('.html')) return '@tui.file-text';
    if (filename.endsWith('.png') || filename.endsWith('.jpg')) return '@tui.image';
    return '@tui.file';
  }

  getStatusAppearance(status: ProcessingStatus): string {
    switch (status) {
      case ProcessingStatus.PENDING:
        return 'warning';
      case ProcessingStatus.PROCESSING:
        return 'info';
      case ProcessingStatus.COMPLETED:
        return 'success';
      case ProcessingStatus.FAILED:
        return 'error';
      default:
        return 'neutral';
    }
  }

  openLightbox(index: number): void {
    const viz = this.visualizations()[index];
    if (!viz) return;

    this.currentVisualizationIndex.set(index);
    this.lightboxImageUrl.set(this.getVisualizationUrl(viz.filename));
    this.lightboxImageName.set(viz.filename);
    this.lightboxOpen.set(true);
    this.resetZoom(); // Reset zoom when opening new image
  }

  closeLightbox(): void {
    this.lightboxOpen.set(false);
    this.lightboxImageUrl.set('');
    this.lightboxImageName.set('');
    this.resetZoom();
  }

  // Zoom methods
  zoomIn(): void {
    const current = this.zoomLevel();
    if (current < 3.0) {
      this.zoomLevel.set(Math.min(current + 0.25, 3.0));
    }
  }

  zoomOut(): void {
    const current = this.zoomLevel();
    if (current > 1.0) {
      this.zoomLevel.set(Math.max(current - 0.25, 1.0));
    }
  }

  resetZoom(): void {
    this.zoomLevel.set(1.0);
  }

  // Drag-to-pan methods
  onImageMouseDown(event: MouseEvent, container: HTMLElement): void {
    // Only enable drag if zoomed in
    if (this.zoomLevel() > 1.0) {
      event.preventDefault(); // Prevent default image drag behavior
      this.isDragging.set(true);
      this.dragStartX.set(event.clientX);
      this.dragStartY.set(event.clientY);
      this.scrollStartX.set(container.scrollLeft);
      this.scrollStartY.set(container.scrollTop);
    }
  }

  onImageMouseMove(event: MouseEvent, container: HTMLElement): void {
    if (this.isDragging() && this.zoomLevel() > 1.0) {
      event.preventDefault();
      const deltaX = event.clientX - this.dragStartX();
      const deltaY = event.clientY - this.dragStartY();
      container.scrollLeft = this.scrollStartX() - deltaX;
      container.scrollTop = this.scrollStartY() - deltaY;
    }
  }

  onImageMouseUp(): void {
    this.isDragging.set(false);
  }

  onImageMouseLeave(): void {
    this.isDragging.set(false);
  }

  // Gallery navigation methods
  nextImage(): void {
    const current = this.currentVisualizationIndex();
    const total = this.visualizations().length;
    if (current < total - 1) {
      this.openLightbox(current + 1);
    }
  }

  previousImage(): void {
    const current = this.currentVisualizationIndex();
    if (current > 0) {
      this.openLightbox(current - 1);
    }
  }

  // Keyboard shortcuts
  @HostListener('document:keydown', ['$event'])
  onKeyDown(event: KeyboardEvent): void {
    if (this.lightboxOpen()) {
      switch(event.key) {
        case 'ArrowLeft':
          event.preventDefault();
          this.previousImage();
          break;
        case 'ArrowRight':
          event.preventDefault();
          this.nextImage();
          break;
        case 'Escape':
          event.preventDefault();
          this.closeLightbox();
          break;
        case '+':
        case '=':
          event.preventDefault();
          this.zoomIn();
          break;
        case '-':
        case '_':
          event.preventDefault();
          this.zoomOut();
          break;
        case '0':
          event.preventDefault();
          this.resetZoom();
          break;
      }
    }
  }

  // Mouse wheel zoom relative to cursor position
  onImageMouseWheel(event: WheelEvent, container: HTMLElement): void {
    event.preventDefault();

    // Get container dimensions and mouse position
    const rect = container.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;

    // Current zoom and scroll
    const oldZoom = this.zoomLevel();
    const scrollX = container.scrollLeft;
    const scrollY = container.scrollTop;

    // Calculate new zoom
    let newZoom = oldZoom;
    if (event.deltaY < 0) {
      newZoom = Math.min(oldZoom + 0.25, 3.0);
    } else {
      newZoom = Math.max(oldZoom - 0.25, 1.0);
    }

    if (newZoom === oldZoom) return; // No zoom change

    // Calculate zoom ratio
    const zoomRatio = newZoom / oldZoom;

    // Apply zoom
    this.zoomLevel.set(newZoom);

    // Adjust scroll to keep point under cursor in place
    // Use requestAnimationFrame for smooth update
    requestAnimationFrame(() => {
      container.scrollLeft = (scrollX + mouseX) * zoomRatio - mouseX;
      container.scrollTop = (scrollY + mouseY) * zoomRatio - mouseY;
    });
  }
}
