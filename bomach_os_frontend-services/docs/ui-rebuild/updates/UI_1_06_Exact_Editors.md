# UI-1.06 — Exact Editors

## UI-1.05 status

UI-1.05 is complete enough to close as the Service Catalogue slice:

- catalogue screen follows the HTML card and filter structure;
- Create & Activate Service wizard exists;
- Configure Service popup follows the literal HTML overview layout;
- modal CSS variables are correctly scoped;
- service creation and configuration use Query, API client and MSW.

Stage 1 is not complete because UI-1.06 through UI-1.09 remain.

## UI-1.06 implementation

### Calculator editor

The previous interpreted editor has been replaced by the compact HTML modal:

- Name;
- Service;
- Template;
- Formula;
- Deposit;
- Tax;
- field-definition textarea;
- Cancel;
- Create/Save Calculator.

### Request Form Builder

The main builder now follows the HTML screenshot:

- 260px Field Palette;
- dashed add-field buttons;
- Save Form;
- Service Request Form Builder canvas;
- service selector;
- compact field rows;
- Edit and Delete actions.

### Request Form editor

The standalone editor uses the same compact modal language and persists through the existing request-form mutation.

### Workflow editor

The workflow editor now uses the compact modal language, line-based stage configuration and a lifecycle preview matching the HTML visual language.

## Architecture

No extra stylesheet was created. All rules remain in:

```text
src/modules/service-administration/styles/service-administration.css
```

The existing TanStack Query, API client, MSW, typed contracts and toast feedback remain in place.

## Remaining Stage 1 slices

- UI-1.07 — Branch Activation;
- UI-1.08 — Command Center and shell fidelity;
- UI-1.09 — states, tests, screenshot comparison and sign-off.
