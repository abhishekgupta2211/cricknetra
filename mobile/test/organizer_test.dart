import 'package:cricnetra/core/api/api_exception.dart';
import 'package:cricnetra/core/auth/auth_provider.dart';
import 'package:cricnetra/core/models/org.dart';
import 'package:cricnetra/core/models/tournament.dart';
import 'package:cricnetra/core/models/user.dart';
import 'package:cricnetra/core/storage/token_storage.dart';
import 'package:cricnetra/core/theme/app_palette.dart';
import 'package:cricnetra/core/theme/app_theme.dart';
import 'package:cricnetra/core/widgets/common.dart';
import 'package:cricnetra/features/organizer/my_assignments_screen.dart';
import 'package:cricnetra/features/organizer/organizer_dashboard_screen.dart';
import 'package:cricnetra/features/organizer/tournament_staff_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/fake_api.dart';

/// The organizer's desk and the screens the staff of a competition use.
///
/// What these guard is the line between "may run competitions" and "may run
/// THIS competition". The capability decides what is drawn; the server decides
/// what happens. So: the controls vanish without the capability, an assigned
/// umpire can read the list without editing it, and when the server refuses —
/// the 409 saying that adding somebody would take away the role they already
/// hold — its sentence reaches the screen intact rather than becoming
/// "Something went wrong".
///
/// The fixtures live in this file rather than in `support/fake_api.dart`: the
/// staff surface is only exercised here, and widening the shared fake for one
/// feature makes every other test carry it.

/// The exact sentence the server sends on a 409. The whole point of the dialog
/// is that it arrives verbatim, so the test compares against the string itself.
const conflictMessage =
    "Rahul Yadav already holds the 'Player' role. Adding them as an umpire "
    'would take that away, so an admin has to change their role first.';

AppUser organizerUser() => AppUser.fromJson({
      'id': '7',
      'full_name': 'Meera Nair',
      'username': 'meera',
      'role': 'organizer',
      'capabilities': const [
        'tournament.create',
        'tournament.manage',
        'umpire.manage',
        'commentator.manage',
      ],
    });

/// An umpire is assignment-scoped: they hold no capabilities at all, and
/// everything they may do comes from being on somebody's staff.
AppUser umpireUser() => AppUser.fromJson({
      'id': '8',
      'full_name': 'Suresh Iyer',
      'username': 'suresh',
      'role': 'umpire',
      'capabilities': const <String>[],
    });

AppUser plainMember() => AppUser.fromJson({
      'id': '9',
      'full_name': 'Plain Member',
      'username': 'member',
      'role': 'general_user',
      'capabilities': const <String>[],
    });

/// Two umpires (one stood down) and a commentator, the way the server returns
/// them — inactive entries included, so an organizer can bring somebody back.
List<TournamentStaff> staffFixture() => [
      TournamentStaff.fromJson({
        'user_id': '4',
        'full_name': 'Vikram Shah',
        'username': 'vikram',
        'mobile_no': '9820011224',
        'staff_role': 'umpire',
        'tournament_id': '1',
      }),
      TournamentStaff.fromJson({
        'user_id': '3',
        'full_name': 'Anita Rao',
        'username': 'anita',
        'staff_role': 'commentator',
        'tournament_id': '1',
      }),
      TournamentStaff.fromJson({
        'user_id': '6',
        'full_name': 'Priya Menon',
        'username': 'priya',
        'staff_role': 'umpire',
        'is_active': false,
        'tournament_id': '1',
      }),
    ];

/// A fake whose organizer surface answers, and which can be told to refuse an
/// umpire the way the server does.
///
/// `FakeApi._answer` is private to its own library, so these overrides return
/// their fixtures directly; anything not listed still falls through to FakeApi
/// and, past that, to the `noSuchMethod` that fails loudly.
class OrgApi extends FakeApi {
  /// Set to make the next `addUmpire` fail — the 409 path.
  Object? addFails;

  int myStaffingCalls = 0;
  final removed = <String>[];

  /// Deliberately carries a competition the caller has nothing to do with, so
  /// "my assignments" can be shown not to leak it.
  @override
  Future<List<TournamentSummary>> tournaments() async => [
        TournamentSummary.fromJson({
          'id': '1',
          'name': 'City Premier League',
          'format': 'round_robin',
          'teams': [
            {'id': '1', 'name': 'Mumbai Strikers'},
            {'id': '2', 'name': 'Chennai Kings'},
          ],
        }),
        TournamentSummary.fromJson({
          'id': '2',
          'name': 'Winter Shield',
          'format': 'knockout',
          'teams': [
            {'id': '1', 'name': 'Mumbai Strikers'},
          ],
        }),
      ];

  @override
  Future<List<Organizer>> organizers({String? areaId}) async => [
        Organizer.fromJson({
          'user_id': '7',
          'full_name': 'Meera Nair',
          'role': 'organizer',
          'area_name': 'Prayagraj',
          'organization_name': 'XYZ Sports',
          'tournaments': 2,
        }),
      ];

  /// The pool the picker searches. Rahul already holds the player role, which
  /// is what the 409 is about; Neha holds none, so she is the promotable case.
  @override
  Future<List<PublicUser>> users({String? role}) async => [
        PublicUser.fromJson({
          'id': '2',
          'full_name': 'Rahul Yadav',
          'username': 'rahul',
          'role': 'player',
          'mobile_no': '9820011223',
        }),
        PublicUser.fromJson({
          'id': '5',
          'full_name': 'Neha Gupta',
          'username': 'neha',
          'role': 'general_user',
        }),
      ];

  @override
  Future<List<TournamentStaff>> tournamentStaff(
    String tournamentId, {
    String? staffRole,
  }) async =>
      staffFixture();

  @override
  Future<TournamentStaff> addUmpire(String tournamentId, String userId) async {
    if (addFails != null) throw addFails!;
    return TournamentStaff.fromJson({
      'user_id': userId,
      'staff_role': 'umpire',
      'tournament_id': tournamentId,
    });
  }

  @override
  Future<void> removeStaff(
    String tournamentId,
    String staffRole,
    String userId,
  ) async =>
      removed.add('$tournamentId/$staffRole/$userId');

  /// The server takes the person from the token, so this can only ever be the
  /// caller's own list — never everything in [tournaments].
  @override
  Future<List<MyStaffing>> myStaffing() async {
    myStaffingCalls++;
    return [
      MyStaffing.fromJson({
        'tournament_id': '1',
        'tournament_name': 'City Premier League',
        'staff_role': 'umpire',
      }),
      MyStaffing.fromJson({
        'tournament_id': '3',
        'tournament_name': 'Sunday Cup',
        'staff_role': 'commentator',
        'is_active': false,
      }),
    ];
  }

  @override
  Future<List<TournamentPlayer>> tournamentPlayers(String tournamentId) async =>
      [
        TournamentPlayer.fromJson({
          'team_id': '1',
          'team_name': 'Mumbai Strikers',
          'player': {'id': '1', 'name': 'Rohit Sharma', 'code': 'P00001'},
        }),
        TournamentPlayer.fromJson({
          'team_id': '1',
          'team_name': 'Mumbai Strikers',
          'player': {'id': '2', 'name': 'Virat Kohli', 'code': 'P00002'},
        }),
        TournamentPlayer.fromJson({
          'team_id': '2',
          'team_name': 'Chennai Kings',
          'player': {'id': '3', 'name': 'Jasprit Bumrah', 'code': 'P00003'},
        }),
      ];
}

/// Everything a staff screen reads fails, for the escapability check.
class FailingApi extends FakeApi {
  @override
  Future<List<TournamentStaff>> tournamentStaff(
    String tournamentId, {
    String? staffRole,
  }) async =>
      throw const ApiException(
        message: 'not your tournament',
        statusCode: 403,
      );

  @override
  Future<Tournament> tournament(String id) async =>
      throw const ApiException(message: 'not found', statusCode: 404);
}

class NoStaffingApi extends FakeApi {
  @override
  Future<List<MyStaffing>> myStaffing() async => const [];
}

/// The shared fake signs in as the seeded admin; every question here is about
/// a specific role, so these tests bring their own account.
class StubAuth extends AuthController {
  StubAuth({required FakeApi api, AppUser? user})
      : super(api: api, tokens: TokenStorage(), client: api.client) {
    state = user == null
        ? const AuthState(status: AuthStatus.signedOut)
        : AuthState(status: AuthStatus.signedIn, user: user);
  }

  // The real controller reads stored tokens on construction; a test should not.
  @override
  Future<void> restore() async {}
}

List<Override> asUser(FakeApi api, AppUser? user) => [
      apiProvider.overrideWithValue(api),
      authControllerProvider
          .overrideWith((ref) => StubAuth(api: api, user: user)),
    ];

void main() {
  /// Pumps a screen on a 375-wide phone — the narrowest the app supports, and
  /// where a row of controls that does not fit becomes an overflow instead of
  /// a layout.
  Future<void> pump(
    WidgetTester tester,
    Widget screen, {
    required FakeApi api,
    AppUser? user,
  }) async {
    tester.view.physicalSize = const Size(375, 812);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(ProviderScope(
      overrides: asUser(api, user),
      child: MaterialApp(
        theme: AppTheme.from(AppPalette.emerald),
        home: screen,
      ),
    ));
    await tester.pumpAndSettle();
  }

  // ------------------------------------------------------------- dashboard

  group('Organizer dashboard', () {
    testWidgets('lists the competitions with a way into staff and players',
        (tester) async {
      await pump(
        tester,
        const OrganizerDashboardScreen(),
        api: OrgApi(),
        user: organizerUser(),
      );

      expect(find.text('City Premier League'), findsOneWidget);
      expect(find.text('Winter Shield'), findsOneWidget);
      expect(find.text('2 teams · League'), findsOneWidget);
      // One pair of working views per competition.
      expect(find.text('Staff'), findsNWidgets(2));
      expect(find.text('Players'), findsNWidgets(2));
      expect(tester.takeException(), isNull);
    });

    testWidgets('shows the area and organization when the account has them',
        (tester) async {
      await pump(
        tester,
        const OrganizerDashboardScreen(),
        api: OrgApi(),
        user: organizerUser(),
      );

      expect(find.text('Meera Nair'), findsOneWidget);
      expect(find.text('XYZ Sports · Prayagraj'), findsOneWidget);
    });

    testWidgets('a posting the server will not hand over is not an error',
        (tester) async {
      // A plain organizer's posting lives on the admin roster, which answers
      // 403 to them. Plain FakeApi does not stub `organizers()` at all, so the
      // read throws — and the dashboard still has to be complete.
      await pump(
        tester,
        const OrganizerDashboardScreen(),
        api: FakeApi(),
        user: organizerUser(),
      );

      expect(find.text('Meera Nair'), findsOneWidget);
      expect(find.text('XYZ Sports · Prayagraj'), findsNothing);
      expect(find.text('City Premier League'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('a non-organizer is told why, and offered nothing to press',
        (tester) async {
      await pump(
        tester,
        const OrganizerDashboardScreen(),
        api: OrgApi(),
        user: plainMember(),
      );

      expect(find.byType(GateCard), findsOneWidget);
      expect(find.textContaining('organize competitions'), findsOneWidget);
      // No competition, and no way into anybody's staff.
      expect(find.text('City Premier League'), findsNothing);
      expect(find.text('Staff'), findsNothing);
      expect(find.text('Players'), findsNothing);
      // The app bar survives, so they can leave.
      expect(find.text('Organizer'), findsOneWidget);
    });
  });

  // ----------------------------------------------------------------- staff

  group('Tournament staff', () {
    testWidgets('renders umpires and commentators as two groups',
        (tester) async {
      await pump(
        tester,
        const TournamentStaffScreen(tournamentId: '1'),
        api: OrgApi(),
        user: organizerUser(),
      );

      expect(find.text('Umpires'), findsOneWidget);
      expect(find.text('Commentators'), findsOneWidget);
      expect(find.text('Vikram Shah'), findsOneWidget);
      expect(find.text('Priya Menon'), findsOneWidget);
      expect(find.text('Anita Rao'), findsOneWidget);
      // A stood-down umpire stays on the list, flagged — otherwise the only
      // way back is to remember the name and add them again.
      expect(find.text('Stood down'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('says removal is per competition, not per account',
        (tester) async {
      await pump(
        tester,
        const TournamentStaffScreen(tournamentId: '1'),
        api: OrgApi(),
        user: organizerUser(),
      );

      expect(find.textContaining('this competition only'), findsOneWidget);
    });

    testWidgets('offers the owner both add controls and a menu per person',
        (tester) async {
      await pump(
        tester,
        const TournamentStaffScreen(tournamentId: '1'),
        api: OrgApi(),
        user: organizerUser(),
      );

      expect(find.text('Add umpire'), findsOneWidget);
      expect(find.text('Add commentator'), findsOneWidget);
      expect(find.byType(PopupMenuButton<String>), findsNWidgets(3));
    });

    testWidgets('an assigned umpire reads the list and writes nothing',
        (tester) async {
      // An umpire on the competition may see who else works it; holding no
      // capability, every control that changes it has to be absent.
      await pump(
        tester,
        const TournamentStaffScreen(tournamentId: '1'),
        api: OrgApi(),
        user: umpireUser(),
      );

      expect(find.text('Vikram Shah'), findsOneWidget);
      expect(find.text('Add umpire'), findsNothing);
      expect(find.text('Add commentator'), findsNothing);
      expect(find.byType(PopupMenuButton<String>), findsNothing);
    });

    testWidgets('shows the 409 the server sent, word for word', (tester) async {
      final api = OrgApi()
        ..addFails =
            const ApiException(message: conflictMessage, statusCode: 409);

      await pump(
        tester,
        const TournamentStaffScreen(tournamentId: '1'),
        api: api,
        user: organizerUser(),
      );

      await tester.ensureVisible(find.text('Add umpire'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Add umpire'));
      await tester.pumpAndSettle();

      // The picker appoints an account that already exists; it is not a second
      // way to create one.
      expect(find.textContaining('promoted on the way in'), findsOneWidget);
      await tester.tap(find.text('Rahul Yadav'));
      await tester.pumpAndSettle();

      // Verbatim. The sentence is the useful part: it says what would be taken
      // away and who can change it.
      expect(find.text('Cannot add them'), findsOneWidget);
      expect(find.text(conflictMessage), findsOneWidget);
    });

    testWidgets('a failure keeps the app bar and the way back', (tester) async {
      tester.view.physicalSize = const Size(375, 812);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      await tester.pumpWidget(ProviderScope(
        overrides: asUser(FailingApi(), organizerUser()),
        child: MaterialApp(
          theme: AppTheme.from(AppPalette.emerald),
          home: Builder(
            builder: (context) => Scaffold(
              body: Center(
                child: ElevatedButton(
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) =>
                          const TournamentStaffScreen(tournamentId: '9'),
                    ),
                  ),
                  child: const Text('open'),
                ),
              ),
            ),
          ),
        ),
      ));
      await tester.tap(find.text('open'));
      await tester.pumpAndSettle();

      expect(find.byType(BackButton), findsOneWidget);
      expect(find.byType(ErrorWidget), findsNothing);
      expect(find.textContaining('not your tournament'), findsWidgets);
    });
  });

  // --------------------------------------------------------------- players

  group('Tournament players', () {
    testWidgets('groups the flattened roster by team', (tester) async {
      await pump(
        tester,
        const TournamentPlayersScreen(tournamentId: '1'),
        api: OrgApi(),
        user: organizerUser(),
      );

      expect(find.text('3 registered'), findsOneWidget);
      expect(find.text('Across 2 teams'), findsOneWidget);
      expect(find.text('Mumbai Strikers'), findsOneWidget);
      expect(find.text('Chennai Kings'), findsOneWidget);
      expect(find.text('Rohit Sharma'), findsOneWidget);
      expect(find.text('Virat Kohli'), findsOneWidget);
      expect(find.text('Jasprit Bumrah'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });

  // -------------------------------------------------------- my assignments

  group('My assignments', () {
    testWidgets('lists only the competitions the caller is staff on',
        (tester) async {
      final api = OrgApi();

      await pump(
        tester,
        const MyAssignmentsScreen(),
        api: api,
        user: umpireUser(),
      );

      expect(api.myStaffingCalls, 1);
      expect(find.text('City Premier League'), findsOneWidget);
      expect(find.text('Sunday Cup'), findsOneWidget);
      // `tournaments()` also has Winter Shield in it. This screen is fed by
      // the token-scoped staffing call, so a competition the caller does not
      // work must not appear here.
      expect(find.text('Winter Shield'), findsNothing);
      expect(tester.takeException(), isNull);
    });

    testWidgets('separates the two jobs and flags being stood down',
        (tester) async {
      await pump(
        tester,
        const MyAssignmentsScreen(),
        api: OrgApi(),
        user: umpireUser(),
      );

      expect(find.text('As umpire'), findsOneWidget);
      expect(find.text('As commentator'), findsOneWidget);
      expect(find.text('Stood down'), findsOneWidget);
      expect(
        find.textContaining('The organizer has stood you down'),
        findsOneWidget,
      );
      expect(find.textContaining('Hello, Suresh'), findsOneWidget);
      // A real screen, not a list of ids: each entry opens its competition and
      // the two views an assigned official is allowed to read.
      expect(find.text('Team sheet'), findsNWidgets(2));
      expect(find.text('Staff'), findsNWidgets(2));
    });

    testWidgets('an official with nothing yet is told what to expect',
        (tester) async {
      await pump(
        tester,
        const MyAssignmentsScreen(),
        api: NoStaffingApi(),
        user: umpireUser(),
      );

      expect(find.text('No competitions yet'), findsOneWidget);
      expect(find.textContaining('An organizer adds you'), findsOneWidget);
    });
  });
}
