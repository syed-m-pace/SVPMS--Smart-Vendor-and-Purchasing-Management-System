# SVPMS Frontend — Vendor Web Portal
## Next.js 14 + TypeScript + Tailwind + shadcn/ui

**Version:** 1.0 | **Date:** February 24, 2026
**Purpose:** Full-featured vendor web portal with parity to Flutter mobile app + web-specific enhancements

---

## 1. Overview

The Vendor Web Portal is a **separate Next.js 14 application** (`vendor-web/`) that gives vendors browser-based access to all procurement workflows. It shares the same backend API and design system as the admin web portal (`web/`) and mobile app (`mobile/`), but is deployed independently at `vendor.svpms.com`.

### Key Design Decisions
- **Separate from admin web** — security isolation, independent deployment, no accidental admin route exposure
- **Full mobile parity** — every feature in the Flutter app is replicated
- **Web-specific extras** — CSV export, bid history, contracts view, analytics, sortable tables, breadcrumb navigation
- **Same design tokens** — unified color scheme from `mobile/lib/core/constants/app_colors.dart`
- **No new backend endpoints** — all 15+ vendor API endpoints already exist

---

## 2. Tech Stack

| Technology | Purpose |
|-----------|---------|
| Next.js 14 (App Router) | Framework + routing |
| TypeScript | Type safety |
| Tailwind CSS + CSS Variables | Styling (shared design tokens) |
| shadcn/ui (Radix primitives) | UI components |
| Zustand + persist | Auth state management |
| Axios | HTTP client with JWT interceptors |
| Zod | Form validation schemas |
| React Hook Form | Form state management |
| react-dropzone | File upload (invoice documents) |
| lucide-react | Icons |
| date-fns | Date formatting |
| sonner | Toast notifications |

---

## 3. Project Structure

```
vendor-web/
├── app/
│   ├── globals.css                     # Design tokens (CSS variables)
│   ├── layout.tsx                      # Root layout + Toaster
│   ├── (auth)/
│   │   ├── layout.tsx                  # Centered unauthenticated layout
│   │   └── login/page.tsx              # Email/password login
│   └── (portal)/
│       ├── layout.tsx                  # Sidebar + Navbar (authenticated)
│       ├── page.tsx                    # Dashboard
│       ├── purchase-orders/
│       │   ├── page.tsx                # PO list + filters + CSV export
│       │   └── [id]/page.tsx           # PO detail + acknowledge
│       ├── rfqs/
│       │   ├── page.tsx                # RFQ list + filters
│       │   ├── bids/page.tsx           # Bid history (web extra)
│       │   └── [id]/
│       │       ├── page.tsx            # RFQ detail + bid display
│       │       └── bid/page.tsx        # Submit/update bid form
│       ├── invoices/
│       │   ├── page.tsx                # Invoice list + filters + CSV export
│       │   ├── upload/page.tsx         # Upload invoice form
│       │   └── [id]/page.tsx           # Detail + status banners + dispute
│       ├── contracts/page.tsx          # Contracts list (web extra)
│       ├── analytics/page.tsx          # Scorecard + spend analytics (web extra)
│       ├── notifications/page.tsx      # Notification inbox
│       └── profile/page.tsx            # Vendor info + change password
├── components/
│   ├── ui/                             # shadcn/ui primitives
│   └── shared/
│       ├── Sidebar.tsx                 # Left nav with vendor branding
│       ├── Navbar.tsx                  # Breadcrumbs + notification bell
│       ├── DataTable.tsx               # Sortable, paginated, exportable
│       ├── StatusBadge.tsx             # Status-to-color pill
│       └── EmptyState.tsx              # Empty data placeholder
├── lib/
│   ├── api/                            # Axios service files per entity
│   ├── stores/                         # Zustand (auth, ui)
│   ├── validations/                    # Zod schemas (bid, invoice, password)
│   └── utils.ts                        # cn(), formatCurrency(), formatDate(), exportCSV()
├── types/models.ts                     # TypeScript interfaces
└── middleware.ts                       # Next.js middleware
```

**Total: 15 pages | ~40 components | ~18 library files**

---

## 4. Pages & Features

### 4.1 Authentication
| Page | Route | Features |
|------|-------|----------|
| Login | `/login` | Email/password, vendor-role check, demo credentials, JWT storage |

### 4.2 Dashboard
| Page | Route | Features |
|------|-------|----------|
| Dashboard | `/` | 4 KPI stat cards (Active POs, Pending RFQs, Open Invoices, Exceptions), recent POs list, scorecard summary |

### 4.3 Purchase Orders
| Page | Route | Features |
|------|-------|----------|
| PO List | `/purchase-orders` | Status filter tabs, sortable columns, CSV export, pagination |
| PO Detail | `/purchase-orders/[id]` | Order info, line items table, Acknowledge dialog with date picker |

### 4.4 RFQs
| Page | Route | Features |
|------|-------|----------|
| RFQ List | `/rfqs` | Status filters (All/Open/Awarded), bid submitted indicator |
| RFQ Detail | `/rfqs/[id]` | Line items, deadline, budget, existing bid display, award banner with PO link |
| Bid Form | `/rfqs/[id]/bid` | Amount, lead time, notes (Zod validated), pre-fills for existing bid |
| Bid History | `/rfqs/bids` | All past bids across RFQs, win/loss status (web extra) |

### 4.5 Invoices
| Page | Route | Features |
|------|-------|----------|
| Invoice List | `/invoices` | Status filter tabs, sortable columns, CSV export |
| Upload Invoice | `/invoices/upload` | PO selector, invoice #, date, amount, drag-and-drop file upload |
| Invoice Detail | `/invoices/[id]` | Status banners (UPLOADED/MATCHED/EXCEPTION/PAID), OCR/match status, view document, dispute dialog |

### 4.6 Web Extras
| Page | Route | Features |
|------|-------|----------|
| Contracts | `/contracts` | Active contracts list with status filters |
| Analytics | `/analytics` | Performance scorecard gauges, spend by month, total spend |

### 4.7 Notifications & Profile
| Page | Route | Features |
|------|-------|----------|
| Notifications | `/notifications` | Inbox with icons by type, relative timestamps, deep-link to entities, clear all |
| Profile | `/profile` | Vendor info (legal name, GST, masked bank), change password dialog, sign out |

---

## 5. API Endpoints Used

All endpoints are already implemented in the backend. No new endpoints required.

| Area | Endpoints |
|------|-----------|
| Auth | `POST /auth/login`, `POST /auth/refresh`, `POST /api/v1/auth/change-password` |
| Profile | `GET /api/v1/vendors/me`, `GET /api/v1/users/me`, `PUT /api/v1/users/{id}` |
| Dashboard | `GET /api/v1/dashboard/stats` |
| POs | `GET /api/v1/purchase-orders`, `GET …/{id}`, `POST …/{id}/acknowledge` |
| RFQs | `GET /api/v1/rfqs`, `GET …/{id}`, `POST …/{id}/bids` |
| Invoices | `GET /api/v1/invoices`, `GET …/{id}`, `POST /api/v1/invoices`, `POST …/{id}/dispute` |
| Files | `POST /api/v1/files/upload`, `GET /api/v1/files/{key}` |
| Scorecard | `GET /api/v1/vendors/{id}/scorecard` |
| Analytics | `GET /api/v1/analytics/spend` |
| Contracts | `GET /api/v1/contracts` |

---

## 6. Design System

Shared CSS variables matching `mobile/lib/core/constants/app_colors.dart`:

```css
--primary: 222 47% 31%;       /* #2A3F5F Deep navy */
--accent: 199 89% 48%;        /* #0EA5E9 Sky blue */
--success: 142 71% 45%;       /* #22C55E */
--warning: 38 92% 50%;        /* #F4B445 */
--destructive: 0 84% 60%;     /* #EF4444 */
--info: 262 83% 58%;          /* #8B5CF6 Violet */
--background: 210 20% 98%;    /* #F8FAFC */
--sidebar: 222 47% 18%;       /* #1E3050 */
```

---

## 7. State Management

| Store | Purpose | Persistence |
|-------|---------|-------------|
| `useAuthStore` | User, vendor, JWT tokens, login/logout | localStorage (zustand/persist) |
| `useUIStore` | Sidebar open/closed, refresh counter | Memory only |

---

## 8. Development

```bash
cd vendor-web
npm install
npm run dev          # http://localhost:3001
npm run build        # Production build
npm run lint         # ESLint check
```

**Backend CORS**: Add `http://localhost:3001` to `CORS_ORIGINS` in `.env`.

**Test credentials**: `sales@alphasupplies.com` / `SvpmsTest123!`

---

## 9. Deployment

- **Platform**: Vercel (separate project from admin web)
- **Domain**: `vendor.svpms.com`
- **Environment variables**: `NEXT_PUBLIC_API_URL` pointing to Cloud Run backend
- **CORS**: Production domain must be added to backend `CORS_ORIGINS`
