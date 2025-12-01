import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Alert,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { router } from 'expo-router';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://192.168.1.4:8002';
console.log('Using backend URL:', BACKEND_URL);

export default function HomeScreen() {
  const [storyText, setStoryText] = useState('');
  const [characterName, setCharacterName] = useState('');
  const [characterAppearance, setCharacterAppearance] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmitStory = async () => {
    if (!storyText.trim()) {
      Alert.alert('Error', 'Please write your daily story!');
      return;
    }

    setIsLoading(true);

    try {
      // 1. Check if backend is alive first
      try {
        const healthController = new AbortController();
        const healthTimeout = setTimeout(() => healthController.abort(), 5000);

        await fetch(`${BACKEND_URL}/api/health`, {
          signal: healthController.signal
        });
        clearTimeout(healthTimeout);
      } catch (e) {
        console.warn('Backend health check failed, but trying submit anyway in case it wakes up');
        // We don't block here, just warn in logs, because the main request might wake it up
      }

      console.log('Sending request to:', `${BACKEND_URL}/api/story/submit`);
      console.log('Request payload:', {
        story_text: storyText,
        character_name: characterName || null,
        character_appearance: characterAppearance || null,
      });

      // Increase timeout for cold starts
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000); // 60s timeout

      const response = await fetch(`${BACKEND_URL}/api/story/submit`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          story_text: storyText,
          character_name: characterName || null,
          character_appearance: characterAppearance || null,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Server response error:', errorText);
        throw new Error(`Server error: ${response.status} - ${errorText}`);
      }

      const data = await response.json();

      // Navigate to comic viewer with episode data
      router.push({
        pathname: '/comic',
        params: { episodeId: data.episode_id },
      });

    } catch (error: any) {
      console.error('Error submitting story:', error);

      let errorMessage = 'Failed to create your manga. Please try again.';
      if (error.name === 'AbortError') {
        errorMessage = 'Server is taking too long to wake up. Please try again in 30 seconds.';
      } else if (error.message.includes('Network request failed')) {
        errorMessage = 'Cannot connect to server. If you are using the cloud server, it might be down.';
      }

      Alert.alert('Connection Error', errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleViewLibrary = () => {
    router.push('/library');
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.title}>DailyToon</Text>
            <Text style={styles.subtitle}>Turn your day into manga!</Text>
          </View>

          {/* Story Input */}
          <View style={styles.inputSection}>
            <Text style={styles.label}>Tell me about your day:</Text>
            <TextInput
              style={styles.storyInput}
              multiline
              numberOfLines={8}
              placeholder="Today I woke up feeling excited because..."
              placeholderTextColor="#999"
              value={storyText}
              onChangeText={setStoryText}
              editable={!isLoading}
            />
          </View>

          {/* Character Details (Optional) */}
          <View style={styles.characterSection}>
            <Text style={styles.sectionTitle}>Character Details (Optional)</Text>

            <Text style={styles.label}>Character Name:</Text>
            <TextInput
              style={styles.input}
              placeholder="e.g., Alex, Sam, Riley"
              placeholderTextColor="#999"
              value={characterName}
              onChangeText={setCharacterName}
              editable={!isLoading}
            />

            <Text style={styles.label}>Character Appearance:</Text>
            <TextInput
              style={styles.input}
              placeholder="e.g., tall with curly brown hair, glasses, casual style"
              placeholderTextColor="#999"
              value={characterAppearance}
              onChangeText={setCharacterAppearance}
              editable={!isLoading}
            />
          </View>

          {/* Action Buttons */}
          <TouchableOpacity
            style={[styles.button, styles.primaryButton, isLoading && styles.buttonDisabled]}
            onPress={handleSubmitStory}
            disabled={isLoading}
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Create My Manga!</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.button, styles.secondaryButton]}
            onPress={handleViewLibrary}
            disabled={isLoading}
          >
            <Text style={styles.secondaryButtonText}>View My Episodes</Text>
          </TouchableOpacity>

          {isLoading && (
            <View style={styles.loadingContainer}>
              <Text style={styles.loadingText}>Creating your manga story...</Text>
              <Text style={styles.loadingSubtext}>This may take a moment</Text>
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  keyboardView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
  },
  header: {
    alignItems: 'center',
    marginBottom: 32,
    marginTop: 16,
  },
  title: {
    fontSize: 40,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 18,
    color: '#7f8c8d',
  },
  inputSection: {
    marginBottom: 24,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    color: '#34495e',
    marginBottom: 8,
  },
  storyInput: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    color: '#2c3e50',
    minHeight: 180,
    textAlignVertical: 'top',
    borderWidth: 2,
    borderColor: '#e0e0e0',
  },
  characterSection: {
    marginBottom: 24,
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#34495e',
    marginBottom: 16,
  },
  input: {
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    color: '#2c3e50',
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  button: {
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginBottom: 12,
  },
  primaryButton: {
    backgroundColor: '#3498db',
  },
  secondaryButton: {
    backgroundColor: '#fff',
    borderWidth: 2,
    borderColor: '#3498db',
  },
  buttonDisabled: {
    backgroundColor: '#95a5a6',
  },
  buttonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  secondaryButtonText: {
    color: '#3498db',
    fontSize: 18,
    fontWeight: 'bold',
  },
  loadingContainer: {
    alignItems: 'center',
    marginTop: 24,
  },
  loadingText: {
    fontSize: 16,
    color: '#34495e',
    marginTop: 12,
  },
  loadingSubtext: {
    fontSize: 14,
    color: '#7f8c8d',
    marginTop: 4,
  },
});
