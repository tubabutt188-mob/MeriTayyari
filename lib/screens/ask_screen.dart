import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_svg/flutter_svg.dart';
import '../services/api_service.dart';
import '../providers/notes_provider.dart';
import 'home_screen.dart';

class AskScreen extends StatefulWidget {
  final String grade;
  final String subject;

  const AskScreen({super.key, required this.grade, required this.subject});

  @override
  State<AskScreen> createState() => _AskScreenState();
}

class _AskScreenState extends State<AskScreen> {
  final _questionController = TextEditingController();
  final _api = ApiService();

  bool _isLoading = false;
  String? _answer;
  String? _diagramSvg;
  String? _error;

  String get _gradeLabel => kGrades.firstWhere(
    (g) => g['value'] == widget.grade,
    orElse: () => {'label': widget.grade},
  )['label']!;
  String get _subjectLabel => kSubjects.firstWhere(
    (s) => s['value'] == widget.subject,
    orElse: () => {'label': widget.subject},
  )['label']!;

  Future<void> _askQuestion() async {
    final question = _questionController.text.trim();
    if (question.isEmpty) return;

    setState(() {
      _isLoading = true;
      _error = null;
      _answer = null;
      _diagramSvg = null;
    });

    try {
      final result = await _api.ask(
        question: question,
        grade: widget.grade,
        subject: widget.subject,
      );
      setState(() {
        _answer = result.answer;
        _diagramSvg = result.diagramSvg;
      });
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _saveNote() async {
    if (_answer == null) return;
    final title = _questionController.text.trim();
    final notesProvider = context.read<NotesProvider>();
    final success = await notesProvider.saveNote(
      title: title.length > 60 ? '${title.substring(0, 60)}...' : title,
      content: _answer!,
      grade: widget.grade,
      subject: widget.subject,
      diagramSvg: _diagramSvg,
    );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(success ? 'Note saved!' : 'Could not save note')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('$_subjectLabel - $_gradeLabel')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextField(
                controller: _questionController,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: 'Type your question here',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              FilledButton(
                onPressed: _isLoading ? null : _askQuestion,
                child: _isLoading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Text('Get Answer'),
              ),
              const SizedBox(height: 16),
              if (_error != null)
                Text(_error!, style: const TextStyle(color: Colors.red)),
              if (_answer != null)
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(
                        child: SingleChildScrollView(
                          child: Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              border: Border.all(color: Colors.grey.shade300),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                Markdown(
                                  data: _answer!,
                                  shrinkWrap: true,
                                  physics: const NeverScrollableScrollPhysics(),
                                ),
                                if (_diagramSvg != null) ...[
                                  const SizedBox(height: 16),
                                  Container(
                                    padding: const EdgeInsets.all(8),
                                    decoration: BoxDecoration(
                                      color: Colors.white,
                                      borderRadius: BorderRadius.circular(8),
                                      border: Border.all(
                                        color: Colors.grey.shade200,
                                      ),
                                    ),
                                    child: SvgPicture.string(_diagramSvg!),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      FilledButton.icon(
                        icon: const Icon(Icons.bookmark_add_outlined),
                        label: const Text('Save as Note'),
                        onPressed: _saveNote,
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
