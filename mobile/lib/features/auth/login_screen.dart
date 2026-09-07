import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';

class LoginScreen extends ConsumerStatefulWidget {
  /// Where to go once signed in, when the router bounced us here.
  final String? next;

  const LoginScreen({super.key, this.next});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _identifier = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  bool _obscure = true;

  @override
  void dispose() {
    _identifier.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await ref.read(authControllerProvider.notifier).login(
            _identifier.text.trim(),
            _password.text,
          );
      if (!mounted) return;
      context.go(widget.next ?? Routes.home);
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
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const BrandMark(),
                    const SizedBox(height: 28),
                    Text('Welcome back', style: context.texts.headlineSmall),
                    const SizedBox(height: 6),
                    Text(
                      'Sign in to score matches and track your career.',
                      style: context.texts.bodySmall,
                    ),
                    const SizedBox(height: 26),
                    TextFormField(
                      controller: _identifier,
                      autofillHints: const [AutofillHints.username],
                      textInputAction: TextInputAction.next,
                      decoration: const InputDecoration(
                        labelText: 'Mobile number or username',
                        prefixIcon: Icon(Icons.person_outline),
                      ),
                      validator: (v) => (v == null || v.trim().length < 3)
                          ? 'Enter your mobile number or username'
                          : null,
                    ),
                    const SizedBox(height: 14),
                    TextFormField(
                      controller: _password,
                      obscureText: _obscure,
                      autofillHints: const [AutofillHints.password],
                      textInputAction: TextInputAction.done,
                      onFieldSubmitted: (_) => _busy ? null : _submit(),
                      decoration: InputDecoration(
                        labelText: 'Password',
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
                      validator: (v) => (v == null || v.length < 6)
                          ? 'Passwords are at least 6 characters'
                          : null,
                    ),
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton(
                        onPressed: () => context.push(Routes.forgotPassword),
                        child: const Text('Forgot password?'),
                      ),
                    ),
                    const SizedBox(height: 6),
                    ElevatedButton(
                      onPressed: _busy ? null : _submit,
                      child: _busy
                          ? const ButtonSpinner()
                          : const Text('Sign in'),
                    ),
                    const SizedBox(height: 18),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text('New to CricNetra?',
                            style: context.texts.bodySmall),
                        TextButton(
                          onPressed: () => context.push(Routes.register),
                          child: const Text('Create an account'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Center(
                      child: TextButton(
                        onPressed: () => context.go(Routes.home),
                        child: const Text('Browse without signing in'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// The wordmark used on the auth screens.
class BrandMark extends StatelessWidget {
  const BrandMark({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: 58,
          height: 58,
          decoration: BoxDecoration(
            color: context.cric.accentSoft,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: context.scheme.primary.withValues(alpha: 0.3)),
          ),
          child: Icon(
            Icons.sports_cricket,
            size: 30,
            color: context.scheme.primary,
          ),
        ),
        const SizedBox(height: 12),
        RichText(
          text: TextSpan(
            style: context.texts.titleLarge?.copyWith(letterSpacing: 0.5),
            children: [
              const TextSpan(text: 'CRIC'),
              TextSpan(
                text: 'NETRA',
                style: TextStyle(color: context.scheme.primary),
              ),
            ],
          ),
        ),
        const SizedBox(height: 4),
        Text(
          'Live cricket scoring, ball by ball',
          style: context.texts.labelSmall?.copyWith(color: context.cric.faint),
        ),
      ],
    );
  }
}

/// A spinner sized to sit inside a button without changing its height.
class ButtonSpinner extends StatelessWidget {
  final Color? color;

  const ButtonSpinner({super.key, this.color});

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 20,
        width: 20,
        child: CircularProgressIndicator(
          strokeWidth: 2.2,
          color: color ?? context.scheme.onPrimary,
        ),
      );
}
