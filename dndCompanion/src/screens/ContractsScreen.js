import React, {useState} from 'react';
import {
  View,
  Text,
  Button,
  StyleSheet,
  Image,
  TouchableOpacity,
  ScrollView,
} from 'react-native';
import monsters from '../../assets/data/monsters.json';

export default function ContractsScreen({navigation}) {
  const [selected, setSelected] = useState([]);

  const getRandomMonsters = () => {
    const shuffled = [...monsters].sort(() => 0.5 - Math.random());
    setSelected(shuffled.slice(0, 4));
  };

  const openDetails = monster => {
    navigation.navigate('MonsterDetail', {monster});
  };

  return (
    <View style={styles.container}>
      <Button title="Draw Monsters" onPress={getRandomMonsters} />
      <ScrollView contentContainerStyle={styles.list}>
        {selected.map(monster => (
          <TouchableOpacity
            key={monster.name}
            style={styles.item}
            onPress={() => openDetails(monster)}>
            <Image source={{uri: monster.image}} style={styles.thumb} />
            <Text style={styles.name}>{monster.name}</Text>
            <Text style={styles.short}>
              {monster.description.slice(0, 30)}...
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
      <Button title="Back" onPress={() => navigation.goBack()} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, padding: 20},
  list: {alignItems: 'center', paddingVertical: 20},
  item: {marginVertical: 10, alignItems: 'center'},
  thumb: {width: 80, height: 80, marginBottom: 5},
  name: {fontWeight: 'bold'},
  short: {textAlign: 'center'},
});
