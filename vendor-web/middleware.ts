import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl;

    // Public routes that don't require auth
    const publicRoutes = ["/login"];
    if (publicRoutes.some((route) => pathname.startsWith(route))) {
        return NextResponse.next();
    }

    // Check for auth token
    const token = request.cookies.get("token")?.value;
    if (!token) {
        const loginUrl = new URL("/login", request.url);
        loginUrl.searchParams.set("redirect", pathname);
        return NextResponse.redirect(loginUrl);
    }

    // Decode JWT payload (base64) to check role and expiry
    try {
        const parts = token.split(".");
        if (parts.length !== 3) throw new Error("Invalid token");
        const payload = JSON.parse(
            Buffer.from(parts[1], "base64url").toString("utf8")
        );

        // Check token expiry
        if (payload.exp && payload.exp * 1000 < Date.now()) {
            const loginUrl = new URL("/login", request.url);
            loginUrl.searchParams.set("redirect", pathname);
            return NextResponse.redirect(loginUrl);
        }

        // Only vendor role allowed on vendor portal
        if (payload.role && payload.role !== "vendor") {
            const loginUrl = new URL("/login", request.url);
            loginUrl.searchParams.set("error", "unauthorized_role");
            return NextResponse.redirect(loginUrl);
        }
    } catch {
        // Invalid token — redirect to login
        const loginUrl = new URL("/login", request.url);
        return NextResponse.redirect(loginUrl);
    }

    return NextResponse.next();
}

export const config = {
    matcher: ["/((?!api|_next/static|_next/image|favicon.ico|fonts).*)"],
};
