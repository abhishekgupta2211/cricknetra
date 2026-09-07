import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/social.dart';

final notificationsProvider =
    FutureProvider.autoDispose<List<AppNotification>>((ref) async {
  if (!ref.watch(isSignedInProvider)) return const [];
  return ref.watch(apiProvider).notifications();
});

/// Drives the bell badge. Returns zero rather than failing when signed out.
final unreadNotificationsProvider =
    FutureProvider.autoDispose<int>((ref) async {
  if (!ref.watch(isSignedInProvider)) return 0;
  try {
    return await ref.watch(apiProvider).unreadNotificationCount();
  } catch (_) {
    return 0;
  }
});

final unreadMessagesProvider = FutureProvider.autoDispose<int>((ref) async {
  if (!ref.watch(isSignedInProvider)) return 0;
  try {
    return await ref.watch(apiProvider).unreadMessageCount();
  } catch (_) {
    return 0;
  }
});

final notificationPrefsProvider =
    FutureProvider.autoDispose<NotificationPrefs>(
  (ref) => ref.watch(apiProvider).notificationPrefs(),
);

final feedProvider = FutureProvider.autoDispose<List<ActivityItem>>((ref) async {
  if (!ref.watch(isSignedInProvider)) return const [];
  return ref.watch(apiProvider).feed();
});

final conversationsProvider =
    FutureProvider.autoDispose<List<Conversation>>((ref) async {
  if (!ref.watch(isSignedInProvider)) return const [];
  return ref.watch(apiProvider).conversations();
});

final threadProvider =
    FutureProvider.autoDispose.family<MessageThread, String>(
  (ref, userId) => ref.watch(apiProvider).thread(userId),
);

/// Who the signed-in account follows, so rows can show the right button.
final followingProvider = FutureProvider.autoDispose<Set<String>>((ref) async {
  if (!ref.watch(isSignedInProvider)) return <String>{};
  try {
    return (await ref.watch(apiProvider).following()).toSet();
  } catch (_) {
    return <String>{};
  }
});
