import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/api/api_config.dart';
import '../../../core/auth/auth_provider.dart';
import '../../../core/models/match.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/common.dart';
import '../match_providers.dart';

/// Dropped catches, runs saved and misfields — the fielding side's ledger.
class FieldingLog extends ConsumerStatefulWidget {
  final String matchId;
  final MatchState match;
  final bool canScore;

  const FieldingLog({
    super.key,
    required this.matchId,
    required this.match,
    required this.canScore,
  });

  @override
  ConsumerState<FieldingLog> createState() => _FieldingLogState();
}

class _FieldingLogState extends ConsumerState<FieldingLog> {
  /// Owned by Autocomplete's own field, captured once when it first builds.
  TextEditingController? _fielderField;
  final _runs = TextEditingController(text: '0');
  String _kind = 'drop';
  bool _busy = false;

  @override
  void dispose() {
    _runs.dispose();
    super.dispose();
  }

  /// Everyone who could be fielding, so the scorer can pick a name quickly.
  List<String> get _names => fieldingSideNames(widget.match);

  Future<void> _add() async {
    final fielder = _fielderField?.text.trim() ?? '';
    if (fielder.isEmpty) {
      context.toast('Name the fielder');
      return;
    }
    setState(() => _busy = true);
    try {
      await ref.read(apiProvider).addFieldingEvent(
            widget.matchId,
            fielder: fielder,
            kind: _kind,
            runs: int.tryParse(_runs.text.trim()) ?? 0,
            innings: widget.match.currentInnings,
          );
      _fielderField?.clear();
      _runs.text = '0';
      ref.invalidate(fieldingProvider(widget.matchId));
    } catch (e) {
      if (mounted) context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final events = ref.watch(fieldingProvider(widget.matchId));

    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(Icons.shield_outlined, size: 17, color: context.cric.muted),
              const SizedBox(width: 8),
              Text('Fielding log', style: context.texts.titleSmall),
            ],
          ),
          if (widget.canScore) ...[
            const SizedBox(height: 12),
            Autocomplete<String>(
              optionsBuilder: (value) {
                if (value.text.isEmpty) return _names.take(8);
                return _names.where(
                  (n) => n.toLowerCase().contains(value.text.toLowerCase()),
                );
              },
              fieldViewBuilder: (context, controller, focus, onSubmit) {
                // Hold the field's own controller rather than mirroring it
                // through a listener, which would stack up on every rebuild.
                _fielderField = controller;
                return TextField(
                  controller: controller,
                  focusNode: focus,
                  decoration: const InputDecoration(
                    labelText: 'Fielder',
                    isDense: true,
                  ),
                );
              },
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  flex: 3,
                  child: DropdownButtonFormField<String>(
                    initialValue: _kind,
                    isExpanded: true,
                    decoration: const InputDecoration(isDense: true),
                    items: [
                      for (final k in FieldingEvent.kinds)
                        DropdownMenuItem(
                          value: k,
                          child: Text(FieldingEvent.kindLabel(k)),
                        ),
                    ],
                    onChanged: (v) => setState(() => _kind = v ?? _kind),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: TextField(
                    controller: _runs,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Runs',
                      isDense: true,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                ElevatedButton(
                  onPressed: _busy ? null : _add,
                  child: const Text('Log'),
                ),
              ],
            ),
          ],
          const SizedBox(height: 12),
          events.when(
            loading: () => const SkeletonBox(height: 34),
            error: (_, _) => Text('Could not load fielding events.',
                style: context.texts.bodySmall),
            data: (list) {
              if (list.isEmpty) {
                return Text('No fielding events logged.',
                    style: context.texts.bodySmall);
              }
              return Column(
                children: [
                  for (final e in list)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 5),
                      child: Row(
                        children: [
                          Icon(
                            e.kind == 'drop'
                                ? Icons.back_hand_outlined
                                : e.kind == 'save'
                                    ? Icons.shield_outlined
                                    : Icons.error_outline,
                            size: 15,
                            color: e.kind == 'save'
                                ? context.scheme.primary
                                : context.cric.amber,
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(e.summary,
                                style: context.texts.bodySmall),
                          ),
                          if (widget.canScore)
                            IconButton(
                              iconSize: 16,
                              visualDensity: VisualDensity.compact,
                              icon: const Icon(Icons.close),
                              onPressed: () async {
                                try {
                                  await ref
                                      .read(apiProvider)
                                      .deleteFieldingEvent(
                                          widget.matchId, e.id);
                                  ref.invalidate(
                                      fieldingProvider(widget.matchId));
                                } catch (err) {
                                  if (context.mounted) {
                                    context.toastError(err);
                                  }
                                }
                              },
                            ),
                        ],
                      ),
                    ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

/// Who is approved to officiate, and the request queue for the organizer.
class OfficialsPanel extends ConsumerStatefulWidget {
  final String matchId;
  final MatchOfficials? officials;
  final Future<void> Function() onChanged;

  const OfficialsPanel({
    super.key,
    required this.matchId,
    required this.officials,
    required this.onChanged,
  });

  @override
  ConsumerState<OfficialsPanel> createState() => _OfficialsPanelState();
}

class _OfficialsPanelState extends ConsumerState<OfficialsPanel> {
  bool _busy = false;

  Future<void> _run(Future<void> Function() action, String done) async {
    setState(() => _busy = true);
    try {
      await action();
      await widget.onChanged();
      if (mounted) context.toast(done);
    } catch (e) {
      if (mounted) context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final o = widget.officials;
    if (o == null) {
      return CnCard(
        child: Row(
          children: [
            Icon(Icons.gavel_outlined, size: 17, color: context.cric.muted),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Sign in to request to officiate this match.',
                style: context.texts.bodySmall,
              ),
            ),
          ],
        ),
      );
    }

    final api = ref.read(apiProvider);

    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(Icons.gavel_outlined, size: 17, color: context.cric.muted),
              const SizedBox(width: 8),
              Text('Match officials', style: context.texts.titleSmall),
            ],
          ),
          const SizedBox(height: 12),
          if (o.isManager) ...[
            if (o.officials.isEmpty)
              Text('No umpire requests yet.', style: context.texts.bodySmall)
            else
              for (final official in o.officials)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 5),
                  child: Row(
                    children: [
                      CnAvatar(name: official.umpireName, size: 30),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(official.umpireName,
                                style: context.texts.bodyMedium),
                            Text(
                              official.isApproved
                                  ? 'Officiating'
                                  : 'Wants to officiate',
                              style: context.texts.labelSmall?.copyWith(
                                color: official.isApproved
                                    ? context.scheme.primary
                                    : context.cric.amber,
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (!official.isApproved)
                        TextButton(
                          onPressed: _busy
                              ? null
                              : () => _run(
                                    () => api.approveOfficial(
                                        widget.matchId, official.umpireId),
                                    'Approved',
                                  ),
                          child: const Text('Approve'),
                        ),
                      IconButton(
                        iconSize: 17,
                        icon: const Icon(Icons.close),
                        onPressed: _busy
                            ? null
                            : () => _run(
                                  () => api.removeOfficial(
                                      widget.matchId, official.umpireId),
                                  'Removed',
                                ),
                      ),
                    ],
                  ),
                ),
          ] else if (o.myStatus == 'approved')
            Row(
              children: [
                Icon(Icons.verified, size: 17, color: context.scheme.primary),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'You are approved to officiate this match.',
                    style: context.texts.bodySmall,
                  ),
                ),
              ],
            )
          else if (o.myStatus == 'pending')
            Row(
              children: [
                Icon(Icons.hourglass_empty,
                    size: 17, color: context.cric.amber),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Requested. Waiting for the organizer to approve.',
                    style: context.texts.bodySmall,
                  ),
                ),
              ],
            )
          else if (!o.canScore)
            OutlinedButton.icon(
              onPressed: _busy
                  ? null
                  : () => _run(
                        () => api.requestToOfficiate(widget.matchId),
                        'Request sent',
                      ),
              icon: const Icon(Icons.pan_tool_alt_outlined, size: 17),
              label: const Text('Request to officiate'),
            )
          else
            Text(
              'You can score this match.',
              style: context.texts.bodySmall,
            ),
        ],
      ),
    );
  }
}

/// Attach a live stream link, so viewers watch alongside the scorecard.
class StreamPanel extends ConsumerStatefulWidget {
  final String matchId;
  final StreamInfo? stream;
  final bool canManage;
  final Future<void> Function() onChanged;

  const StreamPanel({
    super.key,
    required this.matchId,
    required this.stream,
    required this.canManage,
    required this.onChanged,
  });

  @override
  ConsumerState<StreamPanel> createState() => _StreamPanelState();
}

class _StreamPanelState extends ConsumerState<StreamPanel> {
  late final TextEditingController _url =
      TextEditingController(text: widget.stream?.url ?? '');
  bool _busy = false;

  @override
  void dispose() {
    _url.dispose();
    super.dispose();
  }

  Future<void> _save(String? url) async {
    setState(() => _busy = true);
    try {
      await ref.read(apiProvider).setStreamUrl(widget.matchId, url);
      await widget.onChanged();
      if (mounted) {
        context.toast(url == null || url.isEmpty
            ? 'Stream removed'
            : 'Stream link saved');
      }
    } catch (e) {
      if (mounted) context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(Icons.videocam_outlined, size: 17, color: context.cric.muted),
              const SizedBox(width: 8),
              Text('Live stream', style: context.texts.titleSmall),
            ],
          ),
          if (widget.stream != null) ...[
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () async {
                final uri = Uri.parse(widget.stream!.url);
                if (!await launchUrl(uri,
                    mode: LaunchMode.externalApplication)) {
                  if (context.mounted) {
                    context.copyToClipboard(widget.stream!.url);
                  }
                }
              },
              icon: const Icon(Icons.play_circle_outline, size: 18),
              label: Text('Watch on ${_host(widget.stream!.url)}'),
            ),
          ],
          if (widget.canManage) ...[
            const SizedBox(height: 12),
            TextField(
              controller: _url,
              decoration: const InputDecoration(
                hintText: 'Paste a YouTube or Facebook live link',
                isDense: true,
              ),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed:
                        _busy ? null : () => _save(_url.text.trim()),
                    child: Text(widget.stream == null ? 'Go live' : 'Update'),
                  ),
                ),
                if (widget.stream != null) ...[
                  const SizedBox(width: 10),
                  OutlinedButton(
                    onPressed: _busy
                        ? null
                        : () {
                            _url.clear();
                            _save('');
                          },
                    child: const Text('Remove'),
                  ),
                ],
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'The video stays on your platform. Nothing is uploaded to '
              'CricNetra.',
              style:
                  context.texts.labelSmall?.copyWith(color: context.cric.faint),
            ),
          ],
        ],
      ),
    );
  }

  static String _host(String url) {
    try {
      return Uri.parse(url).host.replaceFirst('www.', '');
    } catch (_) {
      return 'the stream';
    }
  }
}

/// Highlight clips attached to this match.
class ClipsPanel extends ConsumerStatefulWidget {
  final String matchId;
  final List<MatchClip> clips;
  final bool canManage;
  final Future<void> Function() onChanged;

  const ClipsPanel({
    super.key,
    required this.matchId,
    required this.clips,
    required this.canManage,
    required this.onChanged,
  });

  @override
  ConsumerState<ClipsPanel> createState() => _ClipsPanelState();
}

class _ClipsPanelState extends ConsumerState<ClipsPanel> {
  final _url = TextEditingController();
  final _label = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _url.dispose();
    _label.dispose();
    super.dispose();
  }

  Future<void> _add() async {
    final url = _url.text.trim();
    if (url.isEmpty) return;
    setState(() => _busy = true);
    try {
      await ref.read(apiProvider).addClip(
            widget.matchId,
            url,
            label: _label.text.trim().isEmpty ? null : _label.text.trim(),
          );
      _url.clear();
      _label.clear();
      await widget.onChanged();
      if (mounted) context.toast('Clip added');
    } catch (e) {
      if (mounted) context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(Icons.movie_outlined, size: 17, color: context.cric.muted),
              const SizedBox(width: 8),
              Text('Highlight clips', style: context.texts.titleSmall),
            ],
          ),
          const SizedBox(height: 12),
          if (widget.clips.isEmpty)
            Text('No clips yet.', style: context.texts.bodySmall)
          else
            for (final clip in widget.clips)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  children: [
                    Icon(
                      clip.isVideoFile
                          ? Icons.play_circle_outline
                          : Icons.link,
                      size: 17,
                      color: context.scheme.primary,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: InkWell(
                        onTap: () async {
                          final uri = Uri.parse(clip.url);
                          if (!await launchUrl(uri,
                              mode: LaunchMode.externalApplication)) {
                            if (context.mounted) {
                              context.copyToClipboard(clip.url);
                            }
                          }
                        },
                        child: Text(
                          clip.label ?? clip.url,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: context.texts.bodySmall,
                        ),
                      ),
                    ),
                    if (widget.canManage)
                      IconButton(
                        iconSize: 16,
                        visualDensity: VisualDensity.compact,
                        icon: const Icon(Icons.delete_outline),
                        onPressed: () async {
                          try {
                            await ref
                                .read(apiProvider)
                                .removeClip(widget.matchId, clip.id);
                            await widget.onChanged();
                          } catch (e) {
                            if (context.mounted) context.toastError(e);
                          }
                        },
                      ),
                  ],
                ),
              ),
          if (widget.canManage) ...[
            const SizedBox(height: 12),
            TextField(
              controller: _url,
              decoration: const InputDecoration(
                hintText: 'Clip URL',
                isDense: true,
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _label,
                    maxLength: 80,
                    decoration: const InputDecoration(
                      hintText: 'Label (optional)',
                      isDense: true,
                      counterText: '',
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                ElevatedButton(
                  onPressed: _busy ? null : _add,
                  child: const Text('Add'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

/// The broadcast overlay links, for anyone streaming the match through OBS.
class BroadcastPanel extends StatelessWidget {
  final String matchId;

  const BroadcastPanel({super.key, required this.matchId});

  @override
  Widget build(BuildContext context) {
    Widget row(String label, String url) => Padding(
          padding: const EdgeInsets.symmetric(vertical: 5),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(label, style: context.texts.labelLarge),
                    Text(
                      url,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: context.texts.labelSmall
                          ?.copyWith(color: context.cric.faint),
                    ),
                  ],
                ),
              ),
              IconButton(
                iconSize: 17,
                icon: const Icon(Icons.copy),
                onPressed: () =>
                    context.copyToClipboard(url, message: 'Overlay link copied'),
              ),
            ],
          ),
        );

    return CnCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.cast_outlined, size: 17, color: context.cric.muted),
              const SizedBox(width: 8),
              Text('Broadcast overlay', style: context.texts.titleSmall),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            'Add these as Browser sources in OBS, Streamlabs or vMix at '
            '1920x1080 with a transparent background.',
            style: context.texts.bodySmall,
          ),
          const SizedBox(height: 10),
          row('Scoreboard', ApiConfig.overlayUrl(matchId)),
          row('Analysis scene', ApiConfig.overlayAnalysisUrl(matchId)),
        ],
      ),
    );
  }
}
