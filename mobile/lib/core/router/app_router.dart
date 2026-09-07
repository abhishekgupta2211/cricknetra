import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/account/account_screen.dart';
import '../../features/account/profile_details_screen.dart';
import '../../features/admin/admin_screen.dart';
import '../../features/admin/areas_screen.dart';
import '../../features/admin/audit_screen.dart';
import '../../features/admin/organizers_screen.dart';
import '../../features/auth/forgot_password_screen.dart';
import '../../features/auth/login_screen.dart';
import '../../features/auth/register_screen.dart';
import '../../features/highlights/highlights_screen.dart';
import '../../features/home/home_screen.dart';
import '../../features/leaderboards/compare_screen.dart';
import '../../features/leaderboards/leaderboards_screen.dart';
import '../../features/looking_for/looking_for_screen.dart';
import '../../features/matches/create_match_screen.dart';
import '../../features/matches/match_screen.dart';
import '../../features/matches/matches_list_screen.dart';
import '../../features/messages/messages_screen.dart';
import '../../features/messages/thread_screen.dart';
import '../../features/more/more_screen.dart';
import '../../features/network/feed_screen.dart';
import '../../features/network/network_screen.dart';
import '../../features/notifications/notifications_screen.dart';
import '../../features/organizer/my_assignments_screen.dart';
import '../../features/organizer/organizer_dashboard_screen.dart';
import '../../features/organizer/tournament_staff_screen.dart';
import '../../features/players/career_screen.dart';
import '../../features/players/player_screen.dart';
import '../../features/players/players_list_screen.dart';
import '../../features/rules/rule_builder_screen.dart';
import '../../features/rules/rule_templates_screen.dart';
import '../../features/search/search_screen.dart';
import '../../features/settings/settings_screen.dart';
import '../../features/shell/main_shell.dart';
import '../../features/teams/team_screen.dart';
import '../../features/teams/teams_list_screen.dart';
import '../../features/tools/tools_screen.dart';
import '../../features/tournaments/tournament_screen.dart';
import '../../features/tournaments/tournaments_list_screen.dart';
import '../../features/venues/venues_screen.dart';
import '../auth/auth_provider.dart';
import '../models/user.dart';
import '../widgets/common.dart';

/// Route paths in one place, so no screen navigates to a string that does not
/// exist. (The previous client pushed `/tournaments/new`, which was never
/// registered, and landed users on an error page.)
class Routes {
  const Routes._();

  static const home = '/home';
  static const matches = '/matches';
  static const tournaments = '/tournaments';
  static const community = '/community';
  static const more = '/more';

  static const login = '/login';
  static const register = '/register';
  static const forgotPassword = '/forgot-password';

  static const newMatch = '/matches/new';
  static String match(String id) => '/matches/$id';

  static const teams = '/teams';
  static String team(String id) => '/teams/$id';

  static const players = '/players';
  static String player(String id) => '/players/$id';
  static String career(String id) => '/players/$id/career';
  static const compare = '/compare';

  static String tournament(String id) => '/tournaments/$id';

  static const leaderboards = '/leaderboards';
  static const highlights = '/highlights';
  static const venues = '/venues';
  static const network = '/network';
  static const feed = '/feed';
  static const messages = '/messages';
  static String thread(String userId) => '/messages/$userId';
  static const lookingFor = '/looking-for';
  static const search = '/search';
  static const notifications = '/notifications';
  static const settings = '/settings';
  static const account = '/account';
  static const profileDetails = '/account/profile';
  static const admin = '/admin';

  // Under `/admin` on purpose: the redirect below gates the whole prefix, so a
  // new admin screen is protected by existing where it belongs.
  static const adminOrganizers = '/admin/organizers';
  static const adminAreas = '/admin/areas';
  static const adminAudit = '/admin/audit';

  /// The organizer's desk, and the working views of one competition. Both
  /// tournament routes are readable by the people assigned to a competition as
  /// well as by its organizer, so they sit under `/organizer` by subject, not
  /// as a claim about who may open them — the server decides that.
  static const organizer = '/organizer';
  static String tournamentStaff(String id) => '/organizer/tournaments/$id/staff';
  static String tournamentPlayers(String id) =>
      '/organizer/tournaments/$id/players';
  static const myAssignments = '/my-assignments';

  static const rules = '/rules';
  static const ruleBuilder = '/rules/new';
  static const tools = '/tools';
}

final _rootKey = GlobalKey<NavigatorState>(debugLabel: 'root');
final _shellKey = GlobalKey<NavigatorState>(debugLabel: 'shell');

final routerProvider = Provider<GoRouter>((ref) {
  // Rebuilding the router on every auth change would lose navigation state, so
  // the redirect reads a listenable instead.
  final refresh = _AuthRefresh(ref);
  ref.onDispose(refresh.dispose);

  return GoRouter(
    navigatorKey: _rootKey,
    initialLocation: Routes.home,
    refreshListenable: refresh,
    redirect: (context, state) {
      final auth = ref.read(authControllerProvider);
      // Never redirect while the stored session is still being checked.
      if (auth.isRestoring) return null;

      final loc = state.matchedLocation;
      final onAuthScreen = loc == Routes.login ||
          loc == Routes.register ||
          loc == Routes.forgotPassword;

      if (auth.isSignedIn && onAuthScreen) return Routes.home;

      if (!auth.isSignedIn && _requiresSignIn(loc)) {
        // Come back here once they are in.
        return '${Routes.login}?next=${Uri.encodeComponent(state.uri.toString())}';
      }

      // Admin is a whole section, not one screen.
      if (loc.startsWith(Routes.admin) && !auth.isAdmin) return Routes.home;

      final needed = _requiredCapability(loc);
      if (needed != null && !auth.can(needed)) return Routes.home;

      return null;
    },
    errorBuilder: (context, state) => Scaffold(
      appBar: AppBar(title: const Text('Not found')),
      body: Center(
        child: EmptyState(
          icon: Icons.explore_off_outlined,
          title: 'That page does not exist',
          message: state.uri.toString(),
          actionLabel: 'Go home',
          onAction: () => context.go(Routes.home),
        ),
      ),
    ),
    routes: [
      GoRoute(
        path: Routes.login,
        builder: (context, state) =>
            LoginScreen(next: state.uri.queryParameters['next']),
      ),
      GoRoute(
        path: Routes.register,
        builder: (context, state) => const RegisterScreen(),
      ),
      GoRoute(
        path: Routes.forgotPassword,
        builder: (context, state) => const ForgotPasswordScreen(),
      ),

      // The five bottom-nav branches keep their own navigation stacks.
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => MainShell(shell: shell),
        branches: [
          StatefulShellBranch(
            navigatorKey: _shellKey,
            routes: [
              GoRoute(
                path: Routes.home,
                builder: (context, state) => const HomeScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: Routes.matches,
                builder: (context, state) => const MatchesListScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: Routes.tournaments,
                builder: (context, state) => const TournamentsListScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: Routes.community,
                builder: (context, state) => const NetworkScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: Routes.more,
                builder: (context, state) => const MoreScreen(),
              ),
            ],
          ),
        ],
      ),

      // Everything else pushes over the shell.
      GoRoute(
        path: Routes.newMatch,
        builder: (context, state) => const CreateMatchScreen(),
      ),
      GoRoute(
        path: '/matches/:id',
        builder: (context, state) =>
            MatchScreen(matchId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: Routes.teams,
        builder: (context, state) => const TeamsListScreen(),
      ),
      GoRoute(
        path: '/teams/:id',
        builder: (context, state) =>
            TeamScreen(teamId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: Routes.players,
        builder: (context, state) => const PlayersListScreen(),
      ),
      GoRoute(
        path: Routes.compare,
        builder: (context, state) => const CompareScreen(),
      ),
      GoRoute(
        path: '/players/:id',
        builder: (context, state) =>
            PlayerScreen(playerId: state.pathParameters['id']!),
        routes: [
          GoRoute(
            path: 'career',
            builder: (context, state) =>
                CareerScreen(playerId: state.pathParameters['id']!),
          ),
        ],
      ),
      GoRoute(
        path: '/tournaments/:id',
        builder: (context, state) =>
            TournamentScreen(tournamentId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: Routes.leaderboards,
        builder: (context, state) => const LeaderboardsScreen(),
      ),
      GoRoute(
        path: Routes.highlights,
        builder: (context, state) => const HighlightsScreen(),
      ),
      GoRoute(
        path: Routes.venues,
        builder: (context, state) => const VenuesScreen(),
      ),
      GoRoute(
        path: Routes.network,
        builder: (context, state) => const NetworkScreen(standalone: true),
      ),
      GoRoute(
        path: Routes.feed,
        builder: (context, state) => const FeedScreen(),
      ),
      GoRoute(
        path: Routes.messages,
        builder: (context, state) => const MessagesScreen(),
      ),
      GoRoute(
        path: '/messages/:id',
        builder: (context, state) =>
            ThreadScreen(otherId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: Routes.lookingFor,
        builder: (context, state) => const LookingForScreen(),
      ),
      GoRoute(
        path: Routes.search,
        builder: (context, state) =>
            SearchScreen(initialQuery: state.uri.queryParameters['q']),
      ),
      GoRoute(
        path: Routes.notifications,
        builder: (context, state) => const NotificationsScreen(),
      ),
      GoRoute(
        path: Routes.settings,
        builder: (context, state) => const SettingsScreen(),
      ),
      GoRoute(
        path: Routes.account,
        builder: (context, state) => const AccountScreen(),
      ),
      GoRoute(
        path: Routes.profileDetails,
        builder: (context, state) => const ProfileDetailsScreen(),
      ),
      GoRoute(
        path: Routes.admin,
        builder: (context, state) => const AdminScreen(),
      ),
      GoRoute(
        path: Routes.adminOrganizers,
        builder: (context, state) => const OrganizersScreen(),
      ),
      GoRoute(
        path: Routes.adminAreas,
        builder: (context, state) => const AreasScreen(),
      ),
      GoRoute(
        path: Routes.adminAudit,
        builder: (context, state) => const AuditScreen(),
      ),
      GoRoute(
        path: Routes.organizer,
        builder: (context, state) => const OrganizerDashboardScreen(),
      ),
      GoRoute(
        path: '/organizer/tournaments/:id/staff',
        builder: (context, state) =>
            TournamentStaffScreen(tournamentId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/organizer/tournaments/:id/players',
        builder: (context, state) =>
            TournamentPlayersScreen(tournamentId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: Routes.myAssignments,
        builder: (context, state) => const MyAssignmentsScreen(),
      ),
      GoRoute(
        path: Routes.rules,
        builder: (context, state) => const RuleTemplatesScreen(),
      ),
      GoRoute(
        path: Routes.ruleBuilder,
        builder: (context, state) =>
            RuleBuilderScreen(templateId: state.uri.queryParameters['from']),
      ),
      GoRoute(
        path: Routes.tools,
        builder: (context, state) => const ToolsScreen(),
      ),
    ],
  );
});

/// Open a link the server generated, in the app.
///
/// Notifications and the activity feed carry links in the website's own
/// shapes: the hash routes the web app uses (`#/match/12`, `#/messages/3`) and
/// the short public paths (`/m/12`, `/t/4`). Both have to map onto app routes,
/// or every notification becomes a dead tap.
///
/// Returns false when the link points somewhere the app has no screen for, so
/// the caller can decide whether to show anything at all.
bool openServerLink(BuildContext context, String link) {
  var path = link.trim();
  if (path.isEmpty) return false;
  // The web client routes on the fragment; strip it and treat the rest as a path.
  if (path.startsWith('#')) path = path.substring(1);
  if (!path.startsWith('/')) path = '/$path';

  String? idAfter(String prefix) =>
      path.startsWith(prefix) && path.length > prefix.length
          ? path.substring(prefix.length).split('/').first
          : null;

  final match = idAfter('/match/') ?? idAfter('/m/');
  if (match != null) {
    context.push(Routes.match(match));
    return true;
  }
  final tournament = idAfter('/tournament/') ?? idAfter('/t/');
  if (tournament != null) {
    context.push(Routes.tournament(tournament));
    return true;
  }
  final thread = idAfter('/messages/');
  if (thread != null) {
    context.push(Routes.thread(thread));
    return true;
  }
  final team = idAfter('/team/');
  if (team != null) {
    context.push(Routes.team(team));
    return true;
  }
  final player = idAfter('/player/');
  if (player != null) {
    context.push(Routes.player(player));
    return true;
  }

  // Whole-screen destinations, including `#/u/{id}` for a member the app has
  // no detail page for — the directory is the closest honest landing spot.
  const screens = <String, String>{
    '/account': Routes.account,
    '/messages': Routes.messages,
    '/notifications': Routes.notifications,
    '/matches': Routes.matches,
    '/feed': Routes.feed,
    '/network': Routes.network,
    '/teams': Routes.teams,
    '/players': Routes.players,
    '/tournaments': Routes.tournaments,
    '/leaderboards': Routes.leaderboards,
    '/highlights': Routes.highlights,
    '/venues': Routes.venues,
    '/looking-for': Routes.lookingFor,
    '/settings': Routes.settings,
    '/admin': Routes.admin,
    '/rules': Routes.rules,
  };
  final exact = screens[path];
  if (exact != null) {
    context.push(exact);
    return true;
  }
  if (path.startsWith('/u/')) {
    context.push(Routes.network);
    return true;
  }
  return false;
}

/// Routes that make no sense signed out. Everything else is browsable as a
/// guest, matching the website, where public pages need no account.
const _protected = <String>[
  Routes.newMatch,
  Routes.notifications,
  Routes.messages,
  Routes.lookingFor,
  Routes.feed,
  Routes.admin,
  // "Which competitions am I on" is answered from the token; signed out it can
  // only ever be an empty list pretending to be an answer.
  Routes.myAssignments,
  Routes.account,
  Routes.profileDetails,
  Routes.ruleBuilder,
];

bool _requiresSignIn(String location) {
  for (final p in _protected) {
    if (location == p || location.startsWith('$p/')) return true;
  }
  return false;
}

/// Routes that need a capability, not merely an account.
///
/// This is a convenience so somebody typing a URL lands somewhere sensible
/// instead of on a locked screen. It is NOT the security boundary: the server
/// checks every one of these again, and checks ownership on top, because a
/// client can always be modified.
const _capabilityRoutes = <String, String>{
  Routes.newMatch: Caps.createMatch,
  Routes.ruleBuilder: Caps.manageRules,
};

/// The capability a route needs, or null if signing in is enough.
String? _requiredCapability(String location) {
  for (final entry in _capabilityRoutes.entries) {
    if (location == entry.key || location.startsWith('${entry.key}/')) {
      return entry.value;
    }
  }
  return null;
}

/// Bridges Riverpod auth changes into go_router's refresh mechanism.
class _AuthRefresh extends ChangeNotifier {
  late final ProviderSubscription<AuthState> _sub;

  _AuthRefresh(Ref ref) {
    _sub = ref.listen<AuthState>(
      authControllerProvider,
      (previous, next) {
        if (previous?.status != next.status) notifyListeners();
      },
    );
  }

  @override
  void dispose() {
    _sub.close();
    super.dispose();
  }
}
