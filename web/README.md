# ActWise Web UI

React/Vite frontend for ActWise V2.

## Features

- submit tasks to `/agent/run`
- resume CLARIFY workflows through `/agent/resume`
- display COMPLETE / CLARIFY / ABSTAIN state
- show executed tools
- show skipped calls
- show decision history
- show thread ID

## Local run

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

## Lint

```bash
npm run lint
```

## Backend

Defaults to `http://127.0.0.1:8000`.

To point at a different backend, set `VITE_API_URL` (see `.env.example`):

```bash
cp .env.example .env
# edit .env to set VITE_API_URL
```
