import { Component, inject, signal, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TuiButton, TuiIcon, TuiLink, TuiNotification, TuiLoader } from '@taiga-ui/core';
import { TuiFiles, type TuiFileLike } from '@taiga-ui/kit';
import { ApiService } from '../../../core/services/api.service';
import { finalize, Subscription } from 'rxjs';

@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    TuiButton,
    TuiIcon,
    TuiLink,
    TuiFiles,
    TuiNotification,
    TuiLoader,
  ],
  template: `
    <div class="upload-container">
      <div class="page-header">
        <h2 class="page-title">Upload Project</h2>
      </div>

      <div class="upload-content">
        <!-- Upload area -->
        <label *ngIf="!uploadedFile()" tuiInputFiles class="upload-label">
          <input
            tuiInputFiles
            type="file"
            accept=".esx"
            [formControl]="fileControl"
            [disabled]="uploading()"
          />
          <ng-template let-dragged>
            <div class="upload-area" [class.dragging]="dragged">
              <tui-icon
                [icon]="dragged ? '@tui.droplet' : '@tui.upload'"
                class="upload-icon"
              ></tui-icon>
              <h3>{{ dragged ? 'Drop your file here!' : 'Drag & Drop your .esx file here' }}</h3>
              <p>or</p>
              <button tuiButton appearance="secondary" size="m" [disabled]="uploading()">
                Browse Files
              </button>
              <p class="upload-hint">Only .esx files are supported (max 500 MB)</p>
            </div>
          </ng-template>
        </label>

        <!-- Loading state -->
        <div *ngIf="uploading()" class="upload-progress">
          <tui-loader size="l"></tui-loader>
          <p>Uploading file...</p>
        </div>

        <!-- Success state -->
        <div *ngIf="uploadedFile()" class="upload-success">
          <tui-notification status="success" class="notification">
            <div class="success-content">
              <h3>File uploaded successfully!</h3>
              <p>Project ID: {{ uploadResponse()?.project_id }}</p>
              <p *ngIf="uploadResponse()?.short_link">
                Short link:
                <a tuiLink [href]="getShortLinkUrl()" target="_blank">
                  {{ uploadResponse()?.short_link }}
                </a>
              </p>
            </div>
          </tui-notification>

          <tui-files class="uploaded-file">
            <tui-file
              [file]="uploadedFile()!"
              state="normal"
              (remove)="resetUpload()"
            ></tui-file>
          </tui-files>

          <div class="action-buttons">
            <button
              tuiButton
              appearance="primary"
              size="l"
              (click)="proceedToProcessing()"
            >
              Configure Processing
              <tui-icon icon="@tui.arrow-right"></tui-icon>
            </button>
            <button
              tuiButton
              appearance="secondary"
              size="l"
              (click)="resetUpload()"
            >
              Upload Another File
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
      .upload-container {
        width: 100%;
      }

      .page-header {
        margin-bottom: 24px;
      }

      .page-title {
        margin: 0;
        font-size: 24px;
        font-weight: 600;
        color: var(--tui-text-01);
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

      p {
        margin: 16px 0;
        color: var(--tui-text-02);
      }

      .upload-hint {
        margin-top: 24px;
        font-size: 14px;
        color: var(--tui-text-03);
      }

      .upload-progress {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 48px;
        gap: 16px;
        color: var(--tui-text-02);
      }

      .upload-success {
        display: flex;
        flex-direction: column;
        gap: 24px;
      }

      .notification {
        margin-bottom: 16px;
      }

      .success-content,
      .error-content {
        h3 {
          margin-bottom: 8px;
        }

        p {
          margin: 8px 0;
        }
      }

      .uploaded-file {
        margin: 16px 0;
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

      input[type="file"] {
        display: none;
      }
    `,
  ],
})
export class UploadComponent implements OnInit, OnDestroy {
  private router = inject(Router);
  private apiService = inject(ApiService);
  private subscription?: Subscription;

  // Form control for file input
  fileControl = new FormControl<File | null>(null);

  // Signals for reactive state
  uploadedFile = signal<TuiFileLike | null>(null);
  uploadResponse = signal<any>(null);
  uploading = signal(false);
  error = signal<string | null>(null);

  ngOnInit(): void {
    console.log('UploadComponent initialized');
    // Subscribe to file control changes
    this.subscription = this.fileControl.valueChanges.subscribe((file) => {
      console.log('File control value changed:', file);
      if (file) {
        this.onFileSelect(file);
      }
    });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }

  onFileSelect(file: File): void {
    console.log('onFileSelect called with file:', file.name);
    console.log('File size:', file.size, 'bytes');

    // Validate file extension
    if (!file.name.toLowerCase().endsWith('.esx')) {
      console.error('Invalid file extension');
      this.error.set('Please select a valid .esx file');
      this.fileControl.reset();
      return;
    }

    // Validate file size (500 MB limit)
    const maxSize = 500 * 1024 * 1024;
    if (file.size > maxSize) {
      console.error('File too large:', file.size);
      this.error.set('File size exceeds 500 MB limit');
      this.fileControl.reset();
      return;
    }

    console.log('Starting upload...');
    // Upload file
    this.uploadFile(file);
  }

  private uploadFile(file: File): void {
    console.log('uploadFile method called with file:', file.name);
    this.uploading.set(true);
    this.error.set(null);

    console.log('Calling apiService.uploadFile...');
    this.apiService
      .uploadFile(file)
      .pipe(
        finalize(() => {
          console.log('Upload finalized');
          this.uploading.set(false);
        })
      )
      .subscribe({
        next: (response) => {
          console.log('Upload success:', response);
          this.uploadedFile.set(file);
          this.uploadResponse.set(response);
        },
        error: (err) => {
          console.error('Upload error:', err);
          this.error.set(
            err.error?.detail || 'Failed to upload file. Please try again.'
          );
          this.fileControl.reset();
        },
      });
  }

  proceedToProcessing(): void {
    const response = this.uploadResponse();
    if (response?.project_id) {
      // Navigate to processing page with project ID
      this.router.navigate(['/admin/processing'], {
        queryParams: { projectId: response.project_id },
      });
    }
  }

  resetUpload(): void {
    this.fileControl.reset();
    this.uploadedFile.set(null);
    this.uploadResponse.set(null);
    this.error.set(null);
  }

  getShortLinkUrl(): string {
    const shortLink = this.uploadResponse()?.short_link;
    return shortLink ? `/s/${shortLink}` : '';
  }
}
