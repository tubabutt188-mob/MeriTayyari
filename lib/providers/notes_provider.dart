import 'package:flutter/foundation.dart';
import '../models/note.dart';
import '../services/api_service.dart';

class NotesProvider extends ChangeNotifier {
  final ApiService _api = ApiService();

  List<Note> _notes = [];
  bool _isLoading = false;
  String? _error;

  List<Note> get notes => _notes;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> loadNotes() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _notes = await _api.getNotes();
    } catch (e) {
      _error = e.toString().replaceFirst('Exception: ', '');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> saveNote({
    required String title,
    required String content,
    required String grade,
    required String subject,
    String? diagramSvg,
  }) async {
    try {
      final note = await _api.createNote(
        title: title,
        content: content,
        grade: grade,
        subject: subject,
        diagramSvg: diagramSvg,
      );
      _notes.insert(0, note);
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString().replaceFirst('Exception: ', '');
      notifyListeners();
      return false;
    }
  }

  Future<bool> updateNote(int id, {String? title, String? content}) async {
    try {
      final updated = await _api.updateNote(
        id: id,
        title: title,
        content: content,
      );
      final idx = _notes.indexWhere((n) => n.id == id);
      if (idx != -1) _notes[idx] = updated;
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString().replaceFirst('Exception: ', '');
      notifyListeners();
      return false;
    }
  }

  Future<bool> deleteNote(int id) async {
    try {
      await _api.deleteNote(id);
      _notes.removeWhere((n) => n.id == id);
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString().replaceFirst('Exception: ', '');
      notifyListeners();
      return false;
    }
  }
}
