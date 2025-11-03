import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ApiService } from './api.service';
import {
  ProjectListItem,
  ProjectDetails,
  UploadResponse,
  ProcessingRequest,
  ProcessingFlags,
  ProjectStats,
  ReportsList,
  ProcessingStatus,
} from '../models/project.model';

describe('ApiService', () => {
  let service: ApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ApiService],
    });

    service = TestBed.inject(ApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('Upload endpoints', () => {
    it('should upload a file', () => {
      const mockFile = new File(['content'], 'test.esx', { type: 'application/zip' });
      const mockResponse: UploadResponse = {
        project_id: 'test-project-id',
        message: 'File uploaded successfully',
        short_link: 'abc123',
      };

      service.uploadFile(mockFile).subscribe((response) => {
        expect(response).toEqual(mockResponse);
        expect(response.project_id).toBe('test-project-id');
      });

      const req = httpMock.expectOne('/api/upload');
      expect(req.request.method).toBe('POST');
      expect(req.request.body instanceof FormData).toBe(true);
      req.flush(mockResponse);
    });

    it('should start processing', () => {
      const projectId = 'test-project-id';
      const processingRequest: ProcessingRequest = {
        group_by: 'floor',
        output_formats: ['csv', 'excel'],
        visualize_floor_plans: true,
        show_azimuth_arrows: false,
        ap_opacity: 0.6,
      };

      service.startProcessing(projectId, processingRequest).subscribe((response) => {
        expect(response).toBeTruthy();
      });

      const req = httpMock.expectOne(`/api/upload/${projectId}/process`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(processingRequest);
      req.flush({ message: 'Processing started' });
    });
  });

  describe('Projects endpoints', () => {
    it('should fetch projects list', () => {
      const mockProjects: ProjectListItem[] = [
        {
          project_id: 'project-1',
          project_name: 'Test Project 1',
          filename: 'test1.esx',
          upload_date: '2025-10-31T10:00:00Z',
          processing_status: ProcessingStatus.COMPLETED,
          aps_count: 10,
          short_link: 'abc123',
        },
        {
          project_id: 'project-2',
          project_name: 'Test Project 2',
          filename: 'test2.esx',
          upload_date: '2025-10-31T11:00:00Z',
          processing_status: ProcessingStatus.PENDING,
          aps_count: 15,
          short_link: 'def456',
        },
      ];

      service.listProjects().subscribe((projects) => {
        expect(projects.length).toBe(2);
        expect(projects[0].project_name).toBe('Test Project 1');
        expect(projects[1].processing_status).toBe(ProcessingStatus.PENDING);
      });

      const req = httpMock.expectOne('/api/projects');
      expect(req.request.method).toBe('GET');
      req.flush(mockProjects);
    });

    it('should fetch projects list with filters', () => {
      const mockProjects: ProjectListItem[] = [];

      service.listProjects(ProcessingStatus.COMPLETED, 50, 'test').subscribe((projects) => {
        expect(projects).toEqual(mockProjects);
      });

      const req = httpMock.expectOne((request) =>
        request.url === '/api/projects' &&
        request.params.get('status') === ProcessingStatus.COMPLETED &&
        request.params.get('limit') === '50' &&
        request.params.get('search') === 'test'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockProjects);
    });

    it('should fetch project details', () => {
      const projectId = 'test-project-id';
      const mockProject: ProjectDetails = {
        project_id: projectId,
        project_name: 'Test Project',
        filename: 'test.esx',
        upload_date: '2025-10-31T10:00:00Z',
        processing_status: ProcessingStatus.COMPLETED,
        file_size: 1024,
        original_file: 'projects/test-project-id/original.esx',
        short_link: 'abc123',
        short_link_expires: '2025-11-30T10:00:00Z',
        buildings_count: 1,
        floors_count: 3,
        aps_count: 15,
        processing_flags: {
          group_by: 'floor',
          csv_export: true,
          excel_export: true,
          json_export: false,
          html_export: false,
          pdf_export: false,
          visualize_floor_plans: true,
          show_azimuth_arrows: false,
          ap_opacity: 0.6,
        },
        processing_started: '2025-10-31T10:05:00Z',
        processing_completed: '2025-10-31T10:10:00Z',
      };

      service.getProject(projectId).subscribe((project) => {
        expect(project).toEqual(mockProject);
        expect(project.project_name).toBe('Test Project');
        expect(project.aps_count).toBe(15);
      });

      const req = httpMock.expectOne(`/api/projects/${projectId}`);
      expect(req.request.method).toBe('GET');
      req.flush(mockProject);
    });

    it('should fetch project by short link', () => {
      const shortLink = 'abc123';
      const mockProject: ProjectDetails = {
        project_id: 'test-project-id',
        project_name: 'Test Project',
        filename: 'test.esx',
        upload_date: '2025-10-31T10:00:00Z',
        processing_status: ProcessingStatus.COMPLETED,
        file_size: 1024,
        original_file: 'projects/test-project-id/original.esx',
        short_link: shortLink,
        short_link_expires: '2025-11-30T10:00:00Z',
        buildings_count: 1,
        floors_count: 3,
        aps_count: 15,
      };

      service.getProjectByShortLink(shortLink).subscribe((project) => {
        expect(project).toEqual(mockProject);
        expect(project.short_link).toBe(shortLink);
      });

      const req = httpMock.expectOne(`/api/projects/short/${shortLink}`);
      expect(req.request.method).toBe('GET');
      req.flush(mockProject);
    });

    it('should process project', () => {
      const projectId = 'test-project-id';
      const flags: ProcessingFlags = {
        group_by: 'floor',
        csv_export: true,
        excel_export: true,
        json_export: false,
        html_export: true,
        pdf_export: false,
        visualize_floor_plans: true,
        show_azimuth_arrows: true,
        ap_opacity: 0.5,
      };
      const shortLinkDays = 30;

      service.processProject(projectId, flags, shortLinkDays).subscribe((response) => {
        expect(response).toBeTruthy();
      });

      const req = httpMock.expectOne(`/api/upload/${projectId}/process`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({
        ...flags,
        short_link_days: shortLinkDays,
      });
      req.flush({ message: 'Processing started' });
    });

    it('should delete project', () => {
      const projectId = 'test-project-id';

      service.deleteProject(projectId).subscribe((response) => {
        expect(response).toBeTruthy();
      });

      const req = httpMock.expectOne(`/api/projects/${projectId}`);
      expect(req.request.method).toBe('DELETE');
      req.flush({ message: 'Project deleted' });
    });

    it('should fetch project stats', () => {
      const mockStats: ProjectStats = {
        total: 10,
        pending: 2,
        processing: 1,
        completed: 7,
        failed: 0,
      };

      service.getProjectStats().subscribe((stats) => {
        expect(stats).toEqual(mockStats);
        expect(stats.total).toBe(10);
        expect(stats.completed).toBe(7);
      });

      const req = httpMock.expectOne('/api/projects/stats/summary');
      expect(req.request.method).toBe('GET');
      req.flush(mockStats);
    });
  });

  describe('Reports endpoints', () => {
    it('should list reports', () => {
      const projectId = 'test-project-id';
      const mockReports: ReportsList = {
        project_id: projectId,
        reports: [
          { filename: 'report.csv', size: 1024, created: '2025-10-31T10:15:00Z' },
          { filename: 'report.xlsx', size: 2048, created: '2025-10-31T10:15:00Z' },
        ],
        visualizations: [
          { filename: 'floor1.png', size: 512, created: '2025-10-31T10:15:00Z' },
        ],
      };

      service.listReports(projectId).subscribe((reports) => {
        expect(reports).toEqual(mockReports);
        expect(reports.reports.length).toBe(2);
        expect(reports.visualizations.length).toBe(1);
      });

      const req = httpMock.expectOne(`/api/reports/${projectId}/list`);
      expect(req.request.method).toBe('GET');
      req.flush(mockReports);
    });

    it('should get project reports', () => {
      const projectId = 'test-project-id';
      const mockReports: ReportsList = {
        project_id: projectId,
        reports: [{ filename: 'report.csv', size: 1024, created: '2025-10-31T10:15:00Z' }],
        visualizations: [],
      };

      service.getProjectReports(projectId).subscribe((reports) => {
        expect(reports).toEqual(mockReports);
      });

      const req = httpMock.expectOne(`/api/reports/${projectId}/list`);
      expect(req.request.method).toBe('GET');
      req.flush(mockReports);
    });

    it('should get project visualizations', () => {
      const projectId = 'test-project-id';
      const mockReports: ReportsList = {
        project_id: projectId,
        reports: [],
        visualizations: [{ filename: 'floor1.png', size: 512, created: '2025-10-31T10:15:00Z' }],
      };

      service.getProjectVisualizations(projectId).subscribe((reports) => {
        expect(reports).toEqual(mockReports);
      });

      const req = httpMock.expectOne(`/api/reports/${projectId}/list`);
      expect(req.request.method).toBe('GET');
      req.flush(mockReports);
    });

    it('should generate report download URL', () => {
      const projectId = 'test-project-id';
      const filename = 'report.csv';

      const url = service.getReportDownloadUrl(projectId, filename);

      expect(url).toBe(`/api/reports/${projectId}/download/${filename}`);
    });

    it('should generate visualization URL', () => {
      const projectId = 'test-project-id';
      const filename = 'floor1.png';

      const url = service.getVisualizationUrl(projectId, filename);

      expect(url).toBe(`/api/reports/${projectId}/visualization/${filename}`);
    });

    it('should generate original file URL', () => {
      const projectId = 'test-project-id';

      const url = service.getOriginalFileUrl(projectId);

      expect(url).toBe(`/api/reports/${projectId}/original`);
    });
  });

  describe('Health check', () => {
    it('should check health', () => {
      const mockHealth = { status: 'ok' };

      service.checkHealth().subscribe((health) => {
        expect(health).toEqual(mockHealth);
      });

      const req = httpMock.expectOne('/health');
      expect(req.request.method).toBe('GET');
      req.flush(mockHealth);
    });
  });
});
