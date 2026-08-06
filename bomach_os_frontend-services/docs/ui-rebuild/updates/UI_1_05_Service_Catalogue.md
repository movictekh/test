# UI-1.05 — Service Catalogue Completion

## Source of truth

This implementation follows the Service Operations HTML catalogue, Configure Service modal and six-step Create & Activate Service wizard.

The HTML defines:

- catalogue filters;
- Branch Availability action;
- Create Service action;
- Configure and Duplicate actions;
- Configure tabs: Overview, Sub-services, Pricing, Request Form and Workflow;
- wizard steps: Basic, Sub-services, Pricing, Request Form, Workflow and Publish.

## Implemented

### Create & Activate Service wizard

The wizard now captures:

1. Basic service information.
2. Sub-services.
3. Pricing method and commercial controls.
4. Required request fields.
5. Workflow stages.
6. Branch activation and publication status.

Creating a service also creates linked mock records for:

- calculator;
- request form;
- workflow;
- branch activations.

### Configure Service workspace

The Configure action now opens the HTML-matched wide modal with:

- Overview;
- Sub-services;
- Pricing;
- Request Form;
- Workflow.

Saving updates the service and linked mock records through the API/Query flow.

### Reuse

The update keeps:

- existing Service Catalogue screen;
- TanStack Query;
- API client;
- MSW;
- mutable mock database;
- toast feedback;
- module stylesheet.

A shared Service Administration modal shell is introduced because both the wizard and configuration workspace use the same HTML modal structure.

## CSS ownership

All new visual rules remain in:

```text
src/modules/service-administration/styles/service-administration.css
```

No small one-off stylesheet was created.

No normal JSX inline-style object was introduced.

## Backend status

The wizard and configuration endpoints are frontend-owned mock contracts:

```text
POST /api/v1/ui-prototype/service-administration/services/wizard
PUT  /api/v1/ui-prototype/service-administration/services/{serviceId}
```

They follow the HTML design regardless of current backend coverage.

## Remaining after UI-1.05

- exact Calculator editor;
- exact Request Form editor;
- exact Workflow editor;
- Branch Activation literal screen;
- Command Center and shell parity;
- tests and screenshot sign-off.

## Configure Service pixel-match correction

The Configure Service popup was reviewed again against the literal HTML renderer.

The HTML behaviour is:

- open a wide `xl` modal;
- show five tab labels;
- keep Overview visually selected;
- render the Overview form directly below the tabs;
- render Sub-services and Assigned calculator in a two-column notice row;
- render Request fields in a yellow notice;
- render Workflow in a blue notice;
- Cancel closes the modal;
- Save Configuration updates only the editable Overview fields.

The HTML does not attach tab-switch actions to the five tab labels in this popup. The earlier React version made those tabs interactive and rendered extra editing screens, which was not a literal match.

This correction removes that invented behaviour and reproduces the HTML structure and interaction model exactly.

CSS remains in:

```text
src/modules/service-administration/styles/service-administration.css
```

No inline style object and no additional CSS file were introduced.
