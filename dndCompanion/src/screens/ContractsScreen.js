import React, {useState} from 'react';
import {View, Text, Button, StyleSheet} from 'react-native';
import contracts from '../../assets/contracts.json';

export default function ContractsScreen({navigation}) {
  const [contract, setContract] = useState(null);
  const getRandom = () => {
    const random = contracts[Math.floor(Math.random() * contracts.length)];
    setContract(random);
  };

  return (
    <View style={styles.container}>
      <Button title="Draw Contract" onPress={getRandom} />
      {contract && <Text style={styles.text}>{contract}</Text>}
      <Button title="Back" onPress={() => navigation.goBack()} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20},
  text: {marginVertical: 20, textAlign: 'center'},
});
