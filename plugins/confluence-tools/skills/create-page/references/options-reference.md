# Create Page - Options Reference

## Required Arguments

| Option | Short | Type | Description |
|--------|-------|------|-------------|
| `--space` | `-s` | string | Space key where the page will be created |
| `--title` | `-t` | string | Page title |

## Optional Arguments

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--body` | `-b` | string | empty | Page body in Confluence storage format (HTML) |
| `--body-file` | - | path | - | Read body content from file (use '-' for stdin) |
| `--parent` | `-p` | string | - | Parent page ID (creates as child page) |
| `--parent-title` | - | string | - | Parent page title (alternative to --parent) |
| `--labels` | `-l` | string | - | Comma-separated labels to add |
| `--format` | `-f` | choice | compact | Output format: compact, text, json |

## Content Format

Confluence uses "storage format" which is XHTML-based. Key elements:

### Basic Formatting

```html
<p>Paragraph text</p>
<strong>Bold</strong>
<em>Italic</em>
<u>Underline</u>
<h1>Heading 1</h1>
<h2>Heading 2</h2>
```

### Lists

```html
<ul>
  <li>Unordered item 1</li>
  <li>Unordered item 2</li>
</ul>

<ol>
  <li>Ordered item 1</li>
  <li>Ordered item 2</li>
</ol>
```

### Tables

```html
<table>
  <tr>
    <th>Header 1</th>
    <th>Header 2</th>
  </tr>
  <tr>
    <td>Cell 1</td>
    <td>Cell 2</td>
  </tr>
</table>
```

### Code Block

```html
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">python</ac:parameter>
  <ac:parameter ac:name="title">Example</ac:parameter>
  <ac:plain-text-body><![CDATA[
def hello():
    print("Hello, World!")
]]></ac:plain-text-body>
</ac:structured-macro>
```

### Info/Warning/Note Panels

```html
<!-- Info panel (blue) -->
<ac:structured-macro ac:name="info">
  <ac:rich-text-body><p>Information message</p></ac:rich-text-body>
</ac:structured-macro>

<!-- Note panel (yellow) -->
<ac:structured-macro ac:name="note">
  <ac:rich-text-body><p>Note message</p></ac:rich-text-body>
</ac:structured-macro>

<!-- Warning panel (red) -->
<ac:structured-macro ac:name="warning">
  <ac:rich-text-body><p>Warning message</p></ac:rich-text-body>
</ac:structured-macro>
```

### Links

```html
<!-- External link -->
<a href="https://example.com">Link text</a>

<!-- Link to another Confluence page -->
<ac:link><ri:page ri:content-title="Page Title"/></ac:link>

<!-- Link to page in specific space -->
<ac:link><ri:page ri:space-key="SPACE" ri:content-title="Page Title"/></ac:link>
```

## Output Format Details

### compact
```
CREATED|{page_id}|{title}|{space_key}
URL:{confluence_url}
```

### text
```
Page Created: {title}
ID: {page_id}
Space: {space_key}
Parent ID: {parent_id}  (if applicable)
URL: {confluence_url}
```

### json
```json
{
  "id": "page_id",
  "title": "Page Title",
  "space": "SPACEKEY",
  "parentId": "parent_id",
  "url": "https://..."
}
```

## Error Codes

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success - page created |
| 1 | Error - space not found, parent not found, or API error |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CONFLUENCE_BASE_URL` | Yes | Confluence instance URL |
| `CONFLUENCE_EMAIL` | Yes | Atlassian account email |
| `CONFLUENCE_API_TOKEN` | Yes | API token from Atlassian account settings |
