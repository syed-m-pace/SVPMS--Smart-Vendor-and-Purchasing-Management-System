class User {
  final String id;
  final String email;
  final String? firstName;
  final String? lastName;
  final String role;
  final String? departmentId;
  final String? profilePhotoUrl;
  final bool isActive;

  const User({
    required this.id,
    required this.email,
    this.firstName,
    this.lastName,
    required this.role,
    this.departmentId,
    this.profilePhotoUrl,
    required this.isActive,
  });

  String get fullName => '$firstName $lastName';

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      email: json['email'],
      firstName: json['first_name'],
      lastName: json['last_name'],
      role: json['role'],
      departmentId: json['department_id'],
      profilePhotoUrl: json['profile_photo_url'],
      isActive: json['is_active'] ?? true,
    );
  }
}
