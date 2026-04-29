// 백엔드와 통신하는 공용 헬퍼

export async function fetchHealth() {
  const r = await fetch('/api/health')
  if (!r.ok) throw new Error('health failed')
  return r.json()
}

export async function listWorks({ limit = 0, offset = 0, q = '' } = {}) {
  const params = new URLSearchParams()
  if (limit) params.set('limit', String(limit))
  if (offset) params.set('offset', String(offset))
  if (q) params.set('q', q)
  const r = await fetch(`/api/works?${params}`)
  if (!r.ok) throw new Error(`listWorks ${r.status}`)
  return r.json()
}

export async function getWork(relicId) {
  const r = await fetch(`/api/works/${relicId}`)
  if (!r.ok) throw new Error(`getWork ${r.status}`)
  return r.json()
}

// SSE 스트리밍 코스 빌더
export async function streamPlan(payload, callbacks = {}) {
  const { onCandidates, onToken, onError, signal } = callbacks
  const resp = await fetch('/api/plan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
  if (!resp.ok || !resp.body) {
    onError?.(`HTTP ${resp.status}`)
    return
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  const SEP = /\r\n\r\n|\n\n|\r\r/
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let m
    while ((m = SEP.exec(buffer))) {
      const raw = buffer.slice(0, m.index)
      buffer = buffer.slice(m.index + m[0].length)
      const ev = parseSSE(raw)
      if (!ev) continue
      if (ev.event === 'candidates') {
        try { onCandidates?.(JSON.parse(ev.data)) } catch { /* ignore */ }
      } else if (ev.event === 'token') {
        onToken?.(ev.data)
      } else if (ev.event === 'error') {
        onError?.(ev.data)
        return
      } else if (ev.event === 'done') {
        return
      }
    }
  }
}

// SSE 스트리밍 챗
export async function streamChat(query, mode, callbacks = {}) {
  const { onSources, onToken, onError, signal } = callbacks
  const resp = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, mode, k: 5 }),
    signal,
  })
  if (!resp.ok || !resp.body) {
    onError?.(`HTTP ${resp.status}`)
    return
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  const SEP = /\r\n\r\n|\n\n|\r\r/
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let m
    while ((m = SEP.exec(buffer))) {
      const raw = buffer.slice(0, m.index)
      buffer = buffer.slice(m.index + m[0].length)
      const ev = parseSSE(raw)
      if (!ev) continue
      if (ev.event === 'sources') {
        try {
          onSources?.(JSON.parse(ev.data))
        } catch {
          /* ignore */
        }
      } else if (ev.event === 'token') {
        onToken?.(ev.data)
      } else if (ev.event === 'error') {
        onError?.(ev.data)
        return
      } else if (ev.event === 'done') {
        return
      }
    }
  }
}

function parseSSE(chunk) {
  const out = { event: 'message', data: '' }
  let hasData = false
  for (const line of chunk.split(/\r\n|\n|\r/)) {
    if (line.startsWith('event:')) out.event = line.slice(6).trim()
    else if (line.startsWith('data:')) {
      const part = line.slice(5).replace(/^ /, '')
      out.data = hasData ? out.data + '\n' + part : part
      hasData = true
    }
  }
  return hasData ? out : null
}
