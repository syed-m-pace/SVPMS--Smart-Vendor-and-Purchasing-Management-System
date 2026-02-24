"use client";

import { useState } from "react";
import { User, Lock, LogOut, Building2, CreditCard, Mail, Phone } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { useAuthStore } from "@/lib/stores/auth";
import { authService } from "@/lib/api/auth";
import { changePasswordSchema, type ChangePasswordFormData } from "@/lib/validations/change-password";
import { toast } from "sonner";

function maskAccount(account: string | null | undefined): string {
    if (!account) return "—";
    if (account.length <= 4) return account;
    return "••••" + account.slice(-4);
}

export default function ProfilePage() {
    const { user, vendor, logout } = useAuthStore();
    const [showPasswordDialog, setShowPasswordDialog] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    const {
        register,
        handleSubmit,
        reset,
        formState: { errors },
    } = useForm<ChangePasswordFormData>({
        resolver: zodResolver(changePasswordSchema),
    });

    const onChangePassword = async (data: ChangePasswordFormData) => {
        setSubmitting(true);
        try {
            await authService.changePassword(data.current_password, data.new_password);
            toast.success("Password changed successfully");
            setShowPasswordDialog(false);
            reset();
        } catch (err: any) {
            toast.error(err?.response?.data?.detail || "Failed to change password");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="max-w-2xl mx-auto space-y-6">
            <div>
                <h1 className="text-2xl font-bold">Profile</h1>
                <p className="text-muted-foreground">Your vendor profile and account settings</p>
            </div>

            {/* Avatar & Name */}
            <Card className="p-6">
                <div className="flex items-center gap-5">
                    <div className="flex h-20 w-20 items-center justify-center rounded-full bg-accent/10 text-accent text-2xl font-bold">
                        {vendor?.legal_name?.[0] || user?.first_name?.[0] || "V"}
                    </div>
                    <div>
                        <h2 className="text-xl font-bold">{vendor?.legal_name || `${user?.first_name} ${user?.last_name}`}</h2>
                        <p className="text-muted-foreground">{user?.email}</p>
                        <span className="inline-block mt-1 px-2 py-0.5 rounded text-xs bg-accent/10 text-accent font-medium">
                            Vendor
                        </span>
                    </div>
                </div>
            </Card>

            {/* Vendor Details */}
            {vendor && (
                <Card className="p-6">
                    <h3 className="font-semibold mb-4">Vendor Details</h3>
                    <div className="space-y-4">
                        <ProfileRow icon={Building2} label="Legal Name" value={vendor.legal_name} />
                        {vendor.trade_name && (
                            <ProfileRow icon={Building2} label="Trade Name" value={vendor.trade_name} />
                        )}
                        <ProfileRow icon={Mail} label="Email" value={vendor.email} />
                        {vendor.phone && <ProfileRow icon={Phone} label="Phone" value={vendor.phone} />}
                        {vendor.contact_person && (
                            <ProfileRow icon={User} label="Contact Person" value={vendor.contact_person} />
                        )}
                        <ProfileRow icon={Building2} label="GST / Tax ID" value={vendor.tax_id || "—"} />
                        <ProfileRow icon={CreditCard} label="Bank Account" value={maskAccount(vendor.bank_account)} />
                        {vendor.bank_name && (
                            <ProfileRow icon={CreditCard} label="Bank Name" value={vendor.bank_name} />
                        )}
                        {vendor.ifsc_code && (
                            <ProfileRow icon={CreditCard} label="IFSC Code" value={vendor.ifsc_code} />
                        )}
                    </div>
                </Card>
            )}

            {/* Account Actions */}
            <Card className="p-6">
                <h3 className="font-semibold mb-4">Account</h3>
                <div className="space-y-3">
                    <Button variant="outline" className="w-full justify-start" onClick={() => setShowPasswordDialog(true)}>
                        <Lock className="h-4 w-4 mr-3" /> Change Password
                    </Button>
                    <Button variant="outline" className="w-full justify-start text-destructive hover:text-destructive" onClick={logout}>
                        <LogOut className="h-4 w-4 mr-3" /> Sign Out
                    </Button>
                </div>
                <p className="text-xs text-muted-foreground mt-4">SVPMS Vendor Portal v1.0.0</p>
            </Card>

            {/* Change Password Dialog */}
            <Dialog open={showPasswordDialog} onOpenChange={setShowPasswordDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Change Password</DialogTitle>
                    </DialogHeader>
                    <form onSubmit={handleSubmit(onChangePassword)} className="space-y-4 py-2">
                        <div className="space-y-2">
                            <Label htmlFor="current_password">Current Password</Label>
                            <Input
                                id="current_password"
                                type="password"
                                {...register("current_password")}
                            />
                            {errors.current_password && <p className="text-xs text-destructive">{errors.current_password.message}</p>}
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="new_password">New Password</Label>
                            <Input
                                id="new_password"
                                type="password"
                                {...register("new_password")}
                            />
                            {errors.new_password && <p className="text-xs text-destructive">{errors.new_password.message}</p>}
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="confirm_password">Confirm New Password</Label>
                            <Input
                                id="confirm_password"
                                type="password"
                                {...register("confirm_password")}
                            />
                            {errors.confirm_password && <p className="text-xs text-destructive">{errors.confirm_password.message}</p>}
                        </div>
                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setShowPasswordDialog(false)}>Cancel</Button>
                            <Button type="submit" disabled={submitting}>
                                {submitting ? (
                                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                ) : (
                                    "Change Password"
                                )}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    );
}

function ProfileRow({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
    return (
        <div className="flex items-center gap-3">
            <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
            <div className="flex-1 flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{label}</span>
                <span className="text-sm font-medium">{value}</span>
            </div>
        </div>
    );
}
