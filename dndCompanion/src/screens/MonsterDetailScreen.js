import React from 'react';
import {
  View,
  Text,
  Image,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';

export default function MonsterDetailScreen({route, navigation}) {
  const {monster} = route.params;

  return (
    <View style={styles.container}>
      <TouchableOpacity
        style={styles.backButton}
        onPress={() => navigation.navigate('Home')}>
        <Text style={styles.backText}>Back</Text>
      </TouchableOpacity>
      <TouchableOpacity onPress={() => navigation.goBack()} style={styles.imageWrapper}>
        <Image
          source={{uri: monster.image}}
          style={styles.image}
          resizeMode="contain"
        />
      </TouchableOpacity>
      <Text style={styles.description}>{monster.description}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: '#000', justifyContent: 'center'},
  backButton: {position: 'absolute', top: 40, left: 20, zIndex: 1},
  backText: {color: '#fff'},
  imageWrapper: {flex: 1, justifyContent: 'center'},
  image: {width: '100%', height: '100%'},
  description: {color: '#fff', textAlign: 'center', padding: 20},
});
