import React, {useState} from 'react';
import {View, Text, Button, StyleSheet} from 'react-native';
import mysteries from '../../assets/mysteries.json';

export default function MysteryScreen({navigation}) {
  const [mystery, setMystery] = useState(null);
  const getRandom = () => {
    const random = mysteries[Math.floor(Math.random() * mysteries.length)];
    setMystery(random);
  };

  return (
    <View style={styles.container}>
      <Button title="Draw Mystery" onPress={getRandom} />
      {mystery && <Text style={styles.text}>{mystery}</Text>}
      <Button title="Back" onPress={() => navigation.goBack()} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20},
  text: {marginVertical: 20, textAlign: 'center'},
});
