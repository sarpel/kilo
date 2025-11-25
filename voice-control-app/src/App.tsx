/**
 * Voice Control App - Main Entry Point
 * React Native Android application for voice control ecosystem
 */

import React, { useEffect } from 'react';
import { StatusBar, StyleSheet } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { gestureHandlerRootHOC } from 'react-native-gesture-handler';

import VoiceControlScreen from './screens/VoiceControlScreen';
import SettingsScreen from './screens/SettingsScreen';
import AboutScreen from './screens/AboutScreen';

import { RootStackParamList } from './types/app';

// Create navigation stack
const Stack = createStackNavigator<RootStackParamList>();

const App: React.FC = () => {
  useEffect(() => {
    // Initialize app-wide configurations
    initializeApp();
  }, []);

  const initializeApp = async () => {
    try {
      // Set up React Native Reanimated
      if (require('react-native-reanimated')) {
        const Reanimated = require('react-native-reanimated');
        if (Reanimated.setProgress) {
          // Reanimated v2 configuration
        }
      }
    } catch (error) {
      console.warn('Reanimated initialization warning:', error);
    }
  };

  const AppNavigator = () => (
    <Stack.Navigator
      initialRouteName="Home"
      screenOptions={{
        headerShown: false,
        cardStyle: { backgroundColor: '#1a1a1a' },
        cardStyleInterpolator: ({ current, layouts }) => {
          return {
            cardStyle: {
              transform: [
                {
                  translateX: current.progress.interpolate({
                    inputRange: [0, 1],
                    outputRange: [layouts.screen.width, 0],
                  }),
                },
              ],
              opacity: current.progress.interpolate({
                inputRange: [0, 0.5, 1],
                outputRange: [0, 1, 1],
              }),
            },
          };
        },
      }}
    >
      <Stack.Screen 
        name="Home" 
        component={VoiceControlScreen}
        options={{
          headerShown: false,
        }}
      />
      <Stack.Screen 
        name="Settings" 
        component={SettingsScreen}
        options={{
          headerShown: true,
          headerStyle: {
            backgroundColor: '#2d2d2d',
          },
          headerTintColor: '#fff',
          headerTitleStyle: {
            fontWeight: '600',
          },
        }}
      />
      <Stack.Screen 
        name="About" 
        component={AboutScreen}
        options={{
          headerShown: true,
          headerStyle: {
            backgroundColor: '#2d2d2d',
          },
          headerTintColor: '#fff',
          headerTitleStyle: {
            fontWeight: '600',
          },
        }}
      />
    </Stack.Navigator>
  );

  return (
    <>
      <StatusBar
        barStyle="light-content"
        backgroundColor="transparent"
        translucent={true}
      />
      <NavigationContainer>
        <AppNavigator />
      </NavigationContainer>
    </>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a1a',
  },
});

export default gestureHandlerRootHOC(App);