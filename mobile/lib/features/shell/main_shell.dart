import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/user.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';

/// The tab frame, with a centre button for starting a match.
///
/// The button only appears for an account that may actually create one. A
/// guest is a viewer, so offering it would only lead to a locked screen.
class MainShell extends ConsumerWidget {
  final StatefulNavigationShell shell;

  const MainShell({super.key, required this.shell});

  void _go(BuildContext context, int index) {
    // Tapping the tab you are already on pops that branch back to its root.
    shell.goBranch(index, initialLocation: index == shell.currentIndex);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final canScore = ref.watch(authControllerProvider).can(Caps.createMatch);

    return Scaffold(
      body: shell,
      floatingActionButton: canScore
          ? FloatingActionButton(
              onPressed: () => context.push(Routes.newMatch),
              tooltip: 'New match',
              child: const Icon(Icons.add, size: 28),
            )
          : null,
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
      bottomNavigationBar: _ShellBar(
        currentIndex: shell.currentIndex,
        onTap: (i) => _go(context, i),
        // With no button docked there is no notch to leave room for.
        reserveNotch: canScore,
      ),
    );
  }
}

class _ShellBar extends StatelessWidget {
  final int currentIndex;
  final ValueChanged<int> onTap;
  final bool reserveNotch;

  const _ShellBar({
    required this.currentIndex,
    required this.onTap,
    required this.reserveNotch,
  });

  static const _items = <({IconData icon, IconData active, String label})>[
    (icon: Icons.home_outlined, active: Icons.home, label: 'Home'),
    (
      icon: Icons.sports_cricket_outlined,
      active: Icons.sports_cricket,
      label: 'Matches'
    ),
    (icon: Icons.emoji_events_outlined, active: Icons.emoji_events, label: 'Cups'),
    (icon: Icons.groups_outlined, active: Icons.groups, label: 'Social'),
    (icon: Icons.more_horiz, active: Icons.more_horiz, label: 'More'),
  ];

  Widget _item(int i) => _NavItem(
        item: _items[i],
        selected: i == currentIndex,
        onTap: () => onTap(i),
      );

  @override
  Widget build(BuildContext context) {
    return BottomAppBar(
      color: context.scheme.surface,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      height: 62,
      padding: EdgeInsets.zero,
      shape: reserveNotch ? const CircularNotchedRectangle() : null,
      notchMargin: 7,
      child: Container(
        decoration: BoxDecoration(
          border: Border(top: BorderSide(color: context.cric.line)),
        ),
        child: reserveNotch
            // The gap for the docked button has to sit dead centre, or the
            // button covers whichever item it lands on. Five equal items
            // cannot split evenly around a centre gap, so the bar becomes two
            // equal halves: two items on the left, three narrower on the right.
            ? Row(
                children: [
                  Expanded(
                    child: Row(
                      children: [
                        for (var i = 0; i < 2; i++) Expanded(child: _item(i)),
                      ],
                    ),
                  ),
                  const SizedBox(width: 64),
                  Expanded(
                    child: Row(
                      children: [
                        for (var i = 2; i < _items.length; i++)
                          Expanded(child: _item(i)),
                      ],
                    ),
                  ),
                ],
              )
            : Row(
                children: [
                  for (var i = 0; i < _items.length; i++)
                    Expanded(child: _item(i)),
                ],
              ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  final ({IconData icon, IconData active, String label}) item;
  final bool selected;
  final VoidCallback onTap;

  const _NavItem({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final color = selected ? context.scheme.primary : context.cric.faint;
    return InkWell(
      onTap: onTap,
      child: Semantics(
        selected: selected,
        button: true,
        label: item.label,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(selected ? item.active : item.icon, size: 22, color: color),
            const SizedBox(height: 2),
            Text(
              item.label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: context.texts.labelSmall?.copyWith(
                color: color,
                fontSize: 10.5,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
