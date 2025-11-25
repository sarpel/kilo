package com.voicecontrolapp;

import android.content.Intent;
import android.content.Context;
import android.os.Build;
import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.pm.PackageManager;
import android.content.ComponentName;
import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;

import com.facebook.react.bridge.ReactContext;
import com.facebook.react.bridge.WritableMap;
import com.facebook.react.bridge.WritableNativeMap;
import com.facebook.react.modules.core.DeviceEventManagerModule;

import java.util.HashMap;
import java.util.Map;

public class VoiceControlTileService extends TileService {
    private static final String TILE_ID = "voice_control";
    private static final int NOTIFICATION_ID = 1001;
    private static final String CHANNEL_ID = "voice_control_service";
    
    private static boolean tileActive = false;
    private static ReactContext reactContext;
    private static VoiceControlTileService instance;
    
    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
        createNotificationChannel();
    }
    
    @Override
    public void onStartListening() {
        super.onStartListening();
        updateTileState();
        
        // Send event to React Native about tile state change
        if (reactContext != null) {
            sendReactEvent("tile_state_changed", getTileStateData());
        }
    }
    
    @Override
    public void onStopListening() {
        super.onStopListening();
    }
    
    @Override
    public void onClick() {
        super.onClick();
        
        // Toggle tile state
        tileActive = !tileActive;
        
        // Update tile UI
        updateTileState();
        
        // Send event to React Native
        if (reactContext != null) {
            sendReactEvent("tile_activated", getTileStateData());
        }
        
        if (tileActive) {
            // Start background voice recording
            startVoiceRecordingService();
            startVoiceRecording();
        } else {
            // Stop background voice recording
            stopVoiceRecordingService();
            stopVoiceRecording();
        }
        
        // Show notification
        showNotification(tileActive);
    }
    
    private void updateTileState() {
        Tile tile = getQsTile();
        if (tile != null) {
            if (tileActive) {
                tile.setState(Tile.STATE_ACTIVE);
                tile.setContentDescription("Voice Control Active");
                tile.setLabel("Voice Control ON");
            } else {
                tile.setState(Tile.STATE_INACTIVE);
                tile.setContentDescription("Voice Control Inactive");
                tile.setLabel("Voice Control OFF");
            }
            tile.updateTile();
        }
    }
    
    private void startVoiceRecordingService() {
        Intent serviceIntent = new Intent(this, VoiceRecordingService.class);
        serviceIntent.setAction("START_RECORDING");
        startForegroundService(serviceIntent);
    }
    
    private void stopVoiceRecordingService() {
        Intent serviceIntent = new Intent(this, VoiceRecordingService.class);
        serviceIntent.setAction("STOP_RECORDING");
        startService(serviceIntent);
    }
    
    private void startVoiceRecording() {
        // Send intent to start recording in background
        Intent intent = new Intent("VOICE_CONTROL_START_RECORDING");
        sendBroadcast(intent);
        
        // Update notification
        showNotification(true);
    }
    
    private void stopVoiceRecording() {
        // Send intent to stop recording
        Intent intent = new Intent("VOICE_CONTROL_STOP_RECORDING");
        sendBroadcast(intent);
        
        // Update notification
        showNotification(false);
    }
    
    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Voice Control Service",
                NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Voice control background service");
            channel.setShowBadge(false);
            channel.setSound(null, null);
            
            NotificationManager notificationManager = getSystemService(NotificationManager.class);
            notificationManager.createNotificationChannel(channel);
        }
    }
    
    private void showNotification(boolean isActive) {
        String title = isActive ? "Voice Control Active" : "Voice Control Inactive";
        String text = isActive ? "Listening for voice commands..." : "Voice control stopped";
        
        Intent mainIntent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
            this, 0, mainIntent, 
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? 
                PendingIntent.FLAG_IMMUTABLE : 0
        );
        
        Intent stopIntent = new Intent(this, VoiceControlTileService.class);
        stopIntent.setAction("STOP_VOICE_CONTROL");
        PendingIntent stopPendingIntent = PendingIntent.getService(
            this, 1, stopIntent,
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? 
                PendingIntent.FLAG_IMMUTABLE : 0
        );
        
        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(getNotificationIcon())
            .setContentTitle(title)
            .setContentText(text)
            .setContentIntent(pendingIntent)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setOngoing(isActive)
            .addAction(
                android.R.drawable.ic_media_pause,
                "Stop",
                stopPendingIntent
            );
        
        NotificationManagerCompat.from(this).notify(NOTIFICATION_ID, builder.build());
    }
    
    private int getNotificationIcon() {
        // Return appropriate icon for voice control
        return android.R.drawable.ic_btn_speak_now;
    }
    
    private WritableMap getTileStateData() {
        WritableMap map = new WritableNativeMap();
        map.putBoolean("active", tileActive);
        map.putString("state", tileActive ? "active" : "inactive");
        map.putString("timestamp", String.valueOf(System.currentTimeMillis()));
        return map;
    }
    
    private void sendReactEvent(String eventName, WritableMap params) {
        if (reactContext != null) {
            reactContext
                .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter.class)
                .emit(eventName, params);
        }
    }
    
    public static void setReactContext(ReactContext context) {
        reactContext = context;
    }
    
    public static boolean isTileActive() {
        return tileActive;
    }
    
    public static VoiceControlTileService getInstance() {
        return instance;
    }
    
    @Override
    public void onDestroy() {
        super.onDestroy();
        instance = null;
    }
}