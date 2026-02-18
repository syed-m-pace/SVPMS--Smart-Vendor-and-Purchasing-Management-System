class User {
  final String id;
  final String email;
  final String firstName;
  final String lastName;
  final String role;
  final String? departmentId;
  final bool isActive;

  User({
    required this.id,
    required this.email,
    required this.firstName,
    required this.lastName,
    required this.role,
    this.departmentId,
    this.isActive = true,
  });

  String get fullName => '$firstName $lastName';

  factory User.fromJson(Map<String, dynamic> json) => User(
    id: json['id'] ?? '',
    email: json['email'] ?? '',
    firstName: json['first_name'] ?? '',
    lastName: json['last_name'] ?? '',
    role: json['role'] ?? '',
    departmentId: json['department_id'],
    isActive: json['is_active'] ?? true,
  );
}
