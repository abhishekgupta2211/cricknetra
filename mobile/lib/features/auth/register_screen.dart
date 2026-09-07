import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/user.dart';
import '../../core/router/app_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import 'login_screen.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _fullName = TextEditingController();
  final _username = TextEditingController();
  final _mobile = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();

  String _role = Roles.player;
  bool _busy = false;
  bool _obscure = true;

  @override
  void dispose() {
    _fullName.dispose();
    _username.dispose();
    _mobile.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      final created = await ref.read(authControllerProvider.notifier).register(
            fullName: _fullName.text.trim(),
            username: _username.text.trim(),
            mobileNo: _mobile.text.trim(),
            password: _password.text,
            role: _role,
            email: _email.text.trim(),
          );
      if (!mounted) return;

      // Elevated roles are created as a general user until an admin approves.
      if (created.rolePending) {
        await showDialog<void>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Account created'),
            content: Text(
              'Your ${Roles.label(created.requestedRole ?? _role)} role is '
              'waiting for an admin to approve it. Until then you are signed '
              'in as a general user and can browse everything.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Got it'),
              ),
            ],
          ),
        );
      }
      if (!mounted) return;
      context.go(Routes.home);
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
      appBar: AppBar(title: const Text('Create account')),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    TextFormField(
                      controller: _fullName,
                      textCapitalization: TextCapitalization.words,
                      textInputAction: TextInputAction.next,
                      decoration: const InputDecoration(
                        labelText: 'Full name',
                        prefixIcon: Icon(Icons.badge_outlined),
                      ),
                      validator: (v) => (v == null || v.trim().length < 2)
                          ? 'Enter your full name'
                          : null,
                    ),
                    const SizedBox(height: 14),
                    TextFormField(
                      controller: _username,
                      textInputAction: TextInputAction.next,
                      inputFormatters: [
                        FilteringTextInputFormatter.allow(
                          RegExp(r'[a-zA-Z0-9_]'),
                        ),
                      ],
                      decoration: const InputDecoration(
                        labelText: 'Username',
                        helperText: 'Letters, numbers and underscores',
                        prefixIcon: Icon(Icons.alternate_email),
                      ),
                      validator: (v) => (v == null || v.trim().length < 3)
                          ? 'Pick a username of at least 3 characters'
                          : null,
                    ),
                    const SizedBox(height: 14),
                    TextFormField(
                      controller: _mobile,
                      keyboardType: TextInputType.phone,
                      textInputAction: TextInputAction.next,
                      decoration: const InputDecoration(
                        labelText: 'Mobile number',
                        prefixIcon: Icon(Icons.phone_outlined),
                      ),
                      validator: (v) {
                        final digits =
                            (v ?? '').replaceAll(RegExp(r'\D'), '');
                        if (digits.length < 10 || digits.length > 15) {
                          return 'Enter a valid mobile number';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 14),
                    TextFormField(
                      controller: _email,
                      keyboardType: TextInputType.emailAddress,
                      textInputAction: TextInputAction.next,
                      decoration: const InputDecoration(
                        labelText: 'Email (optional)',
                        helperText: 'Where verification and reset codes go',
                        prefixIcon: Icon(Icons.mail_outline),
                      ),
                      validator: (v) {
                        final text = (v ?? '').trim();
                        if (text.isEmpty) return null;
                        final ok = text.contains('@') &&
                            text.split('@').last.contains('.');
                        return ok ? null : 'Enter a valid email address';
                      },
                    ),
                    const SizedBox(height: 14),
                    TextFormField(
                      controller: _password,
                      obscureText: _obscure,
                      textInputAction: TextInputAction.done,
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
                          ? 'Use at least 6 characters'
                          : null,
                    ),
                    const SizedBox(height: 20),
                    Text('I am a', style: context.texts.titleSmall),
                    const SizedBox(height: 8),
                    ...Roles.signupChoices.map(
                      (r) => RadioListTile<String>(
                        value: r,
                        // ignore: deprecated_member_use
                        groupValue: _role,
                        // ignore: deprecated_member_use
                        onChanged: (v) => setState(() => _role = v ?? _role),
                        contentPadding: EdgeInsets.zero,
                        dense: true,
                        title: Text(Roles.label(r)),
                        subtitle: Text(
                          Roles.blurb(r),
                          style: context.texts.bodySmall,
                        ),
                      ),
                    ),
                    // Every role is now a request an admin acts on, not just
                    // the elevated ones, so the notice is unconditional.
                    Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: CnCard(
                          color: context.cric.amberSoft,
                          borderColor:
                              context.cric.amber.withValues(alpha: 0.3),
                          padding: const EdgeInsets.all(12),
                          child: Row(
                            children: [
                              Icon(Icons.info_outline,
                                  size: 18, color: context.cric.amber),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  'Every account starts as a general user. An '
                                  'admin reviews this and grants the role.',
                                  style: context.texts.bodySmall,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    const SizedBox(height: 22),
                    ElevatedButton(
                      onPressed: _busy ? null : _submit,
                      child: _busy
                          ? const ButtonSpinner()
                          : const Text('Create account'),
                    ),
                    const SizedBox(height: 10),
                    Center(
                      child: TextButton(
                        onPressed: () => context.pop(),
                        child: const Text('I already have an account'),
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
