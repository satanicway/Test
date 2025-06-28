import React, {useState, useEffect} from 'react';
import {View, Text, Button, StyleSheet, Image} from 'react-native';
import cards from '../../assets/data/mystery_cards.json';

export default function MysteryScreen({navigation}) {
  const [card, setCard] = useState(null);
  const [recentIds, setRecentIds] = useState([]);

  const drawCard = () => {
    const available = cards.filter(c => !recentIds.includes(c.id));
    const next =
      available.length > 0
        ? available[Math.floor(Math.random() * available.length)]
        : cards[Math.floor(Math.random() * cards.length)];

    setCard(next);
    setRecentIds(prev => {
      const updated = [next.id, ...prev];
      if (updated.length > 10) {
        updated.pop();
      }
      return updated;
    });
  };

  useEffect(() => {
    drawCard();
  }, []);

  return (
    <View style={styles.container}>
      {card && (
        <>
          <Image source={{uri: card.image}} style={styles.image} />
          <Text style={styles.text}>{card.text}</Text>
        </>
      )}
      <Button title="Next" onPress={drawCard} />
      <Button title="Back to Home" onPress={() => navigation.popToTop()} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20},
  image: {width: 200, height: 120, marginBottom: 10},
  text: {marginVertical: 20, textAlign: 'center'},
});
