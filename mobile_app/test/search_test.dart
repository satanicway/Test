import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/main.dart';
import 'package:flutter/material.dart';

void main() {
  testWidgets('search filters monsters', (WidgetTester tester) async {
    await tester.pumpWidget(const MyApp());

    await tester.tap(find.text('Search'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const Key('searchField')), 'Goblin');
    await tester.pump();

    expect(find.text('Goblin'), findsOneWidget);
    expect(find.text('Ogre'), findsNothing);
  });
}
