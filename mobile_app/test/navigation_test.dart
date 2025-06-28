import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/main.dart';

void main() {
  testWidgets('navigate to each screen', (WidgetTester tester) async {
    await tester.pumpWidget(const MyApp());

    Future<void> openAndVerify(String button, String text) async {
      await tester.tap(find.text(button));
      await tester.pumpAndSettle();
      expect(find.text(text), findsOneWidget);
      await tester.pageBack();
      await tester.pumpAndSettle();
    }

    await openAndVerify('Contracts', 'Contracts Screen');
    await openAndVerify('Journey', 'Journey Screen');
    await openAndVerify('Mystery', 'Mystery Screen');
    await openAndVerify('Monster', 'Random Monster');
    await openAndVerify('Search', 'Search');
  });
}
