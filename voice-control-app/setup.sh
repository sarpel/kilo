#!/bin/bash

# Voice Control App - Build and Installation Script
# This script sets up the React Native Android application

set -e

echo "🎤 Voice Control App - Android Setup"
echo "=================================="

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found. Please run this script from the voice-control-app directory."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed. Please install Node.js 16+ first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is required but not installed. Please install npm first."
    exit 1
fi

echo "✅ Node.js $(node --version) detected"
echo "✅ npm $(npm --version) detected"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed successfully"

# Check if Android SDK is available
if command -v adb &> /dev/null; then
    echo "✅ Android SDK detected"
else
    echo "⚠️  Android SDK not found. Please install Android Studio and Android SDK."
fi

# Create necessary directories
echo "📁 Creating directory structure..."
mkdir -p android/app/src/main/java/com/voicecontrolapp
mkdir -p android/app/src/main/res/values
mkdir -p android/app/src/main/res/xml
mkdir -p src/native

echo "✅ Directory structure created"

# Copy additional native modules if needed
echo "📄 Setting up native modules..."

# Set up react-native permissions
echo "🔐 Setting up Android permissions..."

# Clean build
echo "🧹 Cleaning previous build..."
cd android
./gradlew clean
cd ..

echo "✅ Setup completed successfully!"
echo ""
echo "📱 Next steps:"
echo "1. Connect your Android device or start an emulator"
echo "2. Run: npm run android"
echo ""
echo "🔧 To debug:"
echo "- Use: npx react-native log-android"
echo "- Use: npx react-native run-android --verbose"
echo ""
echo "🚀 Ready to build!"