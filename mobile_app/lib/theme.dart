import 'package:flutter/material.dart';

class AppTheme {
  /// Light theme used throughout the application. Colors and text styles are
  /// derived from a single seed color to keep the look consistent.
  static ThemeData get lightTheme {
    final base = ThemeData.light(useMaterial3: true);
    return base.copyWith(
      colorScheme: ColorScheme.fromSeed(
        seedColor: Colors.deepPurple,
        primary: Colors.deepPurple,
        secondary: Colors.amber,
        brightness: Brightness.light,
      ),
      textTheme: base.textTheme.copyWith(
        headlineSmall: const TextStyle(
          fontFamily: 'Roboto',
          fontSize: 20,
          fontWeight: FontWeight.bold,
        ),
        titleLarge: const TextStyle(
          fontFamily: 'Roboto',
          fontSize: 18,
          fontWeight: FontWeight.w500,
        ),
        bodyMedium: const TextStyle(
          fontFamily: 'Roboto',
          fontSize: 16,
        ),
      ),
    );
  }
}
