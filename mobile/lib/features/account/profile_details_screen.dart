import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_provider.dart';
import '../../core/models/user.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';

final myProfileProvider = FutureProvider.autoDispose<UserProfile?>(
  (ref) => ref.watch(apiProvider).myProfile(),
);

/// The extended profile. Every field is required, so it saves as one piece.
class ProfileDetailsScreen extends ConsumerStatefulWidget {
  const ProfileDetailsScreen({super.key});

  @override
  ConsumerState<ProfileDetailsScreen> createState() =>
      _ProfileDetailsScreenState();
}

class _ProfileDetailsScreenState
    extends ConsumerState<ProfileDetailsScreen> {
  final _address = TextEditingController();
  final _pincode = TextEditingController();
  final _city = TextEditingController();
  final _district = TextEditingController();
  final _state = TextEditingController();
  final _region = TextEditingController();

  bool _seeded = false;
  bool _busy = false;

  @override
  void dispose() {
    _address.dispose();
    _pincode.dispose();
    _city.dispose();
    _district.dispose();
    _state.dispose();
    _region.dispose();
    super.dispose();
  }

  void _seed(UserProfile p) {
    if (_seeded) return;
    _seeded = true;
    _address.text = p.address;
    _pincode.text = p.pincode;
    _city.text = p.city;
    _district.text = p.district;
    _state.text = p.state;
    _region.text = p.region;
  }

  Future<void> _save(bool exists) async {
    final body = {
      'address': _address.text.trim(),
      'pincode': _pincode.text.trim(),
      'city': _city.text.trim(),
      'district': _district.text.trim(),
      'state': _state.text.trim(),
      'region': _region.text.trim(),
    };
    if (body.values.any((v) => v.isEmpty)) {
      context.toast('Please fill in every field');
      return;
    }
    if (!RegExp(r'^\d{6,10}$').hasMatch(body['pincode']!)) {
      context.toast('Pincode must be 6 to 10 digits');
      return;
    }

    setState(() => _busy = true);
    try {
      final api = ref.read(apiProvider);
      if (exists) {
        await api.updateProfile(body);
      } else {
        await api.completeProfile(body);
      }
      ref.invalidate(myProfileProvider);
      if (!mounted) return;
      context.toast('Profile saved');
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
    final async = ref.watch(myProfileProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Address and location')),
      body: async.when(
        loading: () => const Padding(
          padding: EdgeInsets.all(16),
          child: ListSkeleton(rows: 3),
        ),
        error: (e, _) => ErrorState(
          error: e,
          onRetry: () => ref.invalidate(myProfileProvider),
        ),
        data: (profile) {
          if (profile != null) _seed(profile);
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
            children: [
              Text(
                'Your location puts you on the right local leaderboards and '
                'helps nearby teams find you.',
                style: context.texts.bodySmall,
              ),
              const SizedBox(height: 16),
              _field(_address, 'Address', maxLines: 2),
              _field(_city, 'City'),
              _field(_pincode, 'Pincode', keyboard: TextInputType.number),
              _field(_district, 'District'),
              _field(_state, 'State'),
              _field(_region, 'Region'),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _busy ? null : () => _save(profile != null),
                child: Text(profile == null ? 'Save profile' : 'Save changes'),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _field(
    TextEditingController controller,
    String label, {
    int maxLines = 1,
    TextInputType? keyboard,
  }) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: TextField(
          controller: controller,
          maxLines: maxLines,
          keyboardType: keyboard,
          textCapitalization: TextCapitalization.words,
          decoration: InputDecoration(labelText: label, isDense: true),
        ),
      );
}
