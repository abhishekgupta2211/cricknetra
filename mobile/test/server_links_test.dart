import 'package:cricnetra/core/router/app_router.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

/// Notifications and the activity feed carry links the server writes, in the
/// website's own shapes. Every one has to reach a screen, or the notification
/// is a dead tap — which is exactly what it used to be: the app only handled
/// `/m/` and `/t/` while the server mostly emits `#/match/` and friends.
///
/// The shapes below were taken from the backend, not invented:
///   services/notification_generators.py   #/match/{id}
///   services/match_official_service.py    #/match/{id}
///   services/messaging_service.py         #/messages/{id}
///   services/role_service.py              #/account
///   services/social_service.py            #/u/{id}
///   api/v1/routes/teams.py                #/team/{id}
///   api/v1/routes/matches.py              /m/{id}
///   api/v1/routes/tournaments.py          /t/{id}
void main() {
  /// Opens [link] in a throwaway router and returns where it landed, or null
  /// when the app declined to route it.
  Future<String?> route(WidgetTester tester, String link) async {
    String? landed;
    late BuildContext ctx;

    Widget page(String name) => Builder(builder: (context) {
          landed = name;
          return Scaffold(body: Text(name));
        });

    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder: (context, state) {
            ctx = context;
            return const Scaffold(body: Text('home'));
          },
        ),
        GoRoute(path: '/matches', builder: (c, s) => page('matches')),
        GoRoute(path: '/matches/:id', builder: (c, s) => page('match/${s.pathParameters['id']}')),
        GoRoute(path: '/teams/:id', builder: (c, s) => page('team/${s.pathParameters['id']}')),
        GoRoute(path: '/players/:id', builder: (c, s) => page('player/${s.pathParameters['id']}')),
        GoRoute(path: '/tournaments/:id', builder: (c, s) => page('tournament/${s.pathParameters['id']}')),
        GoRoute(path: '/messages', builder: (c, s) => page('messages')),
        GoRoute(path: '/messages/:id', builder: (c, s) => page('thread/${s.pathParameters['id']}')),
        GoRoute(path: '/account', builder: (c, s) => page('account')),
        GoRoute(path: '/network', builder: (c, s) => page('network')),
        GoRoute(path: '/notifications', builder: (c, s) => page('notifications')),
        GoRoute(path: '/feed', builder: (c, s) => page('feed')),
        GoRoute(path: '/teams', builder: (c, s) => page('teams')),
        GoRoute(path: '/players', builder: (c, s) => page('players')),
        GoRoute(path: '/tournaments', builder: (c, s) => page('tournaments')),
        GoRoute(path: '/leaderboards', builder: (c, s) => page('leaderboards')),
        GoRoute(path: '/highlights', builder: (c, s) => page('highlights')),
        GoRoute(path: '/venues', builder: (c, s) => page('venues')),
        GoRoute(path: '/looking-for', builder: (c, s) => page('looking-for')),
        GoRoute(path: '/settings', builder: (c, s) => page('settings')),
        GoRoute(path: '/admin', builder: (c, s) => page('admin')),
        GoRoute(path: '/rules', builder: (c, s) => page('rules')),
      ],
    );

    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    await tester.pumpAndSettle();

    landed = null;
    final handled = openServerLink(ctx, link);
    await tester.pumpAndSettle();
    return handled ? landed : null;
  }

  group('links the server actually sends', () {
    testWidgets('a wicket or milestone notification opens the match',
        (tester) async {
      expect(await route(tester, '#/match/12'), 'match/12');
    });

    testWidgets('the short public match link opens the match', (tester) async {
      expect(await route(tester, '/m/12'), 'match/12');
    });

    testWidgets('the short public tournament link opens the tournament',
        (tester) async {
      expect(await route(tester, '/t/4'), 'tournament/4');
    });

    testWidgets('a new message opens that thread', (tester) async {
      expect(await route(tester, '#/messages/7'), 'thread/7');
    });

    testWidgets('a role approval opens the account screen', (tester) async {
      expect(await route(tester, '#/account'), 'account');
    });

    testWidgets('a new follower opens the directory', (tester) async {
      // There is no member detail screen, so the directory is the closest
      // honest landing spot rather than a dead tap.
      expect(await route(tester, '#/u/9'), 'network');
    });

    testWidgets('a team activity opens the team', (tester) async {
      expect(await route(tester, '#/team/3'), 'team/3');
    });
  });

  group('shapes that must not collide', () {
    testWidgets('/messages is the list, not a thread', (tester) async {
      expect(await route(tester, '#/messages'), 'messages');
    });

    testWidgets('/teams is the list, not team "s"', (tester) async {
      expect(await route(tester, '#/teams'), 'teams');
    });

    testWidgets('/tournaments is the list, not tournament "s"',
        (tester) async {
      expect(await route(tester, '#/tournaments'), 'tournaments');
    });

    testWidgets('a message thread is not mistaken for a short match link',
        (tester) async {
      // `/m/` is a prefix of `/messages/` if the trailing slash is dropped.
      expect(await route(tester, '/messages/7'), 'thread/7');
    });
  });

  group('shapes that are close but not quite', () {
    testWidgets('a trailing segment after the id is ignored', (tester) async {
      expect(await route(tester, '#/match/12/scorecard'), 'match/12');
    });

    testWidgets('a link without its leading slash still routes',
        (tester) async {
      expect(await route(tester, 'm/12'), 'match/12');
    });

    testWidgets('the matches list is reachable', (tester) async {
      expect(await route(tester, '#/matches'), 'matches');
    });

    testWidgets('an unknown destination is declined rather than mis-routed',
        (tester) async {
      expect(await route(tester, '#/something-else'), isNull);
    });

    testWidgets('an id-less prefix is declined', (tester) async {
      // `#/match/` with nothing after it should not open a blank match.
      expect(await route(tester, '#/match/'), isNull);
    });

    testWidgets('an empty link is declined', (tester) async {
      expect(await route(tester, ''), isNull);
      expect(await route(tester, '   '), isNull);
    });
  });
}
