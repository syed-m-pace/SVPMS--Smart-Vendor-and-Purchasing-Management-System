import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
    // Client-side auth check handles the actual redirect logic
    // This middleware only handles the public/protected route split
    const { pathname } = request.nextUrl;

    // Public routes that don't require auth
    const publicRoutes = ["/login"];
    if (publicRoutes.some((route) => pathname.startsWith(route))) {
        return NextResponse.next();
    }

    return NextResponse.next();
}

export const config = {
    matcher: ["/((?!api|_next/static|_next/image|favicon.ico|fonts).*)"],
};
