class DashboardStats {
  final int pendingPRs;
  final int activePOs;
  final int pendingRFQs;
  final int openInvoices;
  final int budgetUtilization;

  const DashboardStats({
    this.pendingPRs = 0,
    this.activePOs = 0,
    this.pendingRFQs = 0,
    this.openInvoices = 0,
    this.budgetUtilization = 0,
  });

  factory DashboardStats.fromJson(Map<String, dynamic> json) {
    return DashboardStats(
      pendingPRs: json['pending_prs'] ?? json['pendingPRs'] ?? 0,
      activePOs: json['active_pos'] ?? json['activePOs'] ?? 0,
      pendingRFQs: json['pending_rfqs'] ?? json['pendingRFQs'] ?? 0,
      openInvoices: json['open_invoices'] ?? json['openInvoices'] ?? 0,
      budgetUtilization:
          json['budget_utilization'] ?? json['budgetUtilization'] ?? 0,
    );
  }
}
