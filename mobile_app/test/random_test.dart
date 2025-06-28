import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/main.dart';
import 'package:flutter/material.dart';

void main() {
  testWidgets('random monster button shows monster', (WidgetTester tester) async {
    await tester.pumpWidget(const MyApp());

    await tester.tap(find.text('Monster'));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('monsterName')), findsNothing);
    await tester.tap(find.byKey(const Key('randomMonsterBtn')));
    await tester.pump();
    expect(find.byKey(const Key('monsterName')), findsOneWidget);
  });
}
