import React, {useState} from 'react';
import {View, TextInput, FlatList, Text, StyleSheet, Button} from 'react-native';
import monsters from '../../assets/monsters.json';

export default function SearchScreen({navigation}) {
  const [query, setQuery] = useState('');

  const filtered = monsters.filter(m =>
    m.name.toLowerCase().includes(query.toLowerCase()),
  );

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
          <Text style={styles.item}>{item.name}</Text>
        )}
      />
      <Button title="Back" onPress={() => navigation.goBack()} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, padding: 20},
  input: {borderWidth: 1, padding: 10, marginBottom: 10},
  item: {paddingVertical: 5},
});
