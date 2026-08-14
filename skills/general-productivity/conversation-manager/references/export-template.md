# Export Package Template

This reference defines the exact structure and format for every conversation export.

## Directory Structure

```
{backup_path}/{conversation-name - YYYY-MM-DD}/
├── manifest.json
├── conversation.md
├── metadata.json
└── artifacts/
    └── (all files from session workspace)
```

## manifest.json

```json
{
  "title": "Skill Builder Session - 2026-08-13",
  "session_id": "5756e9f1-3c63-479f-8cb7-c054ebd9fa18",
  "exported_at": "2026-08-13T13:42:00-07:00",
  "model": "smart",
  "agent_id": "default",
  "message_count": 14,
  "event_count": 22,
  "artifact_count": 3,
  "artifacts": [
    {
      "name": "chart.html",
      "size_bytes": 4521,
      "relative_path": "artifacts/chart.html"
    }
  ],
  "tools_used": ["file_write", "file_copy", "query_conversations"],
  "created_at": "2026-08-13T13:12:00-07:00",
  "last_updated_at": "2026-08-13T14:30:00-07:00",
  "duration_minutes": 78,
  "export_detail_level": "messages + tool calls + reasoning"
}
```

## metadata.json

All fields from the sessions table, stored as-is with timestamps converted to ISO format:

```json
{
  "id": "5756e9f1-3c63-479f-8cb7-c054ebd9fa18",
  "title": "Skill Builder Session - 2026-08-13",
  "agent_mode": "smart",
  "selected_agent_id": null,
  "created_at": "2026-08-13T13:12:00-07:00",
  "updated_at": "2026-08-13T14:30:00-07:00",
  "last_opened_at": "2026-08-13T14:30:00-07:00",
  "message_count": 14,
  "event_count": 22,
  "folder_id": "abc123",
  "folder_name": "Projects",
  "pinned": false,
  "archived": false,
  "session_type": "main",
  "fork_source_session_id": null,
  "parent_session_id": null,
  "task_objective": null,
  "task_status": null,
  "tools_used": ["file_write", "file_copy", "query_conversations"]
}
```

## conversation.md

Full conversation with all messages, tool calls, reasoning, and sources preserved.

```markdown
# {Title}

**Session ID:** {id}
**Model:** {agent_mode}
**Agent:** {selected_agent_id or "default"}
**Created:** {created_at}
**Exported:** {exported_at}
**Messages:** {message_count}
**Tools Used:** {comma-separated list}

---

## Turn 1

**User:** {message content}

---

## Turn 2

### Reasoning
> {reasoning/thinking content if available}

### Tool Call: `{tool_name}`
```xml
<invoke name="{tool_name}">
  <parameter name="{param}">{value}</parameter>
</invoke>
```

### Tool Result:
```json
{full result JSON}
```

**Assistant:** {message content}

<sources>
{preserved exactly as-is from the original message}
</sources>

---

## Turn N
...
```

## Rules for conversation.md

1. Every message is included, in order, with no summarization or truncation.
2. Tool calls are rendered as XML invocation blocks with full parameters.
3. Tool results are rendered as JSON blocks with full content.
4. Reasoning/thinking blocks are rendered as blockquotes before tool calls.
5. `<sources>` blocks at the end of assistant messages are preserved verbatim.
6. Decision cards and user decision responses are included as-is.
7. System events (tab switches, file attachments) are included with a `[SYSTEM]` prefix.
8. If a message has no tool calls, just show the speaker label and content.
9. Timestamps per message are included if available (from session_messages.timestamp).
