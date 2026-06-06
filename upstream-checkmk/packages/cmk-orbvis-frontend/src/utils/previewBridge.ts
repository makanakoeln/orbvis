export const PREVIEW_EDIT = 'orbvis-preview-edit'
export const PREVIEW_READY = 'orbvis-preview-ready'

export type PreviewEditMessage = {
  source: typeof PREVIEW_EDIT
  patch: Record<string, unknown>
}

export type PreviewReadyMessage = {
  source: typeof PREVIEW_READY
}
