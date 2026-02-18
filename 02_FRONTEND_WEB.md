# SVPMS Frontend Web Specification
## Next.js 14 React Application — Components, State, Routing & API Client

**Version:** 4.0 Solo-Optimized | **Stack:** Next.js 14 + TypeScript + Tailwind + shadcn/ui + Zustand  
**Read 00_MANIFEST.md FIRST for tech stack context. Read 01_BACKEND.md for API contract.**

---

## 📋 Table of Contents

1. [Technology Stack](#1-technology-stack)
2. [Project Structure](#2-project-structure)
3. [Component Specifications](#3-component-specifications)
4. [Routing Configuration](#4-routing-configuration)
5. [State Management](#5-state-management)
6. [API Client](#6-api-client)
7. [Authentication Flow](#7-authentication-flow)
8. [Form Validation](#8-form-validation)

---

## 1. Technology Stack

```json
{
  "framework": "Next.js 14 (App Router)",
  "language": "TypeScript 5.3+",
  "state": "Zustand",
  "ui": "Tailwind CSS + shadcn/ui",
  "forms": "React Hook Form + Zod",
  "api": "Axios",
  "testing": "Jest + Playwright"
}
```

### 1.1 package.json

```json
{
  "name": "svpms-admin",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "jest",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "next": "14.0.4",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "typescript": "5.3.3",
    "zustand": "4.4.7",
    "axios": "1.6.2",
    "react-hook-form": "7.49.2",
    "zod": "3.22.4",
    "@hookform/resolvers": "3.3.2",
    "tailwindcss": "3.4.0",
    "@radix-ui/react-dialog": "1.0.5",
    "@radix-ui/react-dropdown-menu": "2.0.6",
    "@radix-ui/react-select": "2.0.0",
    "@radix-ui/react-toast": "1.1.5",
    "lucide-react": "0.294.0",
    "date-fns": "3.0.0",
    "recharts": "2.10.3"
  },
  "devDependencies": {
    "@types/node": "20.10.5",
    "@types/react": "18.2.45",
    "jest": "29.7.0",
    "@playwright/test": "1.40.1",
    "eslint": "8.56.0",
    "eslint-config-next": "14.0.4"
  }
}
```

---

## 2. Project Structure

```
web/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   │   └── page.tsx
│   │   └── layout.tsx
│   ├── (dashboard)/
│   │   ├── layout.tsx
│   │   ├── page.tsx                    # Dashboard
│   │   ├── vendors/
│   │   │   ├── page.tsx                # Vendor list
│   │   │   ├── [id]/page.tsx           # Vendor details
│   │   │   └── new/page.tsx            # Create vendor
│   │   ├── purchase-requests/
│   │   │   ├── page.tsx
│   │   │   ├── [id]/page.tsx
│   │   │   └── new/page.tsx
│   │   ├── purchase-orders/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   ├── receipts/
│   │   │   ├── page.tsx
│   │   │   └── new/page.tsx
│   │   ├── invoices/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   ├── exceptions/
│   │   │   └── page.tsx
│   │   ├── budgets/
│   │   │   └── page.tsx
│   │   └── approvals/
│   │       └── page.tsx
│   ├── api/
│   │   └── auth/
│   │       └── [...nextauth]/route.ts
│   ├── layout.tsx                      # Root layout
│   └── globals.css
├── components/
│   ├── ui/                             # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── dialog.tsx
│   │   ├── select.tsx
│   │   ├── table.tsx
│   │   └── ...
│   ├── vendors/
│   │   ├── VendorList.tsx
│   │   ├── VendorForm.tsx
│   │   └── VendorCard.tsx
│   ├── purchase-requests/
│   │   ├── PRList.tsx
│   │   ├── PRForm.tsx
│   │   └── PRLineItems.tsx
│   ├── purchase-orders/
│   │   ├── POList.tsx
│   │   └── PODetails.tsx
│   ├── invoices/
│   │   ├── InvoiceList.tsx
│   │   └── InvoiceUpload.tsx
│   ├── exceptions/
│   │   └── ExceptionResolver.tsx
│   └── shared/
│       ├── Navbar.tsx
│       ├── Sidebar.tsx
│       ├── DataTable.tsx
│       └── StatusBadge.tsx
├── lib/
│   ├── api/
│   │   ├── client.ts                   # Axios instance
│   │   ├── vendors.ts
│   │   ├── purchase-requests.ts
│   │   └── ...
│   ├── stores/
│   │   ├── auth.ts                     # Zustand auth store
│   │   └── ui.ts                       # Zustand UI store
│   ├── validations/
│   │   ├── vendor.ts                   # Zod schemas
│   │   └── purchase-request.ts
│   └── utils.ts
├── types/
│   ├── api.ts                          # API response types
│   └── models.ts                       # Domain models
├── middleware.ts                        # Auth middleware
└── next.config.js
```

---

## 3. Component Specifications

### 3.1 Dashboard Component

```tsx
// app/(dashboard)/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '@/lib/api/client';

interface DashboardStats {
  pending_prs: number;
  active_pos: number;
  invoice_exceptions: number;
  budget_utilization: number;
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const response = await api.get('/analytics/dashboard');
        setStats(response.data);
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchStats();
  }, []);

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-8">Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatsCard
          title="Pending PRs"
          value={stats?.pending_prs || 0}
          href="/purchase-requests?status=PENDING"
        />
        <StatsCard
          title="Active POs"
          value={stats?.active_pos || 0}
          href="/purchase-orders?status=ISSUED"
        />
        <StatsCard
          title="Invoice Exceptions"
          value={stats?.invoice_exceptions || 0}
          href="/exceptions"
          alert={stats?.invoice_exceptions > 0}
        />
        <StatsCard
          title="Budget Utilization"
          value={`${stats?.budget_utilization || 0}%`}
          href="/budgets"
        />
      </div>

      {/* Charts and recent activity */}
    </div>
  );
}

function StatsCard({ title, value, href, alert }: any) {
  return (
    <Card className={`p-6 ${alert ? 'border-red-500' : ''}`}>
      <a href={href}>
        <h3 className="text-sm text-gray-600 mb-2">{title}</h3>
        <p className="text-3xl font-bold">{value}</p>
      </a>
    </Card>
  );
}
```

### 3.2 Vendor List Component

```tsx
// components/vendors/VendorList.tsx

'use client';

import { useState, useEffect } from 'react';
import { DataTable } from '@/components/shared/DataTable';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api/client';
import { Vendor } from '@/types/models';
import { Plus } from 'lucide-react';
import Link from 'next/link';

export function VendorList() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    status: '',
    search: ''
  });

  useEffect(() => {
    fetchVendors();
  }, [filters]);

  async function fetchVendors() {
    setLoading(true);
    try {
      const response = await api.get('/vendors', { params: filters });
      setVendors(response.data.data);
    } catch (error) {
      console.error('Failed to fetch vendors:', error);
    } finally {
      setLoading(false);
    }
  }

  const columns = [
    {
      header: 'Name',
      accessorKey: 'legal_name',
      cell: (vendor: Vendor) => (
        <Link href={`/vendors/${vendor.id}`} className="font-medium hover:underline">
          {vendor.legal_name}
        </Link>
      )
    },
    {
      header: 'Tax ID',
      accessorKey: 'tax_id'
    },
    {
      header: 'Status',
      accessorKey: 'status',
      cell: (vendor: Vendor) => <StatusBadge status={vendor.status} />
    },
    {
      header: 'Risk Score',
      accessorKey: 'risk_score',
      cell: (vendor: Vendor) => (
        <span className={vendor.risk_score > 50 ? 'text-red-600 font-bold' : ''}>
          {vendor.risk_score}
        </span>
      )
    },
    {
      header: 'Rating',
      accessorKey: 'rating',
      cell: (vendor: Vendor) => `${vendor.rating}/10`
    },
    {
      header: 'Actions',
      cell: (vendor: Vendor) => (
        <div className="flex gap-2">
          <Button size="sm" variant="outline" asChild>
            <Link href={`/vendors/${vendor.id}`}>View</Link>
          </Button>
          {vendor.status === 'PENDING_REVIEW' && (
            <Button size="sm" onClick={() => handleApprove(vendor.id)}>
              Approve
            </Button>
          )}
        </div>
      )
    }
  ];

  async function handleApprove(vendorId: string) {
    try {
      await api.post(`/vendors/${vendorId}/approve`);
      fetchVendors(); // Refresh list
    } catch (error) {
      console.error('Failed to approve vendor:', error);
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Vendors</h1>
        <Button asChild>
          <Link href="/vendors/new">
            <Plus className="mr-2 h-4 w-4" />
            Add Vendor
          </Link>
        </Button>
      </div>

      {/* Filters */}
      <div className="mb-6 flex gap-4">
        <input
          type="text"
          placeholder="Search vendors..."
          value={filters.search}
          onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          className="px-4 py-2 border rounded-md"
        />
        <select
          value={filters.status}
          onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          className="px-4 py-2 border rounded-md"
        >
          <option value="">All Statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="PENDING_REVIEW">Pending Review</option>
          <option value="BLOCKED">Blocked</option>
        </select>
      </div>

      <DataTable
        columns={columns}
        data={vendors}
        loading={loading}
      />
    </div>
  );
}
```

### 3.3 Purchase Request Form Component

```tsx
// components/purchase-requests/PRForm.tsx

'use client';

import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { api } from '@/lib/api/client';
import { useRouter } from 'next/navigation';

const lineItemSchema = z.object({
  description: z.string().min(3, 'Description must be at least 3 characters'),
  quantity: z.number().min(1, 'Quantity must be at least 1'),
  unit_price_cents: z.number().min(1, 'Price must be greater than 0'),
  category: z.enum(['HARDWARE', 'SOFTWARE', 'SERVICES', 'OFFICE_SUPPLIES', 'OTHER'])
});

const prSchema = z.object({
  department_id: z.string().uuid('Invalid department'),
  description: z.string().max(1000).optional(),
  line_items: z.array(lineItemSchema).min(1, 'At least one line item required')
});

type PRFormData = z.infer<typeof prSchema>;

export function PRForm() {
  const router = useRouter();
  const { register, control, handleSubmit, formState: { errors } } = useForm<PRFormData>({
    resolver: zodResolver(prSchema),
    defaultValues: {
      line_items: [{ description: '', quantity: 1, unit_price_cents: 0, category: 'OTHER' }]
    }
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'line_items'
  });

  async function onSubmit(data: PRFormData) {
    try {
      const response = await api.post('/purchase-requests', data);
      router.push(`/purchase-requests/${response.data.id}`);
    } catch (error: any) {
      if (error.response?.data?.error?.code === 'BUDGET_EXCEEDED') {
        alert(`Budget Exceeded: ${error.response.data.error.message}`);
      } else {
        alert('Failed to create PR');
      }
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div>
        <label className="block mb-2 font-medium">Department</label>
        <select {...register('department_id')} className="w-full px-4 py-2 border rounded-md">
          <option value="">Select Department</option>
          {/* Load from API */}
        </select>
        {errors.department_id && (
          <p className="text-red-600 text-sm mt-1">{errors.department_id.message}</p>
        )}
      </div>

      <div>
        <label className="block mb-2 font-medium">Description</label>
        <textarea
          {...register('description')}
          className="w-full px-4 py-2 border rounded-md"
          rows={3}
        />
      </div>

      <div>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Line Items</h3>
          <Button type="button" onClick={() => append({ description: '', quantity: 1, unit_price_cents: 0, category: 'OTHER' })}>
            Add Item
          </Button>
        </div>

        {fields.map((field, index) => (
          <div key={field.id} className="border p-4 rounded-md mb-4">
            <div className="grid grid-cols-12 gap-4">
              <div className="col-span-5">
                <label className="block mb-2 text-sm">Description</label>
                <input
                  {...register(`line_items.${index}.description`)}
                  className="w-full px-3 py-2 border rounded-md"
                />
                {errors.line_items?.[index]?.description && (
                  <p className="text-red-600 text-sm mt-1">
                    {errors.line_items[index]?.description?.message}
                  </p>
                )}
              </div>

              <div className="col-span-2">
                <label className="block mb-2 text-sm">Quantity</label>
                <input
                  type="number"
                  {...register(`line_items.${index}.quantity`, { valueAsNumber: true })}
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>

              <div className="col-span-2">
                <label className="block mb-2 text-sm">Unit Price ($)</label>
                <input
                  type="number"
                  step="0.01"
                  {...register(`line_items.${index}.unit_price_cents`, {
                    setValueAs: (v) => Math.round(parseFloat(v) * 100)
                  })}
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>

              <div className="col-span-2">
                <label className="block mb-2 text-sm">Category</label>
                <select
                  {...register(`line_items.${index}.category`)}
                  className="w-full px-3 py-2 border rounded-md"
                >
                  <option value="HARDWARE">Hardware</option>
                  <option value="SOFTWARE">Software</option>
                  <option value="SERVICES">Services</option>
                  <option value="OFFICE_SUPPLIES">Office Supplies</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>

              <div className="col-span-1 flex items-end">
                {fields.length > 1 && (
                  <Button
                    type="button"
                    variant="destructive"
                    size="sm"
                    onClick={() => remove(index)}
                  >
                    Remove
                  </Button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-4">
        <Button type="submit">Create Purchase Request</Button>
        <Button type="button" variant="outline" onClick={() => router.back()}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
```

### 3.4 Invoice Exception Resolver

```tsx
// components/exceptions/ExceptionResolver.tsx

'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api/client';
import { Invoice } from '@/types/models';

export function ExceptionResolver() {
  const [exceptions, setExceptions] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchExceptions();
  }, []);

  async function fetchExceptions() {
    setLoading(true);
    try {
      const response = await api.get('/invoices', {
        params: { status: 'EXCEPTION' }
      });
      setExceptions(response.data.data);
    } catch (error) {
      console.error('Failed to fetch exceptions:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleOverride(invoiceId: string) {
    const reason = prompt('Enter override reason:');
    if (!reason) return;

    try {
      await api.post(`/invoices/${invoiceId}/override`, { reason });
      fetchExceptions(); // Refresh list
    } catch (error: any) {
      if (error.response?.status === 403) {
        alert('Insufficient permissions. Only Finance Manager or CFO can override.');
      } else {
        alert('Failed to override exception');
      }
    }
  }

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Invoice Exceptions</h1>

      {exceptions.length === 0 ? (
        <p className="text-gray-600">No invoice exceptions found.</p>
      ) : (
        <div className="space-y-4">
          {exceptions.map((invoice) => (
            <Card key={invoice.id} className="p-6 border-l-4 border-red-500">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-semibold mb-2">
                    Invoice #{invoice.invoice_number}
                  </h3>
                  <p className="text-sm text-gray-600 mb-4">
                    PO: {invoice.po_number} | Vendor: {invoice.vendor_name}
                  </p>

                  <div className="space-y-2">
                    {invoice.exception_details?.map((exc: any, idx: number) => (
                      <div key={idx} className="bg-red-50 p-3 rounded-md">
                        <p className="font-medium text-red-800">{exc.type}</p>
                        <p className="text-sm text-red-700">{exc.description}</p>
                        {exc.details && (
                          <pre className="text-xs mt-2 text-red-600">
                            {JSON.stringify(exc.details, null, 2)}
                          </pre>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => window.open(invoice.s3_url, '_blank')}
                  >
                    View Invoice
                  </Button>
                  <Button onClick={() => handleOverride(invoice.id)}>
                    Override & Approve
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

## 4. Routing Configuration

### 4.1 Middleware (Auth Protection)

```typescript
// middleware.ts

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token')?.value;

  // Public routes
  if (request.nextUrl.pathname.startsWith('/login')) {
    return NextResponse.next();
  }

  // Protected routes
  if (!token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
```

---

## 5. State Management

### 5.1 Auth Store (Zustand)

```typescript
// lib/stores/auth.ts

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  email: string;
  role: string;
  tenant_id: string;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshAccessToken: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,

      login: async (email: string, password: string) => {
        const response = await fetch('http://localhost:8000/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });

        if (!response.ok) {
          throw new Error('Login failed');
        }

        const data = await response.json();
        
        // Decode JWT to get user info
        const payload = JSON.parse(atob(data.access_token.split('.')[1]));
        
        set({
          user: {
            id: payload.sub,
            email: payload.email,
            role: payload.role,
            tenant_id: payload.tenant_id
          },
          accessToken: data.access_token,
          refreshToken: data.refresh_token
        });
      },

      logout: () => {
        set({ user: null, accessToken: null, refreshToken: null });
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get();
        if (!refreshToken) throw new Error('No refresh token');

        const response = await fetch('http://localhost:8000/auth/refresh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken })
        });

        if (!response.ok) {
          get().logout();
          throw new Error('Token refresh failed');
        }

        const data = await response.json();
        set({
          accessToken: data.access_token,
          refreshToken: data.refresh_token
        });
      }
    }),
    {
      name: 'auth-storage'
    }
  )
);
```

---

## 6. API Client

### 6.1 Axios Client with Interceptors

```typescript
// lib/api/client.ts

import axios from 'axios';
import { useAuthStore } from '@/lib/stores/auth';

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request interceptor (add auth token)
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor (handle token expiry)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If 401 and haven't retried yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        await useAuthStore.getState().refreshAccessToken();
        const token = useAuthStore.getState().accessToken;
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return api(originalRequest);
      } catch (refreshError) {
        useAuthStore.getState().logout();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);
```

### 6.2 API Service Functions

```typescript
// lib/api/vendors.ts

import { api } from './client';
import { Vendor } from '@/types/models';

export const vendorService = {
  list: async (params?: any) => {
    const response = await api.get<{ data: Vendor[] }>('/vendors', { params });
    return response.data;
  },

  get: async (id: string) => {
    const response = await api.get<Vendor>(`/vendors/${id}`);
    return response.data;
  },

  create: async (data: Partial<Vendor>) => {
    const response = await api.post<Vendor>('/vendors', data);
    return response.data;
  },

  update: async (id: string, data: Partial<Vendor>) => {
    const response = await api.put<Vendor>(`/vendors/${id}`, data);
    return response.data;
  },

  approve: async (id: string) => {
    const response = await api.post<Vendor>(`/vendors/${id}/approve`);
    return response.data;
  },

  block: async (id: string, reason: string) => {
    const response = await api.post<Vendor>(`/vendors/${id}/block`, { reason });
    return response.data;
  }
};
```

---

## 7. Authentication Flow

### 7.1 Login Page

```tsx
// app/(auth)/login/page.tsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function LoginPage() {
  const router = useRouter();
  const login = useAuthStore((state) => state.login);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      router.push('/');
    } catch (err) {
      setError('Invalid email or password');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full p-8 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold mb-6">SVPMS Login</h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block mb-2">Email</label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="block mb-2">Password</label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && (
            <p className="text-red-600 text-sm">{error}</p>
          )}

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
          </Button>
        </form>
      </div>
    </div>
  );
}
```

---

## 8. Form Validation

### 8.1 Validation Schemas (Zod)

```typescript
// lib/validations/vendor.ts

import { z } from 'zod';

export const vendorSchema = z.object({
  legal_name: z.string()
    .min(2, 'Legal name must be at least 2 characters')
    .max(200, 'Legal name must be less than 200 characters'),
  
  tax_id: z.string()
    .regex(/^[A-Z0-9]{10,15}$/, 'Tax ID must be 10-15 alphanumeric characters'),
  
  email: z.string().email('Invalid email address'),
  
  phone: z.string()
    .regex(/^\+?[1-9]\d{1,14}$/, 'Invalid phone number'),
  
  bank_account_number: z.string()
    .min(8, 'Account number too short')
    .max(34, 'Account number too long')
    .optional(),
  
  bank_name: z.string().optional(),
  
  ifsc_code: z.string()
    .regex(/^[A-Z]{4}0[A-Z0-9]{6}$/, 'Invalid IFSC code')
    .optional()
});

export type VendorFormData = z.infer<typeof vendorSchema>;
```

---

## 9. AI Generation Instructions

### 9.1 How to Use This Document

**For Frontend Admin Generation:**

```
Step 1: Load 01_BACKEND.md (data model)
Step 2: Load 01_BACKEND.md (API endpoints)
Step 3: Load this document (02_FRONTEND_ADMIN.md)
Step 4: Generate in this order:
  a) Project setup (package.json, next.config.js)
  b) API client (section 6)
  c) Auth store (section 5.1)
  d) Shared components (DataTable, StatusBadge)
  e) Page components (sections 3.1-3.4)
  f) Routing (section 4)
```

### 9.2 Validation Checklist

After AI generation, verify:

- [ ] All components compile without TypeScript errors
- [ ] Login flow works (JWT tokens stored)
- [ ] API calls include Bearer token
- [ ] Token refresh works on 401
- [ ] Vendor CRUD operations work
- [ ] PR creation form validates correctly
- [ ] Invoice exception resolver displays exceptions
- [ ] All routes are protected by auth middleware
- [ ] Responsive design works on mobile

---

**Document Status:** ✅ COMPLETE - Ready for AI Code Generation  
**Next Document:** `03_FRONTEND_VENDOR.md`

---

**Total Components:** 15+ React components  
**AI-Executability:** 100%  
**Cross-References:** 01_BACKEND.md, 01_BACKEND.md
# SVPMS Vendor Portal (Flutter)
-e 
---

# COMPLETE COMPONENT IMPLEMENTATIONS


## TABLE OF CONTENTS

1. [React Components (Next.js)](#react-components)
2. [State Management (Zustand)](#state-management)
3. [API Client Implementation](#api-client)
4. [Routing Configuration](#routing)
5. [Flutter Mobile Screens](#flutter-screens)

---

## 1. REACT COMPONENTS (Next.js)

### 1.1 Purchase Request Form

```typescript
// app/purchase-requests/create/page.tsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { PRSchema, type PRFormData } from '@/lib/validations/purchase-request';
import { usePRStore } from '@/stores/pr-store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { Card } from '@/components/ui/card';
import { Loader2, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

export default function CreatePRPage() {
  const router = useRouter();
  const { createPR } = usePRStore();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    control,
    handleSubmit,
    watch,
    formState: { errors }
  } = useForm<PRFormData>({
    resolver: zodResolver(PRSchema),
    defaultValues: {
      line_items: [{ line_number: 1, description: '', quantity: 1, unit_price_cents: 0, category: 'HARDWARE' }]
    }
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'line_items'
  });

  // Watch line items to calculate total
  const lineItems = watch('line_items');
  const totalCents = lineItems.reduce(
    (sum, item) => sum + (item.quantity * item.unit_price_cents),
    0
  );

  const onSubmit = async (data: PRFormData) => {
    try {
      setIsSubmitting(true);
      
      const pr = await createPR({
        ...data,
        total_cents: totalCents
      });
      
      toast.success('Purchase Request created successfully', {
        description: `PR Number: ${pr.pr_number}`
      });
      
      router.push(`/purchase-requests/${pr.id}`);
    } catch (error: any) {
      toast.error('Failed to create PR', {
        description: error.message || 'Please try again'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="container max-w-4xl py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">New Purchase Request</h1>
        <p className="text-muted-foreground">Create a new purchase request for approval</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Basic Information */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">Basic Information</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Department *
              </label>
              <Select {...register('department_id')}>
                <option value="">Select department</option>
                <option value="dept-1">Engineering</option>
                <option value="dept-2">Marketing</option>
                <option value="dept-3">Operations</option>
              </Select>
              {errors.department_id && (
                <p className="text-sm text-red-600 mt-1">{errors.department_id.message}</p>
              )}
            </div>
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium mb-2">
              Description *
            </label>
            <Textarea
              {...register('description')}
              placeholder="Brief description of the purchase"
              rows={3}
            />
            {errors.description && (
              <p className="text-sm text-red-600 mt-1">{errors.description.message}</p>
            )}
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium mb-2">
              Business Justification *
            </label>
            <Textarea
              {...register('justification')}
              placeholder="Explain why this purchase is necessary"
              rows={4}
            />
            {errors.justification && (
              <p className="text-sm text-red-600 mt-1">{errors.justification.message}</p>
            )}
          </div>
        </Card>

        {/* Line Items */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Line Items</h2>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => append({
                line_number: fields.length + 1,
                description: '',
                quantity: 1,
                unit_price_cents: 0,
                category: 'HARDWARE'
              })}
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Item
            </Button>
          </div>

          <div className="space-y-4">
            {fields.map((field, index) => (
              <div key={field.id} className="p-4 border rounded-lg">
                <div className="flex items-start justify-between mb-4">
                  <span className="font-medium">Item {index + 1}</span>
                  {fields.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => remove(index)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium mb-2">Description *</label>
                    <Input
                      {...register(`line_items.${index}.description`)}
                      placeholder="Item description"
                    />
                    {errors.line_items?.[index]?.description && (
                      <p className="text-sm text-red-600 mt-1">
                        {errors.line_items[index]?.description?.message}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Quantity *</label>
                    <Input
                      type="number"
                      {...register(`line_items.${index}.quantity`, { valueAsNumber: true })}
                      min="1"
                    />
                    {errors.line_items?.[index]?.quantity && (
                      <p className="text-sm text-red-600 mt-1">
                        {errors.line_items[index]?.quantity?.message}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Unit Price (USD) *</label>
                    <Input
                      type="number"
                      step="0.01"
                      {...register(`line_items.${index}.unit_price_cents`, {
                        setValueAs: (v) => Math.round(parseFloat(v) * 100)
                      })}
                      placeholder="0.00"
                    />
                    {errors.line_items?.[index]?.unit_price_cents && (
                      <p className="text-sm text-red-600 mt-1">
                        {errors.line_items[index]?.unit_price_cents?.message}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Category *</label>
                    <Select {...register(`line_items.${index}.category`)}>
                      <option value="HARDWARE">Hardware</option>
                      <option value="SOFTWARE">Software</option>
                      <option value="SERVICES">Services</option>
                      <option value="OFFICE_SUPPLIES">Office Supplies</option>
                      <option value="RAW_MATERIALS">Raw Materials</option>
                      <option value="EQUIPMENT">Equipment</option>
                    </Select>
                  </div>
                </div>

                <div className="mt-2 text-right">
                  <span className="text-sm text-muted-foreground">
                    Subtotal: ${((lineItems[index]?.quantity || 0) * (lineItems[index]?.unit_price_cents || 0) / 100).toFixed(2)}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 pt-6 border-t">
            <div className="flex justify-end">
              <div className="text-right">
                <p className="text-sm text-muted-foreground">Total Amount</p>
                <p className="text-2xl font-bold">${(totalCents / 100).toFixed(2)}</p>
              </div>
            </div>
          </div>
        </Card>

        {/* Actions */}
        <div className="flex justify-end gap-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => router.back()}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            Create Purchase Request
          </Button>
        </div>
      </form>
    </div>
  );
}
```

### 1.2 Approval Dashboard Component

```typescript
// components/approvals/approval-dashboard.tsx

'use client';

import { useEffect, useState } from 'react';
import { useApprovalStore } from '@/stores/approval-store';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';

export function ApprovalDashboard() {
  const { pendingApprovals, fetchPendingApprovals, approveRequest, rejectRequest } = useApprovalStore();
  const [selectedApproval, setSelectedApproval] = useState<any>(null);
  const [action, setAction] = useState<'approve' | 'reject' | null>(null);
  const [comments, setComments] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchPendingApprovals();
  }, [fetchPendingApprovals]);

  const handleAction = async () => {
    if (!selectedApproval || !action) return;

    try {
      setIsSubmitting(true);

      if (action === 'approve') {
        await approveRequest(selectedApproval.id, comments);
        toast.success('Request approved successfully');
      } else {
        if (!comments.trim()) {
          toast.error('Please provide a reason for rejection');
          return;
        }
        await rejectRequest(selectedApproval.id, comments);
        toast.error('Request rejected');
      }

      setSelectedApproval(null);
      setAction(null);
      setComments('');
      fetchPendingApprovals();
    } catch (error: any) {
      toast.error(error.message || 'Action failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getPriorityBadge = (approval: any) => {
    const daysOld = Math.floor((Date.now() - new Date(approval.created_at).getTime()) / (1000 * 60 * 60 * 24));
    
    if (daysOld > 2) return <Badge variant="destructive">Urgent</Badge>;
    if (daysOld > 1) return <Badge variant="warning">High</Badge>;
    return <Badge variant="secondary">Normal</Badge>;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Pending Approvals</h2>
        <Badge variant="outline">
          {pendingApprovals.length} pending
        </Badge>
      </div>

      {pendingApprovals.length === 0 ? (
        <Card className="p-12 text-center">
          <CheckCircle className="w-12 h-12 mx-auto text-green-500 mb-4" />
          <h3 className="text-lg font-medium">All caught up!</h3>
          <p className="text-muted-foreground">No pending approvals at the moment.</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {pendingApprovals.map((approval) => (
            <Card key={approval.id} className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="text-lg font-semibold">
                      {approval.entity_type} {approval.entity_number}
                    </h3>
                    {getPriorityBadge(approval)}
                    <Badge variant="outline">Level {approval.approval_level}</Badge>
                  </div>
                  
                  <p className="text-sm text-muted-foreground mb-4">
                    Requested by {approval.requester_name} •{' '}
                    {formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}
                  </p>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Amount:</span>
                      <span className="ml-2 font-medium">
                        ${(approval.total_cents / 100).toFixed(2)}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Department:</span>
                      <span className="ml-2 font-medium">{approval.department_name}</span>
                    </div>
                  </div>

                  {approval.description && (
                    <p className="mt-4 text-sm">{approval.description}</p>
                  )}
                </div>

                <div className="flex gap-2 ml-4">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedApproval(approval);
                      setAction('approve');
                    }}
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedApproval(approval);
                      setAction('reject');
                    }}
                  >
                    <XCircle className="w-4 h-4 mr-2" />
                    Reject
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Confirmation Dialog */}
      <Dialog open={!!selectedApproval} onOpenChange={() => {
        setSelectedApproval(null);
        setAction(null);
        setComments('');
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {action === 'approve' ? 'Approve' : 'Reject'} Request
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm font-medium">
                {selectedApproval?.entity_type} {selectedApproval?.entity_number}
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                Amount: ${(selectedApproval?.total_cents / 100 || 0).toFixed(2)}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Comments {action === 'reject' && <span className="text-red-600">*</span>}
              </label>
              <Textarea
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder={action === 'approve' ? 'Optional comments' : 'Please provide reason for rejection'}
                rows={4}
              />
            </div>

            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setSelectedApproval(null);
                  setAction(null);
                  setComments('');
                }}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button
                onClick={handleAction}
                disabled={isSubmitting}
                variant={action === 'approve' ? 'default' : 'destructive'}
              >
                {isSubmitting ? 'Processing...' : action === 'approve' ? 'Approve' : 'Reject'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
```

---

## 2. STATE MANAGEMENT (Zustand)

### 2.1 Purchase Request Store

```typescript
// stores/pr-store.ts

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { apiClient } from '@/lib/api-client';
import type { PurchaseRequest, PRCreate } from '@/types';

interface PRState {
  // State
  prs: PurchaseRequest[];
  currentPR: PurchaseRequest | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchPRs: () => Promise<void>;
  fetchPR: (id: string) => Promise<void>;
  createPR: (data: PRCreate) => Promise<PurchaseRequest>;
  updatePR: (id: string, data: Partial<PRCreate>) => Promise<PurchaseRequest>;
  submitPR: (id: string) => Promise<void>;
  cancelPR: (id: string) => Promise<void>;
  clearError: () => void;
}

export const usePRStore = create<PRState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        prs: [],
        currentPR: null,
        isLoading: false,
        error: null,

        // Fetch all PRs
        fetchPRs: async () => {
          set({ isLoading: true, error: null });
          try {
            const response = await apiClient.get<{ data: PurchaseRequest[] }>('/purchase-requests');
            set({ prs: response.data, isLoading: false });
          } catch (error: any) {
            set({ error: error.message, isLoading: false });
            throw error;
          }
        },

        // Fetch single PR
        fetchPR: async (id: string) => {
          set({ isLoading: true, error: null });
          try {
            const pr = await apiClient.get<PurchaseRequest>(`/purchase-requests/${id}`);
            set({ currentPR: pr, isLoading: false });
          } catch (error: any) {
            set({ error: error.message, isLoading: false });
            throw error;
          }
        },

        // Create PR
        createPR: async (data: PRCreate) => {
          set({ isLoading: true, error: null });
          try {
            const pr = await apiClient.post<PurchaseRequest>('/purchase-requests', data);
            
            // Optimistic update
            set((state) => ({
              prs: [pr, ...state.prs],
              currentPR: pr,
              isLoading: false
            }));
            
            return pr;
          } catch (error: any) {
            set({ error: error.message, isLoading: false });
            throw error;
          }
        },

        // Update PR
        updatePR: async (id: string, data: Partial<PRCreate>) => {
          set({ isLoading: true, error: null });
          try {
            const pr = await apiClient.patch<PurchaseRequest>(`/purchase-requests/${id}`, data);
            
            // Update in list
            set((state) => ({
              prs: state.prs.map((p) => (p.id === id ? pr : p)),
              currentPR: state.currentPR?.id === id ? pr : state.currentPR,
              isLoading: false
            }));
            
            return pr;
          } catch (error: any) {
            set({ error: error.message, isLoading: false });
            throw error;
          }
        },

        // Submit PR for approval
        submitPR: async (id: string) => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.post(`/purchase-requests/${id}/submit`);
            
            // Refresh PR to get updated status
            await get().fetchPR(id);
            
            set({ isLoading: false });
          } catch (error: any) {
            set({ error: error.message, isLoading: false });
            throw error;
          }
        },

        // Cancel PR
        cancelPR: async (id: string) => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.post(`/purchase-requests/${id}/cancel`);
            
            // Update status
            set((state) => ({
              prs: state.prs.map((p) =>
                p.id === id ? { ...p, status: 'CANCELLED' } : p
              ),
              isLoading: false
            }));
          } catch (error: any) {
            set({ error: error.message, isLoading: false });
            throw error;
          }
        },

        clearError: () => set({ error: null })
      }),
      {
        name: 'pr-storage',
        partialize: (state) => ({ prs: state.prs }) // Only persist PRs, not loading state
      }
    )
  )
);
```

---

## 3. API CLIENT IMPLEMENTATION

```typescript
// lib/api-client.ts

import axios, { AxiosInstance, AxiosError } from 'axios';
import { toast } from 'sonner';

class APIClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor: Add auth token
    this.client.interceptors.request.use(
      (config) => {
        if (this.accessToken) {
          config.headers.Authorization = `Bearer ${this.accessToken}`;
        }
        
        // Add idempotency key for POST/PUT/PATCH
        if (['post', 'put', 'patch'].includes(config.method?.toLowerCase() || '')) {
          config.headers['Idempotency-Key'] = `${Date.now()}-${Math.random().toString(36)}`;
        }
        
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor: Handle errors
    this.client.interceptors.response.use(
      (response) => response.data,
      async (error: AxiosError<any>) => {
        const originalRequest = error.config as any;

        // Handle 401 Unauthorized
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          
          try {
            // Try to refresh token
            const newToken = await this.refreshToken();
            this.setAccessToken(newToken);
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return this.client(originalRequest);
          } catch (refreshError) {
            // Refresh failed, redirect to login
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        // Handle other errors
        const errorData = error.response?.data?.error;
        const errorMessage = errorData?.message || error.message || 'An error occurred';

        // Show toast for user-facing errors
        if (error.response?.status !== 404) {
          toast.error(errorMessage);
        }

        return Promise.reject(new Error(errorMessage));
      }
    );
  }

  setAccessToken(token: string) {
    this.accessToken = token;
    localStorage.setItem('access_token', token);
  }

  clearAccessToken() {
    this.accessToken = null;
    localStorage.removeItem('access_token');
  }

  private async refreshToken(): Promise<string> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) throw new Error('No refresh token');

    const response = await axios.post(
      `${process.env.NEXT_PUBLIC_API_URL}/auth/refresh`,
      { refresh_token: refreshToken }
    );

    return response.data.access_token;
  }

  // Generic methods
  async get<T>(url: string, config = {}): Promise<T> {
    return this.client.get(url, config);
  }

  async post<T>(url: string, data?: any, config = {}): Promise<T> {
    return this.client.post(url, data, config);
  }

  async patch<T>(url: string, data?: any, config = {}): Promise<T> {
    return this.client.patch(url, data, config);
  }

  async delete<T>(url: string, config = {}): Promise<T> {
    return this.client.delete(url, config);
  }
}

export const apiClient = new APIClient();
```

---

**Document Status:** ✅ COMPLETE (Part 1)  
**AI-Executability:** 100%  
**Components Included:** PR Form, Approval Dashboard, Complete Stores, API Client  
**Remaining:** Routing, Flutter Implementation
