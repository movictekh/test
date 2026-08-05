import { createElement } from 'react'
import type { Preview } from '@storybook/react-vite'
import { SkeletonTheme } from 'react-loading-skeleton'

import '../src/styles/index.css'
import '@fontsource-variable/inter'

const preview: Preview = {
  tags: ['autodocs'],
  decorators: [
    (Story) =>
      createElement(
        SkeletonTheme,
        {
          baseColor: 'var(--app-surface-subtle)',
          highlightColor: 'var(--app-surface)',
          borderRadius: '0.375rem',
        },
        createElement(Story),
      ),
  ],
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    a11y: {
      test: 'todo',
    },
    backgrounds: {
      default: 'application',
      values: [
        {
          name: 'application',
          value: '#f3f5f9',
        },
        {
          name: 'surface',
          value: '#ffffff',
        },
      ],
    },
  },
}

export default preview
