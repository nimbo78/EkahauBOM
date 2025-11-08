import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { BatchUploadComponent } from './batch-upload.component';
import { ApiService } from '../../../core/services/api.service';

describe('BatchUploadComponent', () => {
  let component: BatchUploadComponent;
  let fixture: ComponentFixture<BatchUploadComponent>;
  let apiService: jasmine.SpyObj<ApiService>;
  let router: jasmine.SpyObj<Router>;

  beforeEach(async () => {
    const apiServiceSpy = jasmine.createSpyObj('ApiService', ['uploadBatch']);
    const routerSpy = jasmine.createSpyObj('Router', ['navigate']);

    await TestBed.configureTestingModule({
      imports: [BatchUploadComponent, HttpClientTestingModule],
      providers: [
        { provide: ApiService, useValue: apiServiceSpy },
        { provide: Router, useValue: routerSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(BatchUploadComponent);
    component = fixture.componentInstance;
    apiService = TestBed.inject(ApiService) as jasmine.SpyObj<ApiService>;
    router = TestBed.inject(Router) as jasmine.SpyObj<Router>;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize with empty selected files', () => {
    expect(component.selectedFiles()).toEqual([]);
  });

  it('should validate file extensions', () => {
    const invalidFile = new File(['content'], 'test.txt', { type: 'text/plain' });
    component.onFilesSelect([invalidFile]);

    expect(component.selectedFiles()).toEqual([]);
    expect(component.error()).toContain('invalid extension');
  });

  it('should accept valid .esx files', () => {
    const validFile = new File(['content'], 'test.esx', { type: 'application/octet-stream' });
    component.onFilesSelect([validFile]);

    expect(component.selectedFiles().length).toBe(1);
    expect(component.selectedFiles()[0]).toBe(validFile);
  });

  it('should remove file from selection', () => {
    const file1 = new File(['content'], 'test1.esx', { type: 'application/octet-stream' });
    const file2 = new File(['content'], 'test2.esx', { type: 'application/octet-stream' });
    component.onFilesSelect([file1, file2]);

    expect(component.selectedFiles().length).toBe(2);

    component.removeFile(0);

    expect(component.selectedFiles().length).toBe(1);
    expect(component.selectedFiles()[0]).toBe(file2);
  });

  it('should clear all selections', () => {
    const file = new File(['content'], 'test.esx', { type: 'application/octet-stream' });
    component.onFilesSelect([file]);

    component.clearSelection();

    expect(component.selectedFiles()).toEqual([]);
    expect(component.error()).toBeNull();
  });

  it('should reset upload state', () => {
    component.uploadResponse.set({
      batch_id: 'test-batch-id',
      message: 'Test message',
      files_count: 2,
      files_uploaded: ['file1.esx'],
      files_failed: ['file2.esx'],
    });

    component.resetUpload();

    expect(component.uploadResponse()).toBeNull();
    expect(component.selectedFiles()).toEqual([]);
    expect(component.error()).toBeNull();
  });
});
