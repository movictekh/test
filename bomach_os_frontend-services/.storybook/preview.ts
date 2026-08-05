import type { Preview } from '@storybook/react-vite'

import '../src/styles/index.css'
import '@fontsource-variable/inter'

const preview: Preview = {
  tags: ['autodocs'],
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
