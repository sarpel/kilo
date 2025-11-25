import io, { Socket } from 'socket.io-client';
import {
  ClientMessage,
  ServerMessage,
  ConnectionRequest,
  ConnectionResponse,
  AudioStart,
  AudioData,
  AudioStop,
  STTRequest,
  LLMRequest,
  MCPRequest,
  HeartbeatResponse,
  ServerMessage as ServerMessageType,
} from '../types/api';
import { AppState, AppConfig } from '../types/app';

export class WebSocketService {
  private socket: Socket | null = null;
  private config: AppConfig;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 1000;
  private heartbeatInterval: number | null = null;
  private isConnecting = false;
  private messageQueue: ClientMessage[] = [];
  private eventListeners: Map<string, Function[]> = new Map();
  private sessionId: string | null = null;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /**
   * Connect to the WebSocket server
   */
  async connect(): Promise<void> {
    if (this.socket?.connected || this.isConnecting) {
      return Promise.resolve();
    }

    this.isConnecting = true;

    return new Promise((resolve, reject) => {
      try {
        this.socket = io(this.config.websocketUrl, {
          transports: ['websocket'],
          timeout: 10000,
          reconnection: true,
          reconnectionAttempts: this.maxReconnectAttempts,
          reconnectionDelay: this.reconnectInterval,
        });

        this.setupEventHandlers();
        this.socket.connect();

        this.socket.on('connect', () => {
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.log('info', 'Connected to WebSocket server');
          this.startHeartbeat();
          resolve();
        });

        this.socket.on('connect_error', (error: any) => {
          this.isConnecting = false;
          this.log('error', 'Connection failed', error);
          reject(error);
        });

        this.socket.on('disconnect', (reason: any) => {
          this.log('warn', 'Disconnected from server', reason);
          this.stopHeartbeat();
          this.sessionId = null;
          this.emit('disconnect', { reason });
        });

      } catch (error) {
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    if (this.socket) {
      this.stopHeartbeat();
      this.socket.disconnect();
      this.socket = null;
      this.sessionId = null;
    }
  }

  /**
   * Send a message to the server
   */
  sendMessage(message: ClientMessage): void {
    if (!this.socket?.connected) {
      this.messageQueue.push(message);
      return;
    }

    try {
      this.socket.emit('message', message);
      this.log('debug', 'Message sent', message);
    } catch (error) {
      this.log('error', 'Failed to send message', error);
      this.messageQueue.push(message);
    }
  }

  /**
   * Send connection request
   */
  async sendConnectionRequest(clientId: string, capabilities: string[]): Promise<ConnectionResponse> {
    const message: ConnectionRequest = {
      type: 'connection_request',
      timestamp: new Date().toISOString(),
      data: {
        client_id: clientId,
        client_version: '1.0.0',
        capabilities,
        audio_format: {
          sample_rate: 16000,
          channels: 1,
          bit_depth: 16,
          encoding: 'pcm'
        }
      },
      message_id: this.generateMessageId()
    };

    return this.sendWithResponse(message, 'connection_response');
  }

  /**
   * Start audio recording
   */
  sendAudioStart(sessionId: string): void {
    const message: AudioStart = {
      type: 'audio_start',
      timestamp: new Date().toISOString(),
      data: {
        session_id: sessionId,
        audio_config: {
          sample_rate: 16000,
          channels: 1,
          bit_depth: 16,
          encoding: 'pcm'
        },
        processing_options: {
          stt_model: 'whisper-base',
          auto_process: true
        }
      },
      message_id: this.generateMessageId()
    };

    this.sendMessage(message);
  }

  /**
   * Send audio data
   */
  sendAudioData(sessionId: string, audioData: string, sequence: number, isFinal = false): void {
    const message: AudioData = {
      type: 'audio_data',
      timestamp: new Date().toISOString(),
      data: {
        session_id: sessionId,
        audio_chunk: audioData,
        sequence,
        is_final: isFinal
      },
      message_id: this.generateMessageId()
    };

    this.sendMessage(message);
  }

  /**
   * Stop audio recording
   */
  sendAudioStop(sessionId: string, sequence: number, durationMs: number): void {
    const message: AudioStop = {
      type: 'audio_stop',
      timestamp: new Date().toISOString(),
      data: {
        session_id: sessionId,
        sequence,
        duration_ms: durationMs
      },
      message_id: this.generateMessageId()
    };

    this.sendMessage(message);
  }

  /**
   * Send LLM request
   */
  sendLLMRequest(
    sessionId: string,
    text: string,
    model: string = 'llama2',
    options: any = {}
  ): void {
    const message: LLMRequest = {
      type: 'llm_request',
      timestamp: new Date().toISOString(),
      data: {
        session_id: sessionId,
        text,
        model,
        context: 'user_query',
        options: {
          temperature: 0.7,
          max_tokens: 150,
          stream: false,
          ...options
        }
      },
      message_id: this.generateMessageId()
    };

    this.sendMessage(message);
  }

  /**
   * Send MCP request
   */
  sendMCPRequest(sessionId: string, tool: string, arguments_: Record<string, any> = {}): void {
    const message: MCPRequest = {
      type: 'mcp_request',
      timestamp: new Date().toISOString(),
      data: {
        session_id: sessionId,
        tool,
        arguments: arguments_
      },
      message_id: this.generateMessageId()
    };

    this.sendMessage(message);
  }

  /**
   * Send heartbeat response
   */
  sendHeartbeatResponse(): void {
    const message: HeartbeatResponse = {
      type: 'heartbeat_response',
      timestamp: new Date().toISOString(),
      data: {
        client_time: new Date().toISOString()
      },
      message_id: this.generateMessageId()
    };

    this.sendMessage(message);
  }

  /**
   * Add event listener
   */
  on(event: string, callback: Function): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event)!.push(callback);
  }

  /**
   * Remove event listener
   */
  off(event: string, callback?: Function): void {
    if (!callback) {
      this.eventListeners.delete(event);
      return;
    }

    const listeners = this.eventListeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  /**
   * Get connection status
   */
  isConnected(): boolean {
    return this.socket?.connected || false;
  }

  /**
   * Get current session ID
   */
  getSessionId(): string | null {
    return this.sessionId;
  }

  /**
   * Set session ID (called when connection response received)
   */
  setSessionId(sessionId: string): void {
    this.sessionId = sessionId;
    this.emit('session_id_changed', { sessionId });
  }

  /**
   * Setup event handlers
   */
  private setupEventHandlers(): void {
    if (!this.socket) return;

    this.socket.on('message', (message: ServerMessageType) => {
      this.handleMessage(message);
    });

    this.socket.on('connection_response', (message: ServerMessageType) => {
      this.handleMessage(message);
    });

    this.socket.on('stt_response', (message: ServerMessageType) => {
      this.handleMessage(message);
    });

    this.socket.on('llm_response', (message: ServerMessageType) => {
      this.handleMessage(message);
    });

    this.socket.on('llm_stream', (message: ServerMessageType) => {
      this.handleMessage(message);
    });

    this.socket.on('mcp_response', (message: ServerMessageType) => {
      this.handleMessage(message);
    });

    this.socket.on('status_update', (message: ServerMessageType) => {
      this.handleMessage(message);
    });

    this.socket.on('error', (message: ServerMessageType) => {
      this.handleMessage(message);
    });

    this.socket.on('heartbeat', (message: ServerMessageType) => {
      this.handleMessage(message);
    });

    this.socket.on('reconnect_attempt', (attemptNumber: number) => {
      this.log('info', `Reconnection attempt ${attemptNumber}`);
      this.emit('reconnect_attempt', { attempt: attemptNumber });
    });

    this.socket.on('reconnect', (attemptNumber: number) => {
      this.log('info', `Reconnected after ${attemptNumber} attempts`);
      this.flushMessageQueue();
      this.emit('reconnect', { attempts: attemptNumber });
    });
  }

  /**
   * Handle incoming messages
   */
  private handleMessage(message: ServerMessageType): void {
    this.log('debug', 'Message received', message);

    // Set session ID from connection response
    if (message.type === 'connection_response' && 'data' in message) {
      const response = message as ConnectionResponse;
      if (response.data.session_id) {
        this.setSessionId(response.data.session_id);
      }
    }

    // Emit to all listeners
    this.emit(message.type, message);

    // Emit generic message event
    this.emit('message', message);
  }

  /**
   * Send message with response expectation
   */
  private sendWithResponse<T extends ServerMessageType>(
    message: ClientMessage,
    responseType: string
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        this.off(responseType, responseHandler);
        reject(new Error(`Timeout waiting for ${responseType}`));
      }, 10000);

      const responseHandler = (response: T) => {
        if (response.type === responseType) {
          clearTimeout(timeoutId);
          this.off(responseType, responseHandler);
          resolve(response);
        }
      };

      this.on(responseType, responseHandler);
      this.sendMessage(message);
    });
  }

  /**
   * Start heartbeat
   */
  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected()) {
        this.sendHeartbeatResponse();
      }
    }, 30000); // Send heartbeat every 30 seconds
  }

  /**
   * Stop heartbeat
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval !== null) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * Flush queued messages
   */
  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.isConnected()) {
      const message = this.messageQueue.shift();
      if (message) {
        this.sendMessage(message);
      }
    }
  }

  /**
   * Emit event to listeners
   */
  private emit(event: string, data: any): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          this.log('error', 'Error in event listener', error);
        }
      });
    }
  }

  /**
   * Generate unique message ID
   */
  private generateMessageId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Logging
   */
  private log(level: 'debug' | 'info' | 'warn' | 'error', message: string, data?: any): void {
    const logEntry = {
      level,
      message: `[WebSocketService] ${message}`,
      data,
      timestamp: new Date().toISOString(),
      source: 'websocket'
    };

    if (this.config.debug || level !== 'debug') {
      console.log(logEntry);
    }
  }
}