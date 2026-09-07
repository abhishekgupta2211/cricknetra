import 'package:intl/intl.dart';

/// Human-facing formatting: relative times, cricket numbers, initials.
class Fmt {
  const Fmt._();

  /// "just now" · "5m" · "3h" · "2d" · "12 Mar"
  static String timeAgo(String? iso) {
    if (iso == null || iso.isEmpty) return '';
    final t = DateTime.tryParse(iso);
    if (t == null) return '';
    final local = t.toLocal();
    final diff = DateTime.now().difference(local);

    if (diff.isNegative) return 'just now';
    if (diff.inSeconds < 60) return 'just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    if (local.year == DateTime.now().year) {
      return DateFormat('d MMM').format(local);
    }
    return DateFormat('d MMM yyyy').format(local);
  }

  /// "12 Mar 2026, 4:30 pm"
  static String dateTime(String? iso) {
    if (iso == null || iso.isEmpty) return '';
    final t = DateTime.tryParse(iso);
    if (t == null) return '';
    return DateFormat('d MMM yyyy, h:mm a').format(t.toLocal());
  }

  /// "12 Mar 2026"
  static String date(DateTime? t) =>
      t == null ? '' : DateFormat('d MMM yyyy').format(t.toLocal());

  /// "Wednesday, 4 September"
  static String longDate(DateTime t) =>
      DateFormat('EEEE, d MMMM').format(t);

  /// "Good morning" / "Good afternoon" / "Good evening"
  static String greeting([DateTime? now]) {
    final h = (now ?? DateTime.now()).hour;
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  }

  /// Up to two initials from a name, for avatar fallbacks.
  static String initials(String name) {
    final parts = name
        .trim()
        .split(RegExp(r'\s+'))
        .where((p) => p.isNotEmpty)
        .toList();
    if (parts.isEmpty) return '?';
    if (parts.length == 1) {
      final p = parts.first;
      return (p.length > 1 ? p.substring(0, 2) : p).toUpperCase();
    }
    return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
  }

  /// Rates and averages read best at two places; a null average means the
  /// batter has never been out.
  static String rate(double? v, {String dash = '—', int places = 2}) =>
      v == null ? dash : v.toStringAsFixed(places);

  static String rate1(double? v) => rate(v, places: 1);

  /// Net run rate always carries its sign.
  static String signed(double v, {int places = 3}) =>
      '${v >= 0 ? '+' : ''}${v.toStringAsFixed(places)}';

  /// "1,240" — thousands separated.
  static String count(int n) => NumberFormat.decimalPattern().format(n);

  /// "45.5%"
  static String percent(double v, {int places = 1}) =>
      '${v.toStringAsFixed(places)}%';

  /// Overs entered as "12.3" mean 12 overs and 3 balls, not 12.3 overs.
  static double oversToDecimal(double v) {
    if (v < 0) return 0;
    var whole = v.floor();
    var balls = ((v - whole) * 10).round();
    if (balls > 5) {
      whole += 1;
      balls = 0;
    }
    return whole + balls / 6;
  }

  static int oversToBalls(double v) => (oversToDecimal(v) * 6).round();

  /// Turn a count of legal balls back into "12.3".
  static String ballsToOvers(int balls, {int ballsPerOver = 6}) {
    if (ballsPerOver <= 0) return '0.0';
    return '${balls ~/ ballsPerOver}.${balls % ballsPerOver}';
  }

  /// "1st" · "2nd" · "3rd" · "4th"
  static String ordinal(int n) {
    if (n % 100 >= 11 && n % 100 <= 13) return '${n}th';
    return switch (n % 10) {
      1 => '${n}st',
      2 => '${n}nd',
      3 => '${n}rd',
      _ => '${n}th',
    };
  }

  /// "0:45" from 45 seconds, for video anchors.
  static String clock(double seconds) {
    final total = seconds.round();
    final m = total ~/ 60;
    final s = total % 60;
    return '$m:${s.toString().padLeft(2, '0')}';
  }

  /// Accepts "0:45" or "45" and returns seconds.
  static double? parseClock(String raw) {
    final text = raw.trim();
    if (text.isEmpty) return null;
    if (text.contains(':')) {
      final parts = text.split(':');
      if (parts.length != 2) return null;
      final m = int.tryParse(parts[0]);
      final s = double.tryParse(parts[1]);
      if (m == null || s == null) return null;
      return m * 60 + s;
    }
    return double.tryParse(text);
  }

  /// A stable colour seed for an avatar, so the same name keeps its colour.
  static int hashHue(String s) {
    var hash = 0;
    for (var i = 0; i < s.length; i++) {
      hash = (hash * 31 + s.codeUnitAt(i)) % 360;
    }
    return hash;
  }
}
