# Pollyanna notebook structure

## Canonical paths

- Durable collaboration memory: `~/__HOME_ROOT_NAME__/__DOCS_SUBDIR__/__MEMORY_FILE_NAME__`
- Text research notes: `~/__HOME_ROOT_NAME__/__DOCS_SUBDIR__/YYYY-MM-DD/{nn}-{slug}`
- Large or binary research material: `~/__HOME_ROOT_NAME__/__DATA_SUBDIR__/YYYY-MM-DD/{nn}-{slug}`

Use the same `{nn}-{slug}` under `docs` and `data` when an investigation produces both. A text-only investigation normally has no matching data directory.

## Content boundaries

Use `docs` for public-source notes, citations, hypotheses, option comparisons, experiment designs, and concise technical artifacts. Use `data` for public datasets, images, audio, video, archives, large logs, and other bulky captures.

Never persist credentials, access tokens, sensitive personal information, or private source content. Describe the role of unavailable sensitive material without copying it.

## Interaction pattern

Create one entry when an investigation merits a durable trail, then reuse it for that work item. Keep the conversation focused on conclusions and decisions rather than dumping the entire trail into chat.
