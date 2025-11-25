import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
  Dimensions,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { VoiceControlButtonProps } from '../types/app';

const { width } = Dimensions.get('window');

const VoiceControlButton: React.FC<VoiceControlButtonProps> = ({
  onPress,
  isRecording,
  isProcessing,
  disabled = false,
}) => {
  const scaleAnim = React.useRef(new Animated.Value(1)).current;
  const pulseAnim = React.useRef(new Animated.Value(0)).current;
  const glowAnim = React.useRef(new Animated.Value(0)).current;

  React.useEffect(() => {
    // Main button scale animation
    const createScaleAnimation = (toValue: number, duration: number = 200) => {
      return Animated.spring(scaleAnim, {
        toValue,
        useNativeDriver: true,
        tension: 300,
        friction: 10,
      });
    };

    // Pulse animation for recording state
    if (isRecording) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 1000,
            useNativeDriver: false,
          }),
          Animated.timing(pulseAnim, {
            toValue: 0,
            duration: 1000,
            useNativeDriver: false,
          }),
        ])
      ).start();

      // Glow animation
      Animated.loop(
        Animated.sequence([
          Animated.timing(glowAnim, {
            toValue: 1,
            duration: 1500,
            useNativeDriver: false,
          }),
          Animated.timing(glowAnim, {
            toValue: 0,
            duration: 1500,
            useNativeDriver: false,
          }),
        ])
      ).start();
    } else {
      pulseAnim.setValue(0);
      glowAnim.setValue(0);
    }

    // Button press animation
    const handlePressIn = () => {
      if (!isRecording && !isProcessing) {
        createScaleAnimation(0.95).start();
      }
    };

    const handlePressOut = () => {
      if (!isRecording && !isProcessing) {
        createScaleAnimation(1).start();
      }
    };
  }, [isRecording, isProcessing, scaleAnim, pulseAnim, glowAnim]);

  const getButtonContent = () => {
    if (isProcessing) {
      return (
        <View style={styles.processingContainer}>
          <View style={styles.processingDot1} />
          <View style={styles.processingDot2} />
          <View style={styles.processingDot3} />
          <Text style={styles.processingText}>Processing...</Text>
        </View>
      );
    }

    if (isRecording) {
      return (
        <View style={styles.recordingContainer}>
          <View style={styles.recordingIcon} />
          <Text style={styles.recordingText}>Recording...</Text>
        </View>
      );
    }

    return (
      <View style={styles.idleContainer}>
        <Text style={styles.idleText}>Hold to Speak</Text>
      </View>
    );
  };

  const getButtonColors = () => {
    if (isProcessing) {
      return ['#ff9500', '#ff6b00'];
    }
    if (isRecording) {
      return ['#ff3b30', '#d70015'];
    }
    return ['#007aff', '#0056d2'];
  };

  return (
    <View style={styles.container}>
      <Animated.View
        style={[
          styles.buttonContainer,
          {
            transform: [{ scale: scaleAnim }],
          },
        ]}
      >
        {/* Glow effect */}
        {isRecording && (
          <Animated.View
            style={[
              styles.glowEffect,
              {
                opacity: glowAnim,
              },
            ]}
          />
        )}

        {/* Pulse effect */}
        {isRecording && (
          <Animated.View
            style={[
              styles.pulseEffect,
              {
                transform: [
                  {
                    scale: pulseAnim.interpolate({
                      inputRange: [0, 1],
                      outputRange: [1, 1.8],
                    }),
                  },
                ],
              },
            ]}
          />
        )}

        <LinearGradient
          colors={getButtonColors()}
          style={styles.buttonGradient}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
        >
          <TouchableOpacity
            style={[
              styles.button,
              (disabled || isProcessing) && styles.buttonDisabled,
            ]}
            onPress={onPress}
            disabled={disabled || isProcessing}
            activeOpacity={0.8}
          >
            {getButtonContent()}
          </TouchableOpacity>
        </LinearGradient>
      </Animated.View>

      {/* Status indicator */}
      <View style={styles.statusIndicator}>
        <View
          style={[
            styles.statusDot,
            {
              backgroundColor: isRecording
                ? '#ff3b30'
                : isProcessing
                ? '#ff9500'
                : '#34c759',
            },
          ]}
        />
        <Text style={styles.statusText}>
          {isRecording
            ? 'Listening...'
            : isProcessing
            ? 'Processing...'
            : 'Ready'}
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonContainer: {
    position: 'relative',
  },
  button: {
    width: 140,
    height: 140,
    borderRadius: 70,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 4,
    },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  buttonGradient: {
    width: '100%',
    height: '100%',
    borderRadius: 70,
    justifyContent: 'center',
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  idleContainer: {
    alignItems: 'center',
  },
  idleText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
  },
  recordingContainer: {
    alignItems: 'center',
  },
  recordingIcon: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: '#fff',
    marginBottom: 8,
  },
  recordingText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
  },
  processingContainer: {
    alignItems: 'center',
  },
  processingDot1: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#fff',
    marginBottom: 4,
  },
  processingDot2: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#fff',
    marginBottom: 4,
  },
  processingDot3: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: '#fff',
    marginBottom: 8,
  },
  processingText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '500',
    textAlign: 'center',
  },
  pulseEffect: {
    position: 'absolute',
    top: -20,
    left: -20,
    right: -20,
    bottom: -20,
    borderRadius: 80,
    borderWidth: 3,
    borderColor: '#ff3b30',
    backgroundColor: 'transparent',
  },
  glowEffect: {
    position: 'absolute',
    top: -30,
    left: -30,
    right: -30,
    bottom: -30,
    borderRadius: 90,
    backgroundColor: '#ff3b30',
  },
  statusIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 16,
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 20,
    backdropFilter: 'blur(10px)',
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  statusText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '500',
  },
});

export default VoiceControlButton;