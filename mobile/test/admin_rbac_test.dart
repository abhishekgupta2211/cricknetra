import 'package:cricnetra/core/auth/auth_provider.dart';
import 'package:cricnetra/core/models/org.dart';
import 'package:cricnetra/core/models/user.dart';
import 'package:cricnetra/core/storage/token_storage.dart';
import 'package:cricnetra/core/theme/app_palette.dart';
import 'package:cricnetra/core/theme/app_theme.dart';
import 'package:cricnetra/core/widgets/common.dart';
import 'package:cricnetra/features/admin/areas_screen.dart';
import 'package:cricnetra/features/admin/audit_screen.dart';
import 'package:cricnetra/features/admin/organizers_screen.dart';
import 'package:cricnetra/features/admin/role_assign_sheet.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/fake_api.dart';

/// The admin console hands out authority, so the things that can go wrong here
/// are not cosmetic: a control shown to somebody who cannot use it, an
/// organizer list that hides where a person is posted, or a "remove" that reads
/// like a "suspend" and quietly demotes an account.
///
/// The admin fixtures live in this file rather than in `fake_api.dart` so the
/// shared fake stays the shape every other test already expects.
void main() {
  /// A phone-sized surface. Four values across a 375px row is exactly the
  /// layout that has truncated here before, so the screens are rendered at the
  /// width they will actually be read at.
  void useNarrowScreen(WidgetTester tester) {
    tester.view.physicalSize = const Size(375, 812);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
  }

  Widget host(Widget child, {required List<Override> overrides}) {
    return ProviderScope(
      overrides: overrides,
      child: MaterialApp(
        theme: AppTheme.from(AppPalette.emerald),
        home: child,
      ),
    );
  }

  /// Two frames: one to start the futures, one to render what they answered.
  /// `pumpAndSettle` is no use while a skeleton is on screen — it shimmers for
  /// ever — so the loading step is stepped through by hand.
  Future<void> settle(WidgetTester tester) async {
    await tester.pump();
    await tester.pump();
  }

  group('gating', () {
    for (final screen in <({String name, Widget widget})>[
      (name: 'Organizers', widget: const OrganizersScreen()),
      (name: 'Areas', widget: const AreasScreen()),
      (name: 'Audit trail', widget: const AuditScreen()),
    ]) {
      testWidgets('${screen.name} shows a general user the gate, not controls',
          (tester) async {
        useNarrowScreen(tester);
        final api = _AdminApi();

        await tester.pumpWidget(host(
          screen.widget,
          overrides: _overrides(api, _generalUser),
        ));
        await settle(tester);

        expect(find.byType(GateCard), findsOneWidget);
        // Nothing that writes may be on screen: the server would refuse it, and
        // offering it wastes a tap and makes the app look broken.
        expect(find.byType(FloatingActionButton), findsNothing);
        expect(find.text('Add organizer'), findsNothing);
        expect(find.text('Suspend'), findsNothing);
        expect(find.text('Remove'), findsNothing);
        expect(find.text('New'), findsNothing);
        // The app bar survives, so there is a way back out.
        expect(find.byType(AppBar), findsOneWidget);
        expect(api.reads, isEmpty, reason: 'a gated screen should not fetch');
        expect(tester.takeException(), isNull);
      });
    }

    testWidgets('a guest is asked to sign in rather than told off',
        (tester) async {
      useNarrowScreen(tester);

      await tester.pumpWidget(host(
        const OrganizersScreen(),
        overrides: _overrides(_AdminApi(), null),
      ));
      await settle(tester);

      expect(find.text('Sign in'), findsOneWidget);
      expect(find.byType(FloatingActionButton), findsNothing);
    });
  });

  group('organizer list', () {
    testWidgets('shows the name, the posting and the tournament count',
        (tester) async {
      useNarrowScreen(tester);

      await tester.pumpWidget(host(
        const OrganizersScreen(),
        overrides: _overrides(_AdminApi(), FakeApi.adminUser),
      ));
      await settle(tester);

      expect(find.text('Rahul Yadav'), findsOneWidget);
      expect(find.text('Sam Suspended'), findsOneWidget);
      // Where they are posted, and how much of the season is riding on them.
      expect(find.text('XYZ Sports · Prayagraj'), findsOneWidget,
          reason: 'the posting line');
      expect(find.text('XYZ Sports'), findsOneWidget);
      expect(find.text('Prayagraj'), findsWidgets);
      expect(find.text('7'), findsOneWidget, reason: 'tournaments owned');
      expect(find.text('ORGANIZATION'), findsWidgets);
      // An active organizer and a stood-down one must not read the same.
      expect(find.text('Active'), findsOneWidget);
      expect(find.text('Suspended'), findsOneWidget);
      expect(tester.takeException(), isNull,
          reason: 'nothing may overflow at 375px');
    });

    testWidgets('an unreachable server keeps the app bar', (tester) async {
      useNarrowScreen(tester);
      final api = _AdminApi()..failWith = Exception('down');

      await tester.pumpWidget(host(
        const OrganizersScreen(),
        overrides: _overrides(api, FakeApi.adminUser),
      ));
      await settle(tester);

      // Reading the AsyncValue with `.value` would rethrow here and take the
      // whole screen — back arrow included — with it.
      expect(find.byType(ErrorState), findsOneWidget);
      expect(find.text('Organizers'), findsOneWidget, reason: 'the app bar');
    });
  });

  group('suspend versus remove', () {
    testWidgets('are offered as two different acts, with the difference said',
        (tester) async {
      useNarrowScreen(tester);

      await tester.pumpWidget(host(
        const OrganizersScreen(),
        overrides: _overrides(_AdminApi(), FakeApi.adminUser),
      ));
      await settle(tester);

      // Only the active organizer can be stood down, but either can be
      // removed — the two are never the same button.
      expect(find.widgetWithText(TextButton, 'Suspend'), findsOneWidget);
      expect(find.widgetWithText(TextButton, 'Remove'), findsNWidgets(2));
      // The suspended one is offered the way back, not a second suspend.
      expect(find.widgetWithText(TextButton, 'Restore'), findsOneWidget);
      // And the two are explained, not left to be inferred from the labels.
      expect(find.textContaining('Keeps the organizer role'), findsOneWidget);
      expect(find.textContaining('Demotes the account'), findsOneWidget);
    });

    testWidgets('suspending keeps the role and says so', (tester) async {
      useNarrowScreen(tester);
      final api = _AdminApi();

      await tester.pumpWidget(host(
        const OrganizersScreen(),
        overrides: _overrides(api, FakeApi.adminUser),
      ));
      await settle(tester);

      final button = find.widgetWithText(TextButton, 'Suspend');
      await tester.ensureVisible(button);
      await tester.tap(button);
      await tester.pumpAndSettle();

      expect(find.textContaining('keep the organizer role'), findsOneWidget);
      await tester.tap(find.widgetWithText(TextButton, 'Suspend').last);
      await tester.pumpAndSettle();

      expect(api.suspensions, [(userId: '2', isActive: false)]);
      expect(api.removed, isEmpty, reason: 'suspending must not demote');
    });

    testWidgets('removing warns that it demotes the account', (tester) async {
      useNarrowScreen(tester);
      final api = _AdminApi();

      await tester.pumpWidget(host(
        const OrganizersScreen(),
        overrides: _overrides(api, FakeApi.adminUser),
      ));
      await settle(tester);

      final button = find.widgetWithText(TextButton, 'Remove').first;
      await tester.ensureVisible(button);
      await tester.tap(button);
      await tester.pumpAndSettle();

      expect(find.textContaining('demotes the account'), findsOneWidget);
      expect(find.textContaining('stay owned by them'), findsOneWidget,
          reason: 'their tournaments are not deleted with them');

      // Backing out of the heavier action must leave everything alone.
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();
      expect(api.removed, isEmpty);

      await tester.tap(find.widgetWithText(TextButton, 'Remove').first);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Remove and demote'));
      await tester.pumpAndSettle();

      expect(api.removed, ['2']);
      expect(api.suspensions, isEmpty, reason: 'removing is not a suspend');
    });
  });

  group('assign role', () {
    testWidgets('offers every assignable role and reports the choice',
        (tester) async {
      useNarrowScreen(tester);
      final api = _AdminApi();
      RoleAssignment? reported;

      await tester.pumpWidget(host(
        Scaffold(
          body: Builder(
            builder: (context) => TextButton(
              onPressed: () async {
                reported = await showModalBottomSheet<RoleAssignment>(
                  context: context,
                  isScrollControlled: true,
                  builder: (context) => RoleAssignSheet(user: _member),
                );
              },
              child: const Text('open'),
            ),
          ),
        ),
        overrides: _overrides(api, FakeApi.adminUser),
      ));
      await tester.tap(find.text('open'));
      await tester.pumpAndSettle();

      // Somebody who does not know sign-up stopped granting roles goes looking
      // for a setting that no longer exists, so the sheet says it outright.
      expect(find.textContaining('only way a role is given'), findsOneWidget);
      // The sheet scrolls on a 375x812 phone, so the roles below the fold are
      // scrolled to rather than assumed to be laid out already.
      final sheet = find.byType(ListView);
      for (final label in [
        'General user',
        'Player',
        'Team owner',
        'Umpire',
        'Commentator',
        'Organizer',
        'Admin',
      ]) {
        await tester.dragUntilVisible(
            find.text(label), sheet, const Offset(0, -60));
        expect(find.text(label), findsWidgets, reason: 'role option $label');
      }

      await tester.ensureVisible(find.text('Organizer'));
      await tester.tap(find.text('Organizer'));
      await tester.pumpAndSettle();

      final assign = find.text('Assign Organizer');
      await tester.dragUntilVisible(assign, sheet, const Offset(0, -60));
      await tester.tap(assign);
      await tester.pumpAndSettle();

      expect(api.assigned, [(userId: '9', role: 'organizer')]);
      expect(reported?.role, 'organizer');
      expect(reported?.summary, 'Plain Member is now Organizer');
    });

    testWidgets('will not re-assign the role somebody already holds',
        (tester) async {
      useNarrowScreen(tester);

      await tester.pumpWidget(host(
        Scaffold(body: RoleAssignSheet(user: _member)),
        overrides: _overrides(_AdminApi(), FakeApi.adminUser),
      ));
      await tester.pumpAndSettle();

      final label = find.text('Pick a different role');
      await tester.dragUntilVisible(
          label, find.byType(ListView), const Offset(0, -60));

      final button = find.widgetWithText(ElevatedButton, 'Pick a different role');
      expect(button, findsOneWidget);
      expect(tester.widget<ElevatedButton>(button).onPressed, isNull);
    });
  });

  group('areas', () {
    testWidgets('shows each area with what is riding on it', (tester) async {
      useNarrowScreen(tester);

      await tester.pumpWidget(host(
        const AreasScreen(),
        overrides: _overrides(_AdminApi(), FakeApi.adminUser),
      ));
      await settle(tester);

      expect(find.text('Prayagraj · Uttar Pradesh'), findsOneWidget);
      // The counts are the point: an area nobody works is one created by
      // mistake, and deleting it should be an easy call.
      expect(find.text('ORGANIZERS'), findsOneWidget);
      expect(find.text('2'), findsOneWidget);
      expect(find.text('4'), findsOneWidget);
      expect(find.text('XYZ Sports'), findsOneWidget);
      expect(tester.takeException(), isNull,
          reason: 'nothing may overflow at 375px');
    });
  });

  group('audit trail', () {
    testWidgets('flags the weighty lines and leads with the newest',
        (tester) async {
      useNarrowScreen(tester);

      await tester.pumpWidget(host(
        const AuditScreen(),
        overrides: _overrides(_AdminApi(), FakeApi.adminUser),
      ));
      await settle(tester);

      expect(find.text('Role assigned'), findsOneWidget);
      expect(find.text('Tournament created'), findsOneWidget);
      // A role grant and a deletion move authority; a tournament being created
      // does not, so only two of the three carry the flag.
      expect(find.text('Flagged'), findsNWidgets(2));

      final rows = tester.getTopLeft(find.text('Role assigned'));
      final older = tester.getTopLeft(find.text('Tournament created'));
      expect(rows.dy, lessThan(older.dy), reason: 'newest first');

      expect(find.text('Everything'), findsOneWidget, reason: 'action filter');
      expect(find.text('Roles'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}

// ------------------------------------------------------------------ fixtures

final _generalUser = AppUser.fromJson({
  'id': '9',
  'full_name': 'Plain Member',
  'username': 'member',
  'role': 'general_user',
  'capabilities': const <String>[],
});

final _member = PublicUser.fromJson({
  'id': '9',
  'full_name': 'Plain Member',
  'username': 'member',
  'role': 'player',
});

/// The admin half of the API, recording what it was asked to do so a test can
/// tell a suspend from a removal.
class _AdminApi extends FakeApi {
  final removed = <String>[];
  final suspensions = <({String userId, bool isActive})>[];
  final assigned = <({String userId, String role})>[];

  /// Endpoints a gated screen must never reach.
  final reads = <String>[];

  static final _areas = [
    Area.fromJson({
      'id': '1',
      'name': 'Prayagraj',
      'state': 'Uttar Pradesh',
      'organizers': 2,
      'tournaments': 4,
    }),
  ];

  static final _organizers = [
    Organizer.fromJson({
      'user_id': '2',
      'full_name': 'Rahul Yadav',
      'username': 'rahul',
      'role': 'organizer',
      'is_active': true,
      'area_id': '1',
      'area_name': 'Prayagraj',
      'organization_id': '1',
      'organization_name': 'XYZ Sports',
      'tournaments': 7,
    }),
    Organizer.fromJson({
      'user_id': '3',
      'full_name': 'Sam Suspended',
      'username': 'sam',
      'role': 'organizer',
      'is_active': false,
      'area_id': '1',
      'area_name': 'Prayagraj',
      'tournaments': 1,
    }),
  ];

  Future<T> _record<T>(String call, T value) async {
    reads.add(call);
    if (failWith != null) throw failWith!;
    return value;
  }

  @override
  Future<List<Area>> areas() => _record('areas', _areas);

  @override
  Future<List<Organization>> organizations({String? areaId}) => _record(
        'organizations',
        [
          Organization.fromJson({
            'id': '1',
            'name': 'XYZ Sports',
            'area_id': '1',
            'area_name': 'Prayagraj',
          }),
        ],
      );

  @override
  Future<List<Organizer>> organizers({String? areaId}) => _record(
        'organizers',
        areaId == null
            ? _organizers
            : [
                for (final o in _organizers)
                  if (o.areaId == areaId) o,
              ],
      );

  @override
  Future<Organizer> updateOrganizer(
    String userId, {
    String? areaId,
    String? organizationId,
    bool? isActive,
  }) async {
    if (isActive != null) {
      suspensions.add((userId: userId, isActive: isActive));
    }
    return _organizers.firstWhere((o) => o.userId == userId);
  }

  @override
  Future<void> removeOrganizer(String userId) async => removed.add(userId);

  @override
  Future<void> assignRole(String userId, String role) async =>
      assigned.add((userId: userId, role: role));

  @override
  Future<List<AuditEntry>> auditTrail({int? limit, String? action}) => _record(
        'audit',
        [
          AuditEntry.fromJson({
            'id': '2',
            'actor_name': 'Seed Admin',
            'action': 'tournament.created',
            'resource_type': 'tournament',
            'resource_id': '4',
            'when': '2026-09-05T10:00:00',
          }),
          AuditEntry.fromJson({
            'id': '3',
            'actor_name': 'Seed Admin',
            'action': 'role.assigned',
            'resource_type': 'user',
            'resource_id': '2',
            'detail': 'general_user -> organizer',
            'when': '2026-09-06T10:00:00',
          }),
          AuditEntry.fromJson({
            'id': '1',
            'actor_name': 'Seed Admin',
            'action': 'tournament.deleted',
            'resource_type': 'tournament',
            'resource_id': '9',
            'when': '2026-09-01T10:00:00',
          }),
        ],
      );
}

List<Override> _overrides(FakeApi api, AppUser? user) => [
      apiProvider.overrideWithValue(api),
      authControllerProvider.overrideWith((ref) => _StubAuth(api, user)),
    ];

/// The real controller reads stored tokens on construction; a test must not.
class _StubAuth extends AuthController {
  _StubAuth(FakeApi api, AppUser? user)
      : super(api: api, tokens: TokenStorage(), client: api.client) {
    state = user == null
        ? const AuthState(status: AuthStatus.signedOut)
        : AuthState(status: AuthStatus.signedIn, user: user);
  }

  @override
  Future<void> restore() async {}
}
