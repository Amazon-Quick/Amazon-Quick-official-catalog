# Component Library

Eight reusable presentation components. Each section shows the HTML pattern and required CSS. All components assume the design tokens from `design-tokens.md` are loaded.

---

## 1. Definition Block

A quote-style block with a purple left border. Use for key definitions, verbatim quotes, or thesis statements.

### HTML

```html
<div class="definition">
  <p>A skill is a self-contained instruction set that Quick loads on demand to perform a specific type of task.</p>
</div>

```

### CSS

```css
.definition {
  border-left: var(--border-thick) solid var(--primary);
  padding: var(--space-md) var(--space-lg);
  background: var(--primary-light);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  font-size: var(--fs-body);
  line-height: var(--lh-relaxed);
  margin: var(--space-md) 0;
}
.definition p {
  margin: 0;
  color: var(--text);
}

```

### Variants

- Add `font-style: italic;` for attributed quotes
- Add a `<cite>` element below the paragraph for source attribution

---

## 2. Data Table

Rows of field/value pairs with optional badges. Use for specifications, metadata, feature comparisons.

### HTML

```html
<table class="frontmatter-table">
  <thead>
    <tr><th>Field</th><th>Purpose</th><th>Status</th></tr>
  </thead>
  <tbody>
    <tr>
      <td class="field">name</td>
      <td>Unique skill identifier</td>
      <td><span class="badge green">Required</span></td>
    </tr>
    <tr>
      <td class="field">description</td>
      <td>What the skill does (shown during discovery)</td>
      <td><span class="badge green">Required</span></td>
    </tr>
    <tr>
      <td class="field">tools</td>
      <td>Which tools the skill needs access to</td>
      <td><span class="badge blue">Optional</span></td>
    </tr>
  </tbody>
</table>

```

### CSS

```css
.frontmatter-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: var(--fs-small);
  margin: var(--space-md) 0;
}
.frontmatter-table th {
  text-align: left;
  padding: var(--space-sm) var(--space-md);
  background: var(--primary-light);
  font-weight: var(--fw-semi);
  color: var(--primary);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.frontmatter-table th:first-child { border-radius: var(--radius-sm) 0 0 0; }
.frontmatter-table th:last-child { border-radius: 0 var(--radius-sm) 0 0; }
.frontmatter-table td {
  padding: var(--space-sm) var(--space-md);
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}
.frontmatter-table .field {
  font-family: var(--font-mono);
  font-size: var(--fs-mono);
  font-weight: var(--fw-semi);
  color: var(--dark);
}
.badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.72rem;
  font-weight: var(--fw-semi);
}
.badge.green { background: var(--badge-green); color: var(--badge-green-text); }
.badge.blue { background: var(--badge-blue); color: var(--badge-blue-text); }
.badge.orange { background: var(--badge-orange); color: var(--badge-orange-text); }

```

---

## 3. Card Grid

Equal-width cards arranged in columns. Use for agenda items, feature categories, tool types.

### HTML

```html
<div class="card-grid" style="grid-template-columns: repeat(3, 1fr);">
  <div class="card">
    <div class="card-num">1</div>
    <div class="card-label">Skills</div>
  </div>
  <div class="card">
    <div class="card-num">2</div>
    <div class="card-label">Agents</div>
  </div>
  <div class="card">
    <div class="card-num">3</div>
    <div class="card-label">Tools</div>
  </div>
</div>

```

### CSS

```css
.card-grid {
  display: grid;
  gap: var(--space-md);
  margin: var(--space-lg) 0;
}
.card {
  background: var(--white);
  border: var(--border-width) solid var(--border-accent);
  border-radius: var(--radius);
  padding: var(--space-lg) var(--space-md);
  box-shadow: var(--shadow);
  text-align: center;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-hover);
}
.card-num {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-round);
  background: var(--primary-gradient);
  color: var(--white);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: var(--fw-bold);
  font-size: var(--fs-small);
  margin: 0 auto var(--space-sm);
}
.card-label {
  font-size: var(--fs-body);
  font-weight: var(--fw-semi);
  color: var(--text);
}

```

### Variants

- **2-column**: `grid-template-columns: repeat(2, 1fr);`
- **4-column**: `grid-template-columns: repeat(4, 1fr);`
- **With icons**: Replace `.card-num` with an inline SVG icon
- **Agenda style**: Use `.agenda-grid` class with numbered squares

---

## 4. Flow Row

Connected cards with arrows showing a process or sequence. Use for progressive disclosure, workflows, timelines.

### HTML

```html
<div class="flow-row">
  <div class="flow-card">
    <div class="flow-num">1</div>
    <h4>Discovery</h4>
    <p>Name and description visible to the agent</p>
  </div>
  <div class="flow-arrow">
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M5 12h14M12 5l7 7-7 7"/>
    </svg>
  </div>
  <div class="flow-card">
    <div class="flow-num">2</div>
    <h4>Activation</h4>
    <p>Full instructions loaded into context</p>
  </div>
  <div class="flow-arrow">
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M5 12h14M12 5l7 7-7 7"/>
    </svg>
  </div>
  <div class="flow-card">
    <div class="flow-num">3</div>
    <h4>Execution</h4>
    <p>Tools invoked, work performed</p>
  </div>
</div>

```

### CSS

```css
.flow-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin: var(--space-lg) 0;
}
.flow-card {
  flex: 1;
  background: var(--white);
  border: var(--border-width) solid var(--border-accent);
  border-radius: var(--radius);
  padding: var(--space-md);
  text-align: center;
  box-shadow: var(--shadow);
}
.flow-card h4 {
  margin: var(--space-sm) 0 var(--space-xs);
  font-size: var(--fs-body);
  color: var(--primary);
}
.flow-card p {
  margin: 0;
  font-size: var(--fs-small);
  color: var(--text-muted);
}
.flow-num {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-round);
  background: var(--primary-gradient);
  color: var(--white);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: var(--fw-bold);
}
.flow-arrow {
  color: var(--primary);
  flex-shrink: 0;
}

```

---

## 5. Contrast Pair

Two cards side by side for comparing concepts. Use for "this vs that", "before/after", "agent vs automation".

### HTML

```html
<div class="contrast-box">
  <div class="contrast-item">
    <h3>Agents</h3>
    <p>Reason, adapt, decide</p>
    <p class="small-text">Dynamic inputs, autonomous action</p>
  </div>
  <div class="contrast-item">
    <h3>Automations</h3>
    <p>Follow rules, execute steps</p>
    <p class="small-text">Predictable, consistent, fast</p>
  </div>
</div>

```

### CSS

```css
.contrast-box {
  display: flex;
  gap: var(--space-lg);
  margin: var(--space-lg) 0;
}
.contrast-item {
  flex: 1;
  background: var(--white);
  border: var(--border-width) solid var(--border-accent);
  border-radius: var(--radius);
  padding: var(--space-lg);
  box-shadow: var(--shadow);
}
.contrast-item h3 {
  color: var(--primary);
  font-size: var(--fs-section);
  margin: 0 0 var(--space-sm);
}
.contrast-item p {
  margin: var(--space-xs) 0;
  font-size: var(--fs-body);
  color: var(--text);
}
.small-text {
  font-size: var(--fs-small);
  color: var(--text-muted);
}

```

---

## 6. Callout

A small highlighted note or aside. Use for important caveats, tips, or contextual information.

### HTML

```html
<div class="callout">
  <strong>Note:</strong> Skills are loaded on demand. The agent only pays the context cost when a skill is actually activated.
</div>

```

### CSS

```css
.callout {
  background: var(--primary-light);
  border-radius: var(--radius-sm);
  padding: var(--space-sm) var(--space-md);
  font-size: var(--fs-small);
  color: var(--text);
  margin: var(--space-md) 0;
  border: 1px solid var(--border-accent);
}
.callout strong {
  color: var(--primary);
}

```

---

## 7. SVG Tree Diagram

Inline SVG showing hierarchical relationships. Use for composition models, org charts, architecture diagrams.

### HTML Pattern

```html
<div class="diagram-container">
  <svg viewBox="0 0 600 300" xmlns="http://www.w3.org/2000/svg" style="width:100%; max-width:600px;">
    <!-- Root node -->
    <rect x="230" y="20" width="140" height="40" rx="8" fill="#6B2FA0"/>
    <text x="300" y="45" text-anchor="middle" fill="white" font-size="14" font-weight="600">Agent</text>
    <!-- Connector lines -->
    <line x1="300" y1="60" x2="300" y2="80" stroke="#6B2FA0" stroke-width="2"/>
    <line x1="100" y1="80" x2="500" y2="80" stroke="#6B2FA0" stroke-width="2"/>
    <line x1="100" y1="80" x2="100" y2="100" stroke="#6B2FA0" stroke-width="2"/>
    <line x1="300" y1="80" x2="300" y2="100" stroke="#6B2FA0" stroke-width="2"/>
    <line x1="500" y1="80" x2="500" y2="100" stroke="#6B2FA0" stroke-width="2"/>
    <!-- Child nodes -->
    <rect x="40" y="100" width="120" height="36" rx="8" fill="none" stroke="#6B2FA0" stroke-width="2"/>
    <text x="100" y="123" text-anchor="middle" fill="#1a1a2e" font-size="12" font-weight="600">Skills</text>
    <rect x="240" y="100" width="120" height="36" rx="8" fill="none" stroke="#6B2FA0" stroke-width="2"/>
    <text x="300" y="123" text-anchor="middle" fill="#1a1a2e" font-size="12" font-weight="600">Tools</text>
    <rect x="440" y="100" width="120" height="36" rx="8" fill="none" stroke="#6B2FA0" stroke-width="2"/>
    <text x="500" y="123" text-anchor="middle" fill="#1a1a2e" font-size="12" font-weight="600">Knowledge</text>
  </svg>
</div>

```

### CSS

```css
.diagram-container {
  display: flex;
  justify-content: center;
  margin: var(--space-lg) 0;
}
.diagram-container svg {
  max-height: 300px;
}

```

### Guidelines

- Use `viewBox` for scalable sizing; set width via CSS (max-width)
- Root nodes: filled with `--primary`, white text
- Child nodes: stroke only (outline), dark text
- Connector lines: `stroke-width="2"`, brand color
- Font: system sans-serif at 12-14px
- Rounded corners on all rects: `rx="8"`

---

## 8. QR Code Group

Multiple QR codes side by side with labels. Use for call-to-action slides, resource links.

### HTML

```html
<div class="qr-group">
  <div class="qr-item">
    <img class="qr-img" src="data:image/svg+xml;base64,..." alt="QR code"/>
    <span class="qr-label">Visit the catalog</span>
  </div>
  <div class="qr-item">
    <img class="qr-img" src="data:image/svg+xml;base64,..." alt="QR code"/>
    <span class="qr-label">Join the channel</span>
  </div>
  <div class="qr-item">
    <img class="qr-img" src="data:image/svg+xml;base64,..." alt="QR code"/>
    <span class="qr-label">Contribute a skill</span>
  </div>
</div>

```

### CSS

```css
.qr-group {
  display: flex;
  justify-content: center;
  gap: var(--space-xl);
  margin: var(--space-lg) 0;
}
.qr-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm);
}
.qr-img {
  width: 120px;
  height: 120px;
  border: var(--border-width) solid var(--border-accent);
  border-radius: var(--radius-sm);
  padding: var(--space-sm);
  background: var(--white);
}
.qr-label {
  font-size: var(--fs-small);
  font-weight: var(--fw-semi);
  color: var(--text);
}

```

---

## Composition Guidelines

- Use 1-2 components per content slide (max 3 for dense slides)
- Stack vertically with consistent margins (var(--space-lg) between components)
- Always wrap in the slide's max-width container
- Components inherit the slide's font sizing; do not override per-instance
- Prefer semantic HTML (table for tabular data, list for sequences) over generic divs
