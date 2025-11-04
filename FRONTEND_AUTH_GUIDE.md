# Frontend JWT Authentication Guide

## What Changed

### 1. Cookie Support Enabled ✅
The frontend now properly sends and receives cookies by adding `withCredentials: true` to all Axios requests in `external-api.service.ts`.

### 2. New API Function Available
Added `checkAuthentication()` function in `api.service.ts` to check if a user is authenticated.

## How It Works

### Automatic Cookie Storage
When a user successfully validates their password:
1. Backend generates a JWT token
2. Backend sets the `auth_token` cookie (HTTP-only, 7-day expiration)
3. Frontend Axios automatically stores and sends this cookie with all future requests

**No manual cookie handling needed!** The browser and Axios handle it automatically.

## Using Authentication in Your Pages

### Example 1: Check Authentication on Page Load

```typescript
"use client";

import { useEffect, useState } from "react";
import { checkAuthentication } from "../../services/api.service";
import { useRouter } from "next/navigation";

export default function ProtectedPage() {
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const verifyAuth = async () => {
      const { isAuthenticated } = await checkAuthentication();
      
      if (!isAuthenticated) {
        // Redirect to login page if not authenticated
        router.push("/");
      } else {
        setIsLoading(false);
      }
    };

    verifyAuth();
  }, [router]);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      {/* Your protected content here */}
      <h1>Welcome! You are authenticated.</h1>
    </div>
  );
}
```

### Example 2: Get User's Node ID

```typescript
const { isAuthenticated, nodeId } = await checkAuthentication();

if (isAuthenticated) {
  console.log("User's node ID:", nodeId);
  // Use nodeId to fetch user-specific data
}
```

### Example 3: Redirect After Login

The current implementation in `page.tsx` already handles this:

```typescript
const result = await validatePasswordAPI(password);

if (result.isValid && result.redirectUrl) {
  // Cookie is automatically set by the backend
  // Redirect to the next page
  window.location.href = result.redirectUrl;
}
```

## Testing Cookie Storage

### In Browser DevTools:
1. Open your browser's DevTools (F12)
2. Go to the "Application" or "Storage" tab
3. Look for "Cookies" → `http://localhost:3000`
4. After successful password validation, you should see `auth_token` cookie

### Cookie Details:
- **Name**: `auth_token`
- **HttpOnly**: Yes (can't be accessed via JavaScript - security feature)
- **SameSite**: Lax
- **Expires**: 7 days from creation
- **Secure**: No (will be Yes in production with HTTPS)

## API Endpoints Available

### 1. Validate Password (Login)
```typescript
import { validatePassword } from "../../services/api.service";

const { data, error } = await validatePassword("myPassword123");
// Returns: { redirect_url, token } + sets cookie automatically
```

### 2. Check Authentication
```typescript
import { checkAuthentication } from "../../services/api.service";

const { isAuthenticated, nodeId, error } = await checkAuthentication();
```

## Important Notes

1. **Cookies are HttpOnly**: You won't be able to read the `auth_token` cookie with JavaScript (document.cookie). This is a security feature to prevent XSS attacks.

2. **Automatic Cookie Sending**: Once set, the cookie is automatically sent with every request to `http://localhost:8000` thanks to `withCredentials: true`.

3. **Cross-Origin Cookies**: The setup works because:
   - Backend has `allow_credentials=True` in CORS config
   - Frontend uses `withCredentials: true` in Axios
   - Both run on localhost (same domain, different ports)

4. **Production Considerations**:
   - Set `secure: True` in production (requires HTTPS)
   - Update `allow_origins` in backend to match production domain
   - Consider using environment variables for the JWT secret key

## Troubleshooting

### Cookies Not Being Stored?
1. Check browser DevTools console for CORS errors
2. Verify backend is running on `http://localhost:8000`
3. Verify frontend is running on `http://localhost:3000`
4. Check that both services are running (not one or the other)

### Authentication Check Failing?
1. Check if cookie exists in browser DevTools
2. Verify cookie hasn't expired (7 days max)
3. Check backend logs for any JWT validation errors
4. Make sure `withCredentials: true` is set in Axios config

### Cookie Gets Deleted?
- Logging out: Clear cookies manually or add a logout endpoint
- Expiration: Cookies expire after 7 days
- Browser clearing data will remove cookies

## Next Steps for Your App

1. **Create Protected Routes**: Use `checkAuthentication()` on any page that requires login
2. **Add Logout**: Create a function to clear the cookie (or let it expire)
3. **Redirect Logic**: Automatically redirect authenticated users away from login page
4. **Loading States**: Show loading indicators while checking authentication

## Example: Auth Context Provider (Optional)

For a more robust solution, you could create an authentication context:

```typescript
// context/AuthContext.tsx
"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { checkAuthentication } from "../services/api.service";

interface AuthContextType {
  isAuthenticated: boolean;
  nodeId?: number;
  isLoading: boolean;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [nodeId, setNodeId] = useState<number>();
  const [isLoading, setIsLoading] = useState(true);

  const checkAuth = async () => {
    setIsLoading(true);
    const result = await checkAuthentication();
    setIsAuthenticated(result.isAuthenticated);
    setNodeId(result.nodeId);
    setIsLoading(false);
  };

  useEffect(() => {
    checkAuth();
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, nodeId, isLoading, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};
```

Usage:
```typescript
const { isAuthenticated, isLoading } = useAuth();

if (isLoading) return <div>Loading...</div>;
if (!isAuthenticated) router.push("/");
```

