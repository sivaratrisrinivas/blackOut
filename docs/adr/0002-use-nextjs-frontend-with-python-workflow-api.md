# Use Next.js Frontend With Python Workflow API

BlackOut will use a Next.js frontend for the user interface while keeping the Python workflow and memory adapter as the product behavior layer.

The existing implementation already separates product behavior into `BlackOutWorkflow` and exposes Flask JSON endpoints for loading demo evidence, remembering evidence, recalling decisions, applying feedback, asking memory, and forgetting a Late-Night Window. Moving the UI to Next.js should replace the Flask-served HTML template, not rewrite the workflow or Cognee adapter.

This changes the earlier MVP direction from Streamlit-first UI to a split frontend/backend shape:

- Next.js owns the interactive product surface.
- Python owns BlackOut domain behavior and memory lifecycle orchestration.
- Flask remains the thin local API server unless a later decision replaces it with FastAPI.
- Public API integrations remain optional enrichment and must not become required for Morning-After Recall.

This keeps the demo flow focused on the Memory Lifecycle while giving the interface a more maintainable React component model.
