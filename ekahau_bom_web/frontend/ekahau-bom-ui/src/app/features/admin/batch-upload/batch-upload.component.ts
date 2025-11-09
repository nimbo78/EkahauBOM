import { Component, inject, signal, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, FormGroup, ReactiveFormsModule, FormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import {
  TuiButton,
  TuiIcon,
  TuiNotification,
  TuiLoader,
  TuiHint,
  TuiLabel,
} from '@taiga-ui/core';
import { TuiFiles, TuiRadio, type TuiFileLike } from '@taiga-ui/kit';
import { ApiService } from '../../../core/services/api.service';
import { ErrorMessageService } from '../../../shared/services/error-message.service';
import { LoadingService } from '../../../shared/services/loading.service';
import { finalize, Subscription } from 'rxjs';
import { HttpEvent, HttpEventType } from '@angular/common/http';
import { BatchUploadResponse, DirectoryScanResponse, ScannedFile, BatchTemplate } from '../../../core/models/batch.model';
import { ProcessingRequest, ProjectListItem } from '../../../core/models/project.model';
import JSZip from 'jszip';

interface BatchFileConfig {
  file: File;
  action: 'new' | 'update' | 'skip';
  projectName?: string;
  existingProject?: ProjectListItem;
  checkingDuplicate: boolean;
}

@Component({
  selector: 'app-batch-upload',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    TuiButton,
    TuiIcon,
    TuiFiles,
    TuiNotification,
    TuiLoader,
    TuiLabel,
    TuiHint,
    TuiRadio,
  ],
  template: `
    <div class="batch-upload-container">
      <div class="page-header">
        <h2 class="page-title">Batch Upload</h2>
        <p class="page-subtitle">Upload and process multiple .esx files at once</p>
      </div>

      <div class="upload-content">
        <!-- Step 1: File Selection -->
        <div *ngIf="!uploadedFiles().length && !uploading()" class="upload-step">
          <label tuiInputFiles class="upload-label">
            <input
              tuiInputFiles
              type="file"
              accept=".esx"
              multiple
              [formControl]="filesControl"
            />
            <ng-template let-dragged>
              <div class="upload-area" [class.dragging]="dragged">
                <tui-icon
                  [icon]="dragged ? '@tui.droplet' : '@tui.upload-cloud'"
                  class="upload-icon"
                ></tui-icon>
                <h3>{{ dragged ? 'Drop your files here!' : 'Drag & Drop multiple .esx files here' }}</h3>
                <p>or</p>
                <button tuiButton appearance="secondary" size="m" type="button">
                  Browse Files
                </button>
                <p class="upload-hint">Select multiple .esx files (max 500 MB each)</p>
              </div>
            </ng-template>
          </label>

          <!-- Directory Scan (Advanced) -->
          <div class="directory-scan-section">
            <button
              tuiButton
              appearance="flat"
              size="s"
              (click)="toggleDirectoryScan()"
              class="toggle-directory-btn"
            >
              <tui-icon [icon]="showDirectoryScan() ? '@tui.chevron-down' : '@tui.chevron-right'"></tui-icon>
              Advanced: Import from Server Directory
            </button>

            <div *ngIf="showDirectoryScan()" class="directory-scan-content">
              <p class="directory-hint">
                Scan a directory on the server for .esx files (useful for CLI batch output import)
              </p>

              <div class="directory-form">
                <label tuiLabel class="input-label">
                  Directory Path
                  <input
                    type="text"
                    class="tui-input"
                    [(ngModel)]="directoryPath"
                    [ngModelOptions]="{standalone: true}"
                    placeholder="C:\path\to\directory or /path/to/directory"
                  />
                </label>

                <label class="checkbox-label">
                  <input
                    type="checkbox"
                    [(ngModel)]="recursiveScan"
                    [ngModelOptions]="{standalone: true}"
                    class="tui-checkbox"
                  />
                  <span>Scan subdirectories recursively</span>
                </label>

                <button
                  tuiButton
                  appearance="secondary"
                  size="m"
                  (click)="startDirectoryScan()"
                  [disabled]="scanningDirectory()"
                >
                  <tui-icon icon="@tui.search"></tui-icon>
                  {{ scanningDirectory() ? 'Scanning...' : 'Scan Directory' }}
                </button>
              </div>

              <!-- Scanned files results -->
              <div *ngIf="scannedFiles().length > 0" class="scanned-files-results">
                <div class="scanned-files-header">
                  <h4>Found {{ scannedFiles().length }} .esx files</h4>
                  <div class="selection-buttons">
                    <button
                      tuiButton
                      appearance="flat"
                      size="xs"
                      (click)="selectAllScannedFiles()"
                    >
                      <tui-icon icon="@tui.check"></tui-icon>
                      Select All
                    </button>
                    <button
                      tuiButton
                      appearance="flat"
                      size="xs"
                      (click)="deselectAllScannedFiles()"
                    >
                      <tui-icon icon="@tui.x"></tui-icon>
                      Deselect All
                    </button>
                  </div>
                </div>
                <div class="scanned-files-list">
                  <div *ngFor="let file of scannedFiles()" class="scanned-file-item">
                    <label class="checkbox-label">
                      <input
                        type="checkbox"
                        [checked]="selectedScannedFiles().has(file.filepath)"
                        (change)="toggleFileSelection(file.filepath)"
                        class="tui-checkbox"
                      />
                    </label>
                    <tui-icon icon="@tui.file"></tui-icon>
                    <div class="scanned-file-info">
                      <div class="file-name">{{ file.filename }}</div>
                      <div class="file-path">{{ file.filepath }}</div>
                      <div class="file-meta">{{ formatFileSize(file.filesize) }} • {{ file.modified_date | date:'short' }}</div>
                    </div>
                  </div>
                </div>
                <div class="import-section">
                  <button
                    tuiButton
                    appearance="primary"
                    size="m"
                    (click)="importSelectedFiles()"
                    [disabled]="selectedScannedFiles().size === 0 || importingFromPaths()"
                  >
                    <tui-icon icon="@tui.upload"></tui-icon>
                    {{ importingFromPaths() ? 'Importing...' : 'Import ' + selectedScannedFiles().size + ' Selected Files' }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Selected files preview -->
          <div *ngIf="selectedFiles().length > 0" class="selected-files">
            <h3>Selected Files ({{ selectedFiles().length }})</h3>
            <div class="file-list">
              <div
                *ngFor="let file of selectedFiles(); let i = index"
                class="file-item-preview"
              >
                <tui-icon icon="@tui.file" class="file-icon"></tui-icon>
                <div class="file-info-preview">
                  <div class="file-name">{{ file.name }}</div>
                  <div class="file-size">{{ formatFileSize(file.size) }}</div>
                </div>
                <button
                  tuiButton
                  appearance="flat"
                  size="xs"
                  (click)="removeFile(i)"
                  class="remove-btn"
                >
                  <tui-icon icon="@tui.x"></tui-icon>
                </button>
              </div>
            </div>

            <!-- Batch configuration form -->
            <form [formGroup]="batchForm" class="batch-config">
              <div class="form-row">
                <label tuiLabel class="input-label">
                  Batch Name (optional)
                  <input
                    type="text"
                    class="tui-input"
                    formControlName="batchName"
                    placeholder="My Batch"
                  />
                </label>
              </div>

              <div class="form-row">
                <label tuiLabel class="input-label">
                  Parallel Workers
                  <input
                    type="number"
                    class="tui-input"
                    formControlName="parallelWorkers"
                    min="1"
                    max="8"
                    [tuiHint]="'Number of files to process simultaneously (1-8)'"
                  />
                </label>
              </div>

              <div class="form-row checkbox-row">
                <label class="checkbox-label">
                  <input
                    type="checkbox"
                    formControlName="autoProcess"
                    class="tui-checkbox"
                  />
                  <span>Automatically start processing after upload</span>
                </label>
              </div>

              <!-- Template Selector -->
              <div class="template-selector">
                <div class="template-header">
                  <label tuiLabel class="input-label">
                    <tui-icon icon="@tui.layout"></tui-icon>
                    Processing Template (optional)
                  </label>
                  <button
                    *ngIf="selectedTemplateId()"
                    tuiButton
                    appearance="flat"
                    size="xs"
                    (click)="clearTemplate()"
                    type="button"
                  >
                    <tui-icon icon="@tui.x"></tui-icon>
                    Clear Template
                  </button>
                </div>

                <select
                  class="tui-select"
                  [value]="selectedTemplateId() || ''"
                  (change)="onTemplateChange($any($event.target).value)"
                  [disabled]="loadingTemplates()"
                  [tuiHint]="'Choose a predefined template to auto-fill processing options'"
                >
                  <option value="">-- Choose a template --</option>
                  <optgroup *ngIf="hasSystemTemplates" label="System Templates">
                    <option *ngFor="let template of systemTemplates" [value]="template.template_id">
                      {{ template.name }} - {{ template.description }}
                    </option>
                  </optgroup>
                  <optgroup *ngIf="hasCustomTemplates" label="Custom Templates">
                    <option *ngFor="let template of customTemplates" [value]="template.template_id">
                      {{ template.name }} - {{ template.description }}
                    </option>
                  </optgroup>
                </select>

                <p *ngIf="selectedTemplateName" class="template-info">
                  <tui-icon icon="@tui.check-circle" class="success-icon"></tui-icon>
                  Template applied: <strong>{{ selectedTemplateName }}</strong>
                </p>
              </div>

              <!-- Processing Options (always shown) -->
              <div class="processing-options">
                <h4 class="options-title">Processing Options</h4>

                <!-- Group By -->
                <div class="form-row">
                  <label tuiLabel class="input-label">
                    Group By
                    <select
                      class="tui-select"
                      formControlName="groupBy"
                      [tuiHint]="'Group access points by model, floor, or building'"
                    >
                      <option value="model">Model</option>
                      <option value="floor">Floor</option>
                      <option value="building">Building</option>
                    </select>
                  </label>
                </div>

                <!-- Output Formats -->
                <div class="form-row">
                  <label class="input-label">Output Formats</label>
                  <div class="checkbox-group">
                    <label class="checkbox-label">
                      <input type="checkbox" formControlName="formatCsv" class="tui-checkbox" />
                      <span>CSV</span>
                    </label>
                    <label class="checkbox-label">
                      <input type="checkbox" formControlName="formatExcel" class="tui-checkbox" />
                      <span>Excel</span>
                    </label>
                    <label class="checkbox-label">
                      <input type="checkbox" formControlName="formatHtml" class="tui-checkbox" />
                      <span>HTML</span>
                    </label>
                    <label class="checkbox-label">
                      <input type="checkbox" formControlName="formatPdf" class="tui-checkbox" />
                      <span>PDF</span>
                    </label>
                    <label class="checkbox-label">
                      <input type="checkbox" formControlName="formatJson" class="tui-checkbox" />
                      <span>JSON</span>
                    </label>
                  </div>
                </div>

                <!-- Visualization Options -->
                <div class="form-row">
                  <label class="input-label">Visualization</label>
                  <div class="checkbox-group">
                    <label class="checkbox-label">
                      <input type="checkbox" formControlName="visualizeFloorPlans" class="tui-checkbox" />
                      <span>Generate floor plan visualizations</span>
                    </label>
                    <label class="checkbox-label">
                      <input type="checkbox" formControlName="showAzimuthArrows" class="tui-checkbox" />
                      <span>Show azimuth arrows</span>
                    </label>
                  </div>
                </div>

                <!-- AP Opacity -->
                <div class="form-row">
                  <label tuiLabel class="input-label">
                    AP Opacity ({{ batchForm.value.apOpacity }}%)
                    <input
                      type="range"
                      formControlName="apOpacity"
                      min="10"
                      max="100"
                      step="5"
                      class="tui-slider"
                      [tuiHint]="'Opacity of access point markers on floor plans'"
                    />
                  </label>
                </div>

                <!-- Notes Options -->
                <div class="form-row">
                  <label class="input-label">Include Notes</label>
                  <div class="checkbox-group">
                    <label class="checkbox-label">
                      <input type="checkbox" formControlName="includeTextNotes" class="tui-checkbox" />
                      <span>Text Notes</span>
                    </label>
                    <label class="checkbox-label">
                      <input type="checkbox" formControlName="includePictureNotes" class="tui-checkbox" />
                      <span>Picture Notes</span>
                    </label>
                    <label class="checkbox-label">
                      <input type="checkbox" formControlName="includeCableNotes" class="tui-checkbox" />
                      <span>Cable Notes</span>
                    </label>
                  </div>
                </div>

                <!-- Short Link Options -->
                <div class="form-row">
                  <label class="input-label">Short Link Settings</label>
                  <div class="checkbox-group">
                    <label class="checkbox-label">
                      <input type="checkbox" formControlName="createShortLink" class="tui-checkbox" />
                      <span>Create short links for reports</span>
                    </label>
                  </div>
                  <div *ngIf="batchForm.value.createShortLink" class="shortlink-days">
                    <label tuiLabel class="input-label">
                      Days Until Expiration
                      <input
                        type="number"
                        class="tui-input"
                        formControlName="shortLinkExpireDays"
                        min="1"
                        max="365"
                        [tuiHint]="'Number of days before the short link expires (1-365)'"
                      />
                    </label>
                  </div>
                </div>
              </div>
            </form>

            <div class="action-buttons">
              <button
                tuiButton
                appearance="primary"
                size="l"
                (click)="startUpload()"
              >
                Upload {{ selectedFiles().length }} Files
                <tui-icon icon="@tui.arrow-right"></tui-icon>
              </button>
              <button
                tuiButton
                appearance="secondary"
                size="l"
                (click)="clearSelection()"
              >
                Clear Selection
              </button>
            </div>
          </div>
        </div>

        <!-- Step 2: Checking Duplicates -->
        <div *ngIf="checkingDuplicates()" class="checking-duplicates">
          <tui-loader size="l"></tui-loader>
          <h3>Checking for duplicate projects...</h3>
          <p>Analyzing {{ selectedFiles().length }} files</p>
        </div>

        <!-- Step 3: File Configuration -->
        <div *ngIf="showConfigurationStep() && !uploading()" class="file-configuration">
          <h3>Configure Files ({{ fileConfigs().length }})</h3>
          <p class="config-subtitle">Choose an action for each file:</p>

          <tui-notification status="info" class="notification">
            <p>
              <strong>Create New:</strong> Upload as a new project<br/>
              <strong>Update Existing:</strong> Replace the existing project<br/>
              <strong>Skip:</strong> Don't upload this file
            </p>
          </tui-notification>

          <div class="file-configs-list">
            <div *ngFor="let config of fileConfigs(); let i = index" class="file-config-item">
              <div class="file-info-section">
                <tui-icon icon="@tui.file" class="file-icon"></tui-icon>
                <div class="file-details">
                  <div class="file-name">{{ config.file.name }}</div>
                  <div class="file-size">{{ formatFileSize(config.file.size) }}</div>
                  <div *ngIf="config.existingProject" class="existing-project-info">
                    <tui-icon icon="@tui.alert-circle" style="color: var(--tui-warning);"></tui-icon>
                    Duplicate: "{{ config.existingProject.project_name || config.existingProject.filename }}"
                  </div>
                </div>
              </div>

              <div class="file-actions-section">
                <label class="radio-option">
                  <input
                    tuiRadio
                    type="radio"
                    [name]="'action-' + i"
                    [(ngModel)]="config.action"
                    value="new"
                  />
                  Create New
                </label>
                <label class="radio-option" [class.recommended]="config.existingProject">
                  <input
                    tuiRadio
                    type="radio"
                    [name]="'action-' + i"
                    [(ngModel)]="config.action"
                    value="update"
                    [disabled]="!config.existingProject"
                  />
                  Update Existing
                  <span *ngIf="config.existingProject" class="recommended-badge">Recommended</span>
                </label>
                <label class="radio-option">
                  <input
                    tuiRadio
                    type="radio"
                    [name]="'action-' + i"
                    [(ngModel)]="config.action"
                    value="skip"
                  />
                  Skip
                </label>
              </div>

              <button
                tuiButton
                appearance="flat"
                size="s"
                (click)="removeFileConfig(i)"
                class="remove-btn"
              >
                <tui-icon icon="@tui.trash"></tui-icon>
              </button>
            </div>
          </div>

          <div class="action-buttons">
            <button
              tuiButton
              appearance="primary"
              size="l"
              (click)="proceedWithConfiguration()"
            >
              Upload {{ getNonSkippedFilesCount() }} Files
              <tui-icon icon="@tui.arrow-right"></tui-icon>
            </button>
            <button
              tuiButton
              appearance="secondary"
              size="l"
              (click)="cancelConfiguration()"
            >
              Cancel
            </button>
          </div>
        </div>

        <!-- Step 4: Uploading -->
        <div *ngIf="uploading()" class="upload-progress">
          <tui-loader size="l"></tui-loader>
          <h3>Uploading batch...</h3>
          <p>Processing {{ selectedFiles().length }} files</p>
          <div class="progress-info">
            <p>This may take a few moments depending on file sizes</p>
          </div>
        </div>

        <!-- Step 3: Upload Results -->
        <div *ngIf="uploadResponse() && !uploading()" class="upload-results">
          <tui-notification
            *ngIf="uploadResponse()!.files_failed.length === 0"
            status="success"
            class="notification"
          >
            <div class="result-summary">
              <h3>{{ uploadResponse()!.message }}</h3>
              <p>Batch ID: {{ uploadResponse()!.batch_id }}</p>
            </div>
          </tui-notification>
          <tui-notification
            *ngIf="uploadResponse()!.files_failed.length > 0"
            status="warning"
            class="notification"
          >
            <div class="result-summary">
              <h3>{{ uploadResponse()!.message }}</h3>
              <p>Batch ID: {{ uploadResponse()!.batch_id }}</p>
            </div>
          </tui-notification>

          <!-- Successfully uploaded files -->
          <div *ngIf="uploadResponse()!.files_uploaded.length > 0" class="result-section">
            <h4 class="section-title success-title">
              <tui-icon icon="@tui.circle-check"></tui-icon>
              Successfully Uploaded ({{ uploadResponse()!.files_uploaded.length }})
            </h4>
            <ul class="file-results">
              <li *ngFor="let filename of uploadResponse()!.files_uploaded" class="file-item success">
                <tui-icon icon="@tui.check"></tui-icon>
                {{ filename }}
              </li>
            </ul>
          </div>

          <!-- Failed files -->
          <div *ngIf="uploadResponse()!.files_failed.length > 0" class="result-section">
            <h4 class="section-title error-title">
              <tui-icon icon="@tui.circle-alert"></tui-icon>
              Failed Uploads ({{ uploadResponse()!.files_failed.length }})
            </h4>
            <ul class="file-results">
              <li *ngFor="let filename of uploadResponse()!.files_failed" class="file-item error">
                <tui-icon icon="@tui.x"></tui-icon>
                {{ filename }}
              </li>
            </ul>
          </div>

          <div class="action-buttons">
            <button
              tuiButton
              appearance="primary"
              size="l"
              (click)="viewBatchDetails()"
            >
              View Batch Details
              <tui-icon icon="@tui.arrow-right"></tui-icon>
            </button>
            <button
              tuiButton
              appearance="secondary"
              size="l"
              (click)="resetUpload()"
            >
              Upload Another Batch
            </button>
          </div>
        </div>

        <!-- Error state -->
        <tui-notification *ngIf="error()" status="error" class="notification">
          <div class="error-content">
            <h3>Upload failed</h3>
            <p>{{ error() }}</p>
            <button tuiButton size="s" (click)="resetUpload()">Try again</button>
          </div>
        </tui-notification>
      </div>
    </div>
  `,
  styles: [
    `
      .batch-upload-container {
        width: 100%;
      }

      .page-header {
        margin-bottom: 24px;
      }

      .page-title {
        margin: 0 0 8px 0;
        font-size: 24px;
        font-weight: 600;
        color: var(--tui-text-01);
      }

      .page-subtitle {
        margin: 0;
        font-size: 14px;
        color: var(--tui-text-03);
      }

      .upload-content {
        background: var(--tui-base-02);
        border-radius: 12px;
        padding: 48px;
        min-height: 400px;
      }

      .upload-label {
        display: block;
        cursor: pointer;
      }

      .upload-area {
        border: 2px dashed var(--tui-base-04);
        border-radius: 8px;
        padding: 48px;
        text-align: center;
        background: var(--tui-base-01);
        transition: all 0.2s ease;

        &:hover {
          border-color: var(--tui-primary);
          background: var(--tui-base-02);
        }

        &.dragging {
          border-color: var(--tui-primary);
          background: var(--tui-primary-hover);
          border-style: solid;
        }
      }

      .upload-icon {
        font-size: 48px;
        color: var(--tui-primary);
        margin-bottom: 16px;
        display: block;
      }

      h3 {
        margin: 0 0 16px 0;
        color: var(--tui-text-01);
        font-size: 18px;
      }

      h4 {
        margin: 0 0 12px 0;
        color: var(--tui-text-01);
        font-size: 16px;
      }

      p {
        margin: 16px 0;
        color: var(--tui-text-02);
      }

      .upload-hint {
        margin-top: 24px;
        font-size: 14px;
        color: var(--tui-text-03);
      }

      .selected-files {
        margin-top: 32px;
        padding-top: 32px;
        border-top: 1px solid var(--tui-base-04);
      }

      .file-list {
        margin: 16px 0 24px 0;
        display: flex;
        flex-direction: column;
        gap: 12px;
      }

      .file-item-preview {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        background: var(--tui-base-01);
        border: 1px solid var(--tui-base-04);
        border-radius: 8px;
        transition: all 0.2s ease;

        &:hover {
          border-color: var(--tui-base-05);
        }
      }

      .file-icon {
        font-size: 24px;
        color: var(--tui-primary);
        flex-shrink: 0;
      }

      .file-info-preview {
        flex: 1;
        min-width: 0;
      }

      .file-name {
        font-weight: 500;
        color: var(--tui-text-01);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-bottom: 4px;
      }

      .file-size {
        font-size: 12px;
        color: var(--tui-text-03);
      }

      .remove-btn {
        flex-shrink: 0;
      }

      .batch-config {
        background: var(--tui-base-01);
        border-radius: 8px;
        padding: 24px;
        margin: 24px 0;
      }

      .form-row {
        margin-bottom: 20px;

        &:last-child {
          margin-bottom: 0;
        }
      }

      .input-label {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .tui-input {
        width: 100%;
        padding: 12px 16px;
        border: 1px solid var(--tui-base-04);
        border-radius: 8px;
        background: var(--tui-base-01);
        color: var(--tui-text-01);
        font-size: 14px;
        font-family: inherit;
        transition: all 0.2s ease;

        &:hover {
          border-color: var(--tui-base-05);
        }

        &:focus {
          outline: none;
          border-color: var(--tui-primary);
          box-shadow: 0 0 0 3px rgba(var(--tui-primary-rgb), 0.1);
        }

        &::placeholder {
          color: var(--tui-text-03);
        }
      }

      .checkbox-row {
        display: flex;
        align-items: center;
      }

      .checkbox-label {
        display: flex;
        align-items: center;
        gap: 12px;
        cursor: pointer;
        user-select: none;

        input[type="checkbox"] {
          width: 20px;
          height: 20px;
          cursor: pointer;
          accent-color: var(--tui-primary);
        }

        span {
          color: var(--tui-text-01);
          font-size: 14px;
        }
      }

      .template-selector {
        margin-top: 24px;
        padding: 20px;
        background: var(--tui-base-02);
        border-radius: 8px;
        border: 2px solid var(--tui-primary-hover);

        .template-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;

          .input-label {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 0;
            font-size: 15px;
            font-weight: 600;
            color: var(--tui-text-01);

            tui-icon {
              font-size: 18px;
              color: var(--tui-primary);
            }
          }

          button {
            display: flex;
            align-items: center;
            gap: 4px;
          }
        }

        .tui-select {
          margin-bottom: 12px;
        }

        .template-info {
          display: flex;
          align-items: center;
          gap: 8px;
          margin: 12px 0 0 0;
          padding: 12px;
          background: var(--tui-success-bg);
          border-radius: 6px;
          font-size: 14px;
          color: var(--tui-success);

          .success-icon {
            font-size: 18px;
            color: var(--tui-success);
          }

          strong {
            color: var(--tui-success);
            font-weight: 600;
          }
        }
      }

      .processing-options {
        margin-top: 24px;
        padding: 20px;
        background: var(--tui-base-02);
        border-radius: 8px;
        border: 1px solid var(--tui-base-04);
      }

      .options-title {
        margin: 0 0 20px 0;
        color: var(--tui-text-01);
        font-size: 16px;
        font-weight: 600;
      }

      .checkbox-group {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        margin-top: 8px;
      }

      .shortlink-days {
        margin-top: 16px;
        padding-left: 24px;
      }

      .tui-select {
        width: 100%;
        padding: 12px 16px;
        border: 1px solid var(--tui-base-04);
        border-radius: 8px;
        background: var(--tui-base-01);
        color: var(--tui-text-01);
        font-size: 14px;
        font-family: inherit;
        cursor: pointer;
        transition: all 0.2s ease;

        &:hover {
          border-color: var(--tui-base-05);
        }

        &:focus {
          outline: none;
          border-color: var(--tui-primary);
          box-shadow: 0 0 0 3px rgba(var(--tui-primary-rgb), 0.1);
        }
      }

      .tui-slider {
        width: 100%;
        height: 6px;
        border-radius: 3px;
        background: var(--tui-base-04);
        outline: none;
        cursor: pointer;
        appearance: none;

        &::-webkit-slider-thumb {
          appearance: none;
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: var(--tui-primary);
          cursor: pointer;
          transition: all 0.2s ease;

          &:hover {
            transform: scale(1.2);
          }
        }

        &::-moz-range-thumb {
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: var(--tui-primary);
          cursor: pointer;
          border: none;
          transition: all 0.2s ease;

          &:hover {
            transform: scale(1.2);
          }
        }
      }

      .upload-progress {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 48px;
        gap: 16px;
        color: var(--tui-text-02);

        h3 {
          margin: 16px 0 0 0;
        }

        p {
          margin: 8px 0;
        }
      }

      .progress-info {
        text-align: center;
        margin-top: 16px;

        p {
          font-size: 14px;
          color: var(--tui-text-03);
        }
      }

      .upload-results {
        display: flex;
        flex-direction: column;
        gap: 24px;
      }

      .notification {
        margin-bottom: 16px;
      }

      .result-summary {
        h3 {
          margin-bottom: 8px;
        }

        p {
          margin: 8px 0;
          font-family: monospace;
          font-size: 13px;
        }
      }

      .result-section {
        background: var(--tui-base-01);
        border-radius: 8px;
        padding: 20px;
      }

      .section-title {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 16px;
        font-weight: 600;

        tui-icon {
          font-size: 20px;
        }
      }

      .success-title {
        color: var(--tui-positive);
      }

      .error-title {
        color: var(--tui-negative);
      }

      .file-results {
        list-style: none;
        padding: 0;
        margin: 0;
      }

      .file-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 12px;
        margin-bottom: 4px;
        border-radius: 4px;
        font-size: 14px;

        tui-icon {
          font-size: 16px;
        }

        &.success {
          color: var(--tui-positive);
          background: var(--tui-positive-bg-hover);
        }

        &.error {
          color: var(--tui-negative);
          background: var(--tui-negative-bg-hover);
        }
      }

      .action-buttons {
        display: flex;
        gap: 16px;
        justify-content: center;
        margin-top: 24px;

        button {
          tui-icon {
            margin-left: 8px;
          }
        }
      }

      .error-content {
        h3 {
          margin-bottom: 8px;
        }

        p {
          margin: 8px 0;
        }
      }

      input[type="file"] {
        display: none;
      }

      /* Checking duplicates */
      .checking-duplicates {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 48px;
        gap: 16px;
        color: var(--tui-text-02);

        h3 {
          margin: 16px 0 0 0;
        }

        p {
          margin: 8px 0;
        }
      }

      /* File configuration */
      .file-configuration {
        display: flex;
        flex-direction: column;
        gap: 24px;

        h3 {
          margin: 0;
          font-size: 20px;
          font-weight: 600;
          color: var(--tui-text-01);
        }

        .config-subtitle {
          margin: -8px 0 0 0;
          font-size: 14px;
          color: var(--tui-text-03);
        }
      }

      .file-configs-list {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }

      .file-config-item {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 16px;
        background: var(--tui-base-01);
        border: 1px solid var(--tui-base-04);
        border-radius: 8px;
        transition: all 0.2s ease;

        &:hover {
          border-color: var(--tui-base-05);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
      }

      .file-info-section {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        flex: 0 0 250px;
      }

      .file-details {
        display: flex;
        flex-direction: column;
        gap: 4px;
        min-width: 0;

        .file-name {
          font-weight: 500;
          color: var(--tui-text-01);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .file-size {
          font-size: 12px;
          color: var(--tui-text-03);
        }

        .existing-project-info {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 13px;
          color: var(--tui-warning);
          margin-top: 4px;

          tui-icon {
            font-size: 14px;
          }
        }
      }

      .file-actions-section {
        display: flex;
        gap: 16px;
        flex: 1;
        align-items: center;

        .radio-option {
          display: flex;
          align-items: center;
          gap: 8px;
          cursor: pointer;
          font-size: 14px;
          color: var(--tui-text-02);
          transition: color 0.2s ease;
          position: relative;

          &:hover {
            color: var(--tui-text-01);
          }

          &.recommended {
            color: var(--tui-primary);
            font-weight: 500;
          }

          input[type="radio"] {
            cursor: pointer;

            &:disabled {
              cursor: not-allowed;
              opacity: 0.5;
            }
          }
        }

        .recommended-badge {
          font-size: 11px;
          padding: 2px 6px;
          background: var(--tui-primary);
          color: white;
          border-radius: 4px;
          margin-left: 4px;
        }
      }

      /* Directory Scan */
      .directory-scan-section {
        margin-top: 24px;
        padding-top: 24px;
        border-top: 1px solid var(--tui-base-04);
      }

      .toggle-directory-btn {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        font-size: 14px;
        color: var(--tui-text-02);

        &:hover {
          color: var(--tui-text-01);
        }

        tui-icon {
          font-size: 16px;
        }
      }

      .directory-scan-content {
        margin-top: 16px;
        padding: 20px;
        background: var(--tui-base-01);
        border-radius: 8px;
        border: 1px solid var(--tui-base-04);
      }

      .directory-hint {
        margin: 0 0 16px 0;
        font-size: 13px;
        color: var(--tui-text-03);
      }

      .directory-form {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }

      .scanned-files-results {
        margin-top: 24px;
        padding-top: 24px;
        border-top: 1px solid var(--tui-base-04);

        h4 {
          margin: 0 0 16px 0;
          color: var(--tui-text-01);
          font-size: 15px;
          font-weight: 600;
        }
      }

      .scanned-files-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;

        h4 {
          margin: 0;
          color: var(--tui-text-01);
          font-size: 15px;
          font-weight: 600;
        }
      }

      .selection-buttons {
        display: flex;
        gap: 8px;

        button {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          font-size: 13px;

          tui-icon {
            font-size: 14px;
          }
        }
      }

      .scanned-files-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-bottom: 16px;
      }

      .scanned-file-item {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 12px;
        background: var(--tui-base-02);
        border-radius: 6px;
        border: 1px solid var(--tui-base-04);
        transition: all 0.2s ease;

        &:hover {
          border-color: var(--tui-base-05);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }

        .checkbox-label {
          display: flex;
          align-items: center;
          margin: 0;
          padding: 0;

          input[type="checkbox"] {
            margin: 0;
            cursor: pointer;
          }
        }

        tui-icon {
          font-size: 20px;
          color: var(--tui-primary);
          flex-shrink: 0;
          margin-top: 2px;
        }
      }

      .import-section {
        margin-top: 20px;
        display: flex;
        justify-content: center;

        button {
          display: flex;
          align-items: center;
          gap: 8px;

          tui-icon {
            font-size: 18px;
          }
        }
      }

      .scanned-file-info {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 4px;

        .file-name {
          font-weight: 500;
          color: var(--tui-text-01);
          font-size: 14px;
        }

        .file-path {
          font-size: 12px;
          color: var(--tui-text-03);
          font-family: monospace;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .file-meta {
          font-size: 12px;
          color: var(--tui-text-03);
        }
      }

      .more-files-note {
        padding: 12px;
        text-align: center;
        font-size: 13px;
        color: var(--tui-text-03);
        background: var(--tui-base-02);
        border-radius: 6px;
      }
    `,
  ],
})
export class BatchUploadComponent implements OnInit, OnDestroy {
  private router = inject(Router);
  private apiService = inject(ApiService);
  private errorMessageService = inject(ErrorMessageService);
  private loadingService = inject(LoadingService);
  private subscription?: Subscription;

  // Form controls
  filesControl = new FormControl<File[] | null>(null);
  batchForm = new FormGroup({
    batchName: new FormControl<string>(''),
    parallelWorkers: new FormControl<number>(1, [Validators.min(1), Validators.max(8)]),
    autoProcess: new FormControl<boolean>(false),
    // Processing options
    groupBy: new FormControl<string>('model'),
    visualizeFloorPlans: new FormControl<boolean>(true),
    showAzimuthArrows: new FormControl<boolean>(true),
    apOpacity: new FormControl<number>(60),
    includeTextNotes: new FormControl<boolean>(true),
    includePictureNotes: new FormControl<boolean>(true),
    includeCableNotes: new FormControl<boolean>(true),
    // Output formats (multi-select)
    formatCsv: new FormControl<boolean>(true),
    formatExcel: new FormControl<boolean>(true),
    formatHtml: new FormControl<boolean>(true),
    formatPdf: new FormControl<boolean>(true),
    formatJson: new FormControl<boolean>(true),
    // Short link options
    createShortLink: new FormControl<boolean>(true),
    shortLinkExpireDays: new FormControl<number>(120, [Validators.min(1), Validators.max(365)]),
  });

  // Signals for reactive state
  selectedFiles = signal<File[]>([]);
  fileConfigs = signal<BatchFileConfig[]>([]);
  showConfigurationStep = signal(false);
  checkingDuplicates = signal(false);
  uploadedFiles = signal<TuiFileLike[]>([]);
  uploadResponse = signal<BatchUploadResponse | null>(null);
  uploading = signal(false);
  error = signal<string | null>(null);

  // Directory scan signals
  showDirectoryScan = signal(false);
  scanningDirectory = signal(false);
  scannedFiles = signal<ScannedFile[]>([]);
  directoryPath = signal<string>('');
  recursiveScan = signal(false);
  selectedScannedFiles = signal<Set<string>>(new Set()); // Track selected file paths
  importingFromPaths = signal(false);

  // Template signals
  templates = signal<BatchTemplate[]>([]);
  selectedTemplateId = signal<string | null>(null);
  loadingTemplates = signal(false);

  ngOnInit(): void {
    // Load templates
    this.loadTemplates();
    console.log('BatchUploadComponent initialized');
    // Subscribe to file control changes
    this.subscription = this.filesControl.valueChanges.subscribe((value) => {
      console.log('Files control value changed:', value);
      console.log('Value type:', typeof value);
      console.log('Is Array:', Array.isArray(value));

      if (!value) {
        return;
      }

      // TuiFiles может возвращать разные типы в зависимости от версии
      let files: File[] = [];

      if (Array.isArray(value)) {
        // Если это массив, извлекаем File объекты
        files = value.map(item => {
          if (item instanceof File) {
            return item;
          }
          // TuiFileLike может иметь свойство 'file'
          return (item as any).file || item;
        }).filter(f => f instanceof File);
      } else if ((value as any) instanceof File) {
        files = [value as File];
      } else if ((value as any)?.file instanceof File) {
        files = [(value as any).file];
      }

      console.log('Extracted files:', files);
      if (files.length > 0) {
        this.onFilesSelect(files);
      }
    });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }

  onFilesSelect(files: File[]): void {
    console.log('onFilesSelect called with', files.length, 'files');

    const validFiles: File[] = [];
    const invalidFiles: string[] = [];
    const maxSize = 500 * 1024 * 1024; // 500 MB

    files.forEach((file) => {
      // Validate file extension
      if (!file.name.toLowerCase().endsWith('.esx')) {
        console.error('Invalid file extension:', file.name);
        invalidFiles.push(`${file.name} (invalid extension)`);
        return;
      }

      // Validate file size
      if (file.size > maxSize) {
        console.error('File too large:', file.name, file.size);
        invalidFiles.push(`${file.name} (too large)`);
        return;
      }

      validFiles.push(file);
    });

    if (invalidFiles.length > 0) {
      this.error.set(
        `The following files were rejected:\n${invalidFiles.join('\n')}\n\nOnly .esx files under 500 MB are supported.`
      );
    }

    if (validFiles.length > 0) {
      this.selectedFiles.set(validFiles);
      this.error.set(null);
    } else if (invalidFiles.length === files.length) {
      this.filesControl.reset();
    }
  }

  removeFile(index: number): void {
    const files = [...this.selectedFiles()];
    files.splice(index, 1);
    this.selectedFiles.set(files);

    if (files.length === 0) {
      this.filesControl.reset();
    }
  }

  clearSelection(): void {
    this.selectedFiles.set([]);
    this.filesControl.reset();
    this.error.set(null);
  }

  startUpload(): void {
    const files = this.selectedFiles();
    if (files.length === 0) {
      this.error.set('Please select at least one file to upload');
      return;
    }

    // Check for duplicates first
    this.checkFilesForDuplicates();
  }

  startUploadWithConfigs(): void {
    const configs = this.fileConfigs();
    if (configs.length === 0) {
      this.error.set('Please select at least one file to upload');
      return;
    }

    const batchName = this.batchForm.value.batchName || undefined;
    const parallelWorkers = this.batchForm.value.parallelWorkers || 1;
    const autoProcess = this.batchForm.value.autoProcess ?? false;

    console.log('Starting batch upload with', configs.length, 'files');
    console.log('Batch name:', batchName);
    console.log('Parallel workers:', parallelWorkers);
    console.log('Auto process:', autoProcess);

    this.uploading.set(true);
    this.showConfigurationStep.set(false);
    this.error.set(null);

    // Show loading
    this.loadingService.show('Uploading batch...', 'upload', 0);

    // Always prepare processing options (they will be saved with the batch)
    const processingOptions: ProcessingRequest = {
      group_by: this.batchForm.value.groupBy || 'model',
      output_formats: this.getSelectedFormats(),
      visualize_floor_plans: this.batchForm.value.visualizeFloorPlans ?? true,
      show_azimuth_arrows: this.batchForm.value.showAzimuthArrows ?? true,
      ap_opacity: (this.batchForm.value.apOpacity ?? 60) / 100,
      include_text_notes: this.batchForm.value.includeTextNotes ?? true,
      include_picture_notes: this.batchForm.value.includePictureNotes ?? true,
      include_cable_notes: this.batchForm.value.includeCableNotes ?? true,
      create_short_link: this.batchForm.value.createShortLink ?? false,
      short_link_days: this.batchForm.value.shortLinkExpireDays ?? 7,
    };

    // Get files and their actions from configs
    const files = configs.map(c => c.file);
    const fileActions = configs.map(c => ({
      filename: c.file.name,
      action: c.action,
      existingProjectId: c.existingProject?.project_id
    }));

    this.apiService
      .uploadBatchWithActions(files, fileActions, batchName, parallelWorkers, processingOptions, autoProcess)
      .pipe(
        finalize(() => {
          console.log('Batch upload finalized');
          this.uploading.set(false);
          this.loadingService.hide();
        })
      )
      .subscribe({
        next: (event: HttpEvent<BatchUploadResponse>) => {
          // Handle different HTTP event types
          if (event.type === HttpEventType.UploadProgress && event.total) {
            // Calculate and update progress
            const progress = Math.round((100 * event.loaded) / event.total);
            console.log(`Batch upload progress: ${progress}%`);
            this.loadingService.setProgress(progress);
          } else if (event.type === HttpEventType.Response) {
            // Upload complete, process response
            console.log('Batch upload success:', event.body);
            this.uploadedFiles.set(files);
            this.uploadResponse.set(event.body!);
          }
        },
        error: (err: any) => {
          console.error('Batch upload error:', err);
          this.errorMessageService.logError(err, 'Batch Upload');
          const errorMessage = this.errorMessageService.getErrorMessage(err);
          const suggestion = this.errorMessageService.getSuggestion(err);
          this.error.set(suggestion ? `${errorMessage}\n\n${suggestion}` : errorMessage);
        },
      });
  }

  viewBatchDetails(): void {
    const response = this.uploadResponse();
    if (response?.batch_id) {
      // Navigate to batch details page
      this.router.navigate(['/admin/batches', response.batch_id]);
    }
  }

  resetUpload(): void {
    this.filesControl.reset();
    this.selectedFiles.set([]);
    this.uploadedFiles.set([]);
    this.uploadResponse.set(null);
    this.error.set(null);
    this.batchForm.reset({
      batchName: '',
      parallelWorkers: 1,
      autoProcess: false,
      groupBy: 'model',
      visualizeFloorPlans: true,
      showAzimuthArrows: true,
      apOpacity: 60,
      includeTextNotes: true,
      includePictureNotes: true,
      includeCableNotes: true,
      formatCsv: true,
      formatExcel: true,
      formatHtml: true,
      formatPdf: true,
      formatJson: true,
      createShortLink: true,
      shortLinkExpireDays: 120,
    });
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  }

  /**
   * Extract project name from .esx file (ZIP archive).
   * .esx files are ZIP archives containing project.json with project metadata.
   *
   * @param file - The .esx file to extract project name from
   * @returns Project name (title) or null if extraction fails
   */
  private async extractProjectName(file: File): Promise<string | null> {
    try {
      // Read file as ArrayBuffer
      const arrayBuffer = await file.arrayBuffer();

      // Load ZIP archive
      const zip = await JSZip.loadAsync(arrayBuffer);

      // Check if project.json exists
      const projectJsonFile = zip.file('project.json');
      if (!projectJsonFile) {
        console.warn(`project.json not found in ${file.name}`);
        return null;
      }

      // Read and parse project.json
      const projectJsonText = await projectJsonFile.async('text');
      const projectData = JSON.parse(projectJsonText);

      // Extract project title (try 'title' first, then fall back to 'name')
      const projectInfo = projectData?.project;
      if (!projectInfo) {
        console.warn(`No project info found in project.json of ${file.name}`);
        return null;
      }

      return projectInfo.title || projectInfo.name || null;

    } catch (error) {
      console.error(`Error extracting project name from ${file.name}:`, error);
      return null;
    }
  }

  async checkFilesForDuplicates(): Promise<void> {
    const files = this.selectedFiles();
    if (files.length === 0) return;

    this.checkingDuplicates.set(true);
    this.error.set(null);

    // Initialize file configs
    const configs: BatchFileConfig[] = files.map(file => ({
      file,
      action: 'new' as const,
      checkingDuplicate: true
    }));

    this.fileConfigs.set(configs);

    // Check each file for duplicates
    for (let i = 0; i < configs.length; i++) {
      const config = configs[i];
      try {
        // Extract project name from .esx file (ZIP archive)
        const projectName = await this.extractProjectName(config.file);

        // If we couldn't extract project name, fall back to filename
        const nameToCheck = projectName || config.file.name.replace(/\.esx$/i, '');

        // Search for existing project by project name
        const existingProjects = await this.apiService.listProjects().toPromise();
        const existing = existingProjects?.find((p: ProjectListItem) => {
          // Compare by project_name (title) - this is the main comparison
          if (p.project_name && nameToCheck) {
            return p.project_name.toLowerCase() === nameToCheck.toLowerCase();
          }
          return false;
        });

        config.projectName = nameToCheck;
        config.existingProject = existing;
        config.action = existing ? 'update' : 'new';
        config.checkingDuplicate = false;

        // Update the config
        this.fileConfigs.set([...this.fileConfigs()]);

      } catch (error) {
        console.error(`Error checking duplicate for ${config.file.name}:`, error);
        config.checkingDuplicate = false;
        config.action = 'new';
        this.fileConfigs.set([...this.fileConfigs()]);
      }
    }

    this.checkingDuplicates.set(false);
    this.showConfigurationStep.set(true);
  }

  proceedWithConfiguration(): void {
    // Filter out skipped files
    const configs = this.fileConfigs().filter(c => c.action !== 'skip');

    if (configs.length === 0) {
      this.error.set('All files are set to skip. Please select at least one file to upload.');
      return;
    }

    // Update fileConfigs to only include non-skipped files
    this.fileConfigs.set(configs);

    // Proceed to upload
    this.startUploadWithConfigs();
  }

  cancelConfiguration(): void {
    this.showConfigurationStep.set(false);
    this.fileConfigs.set([]);
    this.clearSelection();
  }

  removeFileConfig(index: number): void {
    const configs = [...this.fileConfigs()];
    configs.splice(index, 1);
    this.fileConfigs.set(configs);

    if (configs.length === 0) {
      this.cancelConfiguration();
    }
  }

  getSelectedFormats(): string[] {
    const formats: string[] = [];
    if (this.batchForm.value.formatCsv) formats.push('csv');
    if (this.batchForm.value.formatExcel) formats.push('excel');
    if (this.batchForm.value.formatHtml) formats.push('html');
    if (this.batchForm.value.formatPdf) formats.push('pdf');
    if (this.batchForm.value.formatJson) formats.push('json');
    return formats.length > 0 ? formats : ['csv', 'excel', 'html'];
  }

  getNonSkippedFilesCount(): number {
    return this.fileConfigs().filter((c: BatchFileConfig) => c.action !== 'skip').length;
  }

  // Directory scan methods
  toggleDirectoryScan(): void {
    this.showDirectoryScan.update(v => !v);
    if (!this.showDirectoryScan()) {
      // Reset scan state when closing
      this.scannedFiles.set([]);
      this.directoryPath.set('');
    }
  }

  startDirectoryScan(): void {
    const path = this.directoryPath();
    if (!path || path.trim() === '') {
      this.error.set('Please enter a directory path');
      return;
    }

    this.scanningDirectory.set(true);
    this.error.set(null);
    this.scannedFiles.set([]);

    this.loadingService.show('Scanning directory...', 'default', 0);

    this.apiService
      .scanDirectory(path, this.recursiveScan())
      .pipe(finalize(() => {
        this.scanningDirectory.set(false);
        this.loadingService.hide();
      }))
      .subscribe({
        next: (response: DirectoryScanResponse) => {
          console.log('Directory scan success:', response);
          this.scannedFiles.set(response.files);
          if (response.files.length === 0) {
            this.error.set(`No .esx files found in directory: ${response.directory}`);
          }
        },
        error: (err: any) => {
          console.error('Directory scan error:', err);
          this.errorMessageService.logError(err, 'Directory Scan');
          const errorMessage = this.errorMessageService.getErrorMessage(err);
          this.error.set(errorMessage);
        }
      });
  }

  toggleFileSelection(filepath: string): void {
    const selected = this.selectedScannedFiles();
    const newSelected = new Set(selected);
    if (newSelected.has(filepath)) {
      newSelected.delete(filepath);
    } else {
      newSelected.add(filepath);
    }
    this.selectedScannedFiles.set(newSelected);
  }

  selectAllScannedFiles(): void {
    const allPaths = this.scannedFiles().map(f => f.filepath);
    this.selectedScannedFiles.set(new Set(allPaths));
  }

  deselectAllScannedFiles(): void {
    this.selectedScannedFiles.set(new Set());
  }

  importSelectedFiles(): void {
    const selectedPaths = Array.from(this.selectedScannedFiles());
    if (selectedPaths.length === 0) {
      this.error.set('Please select at least one file to import');
      return;
    }

    const batchName = this.batchForm.value.batchName || undefined;
    const parallelWorkers = this.batchForm.value.parallelWorkers || 1;
    const autoProcess = this.batchForm.value.autoProcess ?? false;

    // Prepare processing options
    const processingOptions: ProcessingRequest = {
      group_by: this.batchForm.value.groupBy || 'model',
      output_formats: this.getSelectedFormats(),
      visualize_floor_plans: this.batchForm.value.visualizeFloorPlans ?? true,
      show_azimuth_arrows: this.batchForm.value.showAzimuthArrows ?? true,
      ap_opacity: (this.batchForm.value.apOpacity ?? 60) / 100,
      include_text_notes: this.batchForm.value.includeTextNotes ?? true,
      include_picture_notes: this.batchForm.value.includePictureNotes ?? true,
      include_cable_notes: this.batchForm.value.includeCableNotes ?? true,
      create_short_link: this.batchForm.value.createShortLink ?? false,
      short_link_days: this.batchForm.value.shortLinkExpireDays ?? 7,
    };

    console.log('Importing', selectedPaths.length, 'files from server paths');
    console.log('Selected paths:', selectedPaths);

    this.importingFromPaths.set(true);
    this.error.set(null);
    this.loadingService.show('Importing files from server...', 'upload', 0);

    this.apiService
      .importFromPaths(selectedPaths, batchName, parallelWorkers, processingOptions, autoProcess)
      .pipe(
        finalize(() => {
          this.importingFromPaths.set(false);
          this.loadingService.hide();
        })
      )
      .subscribe({
        next: (response: BatchUploadResponse) => {
          console.log('Import from paths success:', response);
          this.uploadResponse.set(response);
          this.selectedScannedFiles.set(new Set());
          this.scannedFiles.set([]);
          this.showDirectoryScan.set(false);
        },
        error: (err: any) => {
          console.error('Import from paths error:', err);
          this.errorMessageService.logError(err, 'Import from Paths');
          const errorMessage = this.errorMessageService.getErrorMessage(err);
          const suggestion = this.errorMessageService.getSuggestion(err);
          this.error.set(suggestion ? `${errorMessage}\n\n${suggestion}` : errorMessage);
        }
      });
  }

  // Template getters for template binding
  get systemTemplates(): BatchTemplate[] {
    return this.templates().filter(t => t.is_system);
  }

  get customTemplates(): BatchTemplate[] {
    return this.templates().filter(t => !t.is_system);
  }

  get hasSystemTemplates(): boolean {
    return this.systemTemplates.length > 0;
  }

  get hasCustomTemplates(): boolean {
    return this.customTemplates.length > 0;
  }

  get selectedTemplateName(): string | null {
    const template = this.templates().find(t => t.template_id === this.selectedTemplateId());
    return template ? template.name : null;
  }

  /**
   * Handle template selection change.
   */
  onTemplateChange(templateId: string): void {
    if (!templateId || templateId === '') {
      this.clearTemplate();
      return;
    }
    this.selectedTemplateId.set(templateId);
    this.applyTemplate(templateId);
  }

  /**
   * Load all available templates from backend.
   */
  loadTemplates(): void {
    this.loadingTemplates.set(true);
    this.apiService.listTemplates(true).subscribe({
      next: (templates) => {
        this.templates.set(templates);
        this.loadingTemplates.set(false);
        console.log('Loaded templates:', templates);
      },
      error: (err) => {
        console.error('Error loading templates:', err);
        this.errorMessageService.logError(err, 'Load Templates');
        this.loadingTemplates.set(false);
      },
    });
  }

  /**
   * Apply selected template to batch form.
   */
  applyTemplate(templateId: string): void {
    const template = this.templates().find(t => t.template_id === templateId);
    if (!template) {
      console.warn('Template not found:', templateId);
      return;
    }

    console.log('Applying template:', template.name, template.processing_options);

    // Apply processing options from template
    const options = template.processing_options;

    // Group by
    if (options.group_by) {
      this.batchForm.patchValue({ groupBy: options.group_by });
    }

    // Visualization options
    this.batchForm.patchValue({
      visualizeFloorPlans: options.visualize_floor_plans ?? true,
      showAzimuthArrows: options.show_azimuth_arrows ?? false,
      apOpacity: options.ap_opacity ? Math.round(options.ap_opacity * 100) : 60,
    });

    // Notes options
    this.batchForm.patchValue({
      includeTextNotes: options.include_text_notes ?? false,
      includePictureNotes: options.include_picture_notes ?? false,
      includeCableNotes: options.include_cable_notes ?? false,
    });

    // Output formats
    const formats = options.output_formats || [];
    this.batchForm.patchValue({
      formatCsv: formats.includes('csv'),
      formatExcel: formats.includes('excel'),
      formatHtml: formats.includes('html'),
      formatPdf: formats.includes('pdf'),
      formatJson: formats.includes('json'),
    });

    // Parallel workers
    this.batchForm.patchValue({
      parallelWorkers: template.parallel_workers || 1,
    });

    // Short link options (keep defaults, template doesn't control this)
    // User can still change these if needed

    console.log('Template applied successfully:', template.name);
  }

  /**
   * Clear template selection and reset to defaults.
   */
  clearTemplate(): void {
    this.selectedTemplateId.set(null);
    // Reset form to defaults
    this.batchForm.patchValue({
      groupBy: 'model',
      visualizeFloorPlans: true,
      showAzimuthArrows: true,
      apOpacity: 60,
      includeTextNotes: true,
      includePictureNotes: true,
      includeCableNotes: true,
      formatCsv: true,
      formatExcel: true,
      formatHtml: true,
      formatPdf: true,
      formatJson: true,
      parallelWorkers: 1,
    });
    console.log('Template cleared, form reset to defaults');
  }
}
