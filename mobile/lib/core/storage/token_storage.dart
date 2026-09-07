import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Persists the JWT pair.
///
/// The access token is short-lived (30 min); the refresh token lasts 30 days
/// and is **rotated on every use**, so only one refresh may be in flight at a
/// time — see the mutex in `ApiClient`.
class TokenStorage {
  static const _accessKey = 'cn_access_token';
  static const _refreshKey = 'cn_refresh_token';

  final FlutterSecureStorage _storage;

  TokenStorage({FlutterSecureStorage? storage})
      : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(encryptedSharedPreferences: true),
            );

  /// Cached in memory so the request interceptor does not hit the keystore on
  /// every single call.
  String? _access;
  String? _refresh;
  bool _loaded = false;

  Future<void> _ensureLoaded() async {
    if (_loaded) return;
    try {
      _access = await _storage.read(key: _accessKey);
      _refresh = await _storage.read(key: _refreshKey);
    } catch (_) {
      // A locked or unavailable keystore should log the user out, not crash.
      _access = null;
      _refresh = null;
    }
    _loaded = true;
  }

  Future<String?> getAccessToken() async {
    await _ensureLoaded();
    return _access;
  }

  Future<String?> getRefreshToken() async {
    await _ensureLoaded();
    return _refresh;
  }

  /// The access token without awaiting storage — for building an SSE URL on a
  /// path that has already authenticated at least once.
  String? get cachedAccessToken => _access;

  Future<void> saveTokens({
    required String accessToken,
    String? refreshToken,
  }) async {
    _loaded = true;
    _access = accessToken;
    if (refreshToken != null) _refresh = refreshToken;
    try {
      await _storage.write(key: _accessKey, value: accessToken);
      if (refreshToken != null) {
        await _storage.write(key: _refreshKey, value: refreshToken);
      }
    } catch (_) {
      // Keep the in-memory copy; the session survives until the app restarts.
    }
  }

  Future<void> clearTokens() async {
    _loaded = true;
    _access = null;
    _refresh = null;
    try {
      await _storage.delete(key: _accessKey);
      await _storage.delete(key: _refreshKey);
    } catch (_) {
      // Nothing more we can do.
    }
  }

  Future<bool> get hasSession async {
    await _ensureLoaded();
    return _access != null && _access!.isNotEmpty;
  }
}
