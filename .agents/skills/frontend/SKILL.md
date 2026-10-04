---
name: frontend-workflow
description: >-
  Standard workflow and guidelines for the Next.js React frontend of the ExamSentinel project. Use this when modifying or creating frontend UI components, pages, or state management.
---

# Frontend Guidelines for ExamSentinel

1. **Framework & Stack**: Next.js 14 App Router, React 18, Tailwind CSS.
2. **Icons**: Use `lucide-react` for all iconography.
3. **API Client**: Always use `apiClient.get()`, `apiClient.post()`, `apiClient.put()`, `apiClient.delete()` from `@/services/apiClient` instead of raw `fetch`.
4. **State Management**: Use standard React hooks (`useState`, `useEffect`, `useCallback`). 
5. **Styling**: Use standard Tailwind utility classes.
6. **No Mock Data**: Do not hardcode mock arrays. Handle empty states gracefully (e.g. `setItems(Array.isArray(data) ? data : [])`).

