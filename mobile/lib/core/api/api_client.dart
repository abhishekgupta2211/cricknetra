import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';

import '../storage/token_storage.dart';
import 'api_config.dart';
import 'api_exception.dart';

/// Thin transport over the CricNetra JSON API.
///
/// Two things it does that a naive client does not:
///
/// 1. **One refresh at a time.** The backend rotates the refresh token on every
///    use, so two parallel 401s each refreshing would invalidate one another and
///    sign the user out. Concurrent callers share a single in-flight refresh.
/// 2. **Never surfaces a raw exception.** Every failure becomes an
///    [ApiException] carrying the server's own sentence plus the request id.
class ApiClient {
  final TokenStorage tokenStorage;
  late final Dio dio;

  /// A second Dio with no interceptors, so refreshing cannot recurse.
  late final Dio _plain;

  /// The in-flight refresh, shared by every caller that hits a 401 at once.
  Future<bool>? _refreshing;

  /// Called when the session is definitively gone, so the app can sign out.
  void Function()? onSessionExpired;

  ApiClient({required this.tokenStorage}) {
    final options = BaseOptions(
      baseUrl: ApiConfig.baseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 20),
      sendTimeout: const Duration(seconds: 30),
      headers: {'Accept': 'application/json'},
      // We interpret status codes ourselves.
      validateStatus: (_) => true,
    );

    dio = Dio(options);
    _plain = Dio(options);

    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (opts, handler) async {
          final token = await tokenStorage.getAccessToken();
          if (token != null && token.isNotEmpty) {
            opts.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(opts);
        },
      ),
    );
  }

  // ---------------------------------------------------------------- verbs

  Future<dynamic> get(String path, {Map<String, dynamic>? query}) =>
      _send('GET', path, query: query);

  Future<dynamic> post(String path, {dynamic body}) =>
      _send('POST', path, body: body);

  Future<dynamic> put(String path, {dynamic body}) =>
      _send('PUT', path, body: body);

  Future<dynamic> patch(String path, {dynamic body}) =>
      _send('PATCH', path, body: body);

  Future<dynamic> delete(String path, {dynamic body}) =>
      _send('DELETE', path, body: body);

  /// Upload one file as multipart. Every upload endpoint names the field
  /// `file`, and photos are capped at 4 MB server-side.
  Future<dynamic> upload(
    String path, {
    required String filePath,
    String field = 'file',
    String? filename,
    void Function(int sent, int total)? onProgress,
  }) async {
    final form = FormData.fromMap({
      field: await MultipartFile.fromFile(filePath, filename: filename),
    });
    return _send('POST', path, body: form, onSendProgress: onProgress);
  }

  /// Upload from memory, for image bytes that never hit disk.
  Future<dynamic> uploadBytes(
    String path, {
    required Uint8List bytes,
    required String filename,
    String field = 'file',
  }) async {
    final form = FormData.fromMap({
      field: MultipartFile.fromBytes(bytes, filename: filename),
    });
    return _send('POST', path, body: form);
  }

  // ------------------------------------------------------------ internals

  Future<dynamic> _send(
    String method,
    String path, {
    Map<String, dynamic>? query,
    dynamic body,
    void Function(int, int)? onSendProgress,
    bool allowRetry = true,
  }) async {
    Response<dynamic> res;
    try {
      res = await dio.request<dynamic>(
        path,
        data: body,
        queryParameters: query,
        onSendProgress: onSendProgress,
        options: Options(
          method: method,
          contentType:
              body is FormData ? null : Headers.jsonContentType,
        ),
      );
    } on DioException catch (e) {
      throw _fromDioException(e);
    }

    final status = res.statusCode ?? 0;

    // Try once to rotate the session, then replay the original request.
    if (status == 401 && allowRetry && !_isAuthPath(path)) {
      final ok = await _refreshSession();
      if (ok) {
        return _send(
          method,
          path,
          query: query,
          body: body,
          onSendProgress: onSendProgress,
          allowRetry: false,
        );
      }
      onSessionExpired?.call();
    }

    if (status >= 200 && status < 300) {
      if (status == 204) return null;
      return res.data;
    }

    throw ApiException(
      message: ApiException.humanize(res.data, _defaultMessage(status)),
      statusCode: status,
      requestId: res.headers.value('X-Request-ID'),
    );
  }

  /// `/auth/login` and `/auth/refresh` answering 401 means bad credentials, not
  /// an expired session — refreshing there would loop.
  bool _isAuthPath(String path) =>
      path.startsWith('/auth/login') ||
      path.startsWith('/auth/refresh') ||
      path.startsWith('/auth/register');

  Future<bool> _refreshSession() {
    // Everyone who arrives while a refresh is running awaits the same future.
    return _refreshing ??= _doRefresh().whenComplete(() => _refreshing = null);
  }

  Future<bool> _doRefresh() async {
    final refresh = await tokenStorage.getRefreshToken();
    if (refresh == null || refresh.isEmpty) return false;
    try {
      final res = await _plain.post<dynamic>(
        '/auth/refresh',
        data: {'refresh_token': refresh},
        options: Options(contentType: Headers.jsonContentType),
      );
      final ok = (res.statusCode ?? 0) >= 200 && (res.statusCode ?? 0) < 300;
      final data = res.data;
      if (!ok || data is! Map) {
        await tokenStorage.clearTokens();
        return false;
      }
      final access = '${data['access_token'] ?? ''}';
      if (access.isEmpty) {
        await tokenStorage.clearTokens();
        return false;
      }
      await tokenStorage.saveTokens(
        accessToken: access,
        refreshToken: data['refresh_token'] == null
            ? null
            : '${data['refresh_token']}',
      );
      return true;
    } catch (_) {
      await tokenStorage.clearTokens();
      return false;
    }
  }

  ApiException _fromDioException(DioException e) {
    final res = e.response;
    if (res != null) {
      return ApiException(
        message: ApiException.humanize(
          res.data,
          _defaultMessage(res.statusCode ?? 0),
        ),
        statusCode: res.statusCode,
        requestId: res.headers.value('X-Request-ID'),
      );
    }
    final message = switch (e.type) {
      DioExceptionType.connectionTimeout ||
      DioExceptionType.sendTimeout ||
      DioExceptionType.receiveTimeout =>
        'The server took too long to respond. Check your connection and try again.',
      DioExceptionType.connectionError =>
        'Cannot reach CricNetra. Check your internet connection.',
      DioExceptionType.cancel => 'Request cancelled.',
      _ => 'Something went wrong. Please try again.',
    };
    return const ApiException(message: '').copyWith(message: message);
  }

  static String _defaultMessage(int status) => switch (status) {
        400 => 'That request was not valid.',
        401 => 'Please sign in to continue.',
        403 => 'You do not have permission to do that.',
        404 => 'Not found.',
        409 => 'That action conflicts with the current state.',
        422 => 'Please check the details you entered.',
        429 => 'Too many attempts. Please wait a moment and try again.',
        503 => 'The service is temporarily unavailable.',
        _ => status >= 500
            ? 'The server ran into a problem. Please try again.'
            : 'Something went wrong. Please try again.',
      };

  /// Open a Server-Sent Events stream and yield each `data:` payload decoded.
  ///
  /// Used for live scores (`/matches/{id}/stream`, public) and the notification
  /// stream (`/social/notifications/stream?token=`, which takes the token in the
  /// query because EventSource cannot set headers).
  Stream<SseEvent> sse(
    String path, {
    Map<String, dynamic>? query,
    CancelToken? cancelToken,
  }) async* {
    final res = await dio.request<ResponseBody>(
      path,
      queryParameters: query,
      cancelToken: cancelToken,
      options: Options(
        method: 'GET',
        responseType: ResponseType.stream,
        headers: {'Accept': 'text/event-stream'},
        receiveTimeout: Duration.zero, // a live stream never idles out
      ),
    );

    final status = res.statusCode ?? 0;
    if (status < 200 || status >= 300) {
      throw ApiException(
        message: _defaultMessage(status),
        statusCode: status,
      );
    }

    final body = res.data;
    if (body == null) return;

    var buffer = '';
    String? eventName;
    final dataLines = <String>[];

    await for (final chunk in body.stream) {
      buffer += utf8.decode(chunk, allowMalformed: true);

      while (true) {
        final nl = buffer.indexOf('\n');
        if (nl < 0) break;
        var line = buffer.substring(0, nl);
        buffer = buffer.substring(nl + 1);
        if (line.endsWith('\r')) line = line.substring(0, line.length - 1);

        if (line.isEmpty) {
          // Blank line terminates one event.
          if (dataLines.isNotEmpty) {
            yield SseEvent(
              event: eventName ?? 'message',
              data: dataLines.join('\n'),
            );
          }
          eventName = null;
          dataLines.clear();
          continue;
        }
        if (line.startsWith(':')) continue; // keep-alive comment
        if (line.startsWith('event:')) {
          eventName = line.substring(6).trim();
        } else if (line.startsWith('data:')) {
          dataLines.add(line.substring(5).trimLeft());
        }
      }
    }
  }
}

/// One decoded Server-Sent Event.
class SseEvent {
  final String event;
  final String data;

  const SseEvent({required this.event, required this.data});

  /// The payload as JSON, or an empty map when it is not an object.
  Map<String, dynamic> get json {
    try {
      final decoded = jsonDecode(data);
      return decoded is Map ? Map<String, dynamic>.from(decoded) : {};
    } catch (_) {
      return {};
    }
  }
}

extension on ApiException {
  ApiException copyWith({String? message, int? statusCode, String? requestId}) =>
      ApiException(
        message: message ?? this.message,
        statusCode: statusCode ?? this.statusCode,
        requestId: requestId ?? this.requestId,
      );
}
