import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';

export interface ExcelSheet {
  name: string;
  headers: string[];
  rows: any[][];
  rowCount: number;
}

export interface ExcelData {
  sheets: ExcelSheet[];
  sheetNames: string[];
}

@Injectable({
  providedIn: 'root',
})
export class ExcelParserService {
  /**
   * Parse Excel file (arraybuffer) into structured data
   * This service will use SheetJS (xlsx) library after installation
   *
   * @param buffer - Excel file as ArrayBuffer
   * @returns Observable with parsed data
   */
  parseExcel(buffer: ArrayBuffer): Observable<ExcelData> {
    // TODO: Implement with SheetJS (xlsx) after library installation
    // For now, return placeholder
    console.warn('ExcelParserService: xlsx library not yet installed');

    return of({
      sheets: [
        {
          name: 'Sheet1',
          headers: ['Column 1', 'Column 2', 'Column 3'],
          rows: [
            ['Data 1', 'Data 2', 'Data 3'],
            ['Data 4', 'Data 5', 'Data 6'],
          ],
          rowCount: 2,
        },
      ],
      sheetNames: ['Sheet1'],
    });
  }

  /**
   * Check if Excel file is too large for browser parsing
   *
   * @param size - File size in bytes
   * @returns true if file is safe to parse
   */
  isSafeSize(size: number): boolean {
    const MAX_SIZE_MB = 5;
    const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
    return size <= MAX_SIZE_BYTES;
  }
}
