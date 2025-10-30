# Chat Widget — README

## Run

npm install
npm run dev

# open http://localhost:5173/
By default the project is configured to use a test API (fetch) — requests go to JSONPlaceholder. No backend required.

Switch modes
Test mode (default)
VITE_TEST_FETCH=true

Real backend
VITE_TEST_FETCH=false
VITE_API_BASE=https://your-backend.example.com

Requests go to:
${VITE_API_BASE}/api/chat

After changing .env, restart:
npm run dev


Files 

src/main.tsx — mounts <App />

src/App.tsx — app root, wraps chat with ErrorBoundary

src/Chatbot.tsx — chat logic: state, fetch, autofocus, UI composition

src/types/chat.ts — Message type

src/components/ErrorBoundary.tsx — UI crash guard

src/components/chat/

ChatHeader.tsx — header

MessageList.tsx — list + autoscroll

ChatMessage.tsx — single message bubble

MessageInput.tsx — input + submit

LoadingIndicator.tsx — “typing…” indicator