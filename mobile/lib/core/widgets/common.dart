import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api/api_exception.dart';
import '../theme/app_theme.dart';
import '../utils/formatters.dart';

/// A bordered surface — the app's basic building block, matching the website's
/// card treatment.
class CnCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;
  final Color? color;
  final Color? borderColor;

  const CnCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.onTap,
    this.color,
    this.borderColor,
  });

  @override
  Widget build(BuildContext context) {
    final body = Padding(padding: padding, child: child);
    return Material(
      color: color ?? context.scheme.surface,
      borderRadius: BorderRadius.circular(16),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: borderColor ?? context.cric.line),
          ),
          child: body,
        ),
      ),
    );
  }
}

/// A heading above a group of content, with an optional trailing action.
class SectionHeader extends StatelessWidget {
  final String title;
  final String? subtitle;
  final Widget? trailing;
  final EdgeInsetsGeometry padding;

  const SectionHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.trailing,
    this.padding = const EdgeInsets.fromLTRB(4, 20, 4, 10),
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: padding,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: context.texts.titleMedium),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  Text(subtitle!, style: context.texts.bodySmall),
                ],
              ],
            ),
          ),
          ?trailing,
        ],
      ),
    );
  }
}

/// Initials on a generated colour, or a network photo when one exists.
class CnAvatar extends StatelessWidget {
  final String name;
  final String? imageUrl;
  final double size;

  const CnAvatar({
    super.key,
    required this.name,
    this.imageUrl,
    this.size = 42,
  });

  @override
  Widget build(BuildContext context) {
    final hue = Fmt.hashHue(name).toDouble();
    final a = HSLColor.fromAHSL(1, hue, 0.55, 0.48).toColor();
    final b = HSLColor.fromAHSL(1, (hue + 38) % 360, 0.55, 0.38).toColor();

    return Container(
      width: size,
      height: size,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          colors: [a, b],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: imageUrl == null
          ? _initials(context)
          : Image.network(
              imageUrl!,
              fit: BoxFit.cover,
              width: size,
              height: size,
              // A missing photo is normal, not an error — fall back quietly.
              errorBuilder: (_, _, _) => _initials(context),
              loadingBuilder: (_, child, progress) =>
                  progress == null ? child : _initials(context),
            ),
    );
  }

  Widget _initials(BuildContext context) => Center(
        child: Text(
          Fmt.initials(name),
          style: TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w700,
            fontSize: size * 0.38,
            letterSpacing: 0.2,
          ),
        ),
      );
}

/// A small coloured label: LIVE, DONE, a role, a status.
class CnBadge extends StatelessWidget {
  final String text;
  final Color? color;
  final IconData? icon;
  final bool filled;

  const CnBadge({
    super.key,
    required this.text,
    this.color,
    this.icon,
    this.filled = false,
  });

  @override
  Widget build(BuildContext context) {
    final c = color ?? context.scheme.primary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: filled ? c : c.withValues(alpha: 0.13),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: c.withValues(alpha: filled ? 1 : 0.28)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 12, color: filled ? Colors.white : c),
            const SizedBox(width: 4),
          ],
          Text(
            text,
            style: context.texts.labelSmall?.copyWith(
              color: filled ? Colors.white : c,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.3,
            ),
          ),
        ],
      ),
    );
  }
}

/// The pulsing dot that marks a live match.
class LiveDot extends StatefulWidget {
  final double size;
  final Color? color;

  const LiveDot({super.key, this.size = 8, this.color});

  @override
  State<LiveDot> createState() => _LiveDotState();
}

class _LiveDotState extends State<LiveDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1100),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.color ?? context.cric.wicket;
    return FadeTransition(
      opacity: Tween<double>(begin: 0.35, end: 1).animate(_c),
      child: Container(
        width: widget.size,
        height: widget.size,
        decoration: BoxDecoration(color: c, shape: BoxShape.circle),
      ),
    );
  }
}

/// One number with a caption — the KPI unit used across dashboards.
class StatTile extends StatelessWidget {
  final String label;
  final String value;
  final Color? valueColor;
  final IconData? icon;

  /// Numbers fit on one line; a ground or a team name does not. Grids that
  /// carry text rather than figures pass 2 so the value wraps instead of
  /// ellipsising away the part that identifies it.
  final int valueMaxLines;

  const StatTile({
    super.key,
    required this.label,
    required this.value,
    this.valueColor,
    this.icon,
    this.valueMaxLines = 1,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            if (icon != null) ...[
              Icon(icon, size: 13, color: context.cric.faint),
              const SizedBox(width: 4),
            ],
            Flexible(
              child: Text(
                label.toUpperCase(),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: context.texts.labelSmall?.copyWith(
                  color: context.cric.faint,
                  letterSpacing: 0.6,
                  fontWeight: FontWeight.w600,
                  fontSize: 10,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 3),
        Text(
          value,
          maxLines: valueMaxLines,
          overflow: TextOverflow.ellipsis,
          style: context.texts.titleMedium?.copyWith(
            color: valueColor,
            // Tabular figures line numbers up in a column; on a wrapping text
            // value they only add odd spacing.
            fontFeatures: valueMaxLines == 1
                ? const [FontFeature.tabularFigures()]
                : null,
          ),
        ),
      ],
    );
  }
}

/// A wrapping grid of [StatTile]s — batting cards, bowling cards, records.
class StatGrid extends StatelessWidget {
  final List<({String label, String value})> stats;
  final int columns;

  /// See [StatTile.valueMaxLines] — pass 2 for a grid of names.
  final int valueMaxLines;

  const StatGrid({
    super.key,
    required this.stats,
    this.columns = 4,
    this.valueMaxLines = 1,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        const gap = 12.0;
        final width =
            (constraints.maxWidth - gap * (columns - 1)) / columns;
        return Wrap(
          spacing: gap,
          runSpacing: 16,
          children: [
            for (final s in stats)
              SizedBox(
                width: width,
                child: StatTile(
                  label: s.label,
                  value: s.value,
                  valueMaxLines: valueMaxLines,
                ),
              ),
          ],
        );
      },
    );
  }
}

/// Nothing to show yet, with an optional call to action.
class EmptyState extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final EdgeInsetsGeometry padding;

  const EmptyState({
    super.key,
    this.icon = Icons.inbox_outlined,
    required this.title,
    this.message,
    this.actionLabel,
    this.onAction,
    this.padding = const EdgeInsets.symmetric(horizontal: 24, vertical: 40),
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: padding,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: context.cric.surfaceVariant,
              shape: BoxShape.circle,
            ),
            child: Icon(icon, size: 28, color: context.cric.faint),
          ),
          const SizedBox(height: 14),
          Text(
            title,
            textAlign: TextAlign.center,
            style: context.texts.titleSmall,
          ),
          if (message != null) ...[
            const SizedBox(height: 6),
            Text(
              message!,
              textAlign: TextAlign.center,
              style: context.texts.bodySmall,
            ),
          ],
          if (actionLabel != null && onAction != null) ...[
            const SizedBox(height: 16),
            OutlinedButton(onPressed: onAction, child: Text(actionLabel!)),
          ],
        ],
      ),
    );
  }
}

/// A failed load, phrased for a person and offering a retry.
class ErrorState extends StatelessWidget {
  final Object error;
  final VoidCallback? onRetry;
  final EdgeInsetsGeometry padding;

  const ErrorState({
    super.key,
    required this.error,
    this.onRetry,
    this.padding = const EdgeInsets.symmetric(horizontal: 24, vertical: 36),
  });

  @override
  Widget build(BuildContext context) {
    final api = error is ApiException ? error as ApiException : null;
    final message = api?.message ?? 'Something went wrong.';
    final icon = api == null
        ? Icons.error_outline
        : api.isNetwork
            ? Icons.wifi_off_rounded
            : api.isForbidden
                ? Icons.lock_outline
                : Icons.error_outline;

    return Padding(
      padding: padding,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 30, color: context.cric.wicket),
          const SizedBox(height: 12),
          Text(
            message,
            textAlign: TextAlign.center,
            style: context.texts.bodyMedium,
          ),
          if (api?.requestId != null) ...[
            const SizedBox(height: 6),
            Text(
              'Reference ${api!.requestId!.length > 8 ? api.requestId!.substring(0, 8) : api.requestId!}',
              style: context.texts.labelSmall?.copyWith(
                color: context.cric.faint,
              ),
            ),
          ],
          if (onRetry != null) ...[
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh, size: 18),
              label: const Text('Try again'),
            ),
          ],
        ],
      ),
    );
  }
}

/// A shimmering placeholder block for loading lists.
class SkeletonBox extends StatefulWidget {
  final double height;
  final double? width;
  final double radius;

  const SkeletonBox({
    super.key,
    this.height = 16,
    this.width,
    this.radius = 8,
  });

  @override
  State<SkeletonBox> createState() => _SkeletonBoxState();
}

class _SkeletonBoxState extends State<SkeletonBox>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1200),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: Tween<double>(begin: 0.45, end: 0.95).animate(_c),
      child: Container(
        height: widget.height,
        width: widget.width,
        decoration: BoxDecoration(
          color: context.cric.surfaceVariant,
          borderRadius: BorderRadius.circular(widget.radius),
        ),
      ),
    );
  }
}

/// A few skeleton rows, sized like the list they stand in for.
class ListSkeleton extends StatelessWidget {
  final int rows;

  const ListSkeleton({super.key, this.rows = 5});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (var i = 0; i < rows; i++)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: CnCard(
              child: Row(
                children: [
                  const SkeletonBox(height: 40, width: 40, radius: 20),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SkeletonBox(width: 140 + (i % 3) * 30.0),
                        const SizedBox(height: 8),
                        const SkeletonBox(height: 12, width: 90),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}

/// A locked panel shown where a capability or a session is missing.
class GateCard extends StatelessWidget {
  final String what;
  final bool signedIn;
  final String? role;
  final VoidCallback? onSignIn;
  final VoidCallback? onRegister;

  const GateCard({
    super.key,
    required this.what,
    required this.signedIn,
    this.role,
    this.onSignIn,
    this.onRegister,
  });

  @override
  Widget build(BuildContext context) {
    if (signedIn) {
      return CnCard(
        child: Column(
          children: [
            Icon(Icons.lock_outline, size: 28, color: context.cric.amber),
            const SizedBox(height: 12),
            Text(
              'Your role cannot $what',
              textAlign: TextAlign.center,
              style: context.texts.titleSmall,
            ),
            const SizedBox(height: 6),
            Text(
              role == null
                  ? 'Ask an admin to upgrade your account.'
                  : 'You are signed in as ${role!.replaceAll('_', ' ')}. Ask an admin to upgrade your account.',
              textAlign: TextAlign.center,
              style: context.texts.bodySmall,
            ),
          ],
        ),
      );
    }
    return CnCard(
      child: Column(
        children: [
          Icon(Icons.lock_outline, size: 28, color: context.cric.faint),
          const SizedBox(height: 12),
          Text('Sign in to $what',
              textAlign: TextAlign.center, style: context.texts.titleSmall),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: ElevatedButton(
                  onPressed: onSignIn,
                  child: const Text('Sign in'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton(
                  onPressed: onRegister,
                  child: const Text('Create account'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// A pill-style single-choice selector, the website's `segment` control.
class CnSegmented<T> extends StatelessWidget {
  final List<({T value, String label})> options;
  final T selected;
  final ValueChanged<T> onChanged;

  const CnSegmented({
    super.key,
    required this.options,
    required this.selected,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: context.cric.surfaceVariant,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: context.cric.line),
      ),
      child: Row(
        children: [
          for (final o in options)
            Expanded(
              child: GestureDetector(
                onTap: () => onChanged(o.value),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 160),
                  padding: const EdgeInsets.symmetric(vertical: 9),
                  decoration: BoxDecoration(
                    color: o.value == selected
                        ? context.scheme.surface
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(9),
                    border: Border.all(
                      color: o.value == selected
                          ? context.cric.line
                          : Colors.transparent,
                    ),
                  ),
                  child: Text(
                    o.label,
                    textAlign: TextAlign.center,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: context.texts.labelLarge?.copyWith(
                      color: o.value == selected
                          ? context.scheme.primary
                          : context.cric.muted,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// A horizontally scrolling row of filter chips.
class ChipFilterBar<T> extends StatelessWidget {
  final List<({T value, String label, int? count})> options;
  final T selected;
  final ValueChanged<T> onChanged;
  final EdgeInsetsGeometry padding;

  const ChipFilterBar({
    super.key,
    required this.options,
    required this.selected,
    required this.onChanged,
    this.padding = const EdgeInsets.symmetric(horizontal: 16),
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: padding,
      child: Row(
        children: [
          for (final o in options)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: ChoiceChip(
                selected: o.value == selected,
                onSelected: (_) => onChanged(o.value),
                showCheckmark: false,
                label: Text(
                  o.count == null ? o.label : '${o.label} ${o.count}',
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// A search field with a clear button and debounce handled by the caller.
class SearchField extends StatelessWidget {
  final TextEditingController controller;
  final String hint;
  final ValueChanged<String>? onChanged;
  final VoidCallback? onClear;
  final bool autofocus;

  const SearchField({
    super.key,
    required this.controller,
    this.hint = 'Search',
    this.onChanged,
    this.onClear,
    this.autofocus = false,
  });

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      onChanged: onChanged,
      autofocus: autofocus,
      textInputAction: TextInputAction.search,
      decoration: InputDecoration(
        hintText: hint,
        prefixIcon: const Icon(Icons.search, size: 20),
        suffixIcon: ValueListenableBuilder<TextEditingValue>(
          valueListenable: controller,
          builder: (context, value, _) => value.text.isEmpty
              ? const SizedBox.shrink()
              : IconButton(
                  icon: const Icon(Icons.close, size: 18),
                  onPressed: () {
                    controller.clear();
                    onChanged?.call('');
                    onClear?.call();
                  },
                ),
        ),
      ),
    );
  }
}

/// Toast helpers so every screen reports the same way.
extension SnackX on BuildContext {
  void toast(String message) {
    ScaffoldMessenger.of(this)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  /// Shows an error, using the API's own sentence when there is one.
  void toastError(Object error) {
    final message =
        error is ApiException ? error.message : 'Something went wrong.';
    ScaffoldMessenger.of(this)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(message),
          backgroundColor: cric.wicket,
          behavior: SnackBarBehavior.floating,
        ),
      );
  }

  void copyToClipboard(String text, {String? message}) {
    Clipboard.setData(ClipboardData(text: text));
    toast(message ?? 'Copied');
  }
}

/// Ask before doing something irreversible.
Future<bool> confirmDialog(
  BuildContext context, {
  required String title,
  required String message,
  String confirmLabel = 'Delete',
  String cancelLabel = 'Cancel',
  bool destructive = true,
}) async {
  final ok = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: Text(message),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: Text(cancelLabel),
        ),
        TextButton(
          onPressed: () => Navigator.pop(context, true),
          style: TextButton.styleFrom(
            foregroundColor:
                destructive ? context.cric.wicket : context.scheme.primary,
          ),
          child: Text(confirmLabel),
        ),
      ],
    ),
  );
  return ok ?? false;
}

/// A single-field prompt, for names and short text.
Future<String?> promptDialog(
  BuildContext context, {
  required String title,
  String? hint,
  String initial = '',
  String confirmLabel = 'Save',
  TextInputType? keyboardType,
  int? maxLength,
}) async {
  final controller = TextEditingController(text: initial);
  final value = await showDialog<String>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: TextField(
        controller: controller,
        autofocus: true,
        keyboardType: keyboardType,
        maxLength: maxLength,
        decoration: InputDecoration(hintText: hint),
        onSubmitted: (v) => Navigator.pop(context, v.trim()),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        TextButton(
          onPressed: () => Navigator.pop(context, controller.text.trim()),
          child: Text(confirmLabel),
        ),
      ],
    ),
  );
  controller.dispose();
  final trimmed = value?.trim();
  return (trimmed == null || trimmed.isEmpty) ? null : trimmed;
}
