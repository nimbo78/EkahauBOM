import { Injectable, signal, inject } from '@angular/core';
import { Subject, Observable, timer, EMPTY } from 'rxjs';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { retryWhen, tap, delayWhen, catchError } from 'rxjs/operators';

/**
 * WebSocket message types
 */
export type WebSocketMessageType =
  | 'batch_update'
  | 'project_update'
  | 'batch_created'
  | 'batch_deleted'
  | 'connection_established'
  | 'pong';

/**
 * WebSocket message structure
 */
export interface WebSocketMessage<T = any> {
  type: WebSocketMessageType;
  data: T;
}

/**
 * Batch update data
 */
export interface BatchUpdateData {
  batch_id: string;
  status: string;
  progress?: number;
  message?: string;
}

/**
 * Project update data
 */
export interface ProjectUpdateData {
  batch_id: string;
  project_id: string;
  status: string;
  message?: string;
}

/**
 * Batch created data
 */
export interface BatchCreatedData {
  batch_id: string;
}

/**
 * Batch deleted data
 */
export interface BatchDeletedData {
  batch_id: string;
}

/**
 * Connection status
 */
export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error';

/**
 * WebSocket service for real-time updates.
 *
 * Provides:
 * - Auto-reconnect with exponential backoff
 * - Type-safe message handling
 * - Observable streams for different event types
 * - Connection status tracking
 *
 * Usage:
 * ```typescript
 * constructor(private wsService: WebSocketService) {}
 *
 * ngOnInit() {
 *   this.wsService.connect();
 *
 *   this.wsService.batchUpdates$.subscribe(update => {
 *     console.log('Batch update:', update);
 *   });
 * }
 * ```
 */
@Injectable({
  providedIn: 'root',
})
export class WebSocketService {
  private socket$: WebSocketSubject<WebSocketMessage> | null = null;
  private messagesSubject$ = new Subject<WebSocketMessage>();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private baseReconnectDelay = 1000; // 1 second
  private maxReconnectDelay = 30000; // 30 seconds
  private pingInterval: any = null;
  private clientId: string | null = null;

  // Connection status signal
  public connectionStatus = signal<ConnectionStatus>('disconnected');

  // Observable streams for different message types
  public messages$ = this.messagesSubject$.asObservable();

  public batchUpdates$ = new Observable<BatchUpdateData>((observer) => {
    return this.messages$.subscribe((msg) => {
      if (msg.type === 'batch_update') {
        observer.next(msg.data as BatchUpdateData);
      }
    });
  });

  public projectUpdates$ = new Observable<ProjectUpdateData>((observer) => {
    return this.messages$.subscribe((msg) => {
      if (msg.type === 'project_update') {
        observer.next(msg.data as ProjectUpdateData);
      }
    });
  });

  public batchCreated$ = new Observable<BatchCreatedData>((observer) => {
    return this.messages$.subscribe((msg) => {
      if (msg.type === 'batch_created') {
        observer.next(msg.data as BatchCreatedData);
      }
    });
  });

  public batchDeleted$ = new Observable<BatchDeletedData>((observer) => {
    return this.messages$.subscribe((msg) => {
      if (msg.type === 'batch_deleted') {
        observer.next(msg.data as BatchDeletedData);
      }
    });
  });

  /**
   * Connect to WebSocket server
   */
  public connect(): void {
    if (this.socket$) {
      console.log('[WebSocket] Already connected');
      return;
    }

    this.connectionStatus.set('connecting');

    // Determine WebSocket URL based on current location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/ws`;

    console.log('[WebSocket] Connecting to:', wsUrl);

    this.socket$ = webSocket<WebSocketMessage>({
      url: wsUrl,
      openObserver: {
        next: () => {
          console.log('[WebSocket] Connected');
          this.connectionStatus.set('connected');
          this.reconnectAttempts = 0;
          this.startPingInterval();
        },
      },
      closeObserver: {
        next: () => {
          console.log('[WebSocket] Disconnected');
          this.connectionStatus.set('disconnected');
          this.stopPingInterval();
          this.handleReconnect();
        },
      },
    });

    this.socket$
      .pipe(
        tap((message) => {
          // Handle connection established message
          if (message.type === 'connection_established') {
            this.clientId = message.data.client_id;
            console.log('[WebSocket] Connection established, client ID:', this.clientId);
          }

          // Forward all messages to subject
          this.messagesSubject$.next(message);
        }),
        retryWhen((errors) =>
          errors.pipe(
            tap((err) => {
              console.error('[WebSocket] Error:', err);
              this.connectionStatus.set('error');
            }),
            delayWhen(() => {
              const delay = this.calculateReconnectDelay();
              console.log(`[WebSocket] Reconnecting in ${delay}ms...`);
              return timer(delay);
            })
          )
        ),
        catchError((err) => {
          console.error('[WebSocket] Fatal error:', err);
          this.connectionStatus.set('error');
          return EMPTY;
        })
      )
      .subscribe();
  }

  /**
   * Disconnect from WebSocket server
   */
  public disconnect(): void {
    if (this.socket$) {
      console.log('[WebSocket] Disconnecting...');
      this.stopPingInterval();
      this.socket$.complete();
      this.socket$ = null;
      this.connectionStatus.set('disconnected');
    }
  }

  /**
   * Send a message to the server
   */
  public send(message: WebSocketMessage): void {
    if (this.socket$ && this.connectionStatus() === 'connected') {
      this.socket$.next(message);
    } else {
      console.warn('[WebSocket] Cannot send message, not connected');
    }
  }

  /**
   * Calculate exponential backoff delay for reconnection
   */
  private calculateReconnectDelay(): number {
    const delay = Math.min(
      this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts),
      this.maxReconnectDelay
    );
    this.reconnectAttempts++;
    return delay;
  }

  /**
   * Handle reconnection logic
   */
  private handleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnect attempts reached');
      this.connectionStatus.set('error');
      return;
    }

    const delay = this.calculateReconnectDelay();
    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})...`);

    setTimeout(() => {
      this.socket$ = null;
      this.connect();
    }, delay);
  }

  /**
   * Start ping interval to keep connection alive
   */
  private startPingInterval(): void {
    this.stopPingInterval();

    // Send ping every 30 seconds
    this.pingInterval = setInterval(() => {
      if (this.connectionStatus() === 'connected') {
        this.send({ type: 'ping' as any, data: {} });
      }
    }, 30000);
  }

  /**
   * Stop ping interval
   */
  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Get current connection status
   */
  public getConnectionStatus(): ConnectionStatus {
    return this.connectionStatus();
  }

  /**
   * Check if connected
   */
  public isConnected(): boolean {
    return this.connectionStatus() === 'connected';
  }

  /**
   * Get client ID (available after connection)
   */
  public getClientId(): string | null {
    return this.clientId;
  }
}
