import React from 'react';
import { View, Text, StyleSheet, ScrollView, Animated } from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { TranscriptDisplayProps } from '../types/app';

const TranscriptDisplay: React.FC<TranscriptDisplayProps> = ({
  transcript,
  confidence,
  isProcessing,
  showConfidence = false,
}) => {
  const fadeAnim = React.useRef(new Animated.Value(0)).current;
  const slideAnim = React.useRef(new Animated.Value(20)).current;

  React.useEffect(() => {
    if (transcript.trim()) {
      Animated.parallel([
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 300,
          useNativeDriver: false,
        }),
        Animated.timing(slideAnim, {
          toValue: 0,
          duration: 300,
          useNativeDriver: false,
        }),
      ]).start();
    } else {
      fadeAnim.setValue(0);
      slideAnim.setValue(20);
    }
  }, [transcript, fadeAnim, slideAnim]);

  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.8) return '#34c759';
    if (conf >= 0.6) return '#ff9500';
    return '#ff3b30';
  };

  const getConfidenceText = (conf: number) => {
    if (conf >= 0.8) return 'High';
    if (conf >= 0.6) return 'Medium';
    return 'Low';
  };

  if (!transcript.trim() && !isProcessing) {
    return null;
  }

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={['rgba(0, 0, 0, 0.8)', 'rgba(0, 0, 0, 0.9)']}
        style={styles.gradient}
      >
        <View style={styles.header}>
          <Text style={styles.headerText}>
            {isProcessing ? 'Processing...' : 'Transcript'}
          </Text>
          {showConfidence && confidence > 0 && (
            <View style={styles.confidenceContainer}>
              <View
                style={[
                  styles.confidenceIndicator,
                  { backgroundColor: getConfidenceColor(confidence) },
                ]}
              />
              <Text style={styles.confidenceText}>
                {Math.round(confidence * 100)}% {getConfidenceText(confidence)}
              </Text>
            </View>
          )}
        </View>

        <ScrollView
          style={styles.scrollContainer}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          <Animated.View
            style={[
              styles.contentContainer,
              {
                opacity: fadeAnim,
                transform: [{ translateY: slideAnim }],
              },
            ]}
          >
            {isProcessing ? (
              <View style={styles.processingContainer}>
                <View style={styles.processingDots}>
                  <Animated.View
                    style={[
                      styles.processingDot,
                      {
                        transform: [
                          {
                            scaleY: Animated.sequence([
                              Animated.timing(new Animated.Value(1), {
                                toValue: 0.5,
                                duration: 600,
                                useNativeDriver: false,
                              }),
                              Animated.timing(new Animated.Value(0.5), {
                                toValue: 1,
                                duration: 600,
                                useNativeDriver: false,
                              }),
                            ]),
                          },
                        ],
                      },
                    ]}
                  />
                  <Animated.View
                    style={[
                      styles.processingDot,
                      {
                        transform: [
                          {
                            scaleY: Animated.sequence([
                              Animated.timing(new Animated.Value(1), {
                                toValue: 0.3,
                                duration: 600,
                                delay: 200,
                                useNativeDriver: false,
                              }),
                              Animated.timing(new Animated.Value(0.3), {
                                toValue: 1,
                                duration: 600,
                                useNativeDriver: false,
                              }),
                            ]),
                          },
                        ],
                      },
                    ]}
                  />
                  <Animated.View
                    style={[
                      styles.processingDot,
                      {
                        transform: [
                          {
                            scaleY: Animated.sequence([
                              Animated.timing(new Animated.Value(1), {
                                toValue: 0.8,
                                duration: 600,
                                delay: 400,
                                useNativeDriver: false,
                              }),
                              Animated.timing(new Animated.Value(0.8), {
                                toValue: 1,
                                duration: 600,
                                useNativeDriver: false,
                              }),
                            ]),
                          },
                        ],
                      },
                    ]}
                  />
                </View>
              </View>
            ) : (
              <Text style={styles.transcriptText}>{transcript}</Text>
            )}
          </Animated.View>
        </ScrollView>
      </LinearGradient>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginTop: 20,
    borderRadius: 12,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  gradient: {
    minHeight: 100,
    maxHeight: 200,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  headerText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  confidenceContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  confidenceIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  confidenceText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '500',
  },
  scrollContainer: {
    flexGrow: 1,
  },
  contentContainer: {
    padding: 16,
  },
  transcriptText: {
    color: '#fff',
    fontSize: 16,
    lineHeight: 24,
    fontWeight: '400',
  },
  processingContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 20,
  },
  processingDots: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  processingDot: {
    width: 4,
    height: 16,
    backgroundColor: '#007aff',
    borderRadius: 2,
    marginHorizontal: 2,
  },
});

export default TranscriptDisplay;