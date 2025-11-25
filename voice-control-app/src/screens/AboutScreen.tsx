import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Linking } from 'react-native';
import LinearGradient from 'react-native-linear-gradient';

const AboutScreen: React.FC = () => {
  const appVersion = '1.0.0';
  const buildNumber = '2024.11.25';

  const features = [
    '🎤 Real-time voice recording and processing',
    '🤖 Speech-to-text with multiple models',
    '🧠 Local language model integration',
    '🔧 MCP protocol support',
    '📱 Android Quick Settings tile',
    '🌐 Local network discovery',
    '⚡ Low-latency audio streaming',
    '🔒 Privacy-focused local processing',
  ];

  const technologies = [
    { name: 'React Native', version: '0.73.0' },
    { name: 'TypeScript', version: '4.8.4' },
    { name: 'FastAPI', version: '0.104+' },
    { name: 'WebSocket', version: 'RFC 6455' },
    { name: 'Android SDK', version: 'API 31+' },
  ];

  const openGitHub = () => {
    Linking.openURL('https://github.com/voice-control-ecosystem');
  };

  const openDocumentation = () => {
    Linking.openURL('https://docs.voice-control.app');
  };

  const openSupport = () => {
    Linking.openURL('mailto:support@voice-control.app');
  };

  return (
    <LinearGradient colors={['#1a1a1a', '#2d2d2d']} style={styles.container}>
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <View style={styles.appIcon}>
            <Text style={styles.iconText}>🎤</Text>
          </View>
          <Text style={styles.appTitle}>Voice Control</Text>
          <Text style={styles.appSubtitle}>Local Voice Control Ecosystem</Text>
          <Text style={styles.version}>
            Version {appVersion} ({buildNumber})
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Features</Text>
          <View style={styles.featuresContainer}>
            {features.map((feature, index) => (
              <Text key={index} style={styles.feature}>
                {feature}
              </Text>
            ))}
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Technology Stack</Text>
          <View style={styles.techContainer}>
            {technologies.map((tech, index) => (
              <View key={index} style={styles.techItem}>
                <Text style={styles.techName}>{tech.name}</Text>
                <Text style={styles.techVersion}>{tech.version}</Text>
              </View>
            ))}
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>About This App</Text>
          <Text style={styles.description}>
            This React Native Android application provides a comprehensive voice control
            solution with local processing capabilities. It integrates seamlessly with the
            FastAPI backend server to deliver real-time speech-to-text, LLM processing,
            and MCP protocol support.
          </Text>
          
          <Text style={styles.description}>
            The app features a minimalist UI with a large push-to-talk button, real-time
            audio visualization, and background recording capabilities through Android's
            Quick Settings tile.
          </Text>

          <Text style={styles.description}>
            All audio processing happens locally on your network, ensuring privacy and
            providing fast response times without relying on cloud services.
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Quick Start</Text>
          <Text style={styles.step}>
            1. Ensure your Android device and PC are on the same WiFi network
          </Text>
          <Text style={styles.step}>
            2. Start the FastAPI server: {'\n'}
            <Text style={styles.code}>
              cd voice-control-server{'\n'}
              uvicorn src.main:app --host 0.0.0.0 --port 8000
            </Text>
          </Text>
          <Text style={styles.step}>
            3. Open this app and configure the server address in Settings
          </Text>
          <Text style={styles.step}>
            4. Tap and hold the microphone button to start voice commands
          </Text>
          <Text style={styles.step}>
            5. Add the Quick Settings tile for background voice control
          </Text>
        </View>

        <View style={styles.links}>
          <TouchableOpacity style={styles.linkButton} onPress={openGitHub}>
            <Text style={styles.linkText}>📂 Source Code</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.linkButton} onPress={openDocumentation}>
            <Text style={styles.linkText}>📖 Documentation</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.linkButton} onPress={openSupport}>
            <Text style={styles.linkText}>🛠️ Support</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.footer}>
          <Text style={styles.footerText}>
            Made with ❤️ for privacy-focused voice control
          </Text>
          <Text style={styles.footerText}>
            © 2024 Voice Control Ecosystem Team
          </Text>
        </View>
      </ScrollView>
    </LinearGradient>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  header: {
    alignItems: 'center',
    paddingTop: 40,
    paddingBottom: 30,
  },
  appIcon: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#007aff',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  iconText: {
    fontSize: 40,
  },
  appTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 8,
  },
  appSubtitle: {
    fontSize: 16,
    color: '#ccc',
    marginBottom: 8,
  },
  version: {
    fontSize: 14,
    color: '#888',
  },
  section: {
    margin: 20,
    marginBottom: 0,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#007aff',
    marginBottom: 16,
  },
  featuresContainer: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 12,
    padding: 16,
    backdropFilter: 'blur(10px)',
  },
  feature: {
    fontSize: 14,
    color: '#fff',
    marginBottom: 8,
    lineHeight: 20,
  },
  techContainer: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 12,
    padding: 16,
    backdropFilter: 'blur(10px)',
  },
  techItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  techName: {
    fontSize: 16,
    color: '#fff',
    fontWeight: '500',
  },
  techVersion: {
    fontSize: 14,
    color: '#888',
  },
  description: {
    fontSize: 14,
    color: '#fff',
    lineHeight: 22,
    marginBottom: 12,
  },
  step: {
    fontSize: 14,
    color: '#fff',
    lineHeight: 22,
    marginBottom: 12,
  },
  code: {
    fontFamily: 'monospace',
    backgroundColor: '#222',
    color: '#00ff00',
    padding: 8,
    borderRadius: 4,
    fontSize: 12,
  },
  links: {
    padding: 20,
    gap: 12,
  },
  linkButton: {
    paddingVertical: 12,
    paddingHorizontal: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#333',
  },
  linkText: {
    color: '#007aff',
    fontSize: 16,
    fontWeight: '500',
  },
  footer: {
    alignItems: 'center',
    paddingBottom: 40,
    paddingHorizontal: 20,
  },
  footerText: {
    color: '#888',
    fontSize: 12,
    textAlign: 'center',
    marginBottom: 4,
  },
});

export default AboutScreen;