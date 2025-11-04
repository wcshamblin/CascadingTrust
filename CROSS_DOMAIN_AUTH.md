# Cross-Domain JWT Authentication Guide

## The Problem

When a user validates their password and gets redirected to a different domain (e.g., from `localhost:3000` to `https://example.com/dashboard`), the HTTP-only cookie set by the backend is **NOT accessible** on the destination domain.

**Why?** Cookies are domain-specific. A cookie set for `localhost` cannot be read by `example.com`.

## The Solution Implemented

We now use a **dual-token approach**:

1. **HTTP-only Cookie** (for same-domain security)
   - Set by backend
   - Stored in browser for `localhost:8000`
   - Used for subsequent API calls to the same domain
   - Secure, protected from XSS attacks

2. **Token in URL Fragment** (for cross-domain transfer)
   - Included in redirect URL as `#token=<jwt>`
   - Destination site can read it via JavaScript
   - Not sent to server (stays client-side)
   - Not logged in server access logs

## How It Works

### When User Enters Password:

```
1. User enters password on localhost:3000
2. Frontend calls /api/validate-password
3. Backend validates and returns:
   {
     "redirect_url": "https://example.com/dashboard",
     "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
   }
4. Backend also sets auth_token cookie for localhost
5. Frontend redirects to: https://example.com/dashboard#token=eyJ0eXAi...
```

### On Destination Site:

The destination website can extract the token from the URL fragment:

```javascript
// On https://example.com/dashboard
const hash = window.location.hash;
if (hash.startsWith('#token=')) {
  const token = hash.substring(7); // Remove '#token='
  
  // Option 1: Store in localStorage
  localStorage.setItem('auth_token', token);
  
  // Option 2: Store in sessionStorage (cleared when tab closes)
  sessionStorage.setItem('auth_token', token);
  
  // Option 3: Set as a cookie for this domain
  document.cookie = `auth_token=${token}; max-age=604800; path=/; secure; samesite=strict`;
  
  // Clean up URL (remove token from hash)
  window.history.replaceState(null, '', window.location.pathname);
  
  // Now make authenticated requests
  fetch('/api/user-data', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
}
```

## Alternative Solutions

### Option A: Query Parameter (Simple but Less Secure)

```typescript
// In frontend page.tsx
const redirectUrl = new URL(result.redirectUrl);
if (result.token) {
  redirectUrl.searchParams.set('token', result.token);
}
window.location.href = redirectUrl.toString();
// Result: https://example.com/dashboard?token=eyJ0eXAi...
```

**Pros:**
- Very simple
- Works everywhere

**Cons:**
- Token visible in URL
- Logged in server access logs
- Visible in browser history
- Can be leaked via Referer header

### Option B: POST Request with Form (More Secure)

Instead of GET redirect, use a POST form:

```typescript
// Create a hidden form and submit it
const form = document.createElement('form');
form.method = 'POST';
form.action = result.redirectUrl;

const tokenInput = document.createElement('input');
tokenInput.type = 'hidden';
tokenInput.name = 'token';
tokenInput.value = result.token;

form.appendChild(tokenInput);
document.body.appendChild(form);
form.submit();
```

**Pros:**
- Token not in URL
- Not logged in access logs
- More secure than query params

**Cons:**
- Destination site must handle POST request
- Requires server-side processing

### Option C: Window.postMessage (For Same-Window Communication)

If destination site opens in an iframe or popup:

```typescript
// Parent window
const childWindow = window.open(result.redirectUrl);
childWindow.postMessage({ token: result.token }, 'https://example.com');

// In child window (example.com)
window.addEventListener('message', (event) => {
  if (event.origin === 'http://localhost:3000') {
    const token = event.data.token;
    localStorage.setItem('auth_token', token);
  }
});
```

**Pros:**
- Very secure (origin checking)
- No URL pollution

**Cons:**
- Only works for same-window scenarios
- Complex setup

## Current Implementation Details

### Frontend Changes Made:

1. **page.tsx** - Updated redirect logic to include token in URL fragment:
```typescript
const redirectUrl = new URL(result.redirectUrl);
if (result.token) {
  redirectUrl.hash = `token=${result.token}`;
}
window.location.href = redirectUrl.toString();
```

2. **Dual Storage**:
   - Cookie stored automatically by backend (for localhost API calls)
   - Token in response body (for cross-domain redirect)

### Backend (No Changes Needed):
The backend already returns both:
- Sets HTTP-only cookie
- Returns token in response JSON

## Security Considerations

### URL Fragment Approach (Current):
✅ **Pros:**
- Not sent to server
- Not in access logs
- Reasonably secure for short-lived tokens

⚠️ **Cons:**
- Visible in browser history
- Could be leaked if page has XSS vulnerability
- Visible if user shares URL

### Best Practices for Destination Site:

1. **Extract and Clean Immediately:**
```javascript
const token = window.location.hash.substring(7);
localStorage.setItem('auth_token', token);
window.history.replaceState(null, '', window.location.pathname); // Clean URL
```

2. **Validate Token:**
```javascript
// Verify token structure before using
if (token && token.split('.').length === 3) {
  // Valid JWT structure
  localStorage.setItem('auth_token', token);
}
```

3. **Use HTTPS in Production:**
- Always use HTTPS for production
- Prevents token interception via MITM

4. **Short Token Lifetime:**
- Current: 7 days
- Consider shorter for higher security
- Implement refresh tokens for long sessions

## Example: Complete Destination Site Implementation

```html
<!DOCTYPE html>
<html>
<head>
  <title>Protected Dashboard</title>
</head>
<body>
  <div id="app">Loading...</div>

  <script>
    // Extract token from URL fragment
    function getTokenFromURL() {
      const hash = window.location.hash;
      if (hash.startsWith('#token=')) {
        const token = hash.substring(7);
        // Clean URL immediately
        window.history.replaceState(null, '', window.location.pathname);
        return token;
      }
      return null;
    }

    // Initialize auth
    function initializeAuth() {
      // Check for token in URL
      const urlToken = getTokenFromURL();
      if (urlToken) {
        localStorage.setItem('auth_token', urlToken);
      }

      // Get token from storage
      const token = localStorage.getItem('auth_token');
      
      if (!token) {
        // No token - redirect to login
        window.location.href = 'http://localhost:3000';
        return;
      }

      // Validate token (optional: call your backend)
      validateTokenWithBackend(token)
        .then(isValid => {
          if (isValid) {
            loadDashboard(token);
          } else {
            localStorage.removeItem('auth_token');
            window.location.href = 'http://localhost:3000';
          }
        });
    }

    async function validateTokenWithBackend(token) {
      try {
        const response = await fetch('https://your-api.com/validate-token', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        return response.ok;
      } catch (error) {
        return false;
      }
    }

    function loadDashboard(token) {
      // Use token for authenticated requests
      fetch('https://your-api.com/user-data', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      .then(response => response.json())
      .then(data => {
        document.getElementById('app').innerHTML = `
          <h1>Welcome ${data.username}!</h1>
          <button onclick="logout()">Logout</button>
        `;
      });
    }

    function logout() {
      localStorage.removeItem('auth_token');
      window.location.href = 'http://localhost:3000';
    }

    // Initialize on page load
    initializeAuth();
  </script>
</body>
</html>
```

## Testing the Implementation

1. **Start both services:**
```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate
uvicorn app:app --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
```

2. **Test the flow:**
   - Go to http://localhost:3000
   - Enter a valid password
   - Check the redirect URL in browser address bar
   - Should see: `https://example.com/dashboard#token=eyJ0eXAi...`

3. **Verify cookie storage:**
   - Open DevTools → Application → Cookies
   - Should see `auth_token` for localhost:8000
   - This is used for subsequent API calls to your backend

## Summary

**Current Setup:**
- ✅ HTTP-only cookie for same-domain security
- ✅ Token in URL fragment for cross-domain transfer
- ✅ Destination site can extract and store token as needed
- ✅ Secure, flexible, and works across any domain

**For Destination Sites:**
- Extract token from `window.location.hash`
- Store in localStorage or sessionStorage
- Clean URL immediately
- Use token in Authorization header for API calls

This dual approach gives you the best of both worlds: security for same-domain operations and flexibility for cross-domain authentication.

