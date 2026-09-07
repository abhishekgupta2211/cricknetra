import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import 'login_screen.dart';

/// Two steps: ask for a reset code, then set a new password with it.
///
/// The server always answers the first step generically, so a stranger cannot
/// use it to discover which accounts exist.
class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  ConsumerState<ForgotPasswordScreen> createState() =>
      _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final _identifier = TextEditingController();
  final _token = TextEditingController();
  final _newPassword = TextEditingController();

  bool _busy = false;
  bool _codeSent = false;
  bool _obscure = true;

  @override
  void dispose() {
    _identifier.dispose();
    _token.dispose();
    _newPassword.dispose();
    super.dispose();
  }

  Future<void> _requestCode() async {
    final id = _identifier.text.trim();
    if (id.length < 3) {
      context.toast('Enter your mobile number, username or email');
      return;
    }
    setState(() => _busy = true);
    try {
      final devToken = await ref.read(apiProvider).forgotPassword(id);
      if (!mounted) return;
      setState(() {
        _codeSent = true;
        // Dev builds hand the token straight back so testing needs no mail.
        if (devToken != null) _token.text = devToken;
      });
      context.toast('If that account exists, a reset code is on its way.');
    } catch (e) {
      if (!mounted) return;
      context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _reset() async {
    final token = _token.text.trim();
    final password = _newPassword.text;
    if (token.length < 8) {
      context.toast('Paste the reset code from your message');
      return;
    }
    if (password.length < 6) {
      context.toast('Use at least 6 characters');
      return;
    }
    setState(() => _busy = true);
    try {
      await ref.read(apiProvider).resetPassword(token, password);
      if (!mounted) return;
      context.toast('Password changed. Sign in with it now.');
      context.pop();
    } catch (e) {
      if (!mounted) return;
      context.toastError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Reset password')),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    _codeSent ? 'Enter your code' : 'Find your account',
                    style: context.texts.headlineSmall,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    _codeSent
                        ? 'Paste the reset code you received, then choose a new password.'
                        : 'We will send a reset code to the email or number on your account.',
                    style: context.texts.bodySmall,
                  ),
                  const SizedBox(height: 24),
                  TextField(
                    controller: _identifier,
                    enabled: !_codeSent,
                    decoration: const InputDecoration(
                      labelText: 'Mobile, username or email',
                      prefixIcon: Icon(Icons.person_outline),
                    ),
                  ),
                  if (_codeSent) ...[
                    const SizedBox(height: 14),
                    TextField(
                      controller: _token,
                      decoration: const InputDecoration(
                        labelText: 'Reset code',
                        prefixIcon: Icon(Icons.key_outlined),
                      ),
                    ),
                    const SizedBox(height: 14),
                    TextField(
                      controller: _newPassword,
                      obscureText: _obscure,
                      decoration: InputDecoration(
                        labelText: 'New password',
                        prefixIcon: const Icon(Icons.lock_outline),
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscure
                                ? Icons.visibility_outlined
                                : Icons.visibility_off_outlined,
                            size: 20,
                          ),
                          onPressed: () => setState(() => _obscure = !_obscure),
                        ),
                      ),
                    ),
                  ],
                  const SizedBox(height: 22),
                  ElevatedButton(
                    onPressed: _busy ? null : (_codeSent ? _reset : _requestCode),
                    child: _busy
                        ? const ButtonSpinner()
                        : Text(_codeSent ? 'Change password' : 'Send reset code'),
                  ),
                  if (_codeSent)
                    TextButton(
                      onPressed: _busy
                          ? null
                          : () => setState(() {
                                _codeSent = false;
                                _token.clear();
                              }),
                      child: const Text('Use a different account'),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
