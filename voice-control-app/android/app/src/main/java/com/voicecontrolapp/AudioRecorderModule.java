package com.voicecontrolapp;

import android.content.Context;
import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import com.facebook.react.bridge.Arguments;
import com.facebook.react.bridge.BaseActivityEventListener;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.bridge.ReactContext;
import com.facebook.react.bridge.ReactMethod;
import com.facebook.react.bridge.Promise;
import com.facebook.react.bridge.ReadableArray;
import com.facebook.react.bridge.ReadableMap;
import com.facebook.react.bridge.WritableArray;
import com.facebook.react.bridge.WritableMap;
import com.facebook.react.modules.core.DeviceEventManagerModule;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.concurrent.atomic.AtomicBoolean;

public class AudioRecorderModule extends com.facebook.react.bridge.ReactContextBaseJavaModule {
    private static final String TAG = "AudioRecorderModule";
    private static final String MODULE_NAME = "AudioRecorder";
    
    // Audio recording configuration
    private static final int SAMPLE_RATE = 16000;
    private static final int CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO;
    private static final int AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT;
    private static final int BUFFER_SIZE_FACTOR = 2;
    
    private AudioRecord audioRecord;
    private Thread recordingThread;
    private AtomicBoolean isRecording = new AtomicBoolean(false);
    private Handler mainHandler;
    
    // React context for sending events
    private final ReactApplicationContext reactContext;
    
    public AudioRecorderModule(ReactApplicationContext reactContext) {
        super(reactContext);
        this.reactContext = reactContext;
        this.mainHandler = new Handler(Looper.getMainLooper());
    }
    
    @Override
    public String getName() {
        return MODULE_NAME;
    }
    
    @Override
    public void initialize() {
        super.initialize();
        Log.d(TAG, "AudioRecorderModule initialized");
    }
    
    @Override
    public void onCatalystInstanceDestroy() {
        super.onCatalystInstanceDestroy();
        stopRecording();
        Log.d(TAG, "AudioRecorderModule destroyed");
    }
    
    @ReactMethod
    public void startRecording(final Promise promise) {
        try {
            if (isRecording.get()) {
                promise.reject("ALREADY_RECORDING", "Recording is already in progress");
                return;
            }
            
            int bufferSize = AudioRecord.getMinBufferSize(
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT
            ) * BUFFER_SIZE_FACTOR;
            
            audioRecord = new AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize
            );
            
            if (audioRecord.getState() != AudioRecord.STATE_INITIALIZED) {
                promise.reject("INIT_FAILED", "Failed to initialize AudioRecord");
                return;
            }
            
            audioRecord.startRecording();
            isRecording.set(true);
            
            // Start recording thread
            recordingThread = new Thread(new Runnable() {
                @Override
                public void run() {
                    processAudioData();
                }
            }, "AudioRecorder");
            
            recordingThread.start();
            
            sendEvent("recordingStarted", Arguments.createMap());
            promise.resolve("Recording started successfully");
            
        } catch (Exception e) {
            Log.e(TAG, "Error starting recording", e);
            promise.reject("RECORDING_ERROR", e.getMessage());
        }
    }
    
    @ReactMethod
    public void stopRecording(final Promise promise) {
        try {
            if (!isRecording.get()) {
                promise.reject("NOT_RECORDING", "No recording in progress");
                return;
            }
            
            stopRecording();
            
            sendEvent("recordingStopped", Arguments.createMap());
            promise.resolve("Recording stopped successfully");
            
        } catch (Exception e) {
            Log.e(TAG, "Error stopping recording", e);
            promise.reject("STOP_RECORDING_ERROR", e.getMessage());
        }
    }
    
    @ReactMethod
    public void isRecording(final Promise promise) {
        promise.resolve(isRecording.get());
    }
    
    @ReactMethod
    public void requestMicrophonePermission(final Promise promise) {
        // This should be handled by React Native Permissions module
        // Just return a placeholder for now
        promise.resolve(true);
    }
    
    private void stopRecording() {
        if (isRecording.get()) {
            isRecording.set(false);
            
            if (audioRecord != null) {
                audioRecord.stop();
                audioRecord.release();
                audioRecord = null;
            }
            
            if (recordingThread != null) {
                recordingThread.interrupt();
                recordingThread = null;
            }
        }
    }
    
    private void processAudioData() {
        short[] audioBuffer = new short[1024]; // Process in chunks
        
        while (isRecording.get()) {
            int readResult = audioRecord.read(audioBuffer, 0, audioBuffer.length);
            
            if (readResult > 0) {
                // Calculate audio level for visualization
                int audioLevel = calculateAudioLevel(audioBuffer, readResult);
                
                // Convert short array to byte array for base64 encoding
                byte[] audioBytes = shortsToBytes(audioBuffer, readResult);
                String base64Audio = android.util.Base64.encodeToString(
                    audioBytes, 
                    android.util.Base64.NO_WRAP
                );
                
                // Send audio data to React Native
                WritableMap audioData = Arguments.createMap();
                audioData.putString("audioData", base64Audio);
                audioData.putInt("audioLevel", audioLevel);
                audioData.putInt("sequence", getNextSequence());
                
                sendEvent("audioData", audioData);
            }
        }
    }
    
    private int calculateAudioLevel(short[] buffer, int bufferSize) {
        long sum = 0;
        for (int i = 0; i < bufferSize; i++) {
            sum += Math.abs(buffer[i]);
        }
        
        int average = (int) (sum / bufferSize);
        
        // Normalize to 0-100 scale for React Native
        return Math.min(100, Math.max(0, (int) (average / 327.67)));
    }
    
    private byte[] shortsToBytes(short[] shorts, int length) {
        byte[] bytes = new byte[length * 2];
        for (int i = 0; i < length; i++) {
            short s = shorts[i];
            bytes[i * 2] = (byte) (s & 0x00FF);
            bytes[i * 2 + 1] = (byte) ((s & 0xFF00) >> 8);
        }
        return bytes;
    }
    
    private int sequenceCounter = 0;
    private synchronized int getNextSequence() {
        return ++sequenceCounter;
    }
    
    private void sendEvent(String eventName, WritableMap params) {
        reactContext
            .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter.class)
            .emit(eventName, params);
    }
    
    // Public methods for VoiceControlTileService to access
    public void startBackgroundRecording() {
        try {
            startRecording(new SimplePromise(TAG, "Background recording start"));
        } catch (Exception e) {
            Log.e(TAG, "Error starting background recording", e);
        }
    }
    
    public void stopBackgroundRecording() {
        try {
            stopRecording(new SimplePromise(TAG, "Background recording stop"));
        } catch (Exception e) {
            Log.e(TAG, "Error stopping background recording", e);
        }
    }
    
    public boolean isCurrentlyRecording() {
        return isRecording.get();
    }

    private static class SimplePromise implements Promise {
        private String tag;
        private String operation;
        
        public SimplePromise(String tag, String operation) {
            this.tag = tag;
            this.operation = operation;
        }

        @Override
        public void resolve(Object value) {
            Log.d(tag, operation + " success");
        }

        @Override
        public void reject(String code, String message) {
            Log.e(tag, operation + " failed: " + message);
        }

        @Override
        public void reject(String code, Throwable throwable) {
            Log.e(tag, operation + " failed: " + code, throwable);
        }

        @Override
        public void reject(String code, String message, Throwable throwable) {
            Log.e(tag, operation + " failed: " + message, throwable);
        }

        @Override
        public void reject(Throwable throwable) {
            Log.e(tag, operation + " failed", throwable);
        }

        @Override
        public void reject(Throwable throwable, WritableMap userInfo) {
            Log.e(tag, operation + " failed", throwable);
        }

        @Override
        public void reject(String code, WritableMap userInfo) {
            Log.e(tag, operation + " failed: " + code);
        }

        @Override
        public void reject(String code, Throwable throwable, WritableMap userInfo) {
            Log.e(tag, operation + " failed: " + code, throwable);
        }

        @Override
        public void reject(String code, String message, WritableMap userInfo) {
            Log.e(tag, operation + " failed: " + message);
        }

        @Override
        public void reject(String code, String message, Throwable throwable, WritableMap userInfo) {
            Log.e(tag, operation + " failed: " + message, throwable);
        }
        
        @Override
        public void reject(String code) {
             Log.e(tag, operation + " failed: " + code);
        }
    }
}