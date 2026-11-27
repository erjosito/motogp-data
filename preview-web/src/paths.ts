export function appPath(path: string, pathname = window.location.pathname) {
  return pathname === '/paddock' || pathname.startsWith('/paddock/')
    ? `/paddock${path}`
    : path
}
