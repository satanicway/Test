import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:math';
import 'theme.dart';

const List<Map<String, String>> monsters = [
  {'name': 'Goblin', 'type': 'Humanoid'},
  {'name': 'Ogre', 'type': 'Giant'},
  {'name': 'Specter', 'type': 'Undead'},
];

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter Demo',
      theme: AppTheme.lightTheme,
      home: const MyHomePage(title: 'Flutter Home Page'),
    );
  }
}

class MyHomePage extends StatelessWidget {
  final String title;

  const MyHomePage({super.key, required this.title});

  void _fadePush(BuildContext context, Widget page) {
    Navigator.of(context).push(
      PageRouteBuilder(
        pageBuilder: (_, a1, a2) => page,
        transitionsBuilder: (_, a1, __, child) => FadeTransition(
          opacity: a1,
          child: child,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(title),
      ),
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ElevatedButton(
              onPressed: () => _fadePush(
                context,
                const ContractsScreen(),
              ),
              child: const Text('Contracts'),
            ),
            ElevatedButton(
              onPressed: () => _fadePush(
                context,
                const JourneyScreen(),
              ),
              child: const Text('Journey'),
            ),
            ElevatedButton(
              onPressed: () => _fadePush(
                context,
                const MysteryScreen(),
              ),
              child: const Text('Mystery'),
            ),
            ElevatedButton(
              onPressed: () => _fadePush(
                context,
                const MonsterScreen(),
              ),
              child: const Text('Monster'),
            ),
            ElevatedButton(
              onPressed: () => _fadePush(
                context,
                const SearchScreen(),
              ),
              child: const Text('Search'),
            ),
            ElevatedButton(
              onPressed: () => SystemNavigator.pop(),
              child: const Text('Close'),
            ),
          ],
        ),
      ),
    );
  }
}

class ContractsScreen extends StatelessWidget {
  const ContractsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Contracts')),
      body: const Center(child: Text('Contracts Screen')),
    );
  }
}

class JourneyScreen extends StatelessWidget {
  const JourneyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Journey')),
      body: const Center(child: Text('Journey Screen')),
    );
  }
}

class MysteryScreen extends StatelessWidget {
  const MysteryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mystery')),
      body: const Center(child: Text('Mystery Screen')),
    );
  }
}

class MonsterScreen extends StatefulWidget {
  const MonsterScreen({super.key});

  @override
  State<MonsterScreen> createState() => _MonsterScreenState();
}

class _MonsterScreenState extends State<MonsterScreen> {
  Map<String, String>? monster;

  void getRandom() {
    setState(() {
      monster = monsters[Random().nextInt(monsters.length)];
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Monster')),
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ElevatedButton(
              key: const Key('randomMonsterBtn'),
              onPressed: getRandom,
              child: const Text('Random Monster'),
            ),
            if (monster != null) ...[
              Text(monster!['name']!, key: const Key('monsterName')),
              Text(monster!['type']!),
            ],
          ],
        ),
      ),
    );
  }
}

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final TextEditingController controller = TextEditingController();
  List<Map<String, String>> results = monsters;

  void search(String query) {
    setState(() {
      results = monsters
          .where((m) => m['name']!
              .toLowerCase()
              .contains(query.toLowerCase()))
          .toList();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Search')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: TextField(
              key: const Key('searchField'),
              controller: controller,
              onChanged: search,
            ),
          ),
          Expanded(
            child: ListView(
              children: results
                  .map((m) => ListTile(title: Text(m['name']!)))
                  .toList(),
            ),
          ),
        ],
      ),
    );
  }
}
