/// Defensive JSON coercion helpers.
///
/// The API is well-typed, but a client that hard-casts crashes the whole screen
/// on one unexpected null. Every model in this package parses through these.
library;

int asInt(dynamic v, [int fallback = 0]) {
  if (v is int) return v;
  if (v is num) return v.toInt();
  return int.tryParse('$v') ?? fallback;
}

int? asIntOrNull(dynamic v) {
  if (v == null) return null;
  if (v is int) return v;
  if (v is num) return v.toInt();
  return int.tryParse('$v');
}

double asDouble(dynamic v, [double fallback = 0]) {
  if (v is double) return v;
  if (v is num) return v.toDouble();
  return double.tryParse('$v') ?? fallback;
}

double? asDoubleOrNull(dynamic v) {
  if (v == null) return null;
  if (v is num) return v.toDouble();
  return double.tryParse('$v');
}

bool asBool(dynamic v, [bool fallback = false]) {
  if (v is bool) return v;
  if (v is num) return v != 0;
  if (v is String) return v == 'true' || v == '1';
  return fallback;
}

String asStr(dynamic v, [String fallback = '']) => v == null ? fallback : '$v';

String? asStrOrNull(dynamic v) {
  if (v == null) return null;
  final s = '$v';
  return s.isEmpty ? null : s;
}

/// Coerce anything list-shaped into `List<Map<String, dynamic>>`.
List<Map<String, dynamic>> asMapList(dynamic v) {
  if (v is! List) return const [];
  return v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
}

Map<String, dynamic> asMap(dynamic v) =>
    v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};

Map<String, dynamic>? asMapOrNull(dynamic v) =>
    v is Map ? Map<String, dynamic>.from(v) : null;

List<String> asStrList(dynamic v) {
  if (v is! List) return const [];
  return v.map((e) => '$e').toList();
}

/// `{"Deep Point": 4}` style maps returned by the insights endpoints.
Map<String, int> asIntMap(dynamic v) {
  if (v is! Map) return const {};
  final out = <String, int>{};
  v.forEach((k, val) => out['$k'] = asInt(val));
  return out;
}

Map<String, double> asDoubleMap(dynamic v) {
  if (v is! Map) return const {};
  final out = <String, double>{};
  v.forEach((k, val) => out['$k'] = asDouble(val));
  return out;
}

/// Parse an API timestamp. The backend emits ISO-8601 in UTC (sometimes with a
/// trailing `Z`, sometimes with an explicit offset).
DateTime? asDate(dynamic v) {
  if (v == null) return null;
  return DateTime.tryParse('$v')?.toLocal();
}
