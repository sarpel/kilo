import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  StyleSheet,
  Dimensions,
  StatusBar,
  Alert,
  Platform,
  BackHandler,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import NetInfo from '@react-native-community/netinfo';
import { useFocusEffect } from '@react-navigation/native';

import VoiceControlButton from '../components/VoiceControlButton';
import AudioWaveform from '../components/AudioWaveform';
import ConnectionStatus from '../components/ConnectionStatus';
import TranscriptDisplay from '../components/TranscriptDisplay';
import { VoiceControlNativeModule } from '../native/VoiceControlNativeModule';
import { WebSocketService } from '../services/websocket';
import { AudioService } from '../services/audio';
import {
  AppConfig,
  AppState,
  AudioRecordingState,
  ConnectionState,
  STTState,
  LLMState,
  PermissionState,
} from '../types/app';
import { ConnectionRequest, STTResponse, LLMResponse } from '../types/api';

const { width, height } = Dimensions.get('window');

interface VoiceControlScreenProps {
  navigation: any;
}

const VoiceControlScreen: React.FC<VoiceControlScreenProps> = ({ navigation }) => {
  // Services
  const [webSocketService] = useState(() => new WebSocketService({
    websocketUrl: 'ws://192.168.1.100:8000/ws', // Will be updated via network discovery
    apiBaseUrl: 'http://192.168.1.100:8000',
    debug: true,
    environment: 'development',
  } as AppConfig));

  const [audioService] = useState(() => new AudioService({
    sampleRate: 16000,
    channels: 1,
    bitDepth: 16,
    encoding: 'pcm',
    chunkSize: 1024,
  }));

  // App State
  const [appState, setAppState] = useState<AppState>({
    audio: {
      isRecording: false,
      isProcessing: false,
      audioLevel: 0,
      duration: 0,
    },
    stt: {
      isProcessing: false,
      confidence: 0,
      language: 'en',
      processingTime: 0,
    },
    llm: {
      isProcessing: false,
      isStreaming: false,
      model: 'llama2',
      context: 'user_query',
    },
    connection: {
      isConnected: false,
      isConnecting: false,
    },
    settings: {
      audio: {
        sampleRate: 16000,
        channels: 1,
        bitDepth: 16,
        encoding: 'pcm',
        autoProcess: true,
      },
      stt: {
        model: 'whisper-base',
        language: 'en',
        confidenceThreshold: 0.7,
      },
      llm: {
        model: 'llama2',
        temperature: 0.7,
        maxTokens: 150,
        stream: false,
      },
      notifications: {
        enabled: true,
        sound: true,
        vibration: true,
      },
    },
  });

  const [permissions, setPermissions] = useState<PermissionState>({
    microphone: 'undetermined',
    storage: 'undetermined',
    network: 'undetermined',
  });

  const [currentTranscript, setCurrentTranscript] = useState('');
  const [networkStatus, setNetworkStatus] = useState('unknown');

  // Initialize services and setup event listeners
  useEffect(() => {
    initializeServices();
    setupEventListeners();
    setupVoiceControlTile();

    return () => {
      cleanup();
    };
  }, []);

  // Handle app focus for background/foreground transitions
  useFocusEffect(
    useCallback(() => {
      const onFocus = () => {
        // App came to foreground
        console.log('VoiceControlScreen: App came to foreground');
        // Resume audio processing if needed
      };

      const onBlur = () => {
        // App went to background
        console.log('VoiceControlScreen: App went to background');
        // Pause or continue audio processing based on tile state
      };

      const subscription = {
        addListener: (event: string, callback: any) => {
          if (event === 'focus') {
            const unsubscribe = navigation.addListener('focus', callback);
            return unsubscribe;
          } else if (event === 'blur') {
            const unsubscribe = navigation.addListener('blur', callback);
            return unsubscribe;
          }
          return () => {};
        },
      };

      return () => {
        // Cleanup if needed
      };
    }, [navigation])
  );

  // Handle hardware back button
  useEffect(() => {
    const backHandler = BackHandler.addEventListener('hardwareBackPress', () => {
      // Don't allow back navigation from main screen
      return true;
    });

    return () => backHandler.remove();
  }, []);

  const initializeServices = async () => {
    try {
      // Check permissions
      const permissionResult = await audioService.checkPermissions();
      setPermissions(permissionResult);

      if (permissionResult.microphone === 'denied') {
        Alert.alert(
          'Microphone Permission Required',
          'This app needs microphone access to record your voice commands.',
          [
            { text: 'Cancel', style: 'cancel' },
            {
              text: 'Settings',
              onPress: () => {
                // Open app settings
                VoiceControlNativeModule.openAppSettings();
              },
            },
          ]
        );
        return;
      }

      // Initialize audio service
      await audioService.initialize();

      // Initialize WebSocket service
      await webSocketService.connect();

      // Send connection request
      const connectionRequest: ConnectionRequest = {
        type: 'connection_request',
        timestamp: new Date().toISOString(),
        data: {
          client_id: `voice-control-app-${Date.now()}`,
          client_version: '1.0.0',
          capabilities: ['stt', 'llm', 'mcp'],
          audio_format: {
            sample_rate: 16000,
            channels: 1,
            bit_depth: 16,
            encoding: 'pcm',
          },
        },
        message_id: `conn_${Date.now()}`,
      };

      webSocketService.sendMessage(connectionRequest);

    } catch (error) {
      console.error('Failed to initialize services:', error);
      Alert.alert('Initialization Error', 'Failed to initialize voice control services.');
    }
  };

  const setupEventListeners = () => {
    // WebSocket event listeners
    webSocketService.on('connection_response', (response) => {
      setAppState(prev => ({
        ...prev,
        connection: {
          ...prev.connection,
          isConnected: true,
          isConnecting: false,
          sessionId: response.data.session_id,
          serverInfo: response.data.server_info,
        },
      }));
    });

    webSocketService.on('connection_request', () => {
      setAppState(prev => ({
        ...prev,
        connection: {
          ...prev.connection,
          isConnecting: true,
          isConnected: false,
        },
      }));
    });

    webSocketService.on('disconnect', () => {
      setAppState(prev => ({
        ...prev,
        connection: {
          ...prev.connection,
          isConnected: false,
          isConnecting: false,
          sessionId: undefined,
        },
      }));
    });

    // Audio event listeners
    audioService.on('recording_started', () => {
      setAppState(prev => ({
        ...prev,
        audio: {
          ...prev.audio,
          isRecording: true,
          duration: 0,
        },
      }));
    });

    audioService.on('recording_stopped', () => {
      setAppState(prev => ({
        ...prev,
        audio: {
          ...prev.audio,
          isRecording: false,
        },
      }));
    });

    audioService.on('audio_chunk', (chunk) => {
      // Send audio chunk to server
      if (appState.connection.sessionId) {
        webSocketService.sendAudioData(
          appState.connection.sessionId,
          chunk.data,
          chunk.sequence,
          false
        );
      }
    });

    // STT event listeners
    webSocketService.on('stt_response', (response: STTResponse) => {
      setCurrentTranscript(response.data.text);
      setAppState(prev => ({
        ...prev,
        stt: {
          ...prev.stt,
          isProcessing: false,
          result: {
            text: response.data.text,
            segments: response.data.segments,
          },
          confidence: response.data.confidence,
          language: response.data.language,
          processingTime: response.data.processing_time_ms,
        },
        audio: {
          ...prev.audio,
          isProcessing: false,
        },
      }));
    });

    // LLM event listeners
    webSocketService.on('llm_response', (response: LLMResponse) => {
      setAppState(prev => ({
        ...prev,
        llm: {
          ...prev.llm,
          isProcessing: false,
          result: {
            response: response.data.response,
            tokensUsed: response.data.tokens_used,
            processingTime: response.data.processing_time_ms,
            confidence: response.data.confidence,
          },
        },
      }));
    });

    // Network status monitoring
    NetInfo.addEventListener(state => {
      setNetworkStatus(state.isConnected ? 'connected' : 'disconnected');
    });
  };

  const setupVoiceControlTile = () => {
    // Setup Android Quick Settings Tile
    VoiceControlNativeModule.initializeTile(() => {
      console.log('Quick Settings Tile initialized');
    });
  };

  const handleVoiceButtonPress = async () => {
    try {
      if (!appState.connection.isConnected) {
        Alert.alert('Not Connected', 'Please ensure you are connected to the voice control server.');
        return;
      }

      if (!appState.audio.isRecording) {
        // Start recording
        await audioService.startRecording();
        setAppState(prev => ({
          ...prev,
          audio: {
            ...prev.audio,
            isRecording: true,
            isProcessing: false,
          },
        }));
      } else {
        // Stop recording
        const buffers = await audioService.stopRecording();
        const duration = Date.now() - appState.audio.duration;
        
        // Send audio stop message
        if (appState.connection.sessionId) {
          webSocketService.sendAudioStop(
            appState.connection.sessionId,
            appState.audio.duration, // Use duration as sequence for now
            duration
          );
        }

        setAppState(prev => ({
          ...prev,
          audio: {
            ...prev.audio,
            isRecording: false,
            isProcessing: appState.settings.audio.autoProcess,
          },
          stt: {
            ...prev.stt,
            isProcessing: appState.settings.audio.autoProcess,
          },
        }));
      }
    } catch (error) {
      console.error('Voice button press error:', error);
      Alert.alert('Error', 'Failed to process voice command. Please try again.');
    }
  };

  const cleanup = () => {
    try {
      audioService.destroy();
      webSocketService.disconnect();
    } catch (error) {
      console.error('Cleanup error:', error);
    }
  };

  return (
    <LinearGradient
      colors={['#1a1a1a', '#2d2d2d', '#1a1a1a']}
      style={styles.container}
    >
      <StatusBar
        barStyle="light-content"
        backgroundColor="transparent"
        translucent={true}
      />

      {/* Connection Status */}
      <View style={styles.statusContainer}>
        <ConnectionStatus
          isConnected={appState.connection.isConnected}
          isConnecting={appState.connection.isConnecting}
          sessionId={appState.connection.sessionId}
          error={appState.connection.error}
        />
      </View>

      {/* Main Content */}
      <View style={styles.mainContent}>
        {/* Audio Waveform */}
        {(appState.audio.isRecording || appState.audio.isProcessing) && (
          <View style={styles.waveformContainer}>
            <AudioWaveform
              audioLevel={appState.audio.audioLevel}
              isRecording={appState.audio.isRecording}
              width={width - 32}
              height={100}
            />
          </View>
        )}

        {/* Voice Control Button */}
        <View style={styles.buttonContainer}>
          <VoiceControlButton
            onPress={handleVoiceButtonPress}
            isRecording={appState.audio.isRecording}
            isProcessing={appState.audio.isProcessing || appState.stt.isProcessing}
            disabled={!appState.connection.isConnected}
          />
        </View>

        {/* Transcript Display */}
        <View style={styles.transcriptContainer}>
          <TranscriptDisplay
            transcript={currentTranscript}
            confidence={appState.stt.confidence}
            isProcessing={appState.stt.isProcessing}
            showConfidence={true}
          />
        </View>
      </View>

      {/* Network Status Indicator */}
      <View style={styles.networkIndicator}>
        <Text style={[
          styles.networkText,
          {
            color: networkStatus === 'connected' ? '#34c759' : '#ff3b30'
          }
        ]}>
          {networkStatus === 'connected' ? '🟢' : '🔴'} Network
        </Text>
      </View>
    </LinearGradient>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: StatusBar.currentHeight,
  },
  statusContainer: {
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  mainContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 16,
  },
  waveformContainer: {
    marginBottom: 20,
  },
  buttonContainer: {
    marginBottom: 40,
  },
  transcriptContainer: {
    width: '100%',
    maxHeight: 200,
  },
  networkIndicator: {
    position: 'absolute',
    top: StatusBar.currentHeight + 8,
    right: 16,
  },
  networkText: {
    fontSize: 12,
    fontWeight: '600',
  },
});

export default VoiceControlScreen;