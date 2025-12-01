import { Stack } from 'expo-router';

export default function RootLayout() {
  return (
    <Stack
      screenOptions={{
        headerStyle: {
          backgroundColor: '#3498db',
        },
        headerTintColor: '#fff',
        headerTitleStyle: {
          fontWeight: 'bold',
        },
      }}
    >
      <Stack.Screen
        name="index"
        options={{
          title: 'DailyToon',
          headerShown: false,
        }}
      />
      <Stack.Screen
        name="comic"
        options={{
          title: 'Your Manga',
          headerBackTitle: 'Back',
        }}
      />
      <Stack.Screen
        name="library"
        options={{
          title: 'My Episodes',
          headerBackTitle: 'Back',
        }}
      />
    </Stack>
  );
}
