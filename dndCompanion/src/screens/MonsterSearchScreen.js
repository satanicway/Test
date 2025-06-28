import React, {useState} from 'react';
import {
  View,
  TextInput,
  FlatList,
  Text,
  StyleSheet,
  Button,
  TouchableOpacity,
} from 'react-native';
import monsters from '../../assets/data/monsters.json';

export default function MonsterSearchScreen({navigation}) {
  const [query, setQuery] = useState('');

  const filtered =
    query.length >= 3
      ? monsters.filter(m =>
          m.name.toLowerCase().includes(query.toLowerCase()),
        )
      : [];

  return (
    <View style={styles.container}>
      <TextInput
        placeholder="Search monsters"
        style={styles.input}
        value={query}
        onChangeText={setQuery}
      />
      <FlatList
        data={filtered}
        keyExtractor={item => item.name}
        renderItem={({item}) => (
          <TouchableOpacity
            style={styles.item}
            onPress={() => navigation.navigate('MonsterDetail', {monster: item})}
          >
            <Text>{item.name}</Text>
          </TouchableOpacity>
        )}
      />
      <Button title="Back" onPress={() => navigation.navigate('Home')} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, padding: 20},
  input: {borderWidth: 1, padding: 10, marginBottom: 10},
  item: {paddingVertical: 5},
});
