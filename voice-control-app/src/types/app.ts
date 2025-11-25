// Application State and Configuration Types

export interface AppConfig {
  websocketUrl: string;
  apiBaseUrl: string;
  debug: boolean;
  environment: 'development' | 'production' | 'staging';
}

export interface AudioRecordingState {
  isRecording: boolean;
  isProcessing: boolean;
  audioLevel: number;
  duration: number;
  sessionId?: string;
}

export interface STTState {
  isProcessing: boolean;
  result?: STTResult;
  confidence: number;
  language: string;
  processingTime: number;
}

export interface STTResult {
  text: string;
  segments: Array<{
    text: string;
    start: number;
    end: number;
    confidence: number;
  }>;
}

export interface LLMState {
  isProcessing: boolean;
  isStreaming: boolean;
  result?: LLMResult;
  model: string;
  context: string;
}

export interface LLMResult {
  response: string;
  tokensUsed: number;
  processingTime: number;
  confidence: number;
}

export interface ConnectionState {
  isConnected: boolean;
  isConnecting: boolean;
  sessionId?: string;
  serverInfo?: {
    version: string;
    capabilities: string[];
    supportedModels: string[];
  };
  lastHeartbeat?: string;
  error?: string;
}

export interface AppState {
  audio: AudioRecordingState;
  stt: STTState;
  llm: LLMState;
  connection: ConnectionState;
  settings: AppSettings;
}

export interface AppSettings {
  audio: {
    sampleRate: number;
    channels: number;
    bitDepth: number;
    encoding: string;
    autoProcess: boolean;
  };
  stt: {
    model: string;
    language: string;
    confidenceThreshold: number;
  };
  llm: {
    model: string;
    temperature: number;
    maxTokens: number;
    stream: boolean;
  };
  notifications: {
    enabled: boolean;
    sound: boolean;
    vibration: boolean;
  };
}

// UI Component Types
export interface VoiceControlButtonProps {
  onPress: () => void;
  isRecording: boolean;
  isProcessing: boolean;
  disabled?: boolean;
}

export interface AudioWaveformProps {
  audioLevel: number;
  isRecording: boolean;
  width: number;
  height: number;
}

export interface TranscriptDisplayProps {
  transcript: string;
  confidence: number;
  isProcessing: boolean;
  showConfidence?: boolean;
}

export interface ConnectionStatusProps {
  isConnected: boolean;
  isConnecting: boolean;
  sessionId?: string;
  error?: string;
}

// Error Types
export interface AppError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
}

export type ErrorCode = 
  | 'CONNECTION_FAILED'
  | 'AUDIO_RECORDING_ERROR'
  | 'AUDIO_PROCESSING_ERROR'
  | 'STT_ERROR'
  | 'LLM_ERROR'
  | 'MCP_ERROR'
  | 'NETWORK_ERROR'
  | 'PERMISSION_DENIED'
  | 'INTERNAL_ERROR';

// Permission Types
export interface PermissionState {
  microphone: 'granted' | 'denied' | 'undetermined' | 'prompt';
  storage: 'granted' | 'denied' | 'undetermined' | 'prompt';
  network: 'granted' | 'denied' | 'undetermined' | 'prompt';
}

// Navigation Types
export type RootStackParamList = {
  Home: undefined;
  Settings: undefined;
  About: undefined;
};

export type TabParamList = {
  VoiceControl: undefined;
  History: undefined;
  Settings: undefined;
};

// Event Types
export interface VoiceControlEvent {
  type: 'voice_start' | 'voice_stop' | 'transcript_ready' | 'llm_response' | 'error';
  data: any;
  timestamp: string;
}

// Audio Processing Types
export interface AudioBuffer {
  data: Float32Array;
  sampleRate: number;
  channels: number;
  timestamp: number;
}

export interface AudioConfig {
  sampleRate: number;
  channels: number;
  bitDepth: number;
  encoding: 'pcm' | 'wav' | 'mp3';
  chunkSize: number;
}

// Log Types
export interface LogEntry {
  level: 'debug' | 'info' | 'warn' | 'error';
  message: string;
  data?: any;
  timestamp: string;
  source: 'app' | 'websocket' | 'audio' | 'stt' | 'llm';
}