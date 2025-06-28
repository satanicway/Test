import React, {useState} from 'react';
import {View, Text, Button, StyleSheet} from 'react-native';
import monsters from '../../assets/monsters.json';

export default function MonsterScreen({navigation}) {
  const [monster, setMonster] = useState(null);
  const getRandom = () => {
    const random = monsters[Math.floor(Math.random() * monsters.length)];
    setMonster(random);
  };

  return (
    <View style={styles.container}>
      <Button title="Random Monster" onPress={getRandom} />
      {monster && (
        <View style={styles.monster}>
          <Text style={styles.name}>{monster.name}</Text>
          <Text>{monster.type}</Text>
        </View>
      )}
      <Button title="Back" onPress={() => navigation.goBack()} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20},
  monster: {marginVertical: 20, alignItems: 'center'},
  name: {fontWeight: 'bold'},
});
