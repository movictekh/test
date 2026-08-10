export function withOptionalSearchValue<Search extends object, Key extends keyof Search>(
  key: Key,
  value: Search[Key] | '' | null | undefined,
): Partial<Search> {
  const next: Partial<Search> = {}
  if (value === '' || value == null) return next
  next[key] = value
  return next
}

export function withoutSearchKeys<Search extends object>(
  previous: Search,
  keys: Array<keyof Search>,
): Search {
  const next = { ...previous }
  for (const key of keys) {
    delete next[key]
  }
  return next
}
