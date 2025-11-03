import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { Router } from '@angular/router';
import { ReactiveFormsModule } from '@angular/forms';
import { of, throwError } from 'rxjs';
import { UploadComponent } from './upload.component';
import { ApiService } from '../../../core/services/api.service';
import { TuiButton, TuiIcon, TuiLink, TuiNotification, TuiLoader } from '@taiga-ui/core';
import { TuiFiles } from '@taiga-ui/kit';

describe('UploadComponent', () => {
  let component: UploadComponent;
  let fixture: ComponentFixture<UploadComponent>;
  let mockApiService: jasmine.SpyObj<ApiService>;
  let router: Router;

  beforeEach(async () => {
    mockApiService = jasmine.createSpyObj('ApiService', ['uploadFile']);
    // Setup default mock return value to prevent undefined errors
    mockApiService.uploadFile.and.returnValue(of({
      project_id: 'default-id',
      message: 'Success',
      short_link: 'default',
    }));

    await TestBed.configureTestingModule({
      imports: [
        UploadComponent,
        ReactiveFormsModule,
        RouterTestingModule.withRoutes([]),
        TuiButton,
        TuiIcon,
        TuiLink,
        TuiFiles,
        TuiNotification,
        TuiLoader,
      ],
      providers: [
        { provide: ApiService, useValue: mockApiService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UploadComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  afterEach(() => {
    component.ngOnDestroy();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('Initialization', () => {
    it('should initialize file control with null value', () => {
      expect(component.fileControl.value).toBeNull();
    });

    it('should initialize all signals with default values', () => {
      expect(component.uploadedFile()).toBeNull();
      expect(component.uploadResponse()).toBeNull();
      expect(component.uploading()).toBe(false);
      expect(component.error()).toBeNull();
    });

    it('should subscribe to file control changes on init', () => {
      const spy = spyOn(component, 'onFileSelect');
      const file = new File(['content'], 'test.esx', { type: 'application/zip' });

      component.fileControl.setValue(file);

      expect(spy).toHaveBeenCalledWith(file);
    });
  });

  describe('File Selection', () => {
    it('should accept valid .esx file', () => {
      const file = new File(['content'], 'project.esx', { type: 'application/zip' });
      mockApiService.uploadFile.and.returnValue(
        of({ project_id: 'test-id', message: 'Success', short_link: 'abc123' })
      );

      component.onFileSelect(file);

      expect(mockApiService.uploadFile).toHaveBeenCalledWith(file);
      expect(component.error()).toBeNull();
    });

    it('should reject file without .esx extension', () => {
      const file = new File(['content'], 'project.txt', { type: 'text/plain' });

      component.onFileSelect(file);

      expect(mockApiService.uploadFile).not.toHaveBeenCalled();
      expect(component.error()).toBe('Please select a valid .esx file');
      expect(component.fileControl.value).toBeNull();
    });

    it('should accept .esx file with mixed case extension', () => {
      const file = new File(['content'], 'PROJECT.ESX', { type: 'application/zip' });
      mockApiService.uploadFile.and.returnValue(
        of({ project_id: 'test-id', message: 'Success', short_link: 'abc123' })
      );

      component.onFileSelect(file);

      expect(mockApiService.uploadFile).toHaveBeenCalledWith(file);
    });

    it('should reject file larger than 500 MB', () => {
      const largeSize = 501 * 1024 * 1024; // 501 MB
      const file = new File(['x'.repeat(largeSize)], 'large.esx');
      Object.defineProperty(file, 'size', { value: largeSize, writable: false });

      component.onFileSelect(file);

      expect(mockApiService.uploadFile).not.toHaveBeenCalled();
      expect(component.error()).toBe('File size exceeds 500 MB limit');
      expect(component.fileControl.value).toBeNull();
    });

    it('should accept file equal to 500 MB', () => {
      const maxSize = 500 * 1024 * 1024;
      const file = new File(['x'.repeat(maxSize)], 'max.esx');
      Object.defineProperty(file, 'size', { value: maxSize, writable: false });
      mockApiService.uploadFile.and.returnValue(
        of({ project_id: 'test-id', message: 'Success', short_link: 'abc123' })
      );

      component.onFileSelect(file);

      expect(mockApiService.uploadFile).toHaveBeenCalledWith(file);
    });
  });

  describe('File Upload', () => {
    it('should set uploading to false after successful upload', fakeAsync(() => {
      const file = new File(['content'], 'test.esx');
      mockApiService.uploadFile.and.returnValue(of({
        project_id: 'test-id',
        message: 'Success',
        short_link: 'abc123',
      }));

      component.onFileSelect(file);
      tick();

      expect(component.uploading()).toBe(false);
    }));

    it('should update uploadedFile and uploadResponse on success', fakeAsync(() => {
      const file = new File(['content'], 'test.esx');
      const mockResponse = {
        project_id: 'test-project-id',
        message: 'Upload successful',
        short_link: 'abc123',
      };
      mockApiService.uploadFile.and.returnValue(of(mockResponse));

      component.onFileSelect(file);
      tick();

      expect(component.uploadedFile()).toEqual(file);
      expect(component.uploadResponse()).toEqual(mockResponse);
      expect(component.error()).toBeNull();
    }));

    it('should clear error on successful upload', fakeAsync(() => {
      component.error.set('Previous error');
      const file = new File(['content'], 'test.esx');
      mockApiService.uploadFile.and.returnValue(of({
        project_id: 'test-id',
        message: 'Success',
        short_link: 'abc123',
      }));

      component.onFileSelect(file);
      tick();

      expect(component.error()).toBeNull();
    }));

    it('should handle upload error', fakeAsync(() => {
      const file = new File(['content'], 'test.esx');
      const error = { error: { detail: 'Upload failed' } };
      mockApiService.uploadFile.and.returnValue(throwError(() => error));

      component.onFileSelect(file);
      tick();

      expect(component.error()).toBe('Upload failed');
      expect(component.uploading()).toBe(false);
      expect(component.fileControl.value).toBeNull();
    }));

    it('should show generic error message when detail is not provided', fakeAsync(() => {
      const file = new File(['content'], 'test.esx');
      mockApiService.uploadFile.and.returnValue(throwError(() => ({ error: {} })));

      component.onFileSelect(file);
      tick();

      expect(component.error()).toBe('Failed to upload file. Please try again.');
    }));
  });

  describe('Navigation', () => {
    it('should navigate to processing page with project ID', () => {
      const navigateSpy = spyOn(router, 'navigate');
      component.uploadResponse.set({
        project_id: 'test-project-id',
        message: 'Success',
        short_link: 'abc123',
      });

      component.proceedToProcessing();

      expect(navigateSpy).toHaveBeenCalledWith(['/admin/processing'], {
        queryParams: { projectId: 'test-project-id' },
      });
    });

    it('should not navigate if upload response is null', () => {
      const navigateSpy = spyOn(router, 'navigate');
      component.uploadResponse.set(null);

      component.proceedToProcessing();

      expect(navigateSpy).not.toHaveBeenCalled();
    });

    it('should not navigate if project_id is missing', () => {
      const navigateSpy = spyOn(router, 'navigate');
      component.uploadResponse.set({
        message: 'Success',
        short_link: 'abc123',
      });

      component.proceedToProcessing();

      expect(navigateSpy).not.toHaveBeenCalled();
    });
  });

  describe('Reset Upload', () => {
    it('should reset all state when resetUpload is called', () => {
      const file = new File(['content'], 'test.esx');
      component.uploadedFile.set(file);
      component.uploadResponse.set({ project_id: 'test-id', message: 'Success', short_link: 'abc123' });
      component.error.set('Some error');
      component.fileControl.setValue(file);

      component.resetUpload();

      expect(component.fileControl.value).toBeNull();
      expect(component.uploadedFile()).toBeNull();
      expect(component.uploadResponse()).toBeNull();
      expect(component.error()).toBeNull();
    });
  });

  describe('Short Link URL', () => {
    it('should generate correct short link URL', () => {
      component.uploadResponse.set({
        project_id: 'test-id',
        message: 'Success',
        short_link: 'abc123',
      });

      const url = component.getShortLinkUrl();

      expect(url).toBe('/s/abc123');
    });

    it('should return empty string if short_link is missing', () => {
      component.uploadResponse.set({
        project_id: 'test-id',
        message: 'Success',
      });

      const url = component.getShortLinkUrl();

      expect(url).toBe('');
    });

    it('should return empty string if uploadResponse is null', () => {
      component.uploadResponse.set(null);

      const url = component.getShortLinkUrl();

      expect(url).toBe('');
    });
  });

  describe('Component Lifecycle', () => {
    it('should unsubscribe on destroy', () => {
      const subscription = component['subscription'];
      if (subscription) {
        spyOn(subscription, 'unsubscribe');
        component.ngOnDestroy();
        expect(subscription.unsubscribe).toHaveBeenCalled();
      }
    });
  });
});
