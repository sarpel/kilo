import { AudioRecordingState, AudioBuffer, AudioConfig, PermissionState } from '../types/app';

export class AudioService {
  private audioContext: AudioContext | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private stream: MediaStream | null = null;
  private audioConfig: AudioConfig;
  private isRecording = false;
  private startTime = 0;
  private sequence = 0;
  private permissionState: PermissionState = {
    microphone: 'undetermined',
    storage: 'undetermined',
    network: 'undetermined'
  };
  private eventListeners: Map<string, Function[]> = new Map();

  constructor(config: AudioConfig) {
    this.audioConfig = config;
  }

  /**
   * Check and request microphone permissions
   */
  async checkPermissions(): Promise<PermissionState> {
    try {
      // Check microphone permission
      const micResult = await navigator.permissions.query({ name: 'microphone' as PermissionName });
      this.permissionState.microphone = micResult.state;

      micResult.onchange = () => {
        this.permissionState.microphone = micResult.state;
        this.emit('permission_changed', { 
          type: 'microphone', 
          state: micResult.state 
        });
      };

      return this.permissionState;
    } catch (error) {
      // Fallback for browsers that don't support permissions API
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.permissionState.microphone = 'granted';
        stream.getTracks().forEach(track => track.stop()); // Stop the test stream
      } catch (e) {
        this.permissionState.microphone = 'denied';
      }
      
      return this.permissionState;
    }
  }

  /**
   * Initialize audio context and recording setup
   */
  async initialize(): Promise<void> {
    try {
      // Create audio context for React Native
      // Note: This would be implemented differently in React Native native module
      if (!this.audioContext) {
        // For web browser - React Native would use different API
        this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      }

      // Configure audio settings
      await this.setupAudioContext();
      
      this.log('info', 'Audio service initialized');
      this.emit('initialized', {});
    } catch (error) {
      this.log('error', 'Failed to initialize audio service', error);
      throw error;
    }
  }

  /**
   * Start audio recording
   */
  async startRecording(): Promise<void> {
    if (this.isRecording) {
      throw new Error('Already recording');
    }

    try {
      // Request microphone access
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: this.audioConfig.sampleRate,
          channelCount: this.audioConfig.channels,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });

      // Create media recorder
      this.mediaRecorder = new MediaRecorder(this.stream, {
        mimeType: this.getSupportedMimeType()
      });

      this.setupMediaRecorder();
      
      this.audioChunks = [];
      this.mediaRecorder.start(100); // Collect data every 100ms
      
      this.isRecording = true;
      this.startTime = Date.now();
      this.sequence = 0;

      this.log('info', 'Recording started');
      this.emit('recording_started', { startTime: this.startTime });
      
    } catch (error) {
      this.log('error', 'Failed to start recording', error);
      throw new Error(`Failed to start recording: ${error}`);
    }
  }

  /**
   * Stop audio recording
   */
  async stopRecording(): Promise<AudioBuffer[]> {
    if (!this.isRecording || !this.mediaRecorder) {
      throw new Error('Not currently recording');
    }

    return new Promise((resolve, reject) => {
      try {
        const recorder = this.mediaRecorder!; // We know it's not null at this point
        recorder.onstop = async () => {
          try {
            const duration = Date.now() - this.startTime;
            
            // Create audio buffer from recorded data
            const audioBuffer = await this.createAudioBuffer();
            
            this.isRecording = false;
            this.sequence = 0;

            // Clean up
            this.cleanup();

            this.log('info', 'Recording stopped', { duration, sequenceCount: this.sequence });
            this.emit('recording_stopped', { 
              duration, 
              sequenceCount: this.sequence,
              buffer: audioBuffer 
            });

            resolve([audioBuffer]);
          } catch (error) {
            reject(error);
          }
        };

        recorder.stop();
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Get current recording state
   */
  getRecordingState(): AudioRecordingState {
    return {
      isRecording: this.isRecording,
      isProcessing: false,
      audioLevel: 0,
      duration: this.isRecording ? Date.now() - this.startTime : 0,
    };
  }

  /**
   * Get audio level (for visualization)
   */
  getAudioLevel(): number {
    if (!this.stream) return 0;

    try {
      const audioContext = new AudioContext();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(this.stream);
      
      analyser.fftSize = 256;
      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      
      source.connect(analyser);
      analyser.getByteFrequencyData(dataArray);
      
      // Calculate average amplitude
      const average = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;
      
      // Clean up
      audioContext.close();
      
      return average / 255; // Normalize to 0-1
    } catch (error) {
      return 0;
    }
  }

  /**
   * Convert audio data to base64
   */
  async audioToBase64(audioBuffer: ArrayBuffer): Promise<string> {
    const bytes = new Uint8Array(audioBuffer);
    let binary = '';
    
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    
    return btoa(binary);
  }

  /**
   * Convert base64 to audio buffer
   */
  base64ToAudioBuffer(base64: string): ArrayBuffer {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    
    return bytes.buffer;
  }

  /**
   * Set up media recorder event handlers
   */
  private setupMediaRecorder(): void {
    if (!this.mediaRecorder) return;

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        this.audioChunks.push(event.data);
        this.sequence++;
        
        // Emit audio chunk for real-time processing
        this.processAudioChunk(event.data);
      }
    };

    this.mediaRecorder.onerror = (event) => {
      this.log('error', 'MediaRecorder error', event);
      this.emit('error', { type: 'recording_error', error: event });
    };
  }

  /**
   * Process individual audio chunk
   */
  private async processAudioChunk(chunk: Blob): Promise<void> {
    try {
      const arrayBuffer = await chunk.arrayBuffer();
      const base64Audio = await this.audioToBase64(arrayBuffer);
      
      this.emit('audio_chunk', {
        data: base64Audio,
        sequence: this.sequence,
        timestamp: Date.now()
      });
    } catch (error) {
      this.log('error', 'Failed to process audio chunk', error);
    }
  }

  /**
   * Setup audio context configuration
   */
  private async setupAudioContext(): Promise<void> {
    if (!this.audioContext) return;

    try {
      // Note: sampleRate is read-only in AudioContext
      // The actual sample rate is determined when creating the context
      // We work with the configured sample rate from audioConfig
      
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }
    } catch (error) {
      this.log('warn', 'Audio context setup warning', error);
    }
  }

  /**
   * Create audio buffer from recorded chunks
   */
  private async createAudioBuffer(): Promise<AudioBuffer> {
    // Combine all audio chunks
    const audioBlob = new Blob(this.audioChunks, { type: this.getSupportedMimeType() });
    const arrayBuffer = await audioBlob.arrayBuffer();

    // This would need to be implemented for actual audio decoding
    // For now, return a simple buffer structure
    return {
      data: new Float32Array(), // Would contain actual audio data
      sampleRate: this.audioConfig.sampleRate,
      channels: this.audioConfig.channels,
      timestamp: this.startTime
    };
  }

  /**
   * Get supported MIME type for recording
   */
  private getSupportedMimeType(): string {
    const types = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/mp4',
      'audio/ogg;codecs=opus'
    ];

    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type;
      }
    }

    return ''; // Let browser choose
  }

  /**
   * Clean up resources
   */
  private cleanup(): void {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }

    if (this.mediaRecorder) {
      this.mediaRecorder = null;
    }

    this.audioChunks = [];
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
   * Emit event to listeners
   */
  private emit(event: string, data: any): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          this.log('error', 'Error in audio event listener', error);
        }
      });
    }
  }

  /**
   * Check if service is recording
   */
  getIsRecording(): boolean {
    return this.isRecording;
  }

  /**
   * Destroy service and clean up resources
   */
  destroy(): void {
    if (this.isRecording) {
      this.stopRecording().catch(console.error);
    }
    
    this.cleanup();
    
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }

    this.eventListeners.clear();
    this.log('info', 'Audio service destroyed');
  }

  /**
   * Logging
   */
  private log(level: 'debug' | 'info' | 'warn' | 'error', message: string, data?: any): void {
    const logEntry = {
      level,
      message: `[AudioService] ${message}`,
      data,
      timestamp: new Date().toISOString(),
      source: 'audio'
    };

    if (level !== 'debug') {
      console.log(logEntry);
    }
  }
}