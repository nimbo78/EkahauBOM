import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';

export interface NotificationOptions {
  title: string;
  body: string;
  icon?: string;
  tag?: string;
  requireInteraction?: boolean;
  data?: any;
}

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private router = inject(Router);
  private permissionGranted = false;
  private readonly PERMISSION_KEY = 'notification_permission_requested';

  constructor() {
    this.checkPermission();
  }

  /**
   * Check if browser supports notifications and if permission is granted
   */
  isSupported(): boolean {
    return 'Notification' in window;
  }

  /**
   * Check current notification permission status
   */
  private checkPermission(): void {
    if (!this.isSupported()) {
      console.warn('[NotificationService] Web Notifications API not supported');
      return;
    }

    this.permissionGranted = Notification.permission === 'granted';
  }

  /**
   * Request notification permission from user
   * Returns true if permission granted, false otherwise
   */
  async requestPermission(): Promise<boolean> {
    if (!this.isSupported()) {
      console.warn('[NotificationService] Cannot request permission - API not supported');
      return false;
    }

    if (Notification.permission === 'granted') {
      this.permissionGranted = true;
      return true;
    }

    if (Notification.permission === 'denied') {
      console.warn('[NotificationService] Notification permission denied by user');
      return false;
    }

    try {
      const permission = await Notification.requestPermission();
      this.permissionGranted = permission === 'granted';

      // Save that we've requested permission
      localStorage.setItem(this.PERMISSION_KEY, 'true');

      console.log(`[NotificationService] Permission ${permission}`);
      return this.permissionGranted;
    } catch (error) {
      console.error('[NotificationService] Error requesting permission:', error);
      return false;
    }
  }

  /**
   * Check if permission has been requested before
   */
  hasRequestedPermission(): boolean {
    return localStorage.getItem(this.PERMISSION_KEY) === 'true';
  }

  /**
   * Show a browser notification
   */
  async show(options: NotificationOptions): Promise<Notification | null> {
    if (!this.isSupported()) {
      console.warn('[NotificationService] Cannot show notification - API not supported');
      return null;
    }

    if (!this.permissionGranted) {
      console.warn('[NotificationService] Cannot show notification - permission not granted');
      return null;
    }

    try {
      const notification = new Notification(options.title, {
        body: options.body,
        icon: options.icon || '/favicon.ico',
        tag: options.tag,
        requireInteraction: options.requireInteraction || false,
        data: options.data
      });

      // Add click handler if navigation data provided
      if (options.data?.route) {
        notification.onclick = () => {
          window.focus();
          this.router.navigate([options.data.route]);
          notification.close();
        };
      }

      console.log('[NotificationService] Notification shown:', options.title);
      return notification;
    } catch (error) {
      console.error('[NotificationService] Error showing notification:', error);
      return null;
    }
  }

  /**
   * Show success notification
   */
  async showSuccess(title: string, body: string, data?: any): Promise<Notification | null> {
    return this.show({
      title: `✅ ${title}`,
      body,
      tag: 'success',
      data
    });
  }

  /**
   * Show warning notification
   */
  async showWarning(title: string, body: string, data?: any): Promise<Notification | null> {
    return this.show({
      title: `⚠️ ${title}`,
      body,
      tag: 'warning',
      requireInteraction: true,
      data
    });
  }

  /**
   * Show error notification
   */
  async showError(title: string, body: string, data?: any): Promise<Notification | null> {
    return this.show({
      title: `❌ ${title}`,
      body,
      tag: 'error',
      requireInteraction: true,
      data
    });
  }

  /**
   * Show batch completion notification
   */
  async notifyBatchComplete(
    batchId: string,
    batchName: string,
    successCount: number,
    totalCount: number,
    processingTime: string
  ): Promise<Notification | null> {
    const allSuccess = successCount === totalCount;
    const title = allSuccess
      ? `Batch "${batchName}" completed!`
      : `Batch "${batchName}" partially completed`;

    const body = allSuccess
      ? `✅ ${successCount}/${totalCount} projects processed successfully\n⏱️ Processing time: ${processingTime}`
      : `✅ ${successCount}/${totalCount} projects successful\n❌ ${totalCount - successCount} failed\n⏱️ Processing time: ${processingTime}`;

    const method = allSuccess ? this.showSuccess : this.showWarning;

    return method.call(this, title, body, {
      route: `/admin/batches/${batchId}`
    });
  }

  /**
   * Show batch failure notification
   */
  async notifyBatchFailed(
    batchId: string,
    batchName: string,
    errorMessage: string
  ): Promise<Notification | null> {
    return this.showError(
      `Batch "${batchName}" failed`,
      `Error: ${errorMessage}`,
      {
        route: `/admin/batches/${batchId}`
      }
    );
  }
}
