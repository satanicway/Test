import React, {useState} from 'react';
import {View, Text, Button, StyleSheet} from 'react-native';
import journeys from '../../assets/journeys.json';

export default function JourneyScreen({navigation}) {
  const [journey, setJourney] = useState(null);
  const getRandom = () => {
    const random = journeys[Math.floor(Math.random() * journeys.length)];
    setJourney(random);
  };

  return (
    <View style={styles.container}>
      <Button title="Draw Journey" onPress={getRandom} />
      {journey && <Text style={styles.text}>{journey}</Text>}
      <Button title="Back" onPress={() => navigation.goBack()} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20},
  text: {marginVertical: 20, textAlign: 'center'},
});
