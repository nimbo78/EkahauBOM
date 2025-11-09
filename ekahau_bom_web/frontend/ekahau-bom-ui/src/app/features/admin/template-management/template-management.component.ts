import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TuiButton, TuiIcon, TuiHint } from '@taiga-ui/core';

import { ApiService } from '../../../core/services/api.service';
import { ErrorMessageService } from '../../../shared/services/error-message.service';
import { BatchTemplate } from '../../../core/models/batch.model';

@Component({
  selector: 'app-template-management',
  standalone: true,
  imports: [
    CommonModule,
    TuiButton,
    TuiIcon,
    TuiHint,
  ],
  templateUrl: './template-management.component.html',
  styleUrls: ['./template-management.component.scss'],
})
export class TemplateManagementComponent implements OnInit {
  private readonly apiService = inject(ApiService);
  private readonly errorMessageService = inject(ErrorMessageService);

  // State signals
  templates = signal<BatchTemplate[]>([]);
  loading = signal(false);
  searchQuery = signal('');
  showSystemTemplates = signal(true);
  showCustomTemplates = signal(true);

  // Computed templates based on filters
  filteredTemplates = computed(() => {
    const query = this.searchQuery().toLowerCase();
    const showSystem = this.showSystemTemplates();
    const showCustom = this.showCustomTemplates();

    return this.templates().filter(template => {
      // Filter by type
      if (template.is_system && !showSystem) return false;
      if (!template.is_system && !showCustom) return false;

      // Filter by search query
      if (query) {
        const nameMatch = template.name.toLowerCase().includes(query);
        const descMatch = template.description?.toLowerCase().includes(query);
        return nameMatch || descMatch;
      }

      return true;
    });
  });

  // Table columns
  readonly columns = ['name', 'description', 'type', 'usage', 'workers', 'actions'];

  // Getter methods for template counts
  get systemTemplatesCount(): number {
    return this.templates().filter(t => t.is_system).length;
  }

  get customTemplatesCount(): number {
    return this.templates().filter(t => !t.is_system).length;
  }

  ngOnInit(): void {
    this.loadTemplates();
  }

  loadTemplates(): void {
    this.loading.set(true);
    this.apiService.listTemplates(true).subscribe({
      next: (templates) => {
        this.templates.set(templates);
        this.loading.set(false);
        console.log('Loaded templates:', templates);
      },
      error: (err) => {
        console.error('Error loading templates:', err);
        this.errorMessageService.logError(err, 'Load Templates');
        this.loading.set(false);
      },
    });
  }

  onSearchChange(query: string): void {
    this.searchQuery.set(query);
  }

  clearSearch(): void {
    this.searchQuery.set('');
  }

  toggleSystemTemplates(): void {
    this.showSystemTemplates.set(!this.showSystemTemplates());
  }

  toggleCustomTemplates(): void {
    this.showCustomTemplates.set(!this.showCustomTemplates());
  }

  openCreateDialog(): void {
    // TODO: Implement create template dialog
    alert('Create template dialog - Coming soon!');
  }

  openEditDialog(template: BatchTemplate): void {
    if (template.is_system) {
      alert('Cannot edit system templates');
      return;
    }

    // TODO: Implement edit template dialog
    alert(`Edit template: ${template.name} - Coming soon!`);
  }

  confirmDelete(template: BatchTemplate): void {
    if (template.is_system) {
      alert('Cannot delete system templates');
      return;
    }

    const confirmed = confirm(
      `Are you sure you want to delete the template "${template.name}"?\n\nThis action cannot be undone.`
    );

    if (confirmed) {
      this.deleteTemplate(template);
    }
  }

  deleteTemplate(template: BatchTemplate): void {
    this.apiService.deleteTemplate(template.template_id).subscribe({
      next: () => {
        console.log('Template deleted:', template.name);
        this.loadTemplates();
      },
      error: (err) => {
        console.error('Error deleting template:', err);
        this.errorMessageService.logError(err, 'Delete Template');
      },
    });
  }

  formatDate(dateStr: string | undefined): string {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    return date.toLocaleDateString();
  }

  getTemplateType(isSystem: boolean): string {
    return isSystem ? 'System' : 'Custom';
  }

  getTemplateTypeClass(isSystem: boolean): string {
    return isSystem ? 'badge-system' : 'badge-custom';
  }

  canEdit(template: BatchTemplate): boolean {
    return !template.is_system;
  }

  canDelete(template: BatchTemplate): boolean {
    return !template.is_system;
  }
}
