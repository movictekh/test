import {
  IconFile,
  IconFileDescription,
  IconFileTypeDoc,
  IconFileTypePdf,
  IconPhoto,
} from '@tabler/icons-react'

export function FileTypeIcon({
  fileName,
  contentType,
  size = 16,
}: {
  fileName: string
  contentType: string
  size?: number
}) {
  const name = fileName.toLowerCase()
  const type = contentType.toLowerCase()

  if (type.startsWith('image/') || /\.(png|jpg|jpeg|gif|webp|svg)$/.test(name)) {
    return <IconPhoto size={size} />
  }
  if (type.includes('pdf') || name.endsWith('.pdf')) {
    return <IconFileTypePdf size={size} />
  }
  if (type.includes('word') || /\.(doc|docx)$/.test(name)) {
    return <IconFileTypeDoc size={size} />
  }
  if (type.includes('text') || /\.(txt|csv|rtf)$/.test(name)) {
    return <IconFileDescription size={size} />
  }
  return <IconFile size={size} />
}
