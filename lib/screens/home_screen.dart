import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:open_filex/open_filex.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import 'ask_screen.dart';
import 'notes_list_screen.dart';
import 'login_screen.dart';

const List<Map<String, String>> kGrades = [
  {'label': 'Grade 9', 'value': '9'},
  {'label': 'Grade 10', 'value': '10'},
  {'label': 'Grade 11', 'value': '11'},
  {'label': 'Grade 12', 'value': '12'},
];

// Subjects common to every grade.
const List<Map<String, String>> _kCoreSubjects = [
  {'label': 'Physics', 'value': 'physics'},
  {'label': 'Chemistry', 'value': 'chemistry'},
  {'label': 'Mathematics', 'value': 'mathematics'},
  {'label': 'Biology', 'value': 'biology'},
  {'label': 'Computer', 'value': 'computer'},
  {'label': 'English', 'value': 'english'},
  {'label': 'Urdu', 'value': 'urdu'},
];

const Map<String, String> _kIslamiyat = {
  'label': 'Islamiyat',
  'value': 'islamiyat',
};
const Map<String, String> _kPakStudy = {
  'label': 'Pak Study',
  'value': 'pak_study',
};

/// Returns the subject list for a given grade:
/// - Grade 9 & 10: core subjects + Islamiyat + Pak Study
/// - Grade 11: core subjects + Islamiyat only
/// - Grade 12: core subjects + Pak Study only
List<Map<String, String>> subjectsForGrade(String grade) {
  switch (grade) {
    case '9':
    case '10':
      return [..._kCoreSubjects, _kIslamiyat, _kPakStudy];
    case '11':
      return [..._kCoreSubjects, _kIslamiyat];
    case '12':
      return [..._kCoreSubjects, _kPakStudy];
    default:
      return _kCoreSubjects;
  }
}

// Kept for any other screens that still reference the full list
// (e.g. resolving a subject label from its value in ask_screen.dart).
const List<Map<String, String>> kSubjects = [
  ..._kCoreSubjects,
  _kIslamiyat,
  _kPakStudy,
];

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  String _grade = kGrades[0]['value']!;
  late String _subject = subjectsForGrade(_grade)[0]['value']!;
  bool _isExporting = false;

  void _onGradeChanged(String newGrade) {
    final newSubjects = subjectsForGrade(newGrade);
    final subjectStillValid = newSubjects.any((s) => s['value'] == _subject);
    setState(() {
      _grade = newGrade;
      if (!subjectStillValid) {
        _subject = newSubjects[0]['value']!;
      }
    });
  }

  Future<void> _exportPdf() async {
    setState(() => _isExporting = true);
    try {
      final file = await ApiService().exportPdf();
      if (!mounted) return;
      await OpenFilex.open(file.path);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'PDF export failed: ${e.toString().replaceFirst('Exception: ', '')}',
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _isExporting = false);
    }
  }

  Future<void> _logout() async {
    await context.read<AuthProvider>().logout();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('MeriTayyari'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: _logout,
            tooltip: 'Logout',
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Select Grade and Subject',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: _grade,
                decoration: const InputDecoration(
                  labelText: 'Grade',
                  border: OutlineInputBorder(),
                ),
                items: kGrades
                    .map(
                      (g) => DropdownMenuItem(
                        value: g['value'],
                        child: Text(g['label']!),
                      ),
                    )
                    .toList(),
                onChanged: (v) => _onGradeChanged(v!),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: _subject,
                decoration: const InputDecoration(
                  labelText: 'Subject',
                  border: OutlineInputBorder(),
                ),
                items: subjectsForGrade(_grade)
                    .map(
                      (s) => DropdownMenuItem(
                        value: s['value'],
                        child: Text(s['label']!),
                      ),
                    )
                    .toList(),
                onChanged: (v) => setState(() => _subject = v!),
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                icon: const Icon(Icons.question_answer_outlined),
                label: const Text('Ask a Question'),
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) =>
                          AskScreen(grade: _grade, subject: _subject),
                    ),
                  );
                },
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                icon: const Icon(Icons.notes_outlined),
                label: const Text('View My Notes'),
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const NotesListScreen()),
                  );
                },
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                icon: _isExporting
                    ? const SizedBox(
                        height: 16,
                        width: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.picture_as_pdf_outlined),
                label: Text(
                  _isExporting ? 'Exporting...' : 'Export All Notes as PDF',
                ),
                onPressed: _isExporting ? null : _exportPdf,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
