import React from 'react';
import { View, StyleSheet } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { AudioWaveformProps } from '../types/app';

const BAR_COUNT = 32;
const MAX_BAR_HEIGHT = 80;
const MIN_BAR_HEIGHT = 4;

const AudioWaveform: React.FC<AudioWaveformProps> = ({
  audioLevel,
  isRecording,
  width,
  height,
}) => {
  const barHeights = React.useRef(
    Array.from({ length: BAR_COUNT }, () => MIN_BAR_HEIGHT)
  ).current;

  const animatedValues = React.useRef(
    Array.from({ length: BAR_COUNT }, () => ({
      scaleY: new Animated.Value(MIN_BAR_HEIGHT),
    }))
  ).current;

  // Update bar heights based on audio level
  React.useEffect(() => {
    if (isRecording) {
      barHeights.forEach((_, index) => {
        // Create variation across bars
        const variation = Math.sin(index * 0.3) * 0.3 + 0.7;
        const targetHeight = Math.max(
          MIN_BAR_HEIGHT,
          Math.min(
            MAX_BAR_HEIGHT,
            audioLevel * variation * MAX_BAR_HEIGHT
          )
        );

        animatedValues[index].scaleY.setValue(targetHeight / MAX_BAR_HEIGHT);
      });
    } else {
      // Reset to minimum height when not recording
      animatedValues.forEach((value) => {
        value.scaleY.setValue(MIN_BAR_HEIGHT / MAX_BAR_HEIGHT);
      });
    }
  }, [audioLevel, isRecording, animatedValues, barHeights]);

  return (
    <View
      style={[
        styles.container,
        {
          width,
          height,
        },
      ]}
    >
      <View style={styles.waveform}>
        {animatedValues.map((animatedValue, index) => (
          <AnimatedBar
            key={index}
            animatedValue={animatedValue.scaleY}
            delay={index * 50}
          />
        ))}
      </View>
    </View>
  );
};

interface AnimatedBarProps {
  animatedValue: Animated.Value;
  delay: number;
}

const AnimatedBar: React.FC<AnimatedBarProps> = ({ animatedValue, delay }) => {
  const scaleY = useSharedValue(0.1);

  React.useEffect(() => {
    // Start the animation when component mounts
    scaleY.value = withRepeat(
      withTiming(1, {
        duration: 1000,
        easing: Easing.inOut(Easing.ease),
      }),
      -1,
      false,
      delay
    );
  }, [scaleY, delay]);

  const animatedStyle = useAnimatedStyle(() => {
    return {
      transform: [
        {
          scaleY: scaleY.value,
        },
      ],
    };
  });

  return (
    <View style={styles.barContainer}>
      <Animated.View
        style={[
          styles.bar,
          animatedStyle,
        ]}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.1)',
    borderRadius: 12,
  },
  waveform: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'center',
    height: '100%',
    width: '100%',
    paddingHorizontal: 8,
  },
  barContainer: {
    flex: 1,
    marginHorizontal: 1,
    justifyContent: 'flex-end',
  },
  bar: {
    backgroundColor: '#007aff',
    borderRadius: 2,
    minHeight: 2,
    opacity: 0.8,
  },
});

export default AudioWaveform;