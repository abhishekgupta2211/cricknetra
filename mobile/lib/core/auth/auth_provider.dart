import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../api/api_exception.dart';
import '../api/api_service.dart';
import '../models/user.dart';
import '../storage/token_storage.dart';

final tokenStorageProvider = Provider<TokenStorage>((ref) => TokenStorage());

final apiClientProvider = Provider<ApiClient>(
  (ref) => ApiClient(tokenStorage: ref.watch(tokenStorageProvider)),
);

final apiProvider = Provider<ApiService>(
  (ref) => ApiService(ref.watch(apiClientProvider)),
);

/// Where the session stands. `restoring` is the brief window at launch while we
/// check for a stored token — the router must not redirect during it.
enum AuthStatus { restoring, signedOut, signedIn }

class AuthState {
  final AuthStatus status;
  final AppUser? user;
  final String? error;

  const AuthState({
    this.status = AuthStatus.restoring,
    this.user,
    this.error,
  });

  bool get isSignedIn => status == AuthStatus.signedIn && user != null;
  bool get isRestoring => status == AuthStatus.restoring;

  /// Does the signed-in account hold this capability? Signed-out is always no.
  bool can(String capability) => user?.can(capability) ?? false;

  bool get isAdmin => user?.isAdmin ?? false;

  AuthState copyWith({
    AuthStatus? status,
    AppUser? user,
    String? error,
    bool clearUser = false,
    bool clearError = false,
  }) =>
      AuthState(
        status: status ?? this.status,
        user: clearUser ? null : (user ?? this.user),
        error: clearError ? null : (error ?? this.error),
      );
}

class AuthController extends StateNotifier<AuthState> {
  final ApiService api;
  final TokenStorage tokens;

  AuthController({
    required this.api,
    required this.tokens,
    required ApiClient client,
  }) : super(const AuthState()) {
    // A refresh token that no longer works means the session is over. The
    // transport tells us, and the router follows the state change.
    client.onSessionExpired = handleSessionExpired;
    restore();
  }

  /// Read any stored token and confirm it still works.
  Future<void> restore() async {
    if (!await tokens.hasSession) {
      state = const AuthState(status: AuthStatus.signedOut);
      return;
    }
    try {
      final user = await api.me();
      state = AuthState(status: AuthStatus.signedIn, user: user);
    } on ApiException catch (e) {
      // A network blip should not sign someone out — only a rejected session.
      if (e.isNetwork) {
        state = const AuthState(status: AuthStatus.signedOut);
      } else {
        await tokens.clearTokens();
        state = const AuthState(status: AuthStatus.signedOut);
      }
    } catch (_) {
      state = const AuthState(status: AuthStatus.signedOut);
    }
  }

  Future<void> login(String identifier, String password) async {
    final pair = await api.login(identifier, password);
    await tokens.saveTokens(
      accessToken: pair.accessToken,
      refreshToken: pair.refreshToken,
    );
    final user = await api.me();
    state = AuthState(status: AuthStatus.signedIn, user: user);
  }

  /// Registers, then signs in with the same credentials.
  ///
  /// Returns the created account so the caller can tell the user when an
  /// elevated role is waiting on admin approval.
  Future<AppUser> register({
    required String fullName,
    required String username,
    required String mobileNo,
    required String password,
    required String role,
    String? email,
  }) async {
    final created = await api.register(
      fullName: fullName,
      username: username,
      mobileNo: mobileNo,
      password: password,
      role: role,
      email: email,
    );
    await login(username, password);
    return created;
  }

  Future<void> logout() async {
    final refresh = await tokens.getRefreshToken();
    if (refresh != null && refresh.isNotEmpty) {
      try {
        await api.logout(refresh);
      } catch (_) {
        // Best effort — the local session is cleared either way.
      }
    }
    await tokens.clearTokens();
    state = const AuthState(status: AuthStatus.signedOut);
  }

  /// Revokes every refresh token and forgets push devices.
  Future<void> logoutEverywhere() async {
    try {
      await api.logoutAll();
    } finally {
      await tokens.clearTokens();
      state = const AuthState(status: AuthStatus.signedOut);
    }
  }

  /// Re-read the account, after a profile edit, photo upload or verification.
  Future<void> refreshUser() async {
    if (!state.isSignedIn) return;
    try {
      state = state.copyWith(user: await api.me());
    } catch (_) {
      // Keep the last known user rather than blanking the UI.
    }
  }

  /// Called by the transport when a refresh definitively fails.
  void handleSessionExpired() {
    if (state.status == AuthStatus.signedOut) return;
    state = const AuthState(status: AuthStatus.signedOut);
  }
}

final authControllerProvider =
    StateNotifierProvider<AuthController, AuthState>((ref) {
  return AuthController(
    api: ref.watch(apiProvider),
    tokens: ref.watch(tokenStorageProvider),
    client: ref.watch(apiClientProvider),
  );
});

/// Convenience reads used all over the UI.
final currentUserProvider =
    Provider<AppUser?>((ref) => ref.watch(authControllerProvider).user);

final isSignedInProvider =
    Provider<bool>((ref) => ref.watch(authControllerProvider).isSignedIn);

/// Whether the signed-in account holds a capability.
final capabilityProvider = Provider.family<bool, String>(
  (ref, cap) => ref.watch(authControllerProvider).can(cap),
);
