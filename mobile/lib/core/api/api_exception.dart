/// A failed API call, translated into something worth showing a person.
///
/// The backend wraps every error as `{"detail": ..., "request_id": "..."}`,
/// where `detail` is either a plain string (our own HTTPExceptions) or the
/// FastAPI 422 validation array. Neither should ever reach the screen raw.
class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final String? requestId;

  const ApiException({
    required this.message,
    this.statusCode,
    this.requestId,
  });

  /// No network, DNS failure, or a timeout — worth offering a retry.
  bool get isNetwork => statusCode == null;

  /// The session is gone; the caller should send the user back to sign-in.
  bool get isUnauthorized => statusCode == 401;

  /// The account is real but the role is not allowed to do this.
  bool get isForbidden => statusCode == 403;

  bool get isNotFound => statusCode == 404;

  /// The scoring engine rejected the delivery. Show `message` verbatim and do
  /// not retry — retrying sends the same illegal ball again.
  bool get isConflict => statusCode == 409;

  bool get isValidation => statusCode == 422;

  bool get isRateLimited => statusCode == 429;

  bool get isServer => statusCode != null && statusCode! >= 500;

  @override
  String toString() => message;

  /// Turn a decoded error body into one readable sentence.
  static String humanize(dynamic body, String fallback) {
    if (body is! Map) return fallback;
    final detail = body['detail'] ?? body['message'];

    if (detail is String && detail.isNotEmpty) return detail;

    // FastAPI 422: a list of {loc, msg, type} objects.
    if (detail is List && detail.isNotEmpty) {
      final parts = <String>[];
      for (final e in detail) {
        if (e is! Map) continue;
        final msg = '${e['msg'] ?? ''}';
        if (msg.isEmpty) continue;
        final loc = e['loc'];
        final field = (loc is List && loc.isNotEmpty) ? '${loc.last}' : null;
        parts.add(_phrase(field, msg));
      }
      if (parts.isNotEmpty) return parts.join('. ');
    }

    if (detail is Map && detail['msg'] != null) {
      return _stripValueError('${detail['msg']}');
    }
    return fallback;
  }

  static const _fieldLabels = <String, String>{
    'full_name': 'Full name',
    'username': 'Username',
    'mobile_no': 'Mobile number',
    'email': 'Email',
    'password': 'Password',
    'new_password': 'New password',
    'role': 'Role',
    'identifier': 'Mobile or username',
    'text': 'Message',
    'name': 'Name',
    'team_ids': 'Teams',
    'overs': 'Overs',
    'target': 'Target',
  };

  static String _phrase(String? field, String msg) {
    final cleaned = _stripValueError(msg);
    if (cleaned != msg) return cleaned;
    final label = field == null ? null : _fieldLabels[field];
    if (label == null) return msg;
    // "String should have at least 2 characters" reads better with the label.
    return msg.startsWith('String ')
        ? msg.replaceFirst('String ', '$label ')
        : '$label: $msg';
  }

  static String _stripValueError(String msg) {
    const prefix = 'Value error, ';
    return msg.startsWith(prefix) ? msg.substring(prefix.length) : msg;
  }
}
