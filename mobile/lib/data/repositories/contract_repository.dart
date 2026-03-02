import '../datasources/api/api_client.dart';
import '../models/contract.dart';

class ContractRepository {
  final ApiClient _api;

  ContractRepository({required ApiClient api}) : _api = api;

  Future<List<Contract>> list({String? status, int page = 1}) async {
    final data = await _api.getContracts(status: status, page: page);
    final items =
        data['data'] as List<dynamic>? ??
        data['items'] as List<dynamic>? ??
        [];
    return items
        .map((e) => Contract.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Contract> getById(String id) async {
    final data = await _api.getContract(id);
    return Contract.fromJson(data);
  }
}
