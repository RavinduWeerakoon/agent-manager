import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ThunderIDProvider } from '@thunderid/react'
import './index.css'
import App from './App.jsx'

const clientId = import.meta.env.VITE_CLIENT_ID || "amp-console-client";
const baseUrl = import.meta.env.VITE_AUTH_BASE_URL || "http://localhost:8090";

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThunderIDProvider
      clientId={clientId}
      baseUrl={baseUrl}
      afterSignInUrl={window.location.origin}
      afterSignOutUrl={window.location.origin}
      scopes={["openid", "profile", "email"]}
      tokenValidation={{ idToken: { validate: false } }}
      endpoints={{
        authorization: `${baseUrl}/oauth2/authorize`,
        token: `${baseUrl}/oauth2/token`,
        jwks: `${baseUrl}/oauth2/jwks`,
        userInfo: `${baseUrl}/oauth2/userinfo`,
        endSession: `${baseUrl}/oauth2/logout`
      }}
    >
      <App />
    </ThunderIDProvider>
  </StrictMode>,
)
