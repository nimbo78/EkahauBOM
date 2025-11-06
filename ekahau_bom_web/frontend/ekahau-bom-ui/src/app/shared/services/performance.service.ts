import { Injectable } from '@angular/core';

interface PerformanceMetric {
  name: string;
  value: number;
  timestamp: number;
}

@Injectable({
  providedIn: 'root'
})
export class PerformanceService {
  private metrics: PerformanceMetric[] = [];
  private timers = new Map<string, number>();

  /**
   * Start a performance timer
   * @param name Unique name for the timer
   */
  startTimer(name: string): void {
    this.timers.set(name, performance.now());
  }

  /**
   * End a performance timer and log the result
   * @param name Name of the timer to end
   * @returns Duration in milliseconds
   */
  endTimer(name: string): number {
    const startTime = this.timers.get(name);
    if (!startTime) {
      console.warn(`Performance timer "${name}" was not started`);
      return 0;
    }

    const duration = performance.now() - startTime;
    this.timers.delete(name);

    this.logMetric(name, duration);
    return duration;
  }

  /**
   * Log a performance metric
   * @param name Metric name
   * @param value Metric value (duration in ms)
   */
  private logMetric(name: string, value: number): void {
    const metric: PerformanceMetric = {
      name,
      value,
      timestamp: Date.now()
    };

    this.metrics.push(metric);

    // Log to console in development
    if (!this.isProduction()) {
      console.log(`[Performance] ${name}: ${value.toFixed(2)}ms`);
    }

    // Keep only last 100 metrics to avoid memory issues
    if (this.metrics.length > 100) {
      this.metrics.shift();
    }
  }

  /**
   * Measure and log navigation timing
   */
  measureNavigationTiming(): void {
    if (typeof window === 'undefined' || !window.performance) {
      return;
    }

    // Wait for page to be fully loaded
    if (document.readyState === 'complete') {
      this.logNavigationMetrics();
    } else {
      window.addEventListener('load', () => {
        // Small delay to ensure all metrics are available
        setTimeout(() => this.logNavigationMetrics(), 100);
      });
    }
  }

  /**
   * Log navigation performance metrics
   */
  private logNavigationMetrics(): void {
    const perfData = window.performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    if (!perfData) return;

    const metrics = {
      'DNS Lookup': perfData.domainLookupEnd - perfData.domainLookupStart,
      'TCP Connection': perfData.connectEnd - perfData.connectStart,
      'Request Time': perfData.responseStart - perfData.requestStart,
      'Response Time': perfData.responseEnd - perfData.responseStart,
      'DOM Processing': perfData.domComplete - perfData.domInteractive,
      'Page Load': perfData.loadEventEnd - perfData.fetchStart,
    };

    Object.entries(metrics).forEach(([name, value]) => {
      if (value > 0) {
        this.logMetric(name, value);
      }
    });

    // Log Core Web Vitals if available
    this.measureCoreWebVitals();
  }

  /**
   * Measure Core Web Vitals (LCP, FID, CLS)
   */
  private measureCoreWebVitals(): void {
    if (typeof window === 'undefined' || !('PerformanceObserver' in window)) {
      return;
    }

    try {
      // Largest Contentful Paint (LCP)
      new PerformanceObserver((entryList) => {
        const entries = entryList.getEntries();
        const lastEntry = entries[entries.length - 1] as any;
        this.logMetric('LCP', lastEntry.renderTime || lastEntry.loadTime);
      }).observe({ type: 'largest-contentful-paint', buffered: true });

      // First Input Delay (FID)
      new PerformanceObserver((entryList) => {
        const entries = entryList.getEntries();
        entries.forEach((entry: any) => {
          this.logMetric('FID', entry.processingStart - entry.startTime);
        });
      }).observe({ type: 'first-input', buffered: true });

      // Cumulative Layout Shift (CLS)
      let clsValue = 0;
      new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries()) {
          if (!(entry as any).hadRecentInput) {
            clsValue += (entry as any).value;
          }
        }
        this.logMetric('CLS', clsValue * 1000); // Convert to ms for consistency
      }).observe({ type: 'layout-shift', buffered: true });
    } catch (e) {
      // Performance Observer not supported, silently fail
    }
  }

  /**
   * Get all recorded metrics
   */
  getMetrics(): PerformanceMetric[] {
    return [...this.metrics];
  }

  /**
   * Get metrics by name
   */
  getMetricsByName(name: string): PerformanceMetric[] {
    return this.metrics.filter(m => m.name === name);
  }

  /**
   * Calculate average duration for a metric
   */
  getAverageDuration(name: string): number {
    const metrics = this.getMetricsByName(name);
    if (metrics.length === 0) return 0;

    const sum = metrics.reduce((acc, m) => acc + m.value, 0);
    return sum / metrics.length;
  }

  /**
   * Clear all metrics
   */
  clearMetrics(): void {
    this.metrics = [];
    this.timers.clear();
  }

  /**
   * Check if running in production
   */
  private isProduction(): boolean {
    return typeof window !== 'undefined' &&
           window.location.hostname !== 'localhost' &&
           window.location.hostname !== '127.0.0.1';
  }

  /**
   * Log component initialization time
   * Usage: Call in ngOnInit and ngAfterViewInit
   */
  logComponentInit(componentName: string): void {
    this.startTimer(`${componentName}-init`);
  }

  logComponentRender(componentName: string): void {
    this.endTimer(`${componentName}-init`);
  }

  /**
   * Measure async operation
   * Usage: await performanceService.measureAsync('operation-name', async () => { ... })
   */
  async measureAsync<T>(name: string, fn: () => Promise<T>): Promise<T> {
    this.startTimer(name);
    try {
      return await fn();
    } finally {
      this.endTimer(name);
    }
  }

  /**
   * Measure sync operation
   * Usage: performanceService.measure('operation-name', () => { ... })
   */
  measure<T>(name: string, fn: () => T): T {
    this.startTimer(name);
    try {
      return fn();
    } finally {
      this.endTimer(name);
    }
  }
}
