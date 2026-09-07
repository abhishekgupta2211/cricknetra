import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';

/// Where the API lives.
///
/// Override at build time:
///   flutter run --dart-define=CRICNETRA_API=https://cricnetra.example.com
///
/// With no override we guess a sensible local default, because `127.0.0.1`
/// means "this device" — on an Android emulator that is the emulator itself,
/// not the developer's machine, so it has to be `10.0.2.2` there.
class ApiConfig {
  const ApiConfig._();

  static const _override =
      String.fromEnvironment('CRICNETRA_API', defaultValue: '');

  /// The port the backend runs on locally (`uvicorn --port`).
  static const _devPort =
      String.fromEnvironment('CRICNETRA_PORT', defaultValue: '8023');

  /// Root origin, with no trailing slash and no `/api/v1`.
  static String get origin {
    if (_override.isNotEmpty) return _stripSlash(_override);
    return 'http://${_localHost()}:$_devPort';
  }

  /// Base URL for every JSON call.
  static String get baseUrl => '$origin/api/v1';

  static String _localHost() {
    if (kIsWeb) return '127.0.0.1';
    try {
      // The Android emulator maps the host machine to 10.0.2.2.
      if (Platform.isAndroid) return '10.0.2.2';
    } catch (_) {
      // Platform is unavailable on some targets; fall through.
    }
    return '127.0.0.1';
  }

  static String _stripSlash(String s) =>
      s.endsWith('/') ? s.substring(0, s.length - 1) : s;

  /// Absolute URL for an image the API serves (photos are plain GETs).
  static String photoUrl(String segment, String id, {int? bust}) {
    final q = bust == null ? '' : '?v=$bust';
    return '$baseUrl/$segment/$id/photo$q';
  }

  static String userPhoto(String id, {int? bust}) =>
      photoUrl('users', id, bust: bust);
  static String playerPhoto(String id, {int? bust}) =>
      photoUrl('players', id, bust: bust);
  static String teamPhoto(String id, {int? bust}) =>
      photoUrl('teams', id, bust: bust);

  /// Public share links, served by the marketing site rather than the API.
  static String matchShareUrl(String id) => '$origin/m/$id';
  static String tournamentShareUrl(String id) => '$origin/t/$id';
  static String scorecardPdfUrl(String id) => '$origin/scorecard/$id?print=1';
  static String overlayUrl(String id) => '$origin/overlay/$id';
  static String overlayAnalysisUrl(String id) => '$origin/overlay/$id/analysis';
}
