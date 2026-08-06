# UI-1.03 — Literal HTML Translation Rule

## Decision

From this update onward, UI implementation must be a literal React translation of the Service Operations HTML prototype.

The prototype controls:

- screen composition;
- section order;
- card count;
- grid ratios;
- table columns;
- field placement;
- spacing;
- typography;
- button labels;
- action placement;
- modal width;
- responsive breakpoints;
- status treatment.

The frontend team must not replace a prototype screen with a cleaner or more generic interpretation.

## Reuse rule

Reuse is still required, but only where the prototype itself shares a visual pattern.

Appropriate reuse:

- prototype button;
- prototype card;
- prototype table;
- prototype field;
- prototype notice;
- prototype modal shell;
- prototype lifecycle step;
- shared Query/API/mock infrastructure;
- shared authentication and permissions.

Inappropriate reuse:

- forcing every screen into one generic SummaryStrip;
- forcing every screen into one generic card register;
- using a generic editor layout where the prototype has a different layout;
- changing the information hierarchy to fit an existing component.

## Exact CSS translated

A dedicated prototype stylesheet now reproduces the original HTML values for:

- colours;
- 13px cards;
- card shadows;
- 15px card padding;
- 12px/9px card headings;
- 2:1 calculator grid;
- three-column service catalogue;
- table dimensions;
- filter controls;
- form controls;
- notices;
- builder 260px/1fr layout;
- lifecycle steps;
- mobile breakpoints.

## Screens corrected in this update

### Service Catalogue

Now follows the prototype’s:

- single catalogue card;
- filter row;
- three-column service-card grid;
- 40px division icon;
- description height;
- status and metadata;
- footer actions;
- Configure and Duplicate placement.

### Calculator Library

Now follows the prototype’s exact main composition:

```text
2fr calculator table
+
1fr live calculator test
```

The table columns are:

```text
Calculator
Service
Template
Fields
Deposit
Approval
Action
```

The right panel includes:

- selected calculator name;
- numeric test fields;
- formula notice;
- estimated client price KPI.

### Request Form Builder

Now follows the prototype’s:

```text
260px field palette
+
1fr form canvas
```

### Workflow Designer

Now follows the prototype’s lifecycle sequence and stage table rather than the previously invented stacked editor-card page.

## Mock/API status

No backend shape controlled this design.

All data continues to arrive through the existing typed Query and mock API flow.

The rendering layer was corrected without removing:

- API functions;
- TanStack Query;
- mutations;
- mutable MSW state;
- types;
- editor save flows.

## Known remaining fidelity work

- translate the exact Branch Activation render function;
- translate the exact Configure Service modal tabs;
- translate the exact Create Service wizard steps;
- replace editor modal internals with their exact prototype modal bodies;
- run screenshot overlay comparisons at desktop, tablet and mobile sizes.

## Mandatory workflow for every remaining screen

1. locate the exact HTML render function;
2. copy its DOM hierarchy into a parity note;
3. extract the exact CSS classes and values;
4. build the React component with the same hierarchy;
5. connect existing typed data;
6. compare screenshots;
7. document any unavoidable difference.

No visual feature should be inferred from a feature description when the HTML already defines it.
