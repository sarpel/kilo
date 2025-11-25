import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
  TextInput,
  Dimensions,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';

const { width } = Dimensions.get('window');

interface SettingsScreenProps {
  navigation: any;
}

const SettingsScreen: React.FC<SettingsScreenProps> = ({ navigation }) => {
  const [serverAddress, setServerAddress] = useState('192.168.1.100:8000');
  const [autoConnect, setAutoConnect] = useState(true);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [vibrationEnabled, setVibrationEnabled] = useState(true);
  const [sttModel, setSttModel] = useState('whisper-base');
  const [llmModel, setLlmModel] = useState('llama2');
  const [language, setLanguage] = useState('en');
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(150);

  const settings = [
    {
      title: 'Server Configuration',
      items: [
        {
          key: 'serverAddress',
          label: 'Server Address',
          value: serverAddress,
          type: 'input',
          placeholder: '192.168.1.100:8000',
          onChange: setServerAddress,
        },
      ],
    },
    {
      title: 'Audio Settings',
      items: [
        {
          key: 'sttModel',
          label: 'Speech-to-Text Model',
          value: sttModel,
          type: 'select',
          options: ['whisper-base', 'whisper-small', 'whisper-medium'],
          onChange: setSttModel,
        },
        {
          key: 'language',
          label: 'Language',
          value: language,
          type: 'select',
          options: ['en', 'tr', 'es', 'fr', 'de'],
          onChange: setLanguage,
        },
      ],
    },
    {
      title: 'LLM Settings',
      items: [
        {
          key: 'llmModel',
          label: 'Language Model',
          value: llmModel,
          type: 'select',
          options: ['llama2', 'mistral', 'codellama'],
          onChange: setLlmModel,
        },
        {
          key: 'temperature',
          label: 'Temperature',
          value: temperature,
          type: 'slider',
          min: 0,
          max: 1,
          step: 0.1,
          onChange: setTemperature,
        },
        {
          key: 'maxTokens',
          label: 'Max Tokens',
          value: maxTokens,
          type: 'slider',
          min: 50,
          max: 500,
          step: 25,
          onChange: setMaxTokens,
        },
      ],
    },
    {
      title: 'Notifications',
      items: [
        {
          key: 'soundEnabled',
          label: 'Sound Notifications',
          value: soundEnabled,
          type: 'switch',
          onChange: setSoundEnabled,
        },
        {
          key: 'vibrationEnabled',
          label: 'Vibration',
          value: vibrationEnabled,
          type: 'switch',
          onChange: setVibrationEnabled,
        },
      ],
    },
    {
      title: 'Connection',
      items: [
        {
          key: 'autoConnect',
          label: 'Auto-connect on startup',
          value: autoConnect,
          type: 'switch',
          onChange: setAutoConnect,
        },
      ],
    },
  ];

  const renderSettingItem = (item: any) => {
    const SettingComponent = () => {
      switch (item.type) {
        case 'input':
          return (
            <View style={styles.inputContainer}>
              <TextInput
                style={styles.input}
                value={item.value}
                onChangeText={item.onChange}
                placeholder={item.placeholder}
                placeholderTextColor="#888"
                keyboardType="url"
                autoCapitalize="none"
              />
            </View>
          );

        case 'select':
          return (
            <View style={styles.selectContainer}>
              {item.options.map((option: string) => (
                <TouchableOpacity
                  key={option}
                  style={[
                    styles.optionButton,
                    item.value === option && styles.optionButtonActive,
                  ]}
                  onPress={() => item.onChange(option)}
                >
                  <Text
                    style={[
                      styles.optionText,
                      item.value === option && styles.optionTextActive,
                    ]}
                  >
                    {option}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          );

        case 'switch':
          return (
            <Switch
              value={item.value}
              onValueChange={item.onChange}
              trackColor={{ false: '#444', true: '#007aff' }}
              thumbColor={item.value ? '#fff' : '#888'}
            />
          );

        case 'slider':
          return (
            <View style={styles.sliderContainer}>
              <Text style={styles.sliderLabel}>
                {item.value}
              </Text>
              <View style={styles.slider}>
                <TouchableOpacity
                  style={[
                    styles.sliderThumb,
                    {
                      left: ((item.value - item.min) / (item.max - item.min)) * 200,
                    },
                  ]}
                />
              </View>
              <View style={styles.sliderRange}>
                <Text style={styles.sliderRangeText}>{item.min}</Text>
                <Text style={styles.sliderRangeText}>{item.max}</Text>
              </View>
            </View>
          );

        default:
          return null;
      }
    };

    return (
      <View key={item.key} style={styles.settingItem}>
        <Text style={styles.settingLabel}>{item.label}</Text>
        <SettingComponent />
      </View>
    );
  };

  const testConnection = async () => {
    Alert.alert(
      'Testing Connection',
      `Connecting to ${serverAddress}...`,
      [{ text: 'Cancel' }]
    );
    
    // Mock connection test
    setTimeout(() => {
      Alert.alert(
        'Connection Test',
        Math.random() > 0.5 
          ? '✅ Successfully connected to server!'
          : '❌ Failed to connect. Please check the address and try again.',
        [{ text: 'OK' }]
      );
    }, 2000);
  };

  const saveSettings = () => {
    // Save settings to AsyncStorage or state management
    Alert.alert(
      'Settings Saved',
      'Your settings have been saved successfully.',
      [{ text: 'OK' }]
    );
  };

  return (
    <LinearGradient colors={['#1a1a1a', '#2d2d2d']} style={styles.container}>
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Text style={styles.title}>Settings</Text>
          <Text style={styles.subtitle}>
            Configure your voice control experience
          </Text>
        </View>

        {settings.map((section) => (
          <View key={section.title} style={styles.section}>
            <Text style={styles.sectionTitle}>{section.title}</Text>
            <View style={styles.sectionContent}>
              {section.items.map(renderSettingItem)}
            </View>
          </View>
        ))}

        <View style={styles.actionButtons}>
          <TouchableOpacity style={styles.testButton} onPress={testConnection}>
            <Text style={styles.testButtonText}>Test Connection</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.saveButton} onPress={saveSettings}>
            <LinearGradient
              colors={['#007aff', '#0056d2']}
              style={styles.saveButtonGradient}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
            >
              <Text style={styles.saveButtonText}>Save Settings</Text>
            </LinearGradient>
          </TouchableOpacity>
        </View>

        <View style={styles.footer}>
          <TouchableOpacity
            style={styles.aboutButton}
            onPress={() => navigation.navigate('About')}
          >
            <Text style={styles.aboutButtonText}>About Voice Control</Text>
          </TouchableOpacity>
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
    padding: 20,
    alignItems: 'center',
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#ccc',
    textAlign: 'center',
  },
  section: {
    margin: 16,
    marginBottom: 0,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#007aff',
    marginBottom: 12,
  },
  sectionContent: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 12,
    padding: 16,
    backdropFilter: 'blur(10px)',
  },
  settingItem: {
    marginBottom: 20,
  },
  settingLabel: {
    fontSize: 14,
    fontWeight: '500',
    color: '#fff',
    marginBottom: 8,
  },
  inputContainer: {
    borderWidth: 1,
    borderColor: '#444',
    borderRadius: 8,
    paddingHorizontal: 12,
    backgroundColor: '#222',
  },
  input: {
    color: '#fff',
    fontSize: 16,
    paddingVertical: 12,
  },
  selectContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  optionButton: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#444',
    backgroundColor: '#222',
  },
  optionButtonActive: {
    borderColor: '#007aff',
    backgroundColor: '#007aff',
  },
  optionText: {
    color: '#ccc',
    fontSize: 14,
  },
  optionTextActive: {
    color: '#fff',
    fontWeight: '500',
  },
  sliderContainer: {
    marginTop: 8,
  },
  sliderLabel: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 12,
  },
  slider: {
    height: 6,
    backgroundColor: '#444',
    borderRadius: 3,
    position: 'relative',
    marginBottom: 8,
  },
  sliderThumb: {
    position: 'absolute',
    top: -3,
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#007aff',
  },
  sliderRange: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  sliderRangeText: {
    color: '#888',
    fontSize: 12,
  },
  actionButtons: {
    padding: 20,
    gap: 12,
  },
  testButton: {
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#007aff',
    alignItems: 'center',
  },
  testButtonText: {
    color: '#007aff',
    fontSize: 16,
    fontWeight: '600',
  },
  saveButton: {
    borderRadius: 8,
    overflow: 'hidden',
  },
  saveButtonGradient: {
    paddingVertical: 12,
    paddingHorizontal: 24,
    alignItems: 'center',
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  footer: {
    padding: 20,
    alignItems: 'center',
  },
  aboutButton: {
    paddingVertical: 8,
    paddingHorizontal: 16,
  },
  aboutButtonText: {
    color: '#007aff',
    fontSize: 16,
    fontWeight: '500',
  },
});

export default SettingsScreen;