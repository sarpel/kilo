// API and WebSocket Message Types

export interface BaseMessage {
  type: string;
  timestamp: string;
  data: any;
  message_id: string;
}

// Connection Messages
export interface ConnectionRequest extends BaseMessage {
  type: 'connection_request';
  data: {
    client_id: string;
    client_version: string;
    capabilities: string[];
    audio_format: AudioFormat;
  };
}

export interface ConnectionResponse extends BaseMessage {
  type: 'connection_response';
  data: {
    status: string;
    server_info: ServerInfo;
    session_id: string;
  };
}

// Audio Messages
export interface AudioStart extends BaseMessage {
  type: 'audio_start';
  data: {
    session_id: string;
    audio_config: AudioFormat;
    processing_options: {
      stt_model: string;
      auto_process: boolean;
    };
  };
}

export interface AudioData extends BaseMessage {
  type: 'audio_data';
  data: {
    session_id: string;
    audio_chunk: string; // base64 encoded
    sequence: number;
    is_final: boolean;
  };
}

export interface AudioStop extends BaseMessage {
  type: 'audio_stop';
  data: {
    session_id: string;
    sequence: number;
    duration_ms: number;
  };
}

// STT Messages
export interface STTResponse extends BaseMessage {
  type: 'stt_response';
  data: {
    session_id: string;
    text: string;
    confidence: number;
    language: string;
    processing_time_ms: number;
    audio_duration_ms: number;
    segments: STTSegment[];
  };
}

export interface STTRequest extends BaseMessage {
  type: 'stt_request';
  data: {
    session_id: string;
    audio_url?: string;
    model: string;
    language: string;
  };
}

export interface STTSegment {
  text: string;
  start: number;
  end: number;
  confidence: number;
}

// LLM Messages
export interface LLMRequest extends BaseMessage {
  type: 'llm_request';
  data: {
    session_id: string;
    text: string;
    model: string;
    context: string;
    options: LLMOptions;
  };
}

export interface LLMResponse extends BaseMessage {
  type: 'llm_response';
  data: {
    session_id: string;
    response: string;
    model: string;
    processing_time_ms: number;
    tokens_used: number;
    confidence: number;
  };
}

export interface LLMStream extends BaseMessage {
  type: 'llm_stream';
  data: {
    session_id: string;
    chunk: string;
    is_final: boolean;
  };
}

export interface LLMOptions {
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

// MCP Messages
export interface MCPRequest extends BaseMessage {
  type: 'mcp_request';
  data: {
    session_id: string;
    tool: string;
    arguments: Record<string, any>;
  };
}

export interface MCPResponse extends BaseMessage {
  type: 'mcp_response';
  data: {
    session_id: string;
    result: any;
    success: boolean;
  };
}

// Status and Error Messages
export interface StatusUpdate extends BaseMessage {
  type: 'status_update';
  data: {
    session_id: string;
    status: string;
    progress: number;
    message: string;
  };
}

export interface ErrorMessage extends BaseMessage {
  type: 'error';
  data: {
    session_id: string;
    error_type: string;
    message: string;
    error_code: string;
    details?: any;
  };
}

// Control Messages
export interface Heartbeat extends BaseMessage {
  type: 'heartbeat';
  data: {
    server_time: string;
    uptime: number;
  };
}

export interface HeartbeatResponse extends BaseMessage {
  type: 'heartbeat_response';
  data: {
    client_time: string;
  };
}

// Supporting Types
export interface AudioFormat {
  sample_rate: number;
  channels: number;
  bit_depth: number;
  encoding: string;
}

export interface ServerInfo {
  version: string;
  capabilities: string[];
  supported_models: string[];
}

export type MessageType = 
  | 'connection_request'
  | 'connection_response'
  | 'audio_start'
  | 'audio_data'
  | 'audio_stop'
  | 'stt_request'
  | 'stt_response'
  | 'llm_request'
  | 'llm_response'
  | 'llm_stream'
  | 'mcp_request'
  | 'mcp_response'
  | 'status_update'
  | 'error'
  | 'heartbeat'
  | 'heartbeat_response';

export type ClientMessage = 
  | ConnectionRequest
  | AudioStart
  | AudioData
  | AudioStop
  | STTRequest
  | LLMRequest
  | MCPRequest
  | HeartbeatResponse;

export type ServerMessage = 
  | ConnectionResponse
  | STTResponse
  | LLMResponse
  | LLMStream
  | MCPResponse
  | StatusUpdate
  | ErrorMessage
  | Heartbeat;