import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
    // Auth is handled client-side via Zustand store in (portal)/layout.tsx
    // Middleware only handles static asset exclusions
    return NextResponse.next();
}

export const config = {
    matcher: ["/((?!api|_next/static|_next/image|favicon.ico|fonts).*)"],
};
