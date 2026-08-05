import type { Meta, StoryObj } from '@storybook/react-vite'

import { Card, CardContent } from '@/shared/ui/card'

import { Tabs, TabsContent, TabsList, TabsTrigger } from './Tabs'

function TabsDemo() {
  return (
    <Card className="m-6 max-w-3xl">
      <CardContent className="p-5">
        <Tabs defaultValue="overview">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="activities">Activities</TabsTrigger>
            <TabsTrigger value="files">Files</TabsTrigger>
          </TabsList>
          <TabsContent value="overview">Request summary content.</TabsContent>
          <TabsContent value="activities">Communication and activity history.</TabsContent>
          <TabsContent value="files">Client and internal documents.</TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

const meta = {
  title: 'Shared/Tabs',
  component: TabsDemo,
} satisfies Meta<typeof TabsDemo>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {}
