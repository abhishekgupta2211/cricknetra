import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/social.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/formatters.dart';
import '../../core/widgets/common.dart';
import '../notifications/notification_providers.dart';

/// One conversation. Opening it marks the thread read on the server.
class ThreadScreen extends ConsumerStatefulWidget {
  final String otherId;

  const ThreadScreen({super.key, required this.otherId});

  @override
  ConsumerState<ThreadScreen> createState() => _ThreadScreenState();
}

class _ThreadScreenState extends ConsumerState<ThreadScreen> {
  final _input = TextEditingController();
  final _scroll = ScrollController();

  /// Messages sent in this session, appended so the thread updates instantly.
  final _sent = <DirectMessage>[];
  bool _busy = false;

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _input.text.trim();
    if (text.isEmpty) return;
    setState(() => _busy = true);
    final draft = text;
    _input.clear();
    try {
      final message =
          await ref.read(apiProvider).sendMessage(widget.otherId, draft);
      if (!mounted) return;
      setState(() => _sent.add(message));
      ref.invalidate(conversationsProvider);
      _scrollToEnd();
    } catch (e) {
      if (!mounted) return;
      // Give the text back rather than losing what they typed.
      _input.text = draft;
      context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.jumpTo(_scroll.position.maxScrollExtent);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(threadProvider(widget.otherId));

    return Scaffold(
      appBar: AppBar(title: Text(async.valueOrNull?.otherName ?? 'Conversation')),
      body: Column(
        children: [
          Expanded(
            child: async.when(
              loading: () => const Padding(
                padding: EdgeInsets.all(16),
                child: ListSkeleton(rows: 4),
              ),
              error: (e, _) => ErrorState(
                error: e,
                onRetry: () => ref.invalidate(threadProvider(widget.otherId)),
              ),
              data: (thread) {
                final messages = [...thread.messages, ..._sent];
                if (messages.isEmpty) {
                  return const EmptyState(
                    icon: Icons.waving_hand_outlined,
                    title: 'Say hello',
                  );
                }
                _scrollToEnd();
                return ListView.builder(
                  controller: _scroll,
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                  itemCount: messages.length,
                  itemBuilder: (context, i) => _Bubble(message: messages[i]),
                );
              },
            ),
          ),
          SafeArea(
            top: false,
            child: Container(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
              decoration: BoxDecoration(
                color: context.scheme.surface,
                border: Border(top: BorderSide(color: context.cric.line)),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _input,
                      maxLength: 2000,
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => _busy ? null : _send(),
                      decoration: const InputDecoration(
                        hintText: 'Message',
                        isDense: true,
                        counterText: '',
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed: _busy ? null : _send,
                    icon: const Icon(Icons.send, size: 19),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  final DirectMessage message;

  const _Bubble({required this.message});

  @override
  Widget build(BuildContext context) {
    final mine = message.mine;
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 9),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        decoration: BoxDecoration(
          color: mine ? context.scheme.primary : context.cric.surfaceVariant,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(14),
            topRight: const Radius.circular(14),
            bottomLeft: Radius.circular(mine ? 14 : 4),
            bottomRight: Radius.circular(mine ? 4 : 14),
          ),
          border: mine ? null : Border.all(color: context.cric.line),
        ),
        child: Column(
          crossAxisAlignment:
              mine ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            Text(
              message.text,
              style: context.texts.bodyMedium?.copyWith(
                color: mine ? context.scheme.onPrimary : null,
              ),
            ),
            const SizedBox(height: 3),
            Text(
              Fmt.timeAgo(message.when),
              style: context.texts.labelSmall?.copyWith(
                fontSize: 9.5,
                color: mine
                    ? context.scheme.onPrimary.withValues(alpha: 0.7)
                    : context.cric.faint,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
