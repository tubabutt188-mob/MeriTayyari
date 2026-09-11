import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:path_provider/path_provider.dart';
import '../models/note.dart';

/// Result of the /ask endpoint — the text answer plus an optional
/// colorful SVG diagram (null when no diagram was generated).
class AskResult {
  final String answer;
  final String? diagramSvg;

  AskResult({required this.answer, this.diagramSvg});
}

/// Sab backend API calls yahan se hote hain.
///
/// BASE URL: Physical phone (USB/WiFi) se test karte waqt computer ki
/// actual local IP yahan honi chahiye, aur phone + computer ek hi
/// WiFi pe hone chahiye. Yeh IP router restart hone ya WiFi badalne
/// par change ho sakti hai — terminal mein "ipconfig" chala kar
/// "IPv4 Address" dobara check kar lena agar connection fail ho.
///
/// Agar Android Emulator (physical phone nahi) use kar rahe ho, to
/// "10.0.2.2" use karna hoga (emulator ka localhost alias).
class ApiService {
  static const String baseUrl = "http://192.168.100.151:8000";

  final _storage = const FlutterSecureStorage();

  Future<void> _saveToken(String token) async {
    await _storage.write(key: 'access_token', value: token);
  }

  Future<String?> getToken() async {
    return await _storage.read(key: 'access_token');
  }

  Future<void> logout() async {
    await _storage.delete(key: 'access_token');
  }

  Future<Map<String, String>> _authHeaders() async {
    final token = await getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  // ---------- Auth ----------

  Future<void> signup({
    required String email,
    required String password,
    required String name,
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/signup'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password, 'name': name}),
    );
    if (res.statusCode != 200) {
      throw Exception(_errorMessage(res));
    }
    final data = jsonDecode(res.body);
    await _saveToken(data['access_token']);
  }

  Future<void> login({required String email, required String password}) async {
    final res = await http.post(
      Uri.parse('$baseUrl/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );
    if (res.statusCode != 200) {
      throw Exception(_errorMessage(res));
    }
    final data = jsonDecode(res.body);
    await _saveToken(data['access_token']);
  }

  // ---------- Ask (RAG) ----------

  Future<AskResult> ask({
    required String question,
    required String grade,
    required String subject,
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/ask'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'question': question,
        'grade': grade,
        'subject': subject,
      }),
    );
    if (res.statusCode != 200) {
      throw Exception(_errorMessage(res));
    }
    final data = jsonDecode(res.body);
    return AskResult(
      answer: data['answer'] ?? '',
      diagramSvg: data['diagram_svg'],
    );
  }

  // ---------- Notes CRUD ----------

  Future<List<Note>> getNotes() async {
    final res = await http.get(
      Uri.parse('$baseUrl/notes'),
      headers: await _authHeaders(),
    );
    if (res.statusCode != 200) {
      throw Exception(_errorMessage(res));
    }
    final List data = jsonDecode(res.body);
    return data.map((n) => Note.fromJson(n)).toList();
  }

  Future<Note> createNote({
    required String title,
    required String content,
    required String grade,
    required String subject,
    String? diagramSvg,
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/notes'),
      headers: await _authHeaders(),
      body: jsonEncode({
        'title': title,
        'content': content,
        'grade': grade,
        'subject': subject,
        'diagram_svg': diagramSvg,
      }),
    );
    if (res.statusCode != 200) {
      throw Exception(_errorMessage(res));
    }
    return Note.fromJson(jsonDecode(res.body));
  }

  Future<Note> updateNote({
    required int id,
    String? title,
    String? content,
    String? grade,
    String? subject,
    String? diagramSvg,
  }) async {
    final body = <String, dynamic>{};
    if (title != null) body['title'] = title;
    if (content != null) body['content'] = content;
    if (grade != null) body['grade'] = grade;
    if (subject != null) body['subject'] = subject;
    if (diagramSvg != null) body['diagram_svg'] = diagramSvg;

    final res = await http.put(
      Uri.parse('$baseUrl/notes/$id'),
      headers: await _authHeaders(),
      body: jsonEncode(body),
    );
    if (res.statusCode != 200) {
      throw Exception(_errorMessage(res));
    }
    return Note.fromJson(jsonDecode(res.body));
  }

  Future<void> deleteNote(int id) async {
    final res = await http.delete(
      Uri.parse('$baseUrl/notes/$id'),
      headers: await _authHeaders(),
    );
    if (res.statusCode != 200) {
      throw Exception(_errorMessage(res));
    }
  }

  // ---------- PDF export ----------

  /// PDF backend se download karta hai aur device ki app-documents
  /// directory mein save kar ke poora file path return karta hai.
  Future<File> exportPdf() async {
    final res = await http.post(
      Uri.parse('$baseUrl/export-pdf'),
      headers: await _authHeaders(),
    );
    if (res.statusCode != 200) {
      throw Exception(_errorMessage(res));
    }
    final dir = await getApplicationDocumentsDirectory();
    final file = File('${dir.path}/meritayyari_notes.pdf');
    await file.writeAsBytes(res.bodyBytes);
    return file;
  }

  // ---------- Helpers ----------

  String _errorMessage(http.Response res) {
    try {
      final data = jsonDecode(res.body);
      return data['detail']?.toString() ??
          'Something went wrong (${res.statusCode})';
    } catch (_) {
      return 'Something went wrong (${res.statusCode})';
    }
  }
}
