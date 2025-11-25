// VoiceControl Native Module for React Native
// Provides interface to Android native modules

import { NativeModules, NativeEventEmitter, Platform } from 'react-native';

const { VoiceControlNativeModule } = NativeModules;

export interface VoiceControlTileState {
  active: boolean;
  state: string;
  timestamp: string;
}

export interface AudioRecordingData {
  audioData: string;
  audioLevel: number;
  sequence: number;
}

export class VoiceControlNativeModule {
  private static eventEmitter: NativeEventEmitter | null = null;

  /**
   * Initialize the voice control system
   */
  static initialize(): Promise<boolean> {
    return new Promise((resolve, reject) => {
      try {
        if (Platform.OS === 'android' && VoiceControlNativeModule) {
          VoiceControlNativeModule.initialize()
            .then(() => {
              this.setupEventListeners();
              resolve(true);
            })
            .catch(reject);
        } else {
          resolve(true); // iOS or simulation
        }
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Initialize the Android Quick Settings Tile
   */
  static initializeTile(callback?: (success: boolean) => void): void {
    if (Platform.OS === 'android' && VoiceControlNativeModule) {
      VoiceControlNativeModule.initializeTile()
        .then(() => {
          callback?.(true);
        })
        .catch(() => {
          callback?.(false);
        });
    } else {
      callback?.(true);
    }
  }

  /**
   * Open the app settings page
   */
  static openAppSettings(): Promise<boolean> {
    return new Promise((resolve) => {
      if (Platform.OS === 'android' && VoiceControlNativeModule) {
        VoiceControlNativeModule.openAppSettings()
          .then(() => resolve(true))
          .catch(() => resolve(false));
      } else {
        resolve(true);
      }
    });
  }

  /**
   * Get the current tile state
   */
  static getTileState(): Promise<VoiceControlTileState | null> {
    return new Promise((resolve) => {
      if (Platform.OS === 'android' && VoiceControlNativeModule) {
        VoiceControlNativeModule.getTileState()
          .then((state: VoiceControlTileState) => resolve(state))
          .catch(() => resolve(null));
      } else {
        resolve(null);
      }
    });
  }

  /**
   * Check if tile is active
   */
  static isTileActive(): Promise<boolean> {
    return new Promise((resolve) => {
      if (Platform.OS === 'android' && VoiceControlNativeModule) {
        VoiceControlNativeModule.isTileActive()
          .then(resolve)
          .catch(() => resolve(false));
      } else {
        resolve(false);
      }
    });
  }

  /**
   * Start audio recording
   */
  static startAudioRecording(): Promise<boolean> {
    return new Promise((resolve, reject) => {
      if (Platform.OS === 'android' && VoiceControlNativeModule) {
        VoiceControlNativeModule.startAudioRecording()
          .then(() => resolve(true))
          .catch(reject);
      } else {
        resolve(true); // iOS simulation
      }
    });
  }

  /**
   * Stop audio recording
   */
  static stopAudioRecording(): Promise<boolean> {
    return new Promise((resolve, reject) => {
      if (Platform.OS === 'android' && VoiceControlNativeModule) {
        VoiceControlNativeModule.stopAudioRecording()
          .then(() => resolve(true))
          .catch(reject);
      } else {
        resolve(true);
      }
    });
  }

  /**
   * Check if currently recording
   */
  static isAudioRecording(): Promise<boolean> {
    return new Promise((resolve) => {
      if (Platform.OS === 'android' && VoiceControlNativeModule) {
        VoiceControlNativeModule.isAudioRecording()
          .then(resolve)
          .catch(() => resolve(false));
      } else {
        resolve(false);
      }
    });
  }

  /**
   * Request microphone permission
   */
  static requestMicrophonePermission(): Promise<boolean> {
    return new Promise((resolve, reject) => {
      if (Platform.OS === 'android' && VoiceControlNativeModule) {
        VoiceControlNativeModule.requestMicrophonePermission()
          .then(resolve)
          .catch(reject);
      } else {
        resolve(true);
      }
    });
  }

  /**
   * Setup event listeners for native module events
   */
  private static setupEventListeners(): void {
    if (this.eventEmitter || !VoiceControlNativeModule) {
      return;
    }

    this.eventEmitter = new NativeEventEmitter(VoiceControlNativeModule);

    // Tile state change events
    this.eventEmitter.addListener('tile_state_changed', (state: VoiceControlTileState) => {
      console.log('Tile state changed:', state);
      // Emit custom event for React Native components to listen
      this.emitCustomEvent('voice_control_tile_state_changed', state);
    });

    this.eventEmitter.addListener('tile_activated', (state: VoiceControlTileState) => {
      console.log('Tile activated:', state);
      this.emitCustomEvent('voice_control_tile_activated', state);
    });

    // Audio recording events
    this.eventEmitter.addListener('recordingStarted', () => {
      console.log('Audio recording started');
      this.emitCustomEvent('audio_recording_started', {});
    });

    this.eventEmitter.addListener('recordingStopped', () => {
      console.log('Audio recording stopped');
      this.emitCustomEvent('audio_recording_stopped', {});
    });

    this.eventEmitter.addListener('audioData', (data: AudioRecordingData) => {
      console.log('Audio data received:', data);
      this.emitCustomEvent('audio_recording_data', data);
    });
  }

  /**
   * Emit custom events for React Native components
   */
  private static emitCustomEvent(eventName: string, data: any): void {
    // Create a custom event emitter that components can listen to
    const CustomEventEmitter = require('react-native').NativeEventEmitter;
    if (!this.customEventEmitter) {
      this.customEventEmitter = new CustomEventEmitter();
    }
    this.customEventEmitter.emit(eventName, data);
  }

  // Event listener management
  private static customEventEmitter: any = null;

  /**
   * Add event listener for custom events
   */
  static addEventListener(eventName: string, handler: (data: any) => void): void {
    if (!this.customEventEmitter) {
      const { NativeEventEmitter } = require('react-native');
      this.customEventEmitter = new NativeEventEmitter();
    }
    this.customEventEmitter.addListener(eventName, handler);
  }

  /**
   * Remove event listener
   */
  static removeEventListener(eventName: string, handler?: (data: any) => void): void {
    if (!this.customEventEmitter) return;
    
    if (handler) {
      this.customEventEmitter.removeListener(eventName, handler);
    } else {
      this.customEventEmitter.removeAllListeners(eventName);
    }
  }

  /**
   * Network discovery functions
   */
  static discoverServers(): Promise<string[]> {
    return new Promise((resolve, reject) => {
      if (Platform.OS === 'android' && VoiceControlNativeModule) {
        VoiceControlNativeModule.discoverServers()
          .then(resolve)
          .catch(reject);
      } else {
        // Fallback: return mock server addresses for testing
        resolve(['192.168.1.100:8000', '192.168.1.101:8000']);
      }
    });
  }

  /**
   * Ping server to check connectivity
   */
  static pingServer(serverAddress: string): Promise<boolean> {
    return new Promise((resolve) => {
      if (Platform.OS === 'android' && VoiceControlNativeModule) {
        VoiceControlNativeModule.pingServer(serverAddress)
          .then(resolve)
          .catch(() => resolve(false));
      } else {
        // Mock ping for testing
        resolve(Math.random() > 0.3); // 70% success rate
      }
    });
  }

  /**
   * Get network information
   */
  static getNetworkInfo(): Promise<any> {
    return new Promise((resolve) => {
      if (Platform.OS === 'android' && VoiceControlNativeModule) {
        VoiceControlNativeModule.getNetworkInfo()
          .then(resolve)
          .catch(() => resolve(null));
      } else {
        resolve({
          ip: '192.168.1.100',
          connected: true,
          type: 'wifi'
        });
      }
    });
  }
}

export default VoiceControlNativeModule;