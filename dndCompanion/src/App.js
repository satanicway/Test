import React from 'react';
import {NavigationContainer} from '@react-navigation/native';
import {createStackNavigator} from '@react-navigation/stack';
import HomeScreen from './screens/HomeScreen';
import ContractsScreen from './screens/ContractsScreen';
import JourneyScreen from './screens/JourneyScreen';
import MysteryScreen from './screens/MysteryScreen';
import MonsterScreen from './screens/MonsterScreen';
import MonsterDetailScreen from './screens/MonsterDetailScreen';
import SearchScreen from './screens/SearchScreen';

const Stack = createStackNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Home">
        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen name="Contracts" component={ContractsScreen} />
        <Stack.Screen name="Journey" component={JourneyScreen} />
        <Stack.Screen name="Mystery" component={MysteryScreen} />
        <Stack.Screen name="Monster" component={MonsterScreen} />
        <Stack.Screen name="Search" component={SearchScreen} />
        <Stack.Screen
          name="MonsterDetail"
          component={MonsterDetailScreen}
          options={{headerShown: false}}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
