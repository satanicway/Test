import React from 'react';
import {View, Button, StyleSheet} from 'react-native';

export default function HomeScreen({navigation}) {
  return (
    <View style={styles.container}>
      <Button title="Contracts" onPress={() => navigation.navigate('Contracts')} />
      <Button title="Journey" onPress={() => navigation.navigate('Journey')} />
      <Button title="Mystery" onPress={() => navigation.navigate('Mystery')} />
      <Button title="Monster" onPress={() => navigation.navigate('Monster')} />
      <Button title="Search" onPress={() => navigation.navigate('Search')} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'space-evenly',
    padding: 20,
  },
});
