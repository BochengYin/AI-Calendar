# AI Calendar – API Reference

Base URL (dev): `http://localhost:12345`

## Authentication

The backend does **not** issue tokens itself. Tokens are obtained from Supabase Auth on the frontend and sent as `Authorization: Bearer <jwt>` headers where required.

## Endpoints

### `GET /api/health`
Health-check endpoint. Returns server status and environment sanity.

```json
{
  "status": "ok",
  "api_key_configured": true,
  "supabase_status": "connected",
  "timestamp": "2025-05-23T10:00:00Z"
}
```

### `GET /api/events`
Returns events belonging to the authenticated user.

Query parameters:
* `limit` (optional) – max number of events.

### `POST /api/events`
Creates a new event.

Body fields (JSON):
* `id` (uuid, required)
* `title` (string)
* `description` (string, optional)
* `start` (ISO 8601 string)
* `end` (ISO 8601 string)
* `allDay` (boolean, default: false)

### `PUT /api/events/{id}`
Updates an existing event.

### `DELETE /api/events/{id}`
Soft-deletes an event.

### `POST /api/chat`
Natural-language interface. JSON body:

```json
{
  "message": "Schedule a meeting with Alex tomorrow at 2pm",
  "userId": "<uuid>",
  "userEmail": "name@example.com"
}
```

The server responds with a human-readable `message` and an optional `event` object when a calendar mutation was recognised.

---

Detailed request/response examples can be found in `docs/examples` (TODO). 