# M7A UI Preview Contract v1

## Scope

7A-05 only introduces a separately addressable public UI preview at `/v2`. The existing `/` and `/view` routes remain the M6-compatible entry points; switching the main entry point is reserved for M15.

## Public layer

- `static/v2/index.html` is a shell only. It does not embed a publication dataset or generate an inline full-data table.
- `api.js` is the only preview API transport module and uses the existing read-only JSON endpoints.
- `format.js` owns display formatting and text escaping helpers.
- `table.js` renders bounded, text-only cells and keeps action controls in their own non-wrapping cell.
- `modal.js` owns evidence display, close behavior, Escape handling, focus return, and overlay dismissal.
- `app.js` binds the date/publication context and the current M7A identity, universe, and semantic contracts.

## Interaction contract

Evidence is opened on demand and is never expanded as long content inside a table cell. The preview sends only the selected `publication_id`; it does not request or inline the complete stock, sector, candidate, or queue datasets. Every evidence payload is inserted as text, not HTML.

## Compatibility and delivery

`/view` remains readable and unchanged in purpose. `/v2`, `/v2/`, `/v2/index.html`, and the four shared modules are served from the repository static directory with path traversal rejected. This contract is delivered as the single 7A-05 change and is not a claim that the main UI has switched.
