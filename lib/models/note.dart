class Note {
  final int id;
  final String title;
  final String content;
  final String? grade;
  final String? subject;
  final String? diagramSvg;

  Note({
    required this.id,
    required this.title,
    required this.content,
    this.grade,
    this.subject,
    this.diagramSvg,
  });

  factory Note.fromJson(Map<String, dynamic> json) {
    return Note(
      id: json['id'],
      title: json['title'] ?? '',
      content: json['content'] ?? '',
      grade: json['grade'],
      subject: json['subject'],
      diagramSvg: json['diagram_svg'],
    );
  }
}
