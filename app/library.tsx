import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  SafeAreaView,
  Image,
} from 'react-native';
import { router } from 'expo-router';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function LibraryScreen() {
  const [episodes, setEpisodes] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadEpisodes();
  }, []);

  const loadEpisodes = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/episodes`);
      
      if (!response.ok) {
        throw new Error('Failed to load episodes');
      }

      const data = await response.json();
      setEpisodes(data);
    } catch (error) {
      console.error('Error loading episodes:', error);
      Alert.alert('Error', 'Failed to load your episodes');
    } finally {
      setIsLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadEpisodes();
  };

  const handleEpisodePress = (episodeId: string) => {
    router.push({
      pathname: '/comic',
      params: { episodeId },
    });
  };

  const handleDeleteEpisode = async (episodeId: string) => {
    Alert.alert(
      'Delete Episode',
      'Are you sure you want to delete this episode?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              const response = await fetch(
                `${BACKEND_URL}/api/episodes/${episodeId}`,
                { method: 'DELETE' }
              );

              if (!response.ok) {
                throw new Error('Failed to delete episode');
              }

              // Refresh the list
              loadEpisodes();
            } catch (error) {
              console.error('Error deleting episode:', error);
              Alert.alert('Error', 'Failed to delete episode');
            }
          },
        },
      ]
    );
  };

  const handleGoBack = () => {
    router.back();
  };

  const renderEpisodeCard = ({ item }: { item: any }) => {
    const firstPanelWithImage = item.panels.find((p: any) => p.image_base64);
    const panelCount = item.panels.length;
    const createdDate = new Date(item.created_date).toLocaleDateString();

    return (
      <TouchableOpacity
        style={styles.episodeCard}
        onPress={() => handleEpisodePress(item.episode_id)}
      >
        <View style={styles.cardContent}>
          {/* Thumbnail */}
          <View style={styles.thumbnailContainer}>
            {firstPanelWithImage ? (
              <Image
                source={{
                  uri: `data:image/png;base64,${firstPanelWithImage.image_base64}`,
                }}
                style={styles.thumbnail}
                resizeMode="cover"
              />
            ) : (
              <View style={styles.placeholderThumbnail}>
                <Text style={styles.placeholderText}>📖</Text>
              </View>
            )}
          </View>

          {/* Episode Info */}
          <View style={styles.episodeInfo}>
            <Text style={styles.episodeTitle} numberOfLines={2}>
              {item.title}
            </Text>
            <Text style={styles.episodeDate}>{createdDate}</Text>
            <Text style={styles.episodeStats}>{panelCount} panels</Text>
          </View>
        </View>

        {/* Delete Button */}
        <TouchableOpacity
          style={styles.deleteButton}
          onPress={() => handleDeleteEpisode(item.episode_id)}
        >
          <Text style={styles.deleteButtonText}>×</Text>
        </TouchableOpacity>
      </TouchableOpacity>
    );
  };

  if (isLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#3498db" />
          <Text style={styles.loadingText}>Loading your episodes...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>My Episodes</Text>
        <Text style={styles.subtitle}>Your manga collection</Text>
      </View>

      {episodes.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>No episodes yet</Text>
          <Text style={styles.emptySubtext}>
            Create your first manga story!
          </Text>
          <TouchableOpacity
            style={styles.createButton}
            onPress={handleGoBack}
          >
            <Text style={styles.createButtonText}>Create Story</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={episodes}
          renderItem={renderEpisodeCard}
          keyExtractor={(item) => item.episode_id}
          contentContainerStyle={styles.listContent}
          refreshing={refreshing}
          onRefresh={handleRefresh}
        />
      )}

      <TouchableOpacity
        style={styles.backButton}
        onPress={handleGoBack}
      >
        <Text style={styles.backButtonText}>← Back to Home</Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    padding: 24,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
    color: '#7f8c8d',
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
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  emptyText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#34495e',
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 16,
    color: '#7f8c8d',
    marginBottom: 24,
  },
  createButton: {
    backgroundColor: '#3498db',
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 12,
  },
  createButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  listContent: {
    padding: 16,
  },
  episodeCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    overflow: 'hidden',
  },
  cardContent: {
    flexDirection: 'row',
    padding: 16,
  },
  thumbnailContainer: {
    width: 100,
    height: 100,
    borderRadius: 8,
    overflow: 'hidden',
    marginRight: 16,
  },
  thumbnail: {
    width: '100%',
    height: '100%',
  },
  placeholderThumbnail: {
    width: '100%',
    height: '100%',
    backgroundColor: '#ecf0f1',
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholderText: {
    fontSize: 40,
  },
  episodeInfo: {
    flex: 1,
    justifyContent: 'center',
  },
  episodeTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 8,
  },
  episodeDate: {
    fontSize: 14,
    color: '#7f8c8d',
    marginBottom: 4,
  },
  episodeStats: {
    fontSize: 14,
    color: '#3498db',
    fontWeight: '600',
  },
  deleteButton: {
    position: 'absolute',
    top: 8,
    right: 8,
    backgroundColor: '#e74c3c',
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  deleteButtonText: {
    color: '#fff',
    fontSize: 24,
    fontWeight: 'bold',
    lineHeight: 24,
  },
  backButton: {
    backgroundColor: '#fff',
    padding: 16,
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  backButtonText: {
    color: '#3498db',
    fontSize: 16,
    fontWeight: '600',
  },
});
