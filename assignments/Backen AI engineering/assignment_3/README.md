## API Verification

The following requests were used to verify the running API.

### Health Check

Command:

```bash
curl -i http://localhost:8000/health
```

Expected successful response:

```http
HTTP/1.1 200 OK
content-type: application/json
```

Response body:

```json
{"status":"ok"}
```

### Retrieve All Tasks

Command:

```bash
curl http://localhost:8000/tasks
```

This endpoint returns a JSON array containing the tasks stored in PostgreSQL.

### Create a Task

Command:

```bash
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Complete project documentation","done":false}'
```

A successful request returns HTTP `201 Created` and the newly created task, including its database-generated ID.

### Update a Task

Command:

```bash
curl -i -X PUT http://localhost:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated task title","done":true}'
```

A successful request returns HTTP `200 OK` and the updated task.

### Delete a Task

Command:

```bash
curl -i -X DELETE http://localhost:8000/tasks/1
```

A successful request returns HTTP `204 No Content`.

### Missing Task

Requests for nonexistent task IDs return HTTP `404 Not Found`.