import React from 'react';
import { View, Text, StyleSheet, Animated, Dimensions } from 'react-native';
import { ConnectionStatusProps } from '../types/app';

const { width } = Dimensions.get('window');

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  isConnected,
  isConnecting,
  sessionId,
  error,
}) => {
  const pulseAnim = React.useRef(new Animated.Value(0)).current;
  const fadeAnim = React.useRef(new Animated.Value(1)).current;

  React.useEffect(() => {
    if (isConnecting) {
      // Pulse animation for connecting state
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
    } else {
      pulseAnim.setValue(0);
    }

    // Fade animation for error states
    if (error) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(fadeAnim, {
            toValue: 0.5,
            duration: 800,
            useNativeDriver: false,
          }),
          Animated.timing(fadeAnim, {
            toValue: 1,
            duration: 800,
            useNativeDriver: false,
          }),
        ])
      ).start();
    } else {
      fadeAnim.setValue(1);
    }
  }, [isConnecting, error, pulseAnim, fadeAnim]);

  const getStatusIcon = () => {
    if (error) return '⚠️';
    if (isConnecting) return '🔄';
    if (isConnected) return '✅';
    return '❌';
  };

  const getStatusColor = () => {
    if (error) return '#ff3b30';
    if (isConnecting) return '#ff9500';
    if (isConnected) return '#34c759';
    return '#ff3b30';
  };

  const getStatusText = () => {
    if (error) return `Error: ${error}`;
    if (isConnecting) return 'Connecting to server...';
    if (isConnected) return 'Connected to server';
    return 'Not connected';
  };

  return (
    <View style={styles.container}>
      <Animated.View
        style={[
          styles.statusContainer,
          {
            borderColor: getStatusColor(),
            opacity: fadeAnim,
          },
        ]}
      >
        <Animated.View
          style={[
            styles.iconContainer,
            {
              backgroundColor: getStatusColor(),
              transform: [
                {
                  scale: pulseAnim.interpolate({
                    inputRange: [0, 1],
                    outputRange: [1, 1.1],
                  }),
                },
              ],
            },
          ]}
        >
          <Text style={styles.statusIcon}>{getStatusIcon()}</Text>
        </Animated.View>

        <View style={styles.textContainer}>
          <Text style={styles.statusText}>{getStatusText()}</Text>
          {sessionId && isConnected && (
            <Text style={styles.sessionText}>
              Session: {sessionId.substring(0, 8)}...
            </Text>
          )}
        </View>
      </Animated.View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
    paddingHorizontal: 16,
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 12,
    borderWidth: 1,
    backdropFilter: 'blur(10px)',
  },
  iconContainer: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  statusIcon: {
    fontSize: 16,
  },
  textContainer: {
    flex: 1,
  },
  statusText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  sessionText: {
    color: 'rgba(255, 255, 255, 0.7)',
    fontSize: 12,
    marginTop: 2,
  },
});

export default ConnectionStatus;