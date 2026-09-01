---
name: create-learn-course
description: 'Authoring format for Global AI Learn courses: the folder layout and YAML front matter for course.md, module.md, page files and final-test.md, the question schema (single-choice, multiple-choice, true-false), identifier rules, and loader validation rules. Use when writing, converting, or reviewing course content for the Global AI Community learning platform.'
---

# Global AI Learn course authoring format

Use this skill whenever you create, convert, or review Global AI Learn course
content. Course content is plain Markdown with YAML front matter. The website
loads it at startup with `CourseContentLoader`, validates every file, and drops
any course that produces a single diagnostic. Get the format exactly right or
the course will not appear in the catalog.

## Workflow

1. Identify the course, module, page, or final-test files that need to be created.
2. Create all course documents under `.learn/<course-id>/` in the workspace.
3. Create the required folder layout and put YAML front matter on every file.
4. Keep all identifiers as lowercase slugs and keep reference arrays in order.
5. Validate question types, options, and correct answers.

## When to use

- Writing a new course, module, lesson page, or final test
- Converting a workshop, README, or slide deck into a course
- Reviewing or fixing course content that fails to load

## Golden rules

1. Every file starts with YAML front matter, opened by `---` on line 1 and
   closed by `---` on its own line. Use LF line endings - the parser matches
   `---\n` literally, so CRLF files fail.
2. All ids are slugs matching `^[a-z0-9]+(?:-[a-z0-9]+)*$`. Use lowercase
   letters and digits with single hyphens between words. No spaces, underscores,
   capitals, or leading/trailing hyphens.
3. One diagnostic drops the whole course. A bad question id in one module
   removes the entire course from the catalog, not just that question.
4. Order comes from the arrays, not from the `order:` field. `modules:` in
   `course.md` and `pages:` in `module.md` define the sequence. Keep `order:` in
   sync as documentation.
5. Publication, credits, and the completion badge are not content. Do not put
  them in front matter.

## Folder layout

Create course documents in the workspace's `.learn/` folder. Each
course gets its own `<course-id>/` directory containing `course.md`. The loader
scans the content root recursively for `course.md`, so courses can sit at any
depth after they are copied into the website content root.

```text
.learn/
`-- <course-id>/
    |-- course.md
    |-- final-test.md
    `-- modules/
        |-- 01-<module-id>/
        |   |-- module.md
        |   `-- pages/
        |       |-- 01-<page-id>.md
        |       `-- 02-<page-id>.md
        `-- 02-<module-id>/
            `-- ...
```

Numeric prefixes are optional but recommended. A folder or file name matches an
id when it either equals the id exactly, or is `<digits>-<id>` such as
`03-build-server`.

## `course.md`

```yaml
---
schemaVersion: 1
id: mcp-workshop
version: "1.0"
title: Build with the Model Context Protocol
summary: Build an MCP server, connect a client, and take the result into a browser.
durationMinutes: 115
difficulty: Intermediate
prerequisites:
  - Python 3.10 or newer
  - Git and a terminal
learningOutcomes:
  - Explain how MCP reduces integrations from M x N to M + N
  - Build an MCP server with tools, resources, and prompts
image: /images/learn/mcp.jpg
modules: [setup, mcp-basics, build-server]
---

Intro prose in Markdown. This renders on the course overview page above the outcomes.
```

`schemaVersion` must be exactly `1`. `id` must be a unique slug, and `version`
must be quoted so YAML keeps it as a string. The `id` and `version` pair must be
unique across all courses. Bump `version` for a new revision of the same course.

## `module.md`

```yaml
---
id: build-server
title: Build an MCP server
summary: Define typed tools and expose a resource and prompt.
order: 3
pages: [server-capabilities]
questions:
  - id: structured-output
    type: multiple-choice
    prompt: Which benefits come from returning a Pydantic model from a tool?
    options:
      - id: schema
        text: The SDK can generate an output schema
      - id: validation
        text: Returned data can be validated
      - id: secret-auth
        text: MCP automatically adds authentication
    correctOptionIds: [schema, validation]
    explanation: Typed models provide schema and validation. Authentication stays an application concern.
---

Optional module intro prose.
```

Every module needs at least one question. The questions become the module check
the learner takes after finishing the module's pages. The module `id` must match
the entry in `course.md`, and every page id in `pages:` must resolve to a page file.

## Page files

Page files live under `modules/<module>/pages/`:

```yaml
---
id: server-capabilities
title: Tools, resources, prompts, and errors
order: 1
estimatedMinutes: 25
---

The lesson body in Markdown. This is the whole lesson - there is no other body field.
```

`estimatedMinutes` is required and must be greater than zero. Do not repeat the
page title as an `#` heading; the title from front matter is already rendered as
the page heading. Start body headings at `##`.

## `final-test.md`

`final-test.md` sits next to `course.md` and is required. It has no `id` and no
`schemaVersion`:

```yaml
---
title: MCP workshop final test
questions:
  - id: final-scaling
    type: single-choice
    prompt: What integration shape does MCP provide for M hosts and N systems?
    options:
      - id: additive
        text: Approximately M + N implementations
      - id: multiplicative
        text: M x N custom adapters
    correctOptionIds: [additive]
---

Optional intro prose shown above the final test.
```

## Question schema

| Field | Rule |
|---|---|
| `id` | Required slug, unique within the file |
| `type` | One of `single-choice`, `multiple-choice`, `true-false` |
| `prompt` | Required and non-empty |
| `options` | At least 2; each has a unique slug `id` and non-empty `text` |
| `correctOptionIds` | Non-empty; every entry is an option id in the same question |
| `explanation` | Optional; shown after grading |

Additional type rules:

- `single-choice` and `true-false` have exactly one correct option id.
- `true-false` has exactly two options.
- `multiple-choice` has one or more correct option ids and renders as checkboxes.

Grading is all-or-nothing: the learner must get every question right to pass a
module check or the final test. Write options that are clearly right or clearly
wrong, not judgement calls.

## Markdown body

- The body is everything after the closing `---`.
- Markdig advanced extensions support tables, fenced code blocks with language
  hints, task lists, footnotes, auto-links, and definition lists.
- Output is sanitized. `<script>`, `on*` handlers, and `javascript:` URLs are
  stripped, so raw HTML embeds, iframes, and inline JavaScript will not survive.
  Use Markdown.

## Writing style

Write in a friendly developer-to-developer voice using plain language and second
person. Do not use em dashes; use a regular hyphen. Say "events" instead of
"meetups" and "chapters" instead of "groups". Keep each lesson focused on one
idea and close to its declared `estimatedMinutes`.

## Common loader failures

| Diagnostic | Cause |
|---|---|
| `Document must start with YAML front matter.` | Missing `---`, a BOM, or CRLF line endings |
| `YAML front matter is not closed.` | No closing `---` on its own line |
| `Referenced module 'x' was not found.` | Folder name does not match the id, or `module.md` is missing |
| `Referenced page 'x' was not found.` | File name does not match the id, or it is not in `pages/` |
| `Module id must match reference 'x'.` | `id:` in `module.md` differs from the entry in `modules:` |
| `Invalid course id 'X'.` | Capitals, spaces, or underscores in a slug |
| `Question 'x' has invalid correctOptionIds.` | Empty, or points at an option id that does not exist |
| `schemaVersion must be 1.` | Missing or wrong `schemaVersion` in `course.md` |
| `final-test.md was not found.` | Missing final test beside `course.md` |
| `Duplicate course id and version 'x:1.0'.` | Two courses share id and version; both are dropped |