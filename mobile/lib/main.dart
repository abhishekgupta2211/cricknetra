import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/router/app_router.dart';
import 'core/theme/app_palette.dart';
import 'core/theme/app_theme.dart';
import 'core/theme/theme_provider.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  // If a widget ever throws while building, Flutter replaces it with this.
  // The default is a bare red box (grey in release) with no way out, so when
  // the failing widget is a whole screen the person is stranded. Keeping an
  // app bar means there is always a back arrow.
  ErrorWidget.builder = (details) => Scaffold(
        appBar: AppBar(title: const Text('Something went wrong')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              'This screen could not be shown. Go back and try again.',
              textAlign: TextAlign.center,
            ),
          ),
        ),
      );

  runApp(const ProviderScope(child: CricNetraApp()));
}

class CricNetraApp extends ConsumerWidget {
  const CricNetraApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    final settings = ref.watch(themeControllerProvider);

    return MaterialApp.router(
      title: 'CricNetra',
      debugShowCheckedModeBanner: false,
      routerConfig: router,
      // Out of the box the app follows the phone. Choosing a palette in
      // Settings pins it, and the toggle there hands control back.
      themeMode: settings.mode,
      theme: AppTheme.from(settings.lightCounterpart),
      darkTheme: AppTheme.from(settings.darkCounterpart),
      builder: (context, child) {
        final media = MediaQuery.of(context);
        // Read the device brightness here so the status-bar styling follows
        // the phone the moment it changes, without a restart.
        final palette = resolvePalette(settings, media.platformBrightness);

        return _SystemBars(
          palette: palette,
          child: MediaQuery(
            // Respect the reader's font-size choice, but stop runaway scaling
            // from breaking the scoring pad's fixed grid.
            data: media.copyWith(
              textScaler: media.textScaler.clamp(
                minScaleFactor: 0.85,
                maxScaleFactor: 1.35,
              ),
            ),
            child: child ?? const SizedBox.shrink(),
          ),
        );
      },
    );
  }
}

/// Keeps the status and navigation bars legible against whichever palette is
/// showing, including when the phone switches theme while the app is open.
class _SystemBars extends StatelessWidget {
  final AppPalette palette;
  final Widget child;

  const _SystemBars({required this.palette, required this.child});

  @override
  Widget build(BuildContext context) {
    final dark = palette.isDark;
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: dark ? Brightness.light : Brightness.dark,
        statusBarBrightness: dark ? Brightness.dark : Brightness.light,
        systemNavigationBarColor: palette.background,
        systemNavigationBarIconBrightness:
            dark ? Brightness.light : Brightness.dark,
      ),
      child: child,
    );
  }
}
