import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  SafeAreaView,
  Dimensions,
} from 'react-native';
import { useLocalSearchParams, router } from 'expo-router';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const { width } = Dimensions.get('window');

export default function ComicScreen() {
  const params = useLocalSearchParams();
  const episodeId = params.episodeId as string;

  const [episode, setEpisode] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [generatingPanels, setGeneratingPanels] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (episodeId) {
      loadEpisode();
    }
  }, [episodeId]);

  const loadEpisode = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/episodes/${episodeId}`);

      if (!response.ok) {
        throw new Error('Failed to load episode');
      }

      const data = await response.json();
      setEpisode(data);

      // Auto-generate images for panels without images
      for (const panel of data.panels) {
        if (!panel.image_base64) {
          generatePanelImage(panel.panel_id);
        }
      }
    } catch (error) {
      console.error('Error loading episode:', error);
      Alert.alert('Error', 'Failed to load episode');
    } finally {
      setIsLoading(false);
    }
  };

  const generatePanelImage = async (panelId: string) => {
    setGeneratingPanels(prev => new Set(prev).add(panelId));

    try {
      // Set a timeout for the fetch request (90 seconds to account for cold starts)
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 90000);

      const response = await fetch(`${BACKEND_URL}/api/panels/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          episode_id: episodeId,
          panel_id: panelId,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Server error: ${response.status} - ${errorText}`);
      }

      const data = await response.json();

      // Update episode with new image
      setEpisode((prevEpisode: any) => {
        const updatedPanels = prevEpisode.panels.map((panel: any) => {
          if (panel.panel_id === panelId) {
            return { ...panel, image_base64: data.image_base64 };
          }
          return panel;
        });
        return { ...prevEpisode, panels: updatedPanels };
      });

    } catch (error: any) {
      console.error('Error generating panel:', error);
      let errorMessage = 'Failed to generate manga panel';

      if (error.name === 'AbortError') {
        errorMessage = 'Request timed out. The server might be waking up, please try again.';
      } else if (error.message.includes('Network request failed')) {
        errorMessage = 'Network error. Please check your internet connection.';
      } else if (error.message.includes('500') || error.message.includes('502') || error.message.includes('503')) {
        errorMessage = 'Server is having trouble. Please try again in a moment.';
      }

      Alert.alert('Generation Failed', errorMessage);
    } finally {
      setGeneratingPanels(prev => {
        const newSet = new Set(prev);
        newSet.delete(panelId);
        return newSet;
      });
    }
  };

  const handleGoBack = () => {
    router.back();
  };

  const handleGoToLibrary = () => {
    router.push('/library');
  };

  if (isLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#3498db" />
          <Text style={styles.loadingText}>Loading your manga...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!episode) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>Episode not found</Text>
          <TouchableOpacity style={styles.button} onPress={handleGoBack}>
            <Text style={styles.buttonText}>Go Back</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>{episode.title}</Text>
          <Text style={styles.date}>
            {new Date(episode.created_date).toLocaleDateString()}
          </Text>
        </View>

        {/* Panels */}
        <View style={styles.panelsContainer}>
          {episode.panels.map((panel: any, index: number) => (
            <View key={panel.panel_id} style={styles.panelCard}>
              <Text style={styles.panelNumber}>Panel {index + 1}</Text>

              {/* Image */}
              <View style={styles.imageContainer}>
                {panel.image_base64 ? (
                  <Image
                    source={{ uri: `data:image/png;base64,${panel.image_base64}` }}
                    style={styles.panelImage}
                    resizeMode="contain"
                  />
                ) : generatingPanels.has(panel.panel_id) ? (
                  <View style={styles.generatingContainer}>
                    <ActivityIndicator size="large" color="#3498db" />
                    <Text style={styles.generatingText}>Generating manga art...</Text>
                    <Text style={styles.generatingSubtext}>This may take up to 1 minute</Text>
                  </View>
                ) : (
                  <TouchableOpacity
                    style={styles.generateButton}
                    onPress={() => generatePanelImage(panel.panel_id)}
                  >
                    <Text style={styles.generateButtonText}>Generate Image</Text>
                  </TouchableOpacity>
                )}
              </View>

              {/* Dialogue */}
              {panel.dialogue && (
                <View style={styles.dialogueContainer}>
                  <Text style={styles.dialogue}>{panel.dialogue}</Text>
                </View>
              )}

              {/* Scene Description */}
              <Text style={styles.sceneDescription}>{panel.scene_description}</Text>
            </View>
          ))}
        </View>

        {/* Action Buttons */}
        <View style={styles.actionButtons}>
          <TouchableOpacity
            style={[styles.button, styles.secondaryButton]}
            onPress={handleGoToLibrary}
          >
            <Text style={styles.secondaryButtonText}>View All Episodes</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.button, styles.primaryButton]}
            onPress={handleGoBack}
          >
            <Text style={styles.buttonText}>Create New Story</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollContent: {
    padding: 16,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#34495e',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  errorText: {
    fontSize: 18,
    color: '#e74c3c',
    marginBottom: 24,
  },
  header: {
    alignItems: 'center',
    marginBottom: 24,
    paddingVertical: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 8,
    textAlign: 'center',
  },
  date: {
    fontSize: 14,
    color: '#7f8c8d',
  },
  panelsContainer: {
    marginBottom: 24,
  },
  panelCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  panelNumber: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#3498db',
    marginBottom: 12,
  },
  imageContainer: {
    width: '100%',
    height: 300,
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    marginBottom: 16,
    overflow: 'hidden',
    justifyContent: 'center',
    alignItems: 'center',
  },
  panelImage: {
    width: '100%',
    height: '100%',
  },
  generatingContainer: {
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  generatingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#34495e',
    fontWeight: '600',
  },
  generatingSubtext: {
    marginTop: 8,
    fontSize: 14,
    color: '#7f8c8d',
    textAlign: 'center',
  },
  generateButton: {
    backgroundColor: '#3498db',
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 8,
  },
  generateButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  dialogueContainer: {
    backgroundColor: '#ecf0f1',
    padding: 16,
    borderRadius: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#3498db',
    marginBottom: 12,
  },
  dialogue: {
    fontSize: 16,
    color: '#2c3e50',
    fontStyle: 'italic',
  },
  sceneDescription: {
    fontSize: 14,
    color: '#7f8c8d',
    lineHeight: 20,
  },
  actionButtons: {
    marginTop: 16,
    marginBottom: 32,
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
});
