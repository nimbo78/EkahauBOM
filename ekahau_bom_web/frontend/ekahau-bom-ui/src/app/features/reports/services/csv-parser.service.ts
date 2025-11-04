import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';

export interface CsvData {
  headers: string[];
  rows: any[][];
  rowCount: number;
}

@Injectable({
  providedIn: 'root',
})
export class CsvParserService {
  /**
   * Parse CSV text into structured data
   * This service will use PapaParse library after installation
   *
   * @param csvText - Raw CSV text content
   * @returns Observable with parsed data
   */
  parseCsv(csvText: string): Observable<CsvData> {
    // TODO: Implement with PapaParse after library installation
    // For now, return placeholder
    console.warn('CsvParserService: PapaParse not yet installed');

    return of({
      headers: ['Column 1', 'Column 2', 'Column 3'],
      rows: [
        ['Data 1', 'Data 2', 'Data 3'],
        ['Data 4', 'Data 5', 'Data 6'],
      ],
      rowCount: 2,
    });
  }

  /**
   * Check if CSV file is too large for browser parsing
   *
   * @param size - File size in bytes
   * @returns true if file is safe to parse
   */
  isSafeSize(size: number): boolean {
    const MAX_SIZE_MB = 10;
    const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
    return size <= MAX_SIZE_BYTES;
  }
}
