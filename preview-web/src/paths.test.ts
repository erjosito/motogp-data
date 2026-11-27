import { describe, expect, it } from 'vitest'
import { appPath } from './paths'

describe('paddock paths', () => {
  it('keeps APIs inside the prefix without stealing similar classic paths', () => {
    expect(appPath('/api/seasons', '/paddock/')).toBe('/paddock/api/seasons')
    expect(appPath('/api/seasons', '/paddock')).toBe('/paddock/api/seasons')
    expect(appPath('/api/seasons', '/paddock-other')).toBe('/api/seasons')
    expect(appPath('/api/seasons', '/')).toBe('/api/seasons')
  })
})
