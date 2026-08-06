# CSS Architecture Standard

## Product-oriented structure

Permanent UI files must use product-oriented folders:

```text
screens/
components/
editors/
styles/
api/
mocks/
types/
```

Do not keep production screens under folders or names such as:

```text
prototype
exact
temporary
demo
sample
```

## CSS ownership

Create a CSS file only when it owns a meaningful collection of related rules.

For Service Administration:

```text
src/modules/service-administration/styles/service-administration.css
```

owns the shared visual rules for its catalogue, calculator, form builder, workflow designer and branch activation screens.

Do not create one tiny CSS file for every TSX file by default.

## Inline styles

Do not use JSX inline-style objects for normal design.

Prefer finite CSS state classes such as:

```text
service-admin-service-icon--real-estate
service-admin-service-icon--engineering
service-admin-service-icon--survey
service-admin-service-icon--ict
```

Inline styles are reserved for genuinely calculated runtime values that cannot reasonably be represented by known classes.

## Reuse hierarchy

1. Existing shared component that already matches the HTML.
2. Module-level reusable CSS class.
3. Screen-specific class in the module stylesheet.
4. Small utility class for minor layout.
5. Inline style only as a last resort.

## Naming

Use product-scoped class names:

```text
service-admin-*
dashboard-*
commercial-flow-*
fulfilment-*
client-portal-*
```

Avoid permanent class names such as:

```text
prototype-*
exact-*
temp-*
demo-*
```

## HTML fidelity

CSS organization must not change:

- dimensions;
- spacing;
- colours;
- typography;
- card hierarchy;
- table composition;
- responsive behaviour;
- interaction states.

The Service Operations HTML remains the visual source of truth.
